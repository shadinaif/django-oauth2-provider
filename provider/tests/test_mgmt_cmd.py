"""
Unittests for testing management commands.
"""
import logging
import mock
import unittest
from datetime import datetime, timedelta
from django.core.management import call_command
from django.core.management.base import CommandError
from provider.management.commands.delete_expired_grant_tokens import Command
from provider.oauth2.models import Grant

log = logging.getLogger(__name__)


class TestDeleteExpiredGrantTokens(unittest.TestCase):
    """
    Tests for the `delete_expired_grant_tokens` management command.
    """
    def setUp(self):
        super(TestDeleteExpiredGrantTokens, self).setUp()
        self.command = Command()
        self.command_name = "delete_expired_grant_tokens"
        # Make some expired grant tokens.
        expire_time = datetime.now() - timedelta(4)
        log.info("Creating 10 tokens expiring on %s.", expire_time)
        for i in range(0, 10):
            Grant.objects.create(expires=expire_time, client_id=9, user_id=14)
        # Make some non-expired grant tokens.
        expire_time = datetime.now() + timedelta(4)
        log.info("Creating 10 tokens expiring on %s.", expire_time)
        for i in range(0, 10):
            Grant.objects.create(expires=expire_time, client_id=10, user_id=15)

    def tearDown(self):
        super(TestDeleteExpiredGrantTokens, self).tearDown()
        # Remove ALL grant tokens.
        Grant.objects.all().delete()

    def test_negative_chunk_arg(self):
        errstring = "Only positive chunk size is allowed"
        with self.assertRaisesRegexp(CommandError, errstring):
            self.command.handle(self.command_name, chunk_size=-1000)

    def test_zero_chunk_arg(self):
        errstring = "Only positive chunk size is allowed"
        with self.assertRaisesRegexp(CommandError, errstring):
            self.command.handle(self.command_name, chunk_size=0)

    def test_negative_sleep_arg(self):
        errstring = "Only non-negative sleep between seconds is allowed"
        with self.assertRaisesRegexp(CommandError, errstring):
            self.command.handle(self.command_name, sleep_between=-5.5)

    def test_single_chunk_delete(self):
        call_command(self.command_name)
        self.assertEqual(Grant.objects.all().count(), 10)

    def test_multiple_chunk_delete(self):
        Command.CHUNK_SIZE = 2
        call_command(self.command_name)
        self.assertEqual(Grant.objects.all().count(), 10)

