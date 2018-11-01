
import unittest

from s3_deploy import filematch


class FileMatchTest(unittest.TestCase):
    def test_match_exact_ok(self):
        self.assertTrue(filematch.match_key(
            '/index.html', 'index.html', regexp=False))

    def test_match_exact_fail_different_name(self):
        self.assertFalse(filematch.match_key(
            '/index.html', 'image.png', regexp=False))

    def test_match_exact_fail_different_path(self):
        self.assertFalse(filematch.match_key(
            '/index.html', 'dir/index.html', regexp=False))

    def test_match_exact_with_path_ok(self):
        self.assertTrue(filematch.match_key(
            '/dir/index.html', 'dir/index.html', regexp=False))

    def test_match_exact_with_path_fail_different_name(self):
        self.assertFalse(filematch.match_key(
            '/dir/index.html', 'dir/image.png', regexp=False))

    def test_match_exact_with_path_fail_different_path(self):
        self.assertFalse(filematch.match_key(
            '/dir/index.html', 'altdir/image.png', regexp=False))

    def test_match_base_ok_simple(self):
        self.assertTrue(filematch.match_key(
            'index.html', 'index.html', regexp=False))

    def test_match_base_ok_path(self):
        self.assertTrue(filematch.match_key(
            'index.html', 'dir/index.html', regexp=False))

    def test_match_base_fail_different_name(self):
        self.assertFalse(filematch.match_key(
            'ok.html', 'book.html', regexp=False))

    def test_match_base_fail_different_path(self):
        self.assertFalse(filematch.match_key(
            'ok.html', 'dir/book.html', regexp=False))

    def test_match_variable_base_ok(self):
        self.assertTrue(filematch.match_key(
            '*.html', 'index.html', regexp=False))

    def test_match_variable_base_within_ok(self):
        self.assertTrue(filematch.match_key(
            'image-*.png', 'image-999.png', regexp=False))

    def test_match_variable_with_path_ok(self):
        self.assertTrue(filematch.match_key(
            'images/*.png', 'images/999.png', regexp=False))

    def test_match_variable_with_path_fail(self):
        self.assertFalse(filematch.match_key(
            'images/*.png', 'images/README', regexp=False))

    def test_match_multilevel_fail(self):
        self.assertFalse(filematch.match_key(
            '/dir/*.html', 'dir/second/file.html', regexp=False))

    def test_match_one_ok(self):
        self.assertTrue(filematch.match_key(
            'image?.png', 'image1.png', regexp=False))

    def test_match_one_fail(self):
        self.assertFalse(filematch.match_key(
            'image?.png', 'image10.png', regexp=False))

    def test_match_empty_on_file(self):
        with self.assertRaises(ValueError):
            filematch.match_key('', 'index.html', regexp=False)

    def test_match_empty_on_empty(self):
        with self.assertRaises(ValueError):
            filematch.match_key('', '', regexp=False)

    def test_match_regex_dollar_suffix_ok(self):
        self.assertTrue(filematch.match_key(
            r'image-\d+\.png$', 'image-999.png', regexp=True))

    def test_match_regex_dollar_suffix_fail(self):
        self.assertFalse(filematch.match_key(
            r'image-\d+\.png$', 'image-name.png', regexp=True))

    def test_match_regex_caret_prefix_ok(self):
        self.assertTrue(filematch.match_key(
            r'^dir\/index\.html', 'dir/index.html', regexp=True))

    def test_match_regex_caret_prefix_fail(self):
        self.assertFalse(filematch.match_key(
            r'^dir\/index\.html', 'altdir/index.html', regexp=True))

    def test_match_regex_caret_and_dollar_ok(self):
        self.assertTrue(filematch.match_key(
            r'^dir\/index\.html$', 'dir/index.html', regexp=True))

    def test_match_regex_caret_and_dollar_fail(self):
        self.assertFalse(filematch.match_key(
            r'^dir\/index\.html$', 'dir/index.htm', regexp=True))
