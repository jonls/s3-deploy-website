
import unittest
from datetime import timedelta

from s3_deploy.deploy import timedelta_from_duration_string


class DurationConversionTest(unittest.TestCase):
    def test_duration_numeric(self):
        td = timedelta_from_duration_string('600')
        self.assertEqual(td, timedelta(seconds=600))

    def test_duration_seconds(self):
        td = timedelta_from_duration_string('10 seconds')
        self.assertEqual(td, timedelta(seconds=10))

    def test_duration_one_second(self):
        td = timedelta_from_duration_string('1 second')
        self.assertEqual(td, timedelta(seconds=1))

    def test_duration_minutes(self):
        td = timedelta_from_duration_string('45 minutes')
        self.assertEqual(td, timedelta(minutes=45))

    def test_duration_hours(self):
        td = timedelta_from_duration_string('3 hours')
        self.assertEqual(td, timedelta(hours=3))

    def test_duration_days(self):
        td = timedelta_from_duration_string('7 days')
        self.assertEqual(td, timedelta(days=7))

    def test_duration_months(self):
        td = timedelta_from_duration_string('1 month')
        self.assertEqual(td, timedelta(days=30))

    def test_duration_years(self):
        td = timedelta_from_duration_string('20 years')
        self.assertEqual(td, timedelta(days=(365 * 20)))

    def test_duration_composite(self):
        td = timedelta_from_duration_string('1 hour, 45 minutes, 30 seconds')
        self.assertEqual(td, timedelta(hours=1, minutes=45, seconds=30))
