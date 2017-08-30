"""
Command to delete expired OAuth2 grant tokens from the oauth2_grant table.
"""

from datetime import datetime
import logging
import time
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Min, Max
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

        delete_date = datetime.now()
        total_expired_tokens = Grant.objects.filter(expires__lte=delete_date).count()
        ids = Grant.objects.all().aggregate(Min('id'), Max('id'))
        min_id = ids['id__min']
        max_id = ids['id__max']

        log.info(
            "STARTED: Deleting %s expired grant tokens older than '%s' w/ chunk size of %s and %s secs between chunks. "
            "Ids are %s - %s.",
            total_expired_tokens, delete_date, chunk_size, sleep_between, min_id, max_id
            )

        while True:
            log.info("Deleting up to %s expired tokens with id <= %s", chunk_size, min_id+chunk_size)
            with transaction.atomic():
                Grant.objects.filter(id__lte=min_id+chunk_size, expires__lte=delete_date).delete()

            min_id += chunk_size
            if min_id > max_id:
                break

            log.info("Sleeping %s seconds...", sleep_between)
            time.sleep(sleep_between)

        log.info("FINISHED: Deleted %s expired grant tokens total.", total_expired_tokens)
