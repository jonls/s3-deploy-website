
import os
import shutil
import tempfile
import time
import unittest

import boto3
import mock
from mock import call
from mock import patch
from moto import mock_s3

from s3_deploy import deploy


class KeyNameFromPathTest(unittest.TestCase):
    def test_base_path(self):
        key = deploy.key_name_from_path('index.html')
        self.assertEqual(key, 'index.html')

    def test_base_path_with_dot(self):
        path = os.path.join('.', 'index.html')
        key = deploy.key_name_from_path(path)
        self.assertEqual(key, 'index.html')

    def test_directory_path(self):
        path = os.path.join('directory', 'image.png')
        key = deploy.key_name_from_path(path)
        self.assertEqual(key, 'directory/image.png')

    def test_directory_path_with_dot(self):
        path = os.path.join('.', 'directory', 'image.png')
        key = deploy.key_name_from_path(path)
        self.assertEqual(key, 'directory/image.png')


@mock_s3
class UploadKeyTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

        self.s3 = boto3.resource('s3', region_name='us-east-1')
        self.bucket = self.s3.Bucket('test_bucket')
        self.bucket.create()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    @patch('mimetypes.guess_type', return_value=['text/plain'])
    def test_upload_key(self, mock_mime):
        file_contents = 'file contents\nanother line\n'
        file_path = os.path.join(self.tmp_dir, 'some_file')
        with open(file_path, 'w') as f:
            f.write(file_contents)

        obj = self.bucket.Object('some_file')

        deploy.upload_key(obj, file_path, {}, False)

        self.assertEqual(obj.content_type, 'text/plain')
        self.assertEqual(
            obj.get()['Body'].read().decode('utf-8'), file_contents)


@mock_s3
class MainDeployTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.site_dir = os.path.join(self.tmp_dir, '_site')
        os.mkdir(self.site_dir)

        now = time.time()
        past = now - 100000

        # Create existing file
        with open(os.path.join(self.site_dir, 'unchanged_file.txt'), 'w') as f:
            f.write('file contents\n')

        os.utime(
            os.path.join(self.site_dir, 'unchanged_file.txt'), (past, past))

        self.s3 = boto3.resource('s3', region_name='us-east-1')
        self.bucket = self.s3.Bucket('test_bucket')
        self.bucket.create()

        # Create uploaded files in bucket
        obj_1 = self.bucket.Object('unchanged_file.txt')
        obj_1.put(Body='file contents\n', ContentType='text/plain')

        obj_2 = self.bucket.Object('updated_file.txt')
        obj_2.put(Body='old contents\n', ContentType='text/plain')

        obj_3 = self.bucket.Object('deleted_file.txt')
        obj_3.put(Body='file contents\n', ContentType='text/plain')

        time.sleep(0.2)

        # Create updated files
        with open(os.path.join(self.site_dir, 'updated_file.txt'), 'w') as f:
            f.write('new contents\n')

        with open(os.path.join(self.site_dir, 'new_file.txt'), 'w') as f:
            f.write('new contents\n')

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def assert_upload_key_called_correctly(self, mock_upload, dry=False):
        """Assert that upload_key is called correctly."""
        mock_upload.assert_has_calls([
            call(
                mock.ANY, os.path.join(self.site_dir, path), [], dry,
                storage_class=deploy._STORAGE_STANDARD)
            for path in ['updated_file.txt', 'new_file.txt']
        ], any_order=True)

    @patch('s3_deploy.deploy.upload_key')
    @patch('s3_deploy.deploy.invalidate_paths')
    def test_deploy_without_cloudfront(self, mock_invalidate, mock_upload):
        deploy.deploy({
            's3_bucket': self.bucket.name,
            'site': '_site',
        }, self.tmp_dir, False, False)

        self.assert_upload_key_called_correctly(mock_upload, dry=False)
        mock_invalidate.assert_not_called()

    @patch('s3_deploy.deploy.upload_key')
    @patch('s3_deploy.deploy.invalidate_paths')
    def test_deploy_with_cloudfront(self, mock_invalidate, mock_upload):
        deploy.deploy({
            's3_bucket': self.bucket.name,
            'site': '_site',
            'cloudfront_distribution_id': 'ABCDEFGHI',
        }, self.tmp_dir, False, False)

        self.assert_upload_key_called_correctly(mock_upload, dry=False)

        expect_invalidated_paths = [
            '/deleted_file.txt',
            '/new_file.txt',
            '/updated_file.txt',
        ]
        mock_invalidate.assert_called_once_with(
            'ABCDEFGHI', expect_invalidated_paths, False)

    @patch('s3_deploy.deploy.upload_key')
    @patch('s3_deploy.deploy.invalidate_paths')
    def test_deploy_dry(self, mock_invalidate, mock_upload):
        deploy.deploy({
            's3_bucket': self.bucket.name,
            'site': '_site',
        }, self.tmp_dir, False, True)

        self.assert_upload_key_called_correctly(mock_upload, dry=True)
        mock_invalidate.assert_not_called()


class InvalidatePathsTest(unittest.TestCase):
    @patch('boto3.client')
    def test_invalidate_paths_empty(self, mock_client):
        mock_cloudfront = mock.Mock(spec=['create_invalidation'])
        mock_client.return_value = mock_cloudfront
        deploy.invalidate_paths('ABCDEFGHI', [], False)
        mock_cloudfront.create_invalidation.assert_not_called()

    @patch('boto3.client')
    def test_invalidate_paths(self, mock_client):
        mock_cloudfront = mock.Mock(spec=['create_invalidation'])
        mock_client.return_value = mock_cloudfront
        mock_cloudfront.create_invalidation.return_value = dict(
            Invalidation=dict(Id='fake_id', Status='fake_status'))

        fake_paths = [
            '/some/path.txt',
            '/some/prefix/*',
        ]

        deploy.invalidate_paths('ABCDEFGHI', fake_paths, False)

        mock_cloudfront.create_invalidation.assert_called_once_with(
            DistributionId='ABCDEFGHI',
            InvalidationBatch=dict(
                Paths=dict(
                    Quantity=2,
                    Items=fake_paths
                ),
                CallerReference='s3-deploy-website'
            )
        )

    @patch('boto3.client')
    def test_invalidate_paths_dry_run(self, mock_client):
        mock_cloudfront = mock.Mock(spec=['create_invalidation'])
        mock_client.return_value = mock_cloudfront

        fake_paths = [
            '/some/path.txt',
            '/some/prefix/*',
        ]

        deploy.invalidate_paths('ABCDEFGHI', fake_paths, True)
        mock_cloudfront.create_invalidation.assert_not_called()


class MainTest(unittest.TestCase):
    @patch('s3_deploy.config.load_config_file')
    @patch('s3_deploy.deploy.deploy')
    def test_main_with_config(self, mock_deploy, mock_load_config):
        fake_path = os.path.join('path', 'to', 'website')
        mocked_config_dict = {}
        mock_load_config.return_value = mocked_config_dict, fake_path
        deploy.main([fake_path])

        mock_load_config.assert_called_once_with(fake_path)
        mock_deploy.assert_called_once_with(
            mocked_config_dict, fake_path, False, False)
