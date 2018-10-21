
from datetime import timedelta
import os
import shutil
import tempfile
import unittest

from mock import patch, call

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

    def test_resolve_no_match_key(self):
        with self.assertRaises(ValueError):
            config.resolve_cache_rules('test', [
                {'maxage': 3000},
            ])

    def test_resolve_catch_all_to_cache_control(self):
        cache = config.resolve_cache_rules('test', [
            {'match': '*', 'cache_control': 'public, maxage=500'}
        ])
        self.assertEqual(cache, 'public, maxage=500')

    def test_resolve_catch_all_to_maxage_integer(self):
        cache = config.resolve_cache_rules('test', [
            {'match': '*', 'maxage': 3600}
        ])
        self.assertEqual('max-age=3600', cache)

    def test_resolve_catch_all_to_maxage_string(self):
        cache = config.resolve_cache_rules('test', [
            {'match': '*', 'maxage': '1 hour'}
        ])
        self.assertEqual('max-age=3600', cache)

    def test_resolve_catch_all_to_both(self):
        cache = config.resolve_cache_rules('test', [
            {'match': '*', 'cache_control': 'public', 'maxage': '1 hour'}
        ])
        self.assertEqual('public, max-age=3600', cache)

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
        self.assertEqual(cache, 'max-age=200')

    def test_resolve_multiple_match_keys(self):
        with self.assertRaises(ValueError):
            config.resolve_cache_rules('test', [
                {'match': 'test*', 'match_regexp': 'test.*'},
            ])

    def test_resolve_regexp_match_key(self):
        cache = config.resolve_cache_rules('test', [
            {'match_regexp': 't[es]{2}(t|a)$', 'maxage': 100},
        ])
        self.assertEqual(cache, 'max-age=100')


class LoadConfigFileTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_load_config_from_path(self):
        path = os.path.join(self.tmp_dir, 'some_file_name')
        with open(path, 'w') as f:
            f.write('\n'.join([
                'site: _site',
                's3_bucket: example.com',
                'cloudfront_distribution_id: ABCDEFGHI',
                '',
                'cache_rules:',
                '- match: "/assets/*"',
                '  maxage: 30 days',
                '',
                '- match: "/css/*"',
                '  maxage: 30 days',
                '',
                '- match: "*"',
                '  maxage: 1 hour',
                '',
            ]))

        self.assertEqual(config._load_config_from_path(path), {
            'site': '_site',
            's3_bucket': 'example.com',
            'cloudfront_distribution_id': 'ABCDEFGHI',
            'cache_rules': [
                {
                    'match': '/assets/*',
                    'maxage': '30 days',
                },
                {
                    'match': '/css/*',
                    'maxage': '30 days',
                },
                {
                    'match': '*',
                    'maxage': '1 hour',
                },
            ]
        })

    @patch('os.path.isdir', return_value=False)
    @patch('s3_deploy.config._load_config_from_path')
    def test_load_config_file_from_absolute_path(self, mock_load, mock_is_dir):
        mocked_config_dict = {}
        mock_load.return_value = mocked_config_dict
        fake_path = os.path.join('path', 'to', 'some_file.ext')
        config_dict, base_path = config.load_config_file(fake_path)

        mock_load.assert_called_with(fake_path)
        self.assertEqual(config_dict, mocked_config_dict)
        self.assertEqual(base_path, os.path.join('path', 'to'))

    @patch('os.path.isdir', return_value=False)
    @patch('s3_deploy.config._load_config_from_path')
    def test_load_config_file_from_nonexisting_file(
            self, mock_load, mock_is_dir):
        mock_load.side_effect = IOError('Failed to load fake file')
        fake_path = os.path.join('path', 'to', 'some_file.ext')
        with self.assertRaises(IOError):
            config.load_config_file(fake_path)

        mock_load.assert_called_with(fake_path)

    @patch('os.path.isdir', return_value=True)
    @patch('s3_deploy.config._load_config_from_path')
    def test_load_config_file_from_directory(self, mock_load, mock_is_dir):
        mocked_config_dict = {}
        mock_load.return_value = mocked_config_dict
        fake_path = os.path.join('path', 'to', 'some', 'directory')
        config_dict, base_path = config.load_config_file(fake_path)

        mock_load.assert_called_once_with(
            os.path.join(fake_path, '.s3_website.yaml'))
        self.assertEqual(config_dict, mocked_config_dict)
        self.assertEqual(base_path, fake_path)

    @patch('os.path.isdir', return_value=True)
    @patch('s3_deploy.config._load_config_from_path')
    def test_load_config_file_from_directory_nonexisting(
            self, mock_load, mock_is_dir):
        mock_load.side_effect = IOError('Failed to load fake file')
        fake_path = os.path.join('path', 'to', 'directory')
        with self.assertRaises(ValueError):
            config.load_config_file(fake_path)

        mock_load.assert_has_calls([
            call(os.path.join(fake_path, '.s3_website.yaml')),
            call(os.path.join(fake_path, '.s3_website.yml'))
        ])
