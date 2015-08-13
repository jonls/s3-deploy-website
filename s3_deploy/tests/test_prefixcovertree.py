
import unittest

from s3_deploy.prefixcovertree import PrefixCoverTree


class PrefixCoverTreeTest(unittest.TestCase):
    def test_iter(self):
        t = PrefixCoverTree()
        t.include('/index.html')

        t.exclude('/assets/favicon.ico')
        t.exclude('/assets/image1.png')

        t.include('/assets/image2.png')
        t.include('/content/page1.html')
        t.include('/content/page2.html')
        t.include('/content/page3.html')
        t.include('/css/main.css')

        entries = list(t)
        self.assertEqual(entries, [
            '/assets/favicon.ico',
            '/assets/image1.png',
            '/assets/image2.png',
            '/content/page1.html',
            '/content/page2.html',
            '/content/page3.html',
            '/css/main.css',
            '/index.html'
        ])

    def test_iter_empty(self):
        t = PrefixCoverTree()
        self.assertEqual(list(t), [])

    def test_include_empty_key(self):
        t = PrefixCoverTree()
        t.include('')
        self.assertEqual(list(t), [''])

    def test_include_twice(self):
        t = PrefixCoverTree()
        t.include('/index.html')
        t.include('/index.html')
        self.assertEqual(list(t), ['/index.html'])
        self.assertEqual(set(t.matches()), {('', False)})

    def test_include_then_exclude(self):
        t = PrefixCoverTree()
        t.include('/index.html')
        t.exclude('/index.html')
        self.assertEqual(list(t), ['/index.html'])
        self.assertEqual(set(t.matches()), set())

    def test_exclude_then_include(self):
        t = PrefixCoverTree()
        t.exclude('/index.html')
        with self.assertRaises(ValueError):
            t.include('/index.html')

    def test_matches(self):
        t = PrefixCoverTree()
        t.include('/index.html')

        t.exclude('/assets/favicon.ico')
        t.exclude('/assets/image1.png')

        t.include('/assets/image2.png')
        t.include('/content/page1.html')
        t.include('/content/page2.html')
        t.include('/content/page3.html')
        t.include('/css/main.css')

        matches = set(t.matches())
        self.assertEqual(matches, {
            ('/index.html', True),
            ('/assets/image2.png', True),
            ('/c', False)
        })

    def test_matches_include_partial(self):
        t = PrefixCoverTree()
        t.exclude('/assets/favicon.ico')
        t.include('/assets/')

        matches = set(t.matches())
        self.assertEqual(matches, {
            ('/assets/', True)
        })

    def test_matches_include_none(self):
        t = PrefixCoverTree()
        t.exclude('/index.html')
        t.exclude('/assets/image1.png')
        t.exclude('/assets/image2.png')

        matches = set(t.matches())
        self.assertEqual(matches, set())

    def test_matches_empty(self):
        t = PrefixCoverTree()
        matches = set(t.matches())
        self.assertEqual(matches, set())

    def test_matches_only_include(self):
        t = PrefixCoverTree()
        t.include('/index.html')
        t.include('/assets/image1.png')
        t.include('/assets/image2.png')

        matches = set(t.matches())
        self.assertEqual(matches, {
            ('', False)
        })
