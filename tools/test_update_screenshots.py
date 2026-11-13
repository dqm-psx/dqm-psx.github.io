"""Checks for reviewed screenshot imports and the committed gallery data."""
from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

import update_screenshots as updater


ISSUE = 'https://github.com/dqm-psx/dqm-psx.github.io/issues/12'


class ScreenshotUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'data').mkdir()
        (self.root / 'assets/screenshots').mkdir(parents=True)
        self.original = self.make_image((20, 80, 150))
        (self.root / 'assets/screenshots/first.png').write_bytes(self.original)
        self.scene = {'src': 'assets/screenshots/first.png', 'alt': 'A monster by a gate.',
                      'caption': 'Through the gate', 'credit': 'First contributor'}
        info = updater.inspect_image(self.original)
        self.record = {'file': 'screenshots/first.png', 'contributor': 'First contributor',
                       **{key: info[key] for key in ('width', 'height', 'sha256', 'bytes')}}
        self.manifest = {'schemaVersion': 1, 'screenshots': [deepcopy(self.scene)]}
        self.provenance = [deepcopy(self.record)]
        self.write_inputs()
        updater.update(self.root)
        self.incoming = self.root / 'incoming.png'
        self.incoming.write_bytes(self.make_image((80, 150, 20)))

    @staticmethod
    def make_image(color):
        output = BytesIO()
        Image.new('RGB', (8, 6), color).save(output, format='PNG')
        return output.getvalue()

    def write_inputs(self):
        (self.root / updater.MANIFEST).write_text(json.dumps(self.manifest), encoding='utf-8')
        (self.root / updater.PROVENANCE).write_text(json.dumps(self.provenance), encoding='utf-8')

    def snapshot(self):
        return {str(path.relative_to(self.root)): path.read_bytes()
                for path in self.root.rglob('*') if path.is_file()}

    def import_image(self, **overrides):
        arguments = dict(image=self.incoming, name='new-scene', credit='New contributor',
                         caption='At the table', alt='Terry talks with a monster.', issue=ISSUE,
                         root=self.root)
        arguments.update(overrides)
        return updater.import_screenshot(**arguments)

    def test_generation_preserves_scene_order_and_omits_unknown_version(self):
        updater.update(self.root, check=True)
        output = (self.root / updater.OUTPUT).read_text(encoding='utf-8')
        self.assertIn('window.DqmScreenshots = ', output)
        self.assertNotIn('patchVersion', output)
        self.assertEqual(json.loads(output.split(' = ', 1)[1][:-2]), [self.scene])

    def test_initial_image_and_credit_follow_gallery_order(self):
        self.import_image(patch_version='1.0.74', alt='A "new" scene & a monster.')
        manifest, _ = updater.read_data(self.root)
        manifest['screenshots'].reverse()
        (self.root / updater.MANIFEST).write_text(json.dumps(manifest), encoding='utf-8')
        homepage = self.root / 'index.html'
        homepage.write_text('<img id="featured-screen" src="old.png" loading="lazy">\n'
                            '<p class="screen-caption" id="screen-caption">Old caption</p>\n'
                            '<p class="screen-credit" id="screen-credit">Old credit</p>')
        updater.update(self.root)
        page = homepage.read_text()
        self.assertIn('src="assets/screenshots/new-scene.png" width="8" height="6"', page)
        self.assertIn('alt="A &quot;new&quot; scene &amp; a monster."', page)
        self.assertIn('>At the table</p>', page)
        self.assertIn('Screenshot by New contributor (v1.0.74)', page)
        self.assertNotIn('loading="lazy"', page)
        updater.update(self.root, check=True)
        homepage.write_text(page.replace('At the table', 'Stale caption'))
        with self.assertRaisesRegex(ValueError, 'Initial screenshot markup is stale'):
            updater.update(self.root, check=True)

    def test_crop_preserves_pixels_and_records_original_digest_and_version(self):
        original_data = self.incoming.read_bytes()
        src = self.import_image(patch_version='v1.0.72', crop=[1, 1, 6, 4])
        with Image.open(BytesIO(original_data)) as original, Image.open(self.root / src) as actual:
            self.assertEqual(actual.size, (6, 4))
            self.assertEqual(actual.convert('RGB').tobytes(), original.crop((1, 1, 7, 5)).tobytes())
        manifest, provenance = updater.read_data(self.root)
        self.assertEqual(manifest['screenshots'][0], self.scene)
        imported = manifest['screenshots'][-1]
        self.assertEqual(imported['patchVersion'], '1.0.72')
        self.assertEqual(imported['sourceIssue'], ISSUE)
        self.assertNotIn('viewport', imported)
        self.assertEqual(provenance[-1]['sourceCrop'], {'x': 1, 'y': 1, 'width': 6, 'height': 4})
        self.assertEqual(provenance[-1]['patchVersion'], '1.0.72')
        self.assertEqual(provenance[-1]['sourceSha256'], updater.inspect_image(original_data)['sha256'])
        updater.update(self.root, check=True)

    def test_unknown_cli_version_is_omitted(self):
        self.import_image(patch_version='unknown')
        manifest, provenance = updater.read_data(self.root)
        self.assertNotIn('patchVersion', manifest['screenshots'][-1])
        self.assertNotIn('patchVersion', provenance[-1])

    def test_rejects_invalid_versions_without_writing(self):
        before = self.snapshot()
        for value in ('1.0', 'v1.x.x', '1.0.72-beta', '01.0.72', '1.0.72<script>', 72):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.import_image(patch_version=value)
            self.assertEqual(self.snapshot(), before)
        for value in ('unknown', 'v1.0.72', '', None):
            manifest = deepcopy(self.manifest)
            manifest['screenshots'][0]['patchVersion'] = value
            with self.subTest(manifest_value=value), self.assertRaises(ValueError):
                updater.validate(manifest, self.provenance, self.root)

    def test_rejects_invalid_crops_without_writing(self):
        before = self.snapshot()
        for crop in ([-1, 0, 1, 1], [0, 0, 9, 6], [0, 5, 8, 2], [0, 0, 0, 6],
                     [True, 0, 4, 4], [0.5, 0, 4, 4], [0, 0, 4], {'x': 0}):
            with self.subTest(crop=crop), self.assertRaises(ValueError):
                self.import_image(crop=crop)
            self.assertEqual(self.snapshot(), before)

    def test_rejects_remote_absolute_and_traversal_paths(self):
        for src in ('https://example.com/image.png', '../image.png', '/assets/first.png',
                    'assets/screenshots/../../incoming.png', 'assets\\screenshots\\first.png',
                    'C:/images/first.png', 'assets/screenshots/%2e%2e/image.png'):
            manifest = deepcopy(self.manifest)
            manifest['screenshots'][0]['src'] = src
            with self.subTest(src=src), self.assertRaises(ValueError):
                updater.validate(manifest, self.provenance, self.root)
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.import_image(name='../new-scene')
        self.assertEqual(self.snapshot(), before)

    def test_rejects_duplicate_scene_paths_and_image_content(self):
        manifest = deepcopy(self.manifest)
        manifest['screenshots'].append(deepcopy(self.scene))
        with self.assertRaisesRegex(ValueError, 'Duplicate screenshot path'):
            updater.validate(manifest, self.provenance, self.root)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'Duplicate screenshot content'):
            self.import_image(image=self.root / self.scene['src'])
        self.assertEqual(self.snapshot(), before)

    def test_rejects_missing_duplicate_and_mismatched_provenance(self):
        with self.assertRaisesRegex(ValueError, 'Missing asset provenance'):
            updater.validate(self.manifest, [], self.root)
        with self.assertRaisesRegex(ValueError, 'Duplicate provenance'):
            updater.validate(self.manifest, self.provenance * 2, self.root)
        for key, value in (('width', 9), ('height', 7), ('sha256', '0' * 64), ('bytes', 1),
                           ('contributor', 'Wrong credit')):
            provenance = deepcopy(self.provenance)
            provenance[0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                updater.validate(self.manifest, provenance, self.root)

    def test_known_version_issue_and_crop_must_match_provenance(self):
        for field, value in (('patchVersion', '1.0.72'), ('sourceIssue', ISSUE),
                             ('viewport', {'x': 0, 'y': 0, 'width': 8, 'height': 6})):
            manifest = deepcopy(self.manifest)
            manifest['screenshots'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                updater.validate(manifest, self.provenance, self.root)

    def test_rejects_wrong_repository_issue_and_existing_destination(self):
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.import_image(issue='https://github.com/dqm-psx/patch/issues/12')
        with self.assertRaisesRegex(ValueError, 'Destination already exists'):
            self.import_image(name='first')
        self.assertEqual(self.snapshot(), before)

    def test_rejects_truncated_image_and_format_mismatch(self):
        self.incoming.write_bytes(self.incoming.read_bytes()[:40])
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.import_image()
        self.assertEqual(self.snapshot(), before)
        (self.root / 'assets/screenshots/first.jpg').write_bytes(self.original)
        manifest, provenance = deepcopy(self.manifest), deepcopy(self.provenance)
        manifest['screenshots'][0]['src'] = 'assets/screenshots/first.jpg'
        provenance[0]['file'] = 'screenshots/first.jpg'
        with self.assertRaisesRegex(ValueError, 'extension does not match'):
            updater.validate(manifest, provenance, self.root)

    def test_check_detects_stale_output_without_overwriting(self):
        output = self.root / updater.OUTPUT
        output.write_text('// stale\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'stale'):
            updater.update(self.root, check=True)
        self.assertEqual(output.read_text(encoding='utf-8'), '// stale\n')


if __name__ == '__main__':
    unittest.main()
