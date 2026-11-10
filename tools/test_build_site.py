"""Exercise the HTML Pages actually serves, including nested 404 URLs."""

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from urllib.parse import urlsplit

import build_site


class SiteBuildTests(unittest.TestCase):
    def test_built_pages_resolve_assets_and_use_the_current_bundle(self):
        with TemporaryDirectory() as directory:
            out = Path(directory)
            build_site.build(out)
            build_site.build(out)
            for name in build_site.PAGES:
                html = (out / name).read_text(encoding='utf-8')
                theme = (build_site.ROOT / 'theme.js').read_text(encoding='utf-8')
                self.assertLess(html.index(theme), html.index('rel="stylesheet"'), name)
                page = build_site.Page(html)
                for url in page.urls:
                    parts = urlsplit(url)
                    if parts.netloc or not parts.path.strip('/'):
                        continue
                    path = parts.path.lstrip('/')
                    self.assertTrue((out / path).is_file(), f'{name}: {url}')
                    if name == '404.html':
                        self.assertTrue(url.startswith('/'), url)
                    if path.endswith(('.css', '.js')):
                        digest = hashlib.sha256((out / path).read_bytes()).hexdigest()[:12]
                        self.assertIn(digest, path)
                if name == 'index.html':
                    self.assertEqual(len(page.scripts), 1)
            self.assertFalse((out / 'assets/artwork/japanese-retail-front.jpg').exists())

    def test_duplicate_anchors_fail_the_build(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate HTML id'):
            build_site.Page('<a id="download"></a><button id="download"></button>')


if __name__ == '__main__':
    unittest.main()
