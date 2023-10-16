"""
Test custom Django management commands.
"""
from django.core.management import call_command
from django.db.utils import OperationalError
from django.test import SimpleTestCase

from unittest.mock import patch
from psycopg2 import OperationalError as Psycopg2OpError


# mock the behaviour of wait_for_db management command:
@patch('core.management.commands.wait_for_db.Command.check')
class CommandTests(SimpleTestCase):
    """
    Test commands.
    """

    def test_wait_for_db_ready(self, patched_check):
        """
        Test waiting for database if database is ready.
        """
        # we assume that there are no exceptions:
        patched_check.return_value = True
        call_command('wait_for_db')
        # test for calling the wait_for_db command only once with our default database:
        patched_check.assert_called_once_with(databases=['default'])

    # to avoid slowing down the tests, mock the behaviour of sleep command.
    @patch('time.sleep')
    def test_wait_for_db_delay(self, patched_sleep, patched_check):
        """
        Test waiting for database when getting OperationalError.
        """
        # simulating two different errors for 5 times:
        patched_check.side_effect = [Psycopg2OpError] * 2 + [OperationalError] * 3 + \
            [True]  # sixth time, returning true.
        call_command('wait_for_db')
        # because we are raising the first two exceptions, then three more exceptions,
        # and then the sixth time we're returning a value, we would except it to call
        # the check method six times:
        self.assertEqual(patched_check.call_count, 6)
        # test for calling the wait_for_db command multiple times with our default
        # database:
        patched_check.assert_called_with(databases=['default'])
