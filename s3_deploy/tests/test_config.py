
import unittest
from datetime import timedelta

from s3_deploy import config


class DurationConversionTest(unittest.TestCase):
    def test_duration_numeric(self):
        td = config.timedelta_from_duration_string('600')
        self.assertEqual(td, timedelta(seconds=600))

    def test_duration_seconds(self):
        td = config.timedelta_from_duration_string('10 seconds')
        self.assertEqual(td, timedelta(seconds=10))

    def test_duration_one_second(self):
        td = config.timedelta_from_duration_string('1 second')
        self.assertEqual(td, timedelta(seconds=1))

    def test_duration_minutes(self):
        td = config.timedelta_from_duration_string('45 minutes')
        self.assertEqual(td, timedelta(minutes=45))

    def test_duration_hours(self):
        td = config.timedelta_from_duration_string('3 hours')
        self.assertEqual(td, timedelta(hours=3))

    def test_duration_days(self):
        td = config.timedelta_from_duration_string('7 days')
        self.assertEqual(td, timedelta(days=7))

    def test_duration_months(self):
        td = config.timedelta_from_duration_string('1 month')
        self.assertEqual(td, timedelta(days=30))

    def test_duration_years(self):
        td = config.timedelta_from_duration_string('20 years')
        self.assertEqual(td, timedelta(days=(365 * 20)))

    def test_duration_composite(self):
        td = config.timedelta_from_duration_string(
            '1 hour, 45 minutes, 30 seconds')
        self.assertEqual(td, timedelta(hours=1, minutes=45, seconds=30))

    def test_duration_invalid_negative(self):
        with self.assertRaises(ValueError):
            config.timedelta_from_duration_string('-45 hours')


class ResolveCacheRulesTest(unittest.TestCase):
    def test_resolve_empty(self):
        cache = config.resolve_cache_rules('test', [])
        self.assertIsNone(cache)

    def test_resolve_catch_all_to_cache_control(self):
        cache = config.resolve_cache_rules('test', [
            {'match': '*', 'cache_control': 'public, maxage=500'}
        ])
        self.assertEqual(cache, 'public, maxage=500')

    def test_resolve_catch_all_to_maxage_integer(self):
        cache = config.resolve_cache_rules('test', [
            {'match': '*', 'maxage': 3600}
        ])
        self.assertEqual('maxage=3600', cache)

    def test_resolve_catch_all_to_maxage_string(self):
        cache = config.resolve_cache_rules('test', [
            {'match': '*', 'maxage': '1 hour'}
        ])
        self.assertEqual('maxage=3600', cache)

    def test_resolve_catch_all_to_both(self):
        cache = config.resolve_cache_rules('test', [
            {'match': '*', 'cache_control': 'public', 'maxage': '1 hour'}
        ])
        self.assertEqual('public, maxage=3600', cache)

    def test_resolve_catch_all_to_none(self):
        cache = config.resolve_cache_rules('test', [
            {'match': '*'}
        ])
        self.assertIsNone(cache)

    def test_resolve_no_rules(self):
        cache = config.resolve_cache_rules('test', [
            {'match': 'test1'},
            {'match': 'test2'}
        ])
        self.assertIsNone(cache)

    def test_resolve_second_rule(self):
        cache = config.resolve_cache_rules('test', [
            {'match': 'other/*', 'maxage': 100},
            {'match': 'test', 'maxage': 200},
            {'match': '*', 'maxage': 300}
        ])
        self.assertEqual(cache, 'maxage=200')
