"""Regression checks for package validation and automatic release credits."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import update_release as updater


class ReleaseUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'downloads').mkdir()
        (self.root / 'data').mkdir()
        self.page = self.root / 'index.html'
        self.page.write_text(
            '<main>\n          <!-- release:begin -->\nold download\n          <!-- release:end -->\n'
            '                <!-- contributors:begin -->\nold credits\n                <!-- contributors:end -->\n</main>\n',
            encoding='utf-8',
        )
        self.write_contributors([{'name': 'Cats4gold', 'contribution': 'Breeding tool', 'source': 'Project owner'}])

    def write_contributors(self, records):
        (self.root / 'data/contributors.json').write_text(
            json.dumps({'schemaVersion': 1, 'contributors': records}), encoding='utf-8',
        )

    def package(self, version, readme, *, cue=None, extra=None):
        stem = f'DQM1-2-English-v{version}'
        filename = stem + '-public.zip'
        path = self.root / 'downloads' / filename
        contents = [stem + '.bps', stem + '.cue', 'README.txt']
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr(contents[0], b'fixture patch')
            archive.writestr(contents[1], cue if cue is not None else
                             f'FILE "{stem}.bin" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n')
            archive.writestr('README.txt', readme)
            if extra:
                archive.writestr(extra, 'unexpected')
        data = path.read_bytes()
        return {'version': version, 'name': 'English translation', 'file': filename,
                'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'contents': contents,
                'notes': ['A release note.']}

    def manifest(self, *releases):
        (self.root / 'downloads/releases.json').write_text(
            json.dumps({'schemaVersion': 1, 'releases': list(releases)}), encoding='utf-8',
        )

    def test_new_release_updates_download_and_retains_older_credits(self):
        old = self.package('1.0.63', 'PUBLIC RELEASE HIGHLIGHTS\nThanks to Older for the report!\n')
        del old['notes']  # Older manifest entries do not need current-card notes.
        latest = self.package('1.0.64', 'PUBLIC RELEASE HIGHLIGHTS\nThanks to Newer for the report!\n')
        self.manifest(latest, old)
        updater.update(self.root)
        source = self.page.read_text(encoding='utf-8')
        self.assertIn('Download v1.0.64', source)
        self.assertIn('<li>Cats4gold</li>', source)
        self.assertIn('<li>Newer</li>', source)
        self.assertIn('<li>Older</li>', source)
        future = self.package('1.0.65', 'PUBLIC RELEASE HIGHLIGHTS\nOnly the newest fix.\n'
                              'CONTRIBUTORS\n- Future Name\nREQUIRED GAME\nRetail game.\n')
        self.manifest(future, latest, old)
        updater.update(self.root)
        source = self.page.read_text(encoding='utf-8')
        self.assertIn('Download v1.0.65', source)
        for name in ('Cats4gold', 'Newer', 'Older', 'Future Name'):
            self.assertEqual(source.count(f'<li>{name}</li>'), 1)
        updater.update(self.root, check=True)

    def test_deduplicates_case_variants_and_escapes_structured_and_manual_names(self):
        self.write_contributors([
            {'name': 'cats4gold', 'contribution': 'Tool', 'source': 'Owner'},
            {'name': 'A & B <team>', 'contribution': 'Testing', 'source': 'Owner'},
        ])
        release = self.package('1.0.64', 'PUBLIC RELEASE HIGHLIGHTS\nThanks to Cats4gold and _Zev for reports!\n'
                               'CONTRIBUTORS\n- _zev\n- "Other" <friend>\n')
        self.manifest(release)
        updater.update(self.root)
        source = self.page.read_text(encoding='utf-8')
        self.assertEqual(source.count('<li>cats4gold</li>'), 1)
        self.assertEqual(source.count('<li>_Zev</li>'), 1)
        self.assertNotIn('<li>_zev</li>', source)
        self.assertIn('<li>A &amp; B &lt;team&gt;</li>', source)
        self.assertIn('<li>&quot;Other&quot; &lt;friend&gt;</li>', source)
        self.assertLess(source.index('<li>cats4gold'), source.index('<li>_Zev'))

    def test_existing_thanks_grammar_and_wrapped_lines(self):
        text = ('PUBLIC RELEASE HIGHLIGHTS\n- Fixed a bug; thanks Wingforth for the report!\n'
                'Thanks also to nextlvlroy for helping reproduce\nand test the crash.\n'
                'Thanks to Schnaki and _Zev for reports!\nThanks Alice, Bob, and Carol for testing!\n')
        self.assertEqual(updater.readme_contributors(text),
                         ['Wingforth', 'nextlvlroy', 'Schnaki', '_Zev', 'Alice', 'Bob', 'Carol'])

    def test_ambiguous_or_unparsed_thanks_do_not_write(self):
        examples = [
            'PUBLIC RELEASE HIGHLIGHTS\nThanks to Alice / Bob for testing!\n',
            'PUBLIC RELEASE HIGHLIGHTS\nThanks to Alice Smith for testing!\n',
            'PUBLIC RELEASE HIGHLIGHTS\nThanks to Alice!\n',
            'PUBLIC RELEASE HIGHLIGHTS\nThanks to Alice for testing\n',
            'PUBLIC RELEASE HIGHLIGHTS\nThanks to everyone and Alice for testing!\n',
            'PUBLIC RELEASE HIGHLIGHTS\nThanks to everyone who contributed testing and Alice for reporting!\n',
            'PUBLIC RELEASE HIGHLIGHTS\nThanks to everyone who contributed testing, especially Alice!\n',
            'PUBLIC RELEASE HIGHLIGHTS\nThanks to Alice for reports and Bob for testing!\n',
            'PUBLIC RELEASE HIGHLIGHTS\nThanks to Alice for reports, Bob for testing!\n',
            'REQUIRED GAME\nThanks to Alice for testing!\n',
            'CONTRIBUTORS\nAlice\n',
        ]
        original = self.page.read_bytes()
        for readme in examples:
            with self.subTest(readme=readme):
                self.manifest(self.package('1.0.64', readme))
                with self.assertRaises(ValueError):
                    updater.update(self.root)
                self.assertEqual(self.page.read_bytes(), original)

    def test_collective_gratitude_preserves_adjacent_named_credits(self):
        readme = ('PUBLIC RELEASE HIGHLIGHTS\n'
                  'Thanks to everyone who contributed translation suggestions and feedback!\n'
                  'Thanks to Nelin and Sparrow for the reports and help!\n'
                  'Thanks to everyone who contributed reports, suggestions, and testing!\n'
                  'Thanks to everybody for testing. Thanks to Suppi for the report!\n')
        self.assertEqual(updater.readme_contributors(readme), ['Nelin', 'Sparrow', 'Suppi'])
        self.manifest(self.package('1.0.72', readme))
        updater.update(self.root)
        source = self.page.read_text(encoding='utf-8')
        for name in ('Nelin', 'Sparrow', 'Suppi'):
            self.assertIn(f'<li>{name}</li>', source)
        self.assertNotIn('<li>everyone</li>', source)
        self.assertNotIn('<li>everybody</li>', source)

    def test_check_detects_stale_credit_list_without_writing(self):
        self.manifest(self.package('1.0.64', 'CONTRIBUTORS\n- Alice\n'))
        updater.update(self.root)
        self.page.write_text(self.page.read_text(encoding='utf-8').replace('<li>Alice</li>', '<li>Stale</li>'),
                             encoding='utf-8')
        original = self.page.read_bytes()
        with self.assertRaisesRegex(ValueError, 'stale'):
            updater.update(self.root, check=True)
        self.assertEqual(self.page.read_bytes(), original)

    def test_retained_package_hash_must_validate_before_writing(self):
        latest = self.package('1.0.64', 'CONTRIBUTORS\n- Newer\n')
        old = self.package('1.0.63', 'CONTRIBUTORS\n- Older\n')
        self.manifest(latest, old)
        path = self.root / 'downloads' / old['file']
        path.write_bytes(path.read_bytes() + b'corruption')
        original = self.page.read_bytes()
        with self.assertRaisesRegex(ValueError, 'size or SHA-256'):
            updater.update(self.root)
        self.assertEqual(self.page.read_bytes(), original)

    def test_matching_hash_does_not_bypass_cue_or_zip_contents_validation(self):
        original = self.page.read_bytes()
        for options in ({'cue': 'FILE "wrong.bin" BINARY\n'}, {'extra': 'unexpected.txt'}):
            with self.subTest(options=options):
                self.manifest(self.package('1.0.64', 'CONTRIBUTORS\n- Alice\n', **options))
                with self.assertRaises(ValueError):
                    updater.update(self.root)
                self.assertEqual(self.page.read_bytes(), original)

    def test_missing_credit_markers_do_not_partially_update_card(self):
        self.manifest(self.package('1.0.64', 'CONTRIBUTORS\n- Alice\n'))
        self.page.write_text('<!-- release:begin -->old<!-- release:end -->', encoding='utf-8')
        original = self.page.read_bytes()
        with self.assertRaisesRegex(ValueError, 'contributors:begin'):
            updater.update(self.root)
        self.assertEqual(self.page.read_bytes(), original)

    def test_replace_failure_preserves_original_and_cleans_temporary_file(self):
        self.manifest(self.package('1.0.64', 'CONTRIBUTORS\n- Alice\n'))
        original = self.page.read_bytes()
        with patch.object(updater.os, 'replace', side_effect=OSError('Simulated replacement failure')):
            with self.assertRaises(OSError):
                updater.update(self.root)
        self.assertEqual(self.page.read_bytes(), original)
        self.assertEqual(list(self.root.glob('.index-*.tmp')), [])

    def test_missing_manual_provenance_is_rejected(self):
        self.manifest(self.package('1.0.64', 'CONTRIBUTORS\n- Alice\n'))
        self.write_contributors([{'name': 'Manual', 'contribution': 'Testing'}])
        with self.assertRaisesRegex(ValueError, 'recorded source'):
            updater.update(self.root)


class PublishedCreditsTests(unittest.TestCase):
    def test_bundled_release_credits_are_all_preserved(self):
        manifest = json.loads((updater.ROOT / 'downloads/releases.json').read_text(encoding='utf-8'))
        expected = {'nextlvlroy', 'BalK', 'gollum_007', 'Lori', 'Wingforth', '_Zev', 'Schnaki'}
        for release in manifest['releases']:
            if release['version'] in ('1.0.63', '1.0.64'):
                with self.subTest(version=release['version']):
                    _, readme = updater.validate_package(release, updater.ROOT)
                    self.assertEqual(set(updater.readme_contributors(readme)), expected)
            elif release['version'] == '1.0.72':
                _, readme = updater.validate_package(release, updater.ROOT)
                self.assertEqual(set(updater.readme_contributors(readme)),
                                 expected | {'Nelin', 'Sparrow', 'Suppi', 'PkmnTrainerAbram'})


if __name__ == '__main__':
    unittest.main()
