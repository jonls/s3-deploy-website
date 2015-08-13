
import unittest
import os

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
