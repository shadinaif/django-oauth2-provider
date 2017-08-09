"""
Command to delete expired OAuth2 grant tokens from the oauth2_grant table.
"""

from datetime import datetime, timedelta
import logging
import time
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from provider.oauth2.models import Grant

log = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Example usage: ./manage.py lms --settings=devstack delete_expired_grant_tokens.py
    """
    help = 'Deletes all expired OAuth2 grant tokens (in chunks).'

    # Default maximum number of expired tokens to delete in a single transaction.
    DEFAULT_CHUNK_SIZE = 10000

    # Default seconds to sleep between chunked deletes of expired tokens.
    DEFAULT_SLEEP_BETWEEN_DELETES = 0

    def add_arguments(self, parser):
        parser.add_argument(
            '--chunk_size',
            default=self.DEFAULT_CHUNK_SIZE,
            type=int,
            help='Maximum number of expired tokens to delete in one transaction.'
        )
        parser.add_argument(
            '--sleep_between',
            default=self.DEFAULT_SLEEP_BETWEEN_DELETES,
            type=float,
            help='Seconds to sleep between chunked delete of expired tokens.'
        )

    def handle(self, *args, **options):
        """
        Deletes expired oauth2_grant tokens, chunking the deletes to avoid long table/row locks.
        """
        # Process the command arguments.
        chunk_size = options.get('chunk_size', self.DEFAULT_CHUNK_SIZE)
        if chunk_size <= 0:
            raise CommandError('Only positive chunk size is allowed ({}).'.format(chunk_size))
        sleep_between = options.get('sleep_between', self.DEFAULT_SLEEP_BETWEEN_DELETES)
        if sleep_between < 0:
            raise CommandError('Only non-negative sleep between seconds is allowed ({}).'.format(sleep_between))

        table_name = 'oauth2_grant'
        delete_date = datetime.now()
        where_clause = "WHERE expires < '{}'".format(delete_date.strftime('%Y-%m-%d %H:%m:%S'))
        # The "as id" below fools Django raw query into thinking the primary key is being queried.
        total_expired_tokens = Grant.objects.raw(
            'SELECT COUNT(*) as id FROM {} {}'.format(table_name, where_clause)
        )[0].id
        log.info("STARTED: Deleting %s expired grant tokens older than '%s' with chunk size of %s and %s seconds between chunk.",
            total_expired_tokens, delete_date, chunk_size, sleep_between
        )

        total_deletions = 0
        while total_deletions < total_expired_tokens:
            deletions_now = min(chunk_size, total_expired_tokens - total_deletions)
            log.info("Deleting %s expired tokens...", deletions_now)
            with transaction.atomic():
                delete_sql = 'DELETE FROM {} WHERE id IN (SELECT id FROM {} {} LIMIT {})'.format(
                    table_name, table_name, where_clause, deletions_now
                )
                log.info(delete_sql)
                try:
                    list(Grant.objects.raw(delete_sql))
                except TypeError:
                    # The list() above is simply to get the RawQuerySet to be evaluated.
                    # Without evaluation, the raw DELETE SQL will *not* actually execute.
                    # But - it will cause a "TypeError: 'NoneType' object is not iterable" to be ignored.
                    pass
            total_deletions += deletions_now
            log.info("Sleeping %s seconds...", sleep_between)
            time.sleep(sleep_between)
        log.info("FINISHED: Deleted %s expired grant tokens total.", total_deletions)
