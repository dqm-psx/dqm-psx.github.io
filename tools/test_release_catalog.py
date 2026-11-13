"""Check edition identity, complete feature documentation, and stable FAQ behavior."""
from copy import deepcopy
import hashlib
from io import BytesIO
import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest
import zipfile
import zlib

import release_catalog as catalog
import update_release as updater


def bps_integer(value):
    data = bytearray()
    while True:
        byte = value & 0x7f
        value >>= 7
        if value == 0:
            return data + bytes([byte | 0x80])
        data.append(byte)
        value -= 1


def sample_catalog(version='1.0.74'):
    source = catalog.SOURCE_IMAGE.copy()
    features = [
        {'id': 'movement', 'name': 'Movement settings', 'category': 'quality-of-life', 'requires': [], 'introduced': '1.0.73'},
        {'id': 'retail-fix', 'name': 'Original-game fix', 'category': 'bug-fix', 'requires': [], 'introduced': version},
    ]
    record = {'schemaVersion': 2, 'version': version, 'defaultEdition': 'enhanced', 'sourceImage': source,
              'notes': ['Updated the English patch.'], 'contributors': ['Player'], 'features': features,
              'faq': [{'id': 'movement-settings', 'section': 'quality-of-life', 'question': 'How do I run?',
                       'answerHtml': '<p>Hold <strong>R1</strong> to run.</p>', 'features': ['movement']},
                      {'id': 'original-game-fix', 'section': 'bug-fixes', 'question': 'What game bug is fixed?',
                       'answerHtml': '<p>The original flag is repaired.</p>', 'features': ['retail-fix']}],
              'editions': []}
    assets = {}
    for name, display in catalog.EDITION_NAMES.items():
        selected = ['movement', 'retail-fix'] if name == 'enhanced' else ['retail-fix']
        stem = f'DQM1-2-English-v{version}-{name}'
        build = {'schemaVersion': 1, 'version': version, 'edition': name,
                 'sourceRevision': 'a' * 40, 'translation': 'current', 'language': 'en',
                 'fonts': {'dialogue': 'default', 'menu': 'default', 'battle': 'default'},
                 'features': selected, 'sourceImage': source,
                 'output': {'file': stem + '.bin', 'bytes': source['bytes'], 'sha256': 'b' * 64}}
        build['buildId'] = hashlib.sha256(json.dumps(build, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
        bps = b'BPS1' + bps_integer(source['bytes']) * 2 + bps_integer(0)
        bps += bps_integer((source['bytes'] - 1) << 2) + struct.pack('<II', 0, 0)
        bps += struct.pack('<I', zlib.crc32(bps))
        stream = BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr(stem + '.bps', bps)
            archive.writestr(stem + '.cue', f'FILE "{stem}.bin" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n')
            archive.writestr('README.txt', 'English patch\n')
            archive.writestr('BUILD.json', json.dumps(build))
        data = stream.getvalue()
        edition = {'id': name, 'name': display, 'description': display + ' description.',
                   'file': stem + '.zip', 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                   'contents': [stem + '.bps', stem + '.cue', 'README.txt', 'BUILD.json'],
                   'features': selected, 'build': build}
        record['editions'].append(edition)
        assets[edition['file']] = data
    return record, assets


class ReleaseCatalogTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'downloads').mkdir()
        (self.root / 'data').mkdir()
        (self.root / 'data/contributors.json').write_text(json.dumps({'schemaVersion': 1, 'contributors': []}))
        self.page = self.root / 'index.html'
        pairs = [('hero-download', 12), ('release', 10), ('install-download', 16),
                 ('contributors', 16), ('ai-contributors', 16), ('editions-faq', 10), ('feature-faq', 8),
                 ('feature-faq-nav', 14)]
        self.page.write_text('\n'.join(' ' * indent + f'<!-- {key}:begin -->\nold\n'
                                       + ' ' * indent + f'<!-- {key}:end -->' for key, indent in pairs))

    def write_release(self, record, assets):
        for name, data in assets.items():
            (self.root / 'downloads' / name).write_bytes(data)
        (self.root / 'downloads/releases.json').write_text(json.dumps({'schemaVersion': 1, 'releases': [record]}))
        self.write_website_faq(record)

    def write_website_faq(self, *records):
        (self.root / 'data/feature-faq.json').write_text(json.dumps({
            'schemaVersion': 1,
            'releases': [{'version': record['version'], 'faq': record['faq']} for record in records],
        }))

    def test_both_editions_render_with_one_gold_button_and_global_faq(self):
        record, assets = sample_catalog()
        self.write_release(record, assets)
        updater.update(self.root)
        html = self.page.read_text(encoding='utf-8')
        self.assertEqual(html.count('button-gold'), 1)
        self.assertEqual(html.count('data-edition-select'), 2)
        self.assertIn('Translation only', html)
        self.assertIn('id="patch-editions"', html)
        self.assertIn('id="movement-settings"', html)
        faq = html.split(updater.FAQ_START)[1].split(updater.FAQ_END)[0]
        self.assertNotIn('data-edition', faq)
        self.assertIn('<strong>R1</strong>', faq)
        self.assertIn('original-game-fix', faq)
        self.assertIn('Available since v1.0.73.', faq)
        self.assertIn('<a href="#faq-fixes">Game fixes</a>', html)
        updater.update(self.root, check=True)

    def test_missing_explanation_or_edition_holds_entire_update(self):
        record, assets = sample_catalog()
        before = self.page.read_bytes()
        for remove in ('faq', 'editions'):
            incomplete = deepcopy(record)
            incomplete[remove].pop()
            self.write_release(incomplete, assets)
            with self.assertRaises(ValueError):
                updater.update(self.root)
            self.assertEqual(self.page.read_bytes(), before)

    def test_dependency_and_build_choices_must_agree(self):
        record, _ = sample_catalog()
        broken = deepcopy(record)
        broken['features'][1]['requires'] = ['movement']
        with self.assertRaisesRegex(ValueError, 'dependencies'):
            catalog.validate_catalog(broken)
        build = record['editions'][0]['build']
        build['features'] = ['retail-fix']
        identity = {key: value for key, value in build.items() if key != 'buildId'}
        build['buildId'] = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
        with self.assertRaisesRegex(ValueError, 'Build features'):
            catalog.validate_catalog(record)

    def test_build_identity_detects_changed_configuration(self):
        record, _ = sample_catalog()
        record['editions'][0]['build']['sourceModified'] = True
        with self.assertRaisesRegex(ValueError, 'Build identifier'):
            catalog.validate_catalog(record)

    def test_html_and_download_urls_cannot_add_executable_content(self):
        record, _ = sample_catalog()
        for markup in ('<script>alert(1)</script>', '<p onclick="bad()">Text</p>',
                       '<a href="javascript:bad()">Link</a>', '<p><strong>Unclosed</p>'):
            broken = deepcopy(record)
            broken['faq'][0]['answerHtml'] = markup
            with self.assertRaises(ValueError):
                catalog.validate_catalog(broken)
        record['editions'][0]['downloadUrl'] = 'https://example.com/patch.zip'
        with self.assertRaisesRegex(ValueError, 'downloadUrl'):
            catalog.validate_catalog(record)

    def test_zip_checks_bind_build_record_and_bps_to_the_edition(self):
        record, assets = sample_catalog()
        edition = record['editions'][0]
        data = assets[edition['file']]
        catalog.validate_catalog(record)
        catalog.validate_edition_package(record, edition, data)
        for changed in ('BUILD.json', edition['contents'][0], edition['contents'][1]):
            stream = BytesIO()
            with zipfile.ZipFile(BytesIO(data)) as original, zipfile.ZipFile(stream, 'w') as target:
                for name in original.namelist():
                    content = original.read(name)
                    if name == changed:
                        content = b'{}' if changed == 'BUILD.json' else content + b'broken'
                    target.writestr(name, content)
            bad_data = stream.getvalue()
            bad_edition = {**edition, 'bytes': len(bad_data), 'sha256': hashlib.sha256(bad_data).hexdigest()}
            with self.assertRaises(ValueError):
                catalog.validate_edition_package(record, bad_edition, bad_data)

    def test_rollback_preserves_newer_answers_and_existing_anchors(self):
        older, _ = sample_catalog('1.0.74')
        newer, _ = sample_catalog('1.0.75')
        older['publishedAt'] = '2026-01-01T00:00:00Z'
        newer['publishedAt'] = '2026-02-01T00:00:00Z'
        newer['faq'][0]['answerHtml'] = '<p>Newer instructions.</p>'
        newer['faq'].append({'id': 'extra-answer', 'section': 'quality-of-life',
                             'question': 'More help?', 'answerHtml': '<p>More help.</p>', 'features': ['movement']})
        self.write_website_faq(older, newer)
        html = updater.feature_faq([older, newer], self.root)
        self.assertEqual(html, updater.feature_faq([newer, older], self.root))
        self.assertIn('id="movement-settings"', html)
        self.assertIn('Newer instructions.', html)
        self.assertIn('id="extra-answer"', html)
        self.assertNotIn('Hold <strong>R1</strong>', html)


if __name__ == '__main__':
    unittest.main()
