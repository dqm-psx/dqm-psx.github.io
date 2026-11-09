"""Regression checks for package validation and automatic release credits."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
import zipfile

import sync_release
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
            '                <!-- install-download:begin -->\nold link\n                <!-- install-download:end -->\n'
            '                <!-- contributors:begin -->\nold credits\n                <!-- contributors:end -->\n'
            '                <!-- ai-contributors:begin -->\nold AI credits\n                <!-- ai-contributors:end -->\n</main>\n',
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

    @staticmethod
    def public_source(record):
        tag = 'v' + record['version']
        url = f'{sync_release.UPSTREAM}/releases/download/{tag}/{record["file"]}'
        return {'tag_name': tag, 'published_at': '2026-11-07T01:00:00Z', 'draft': False,
                'prerelease': False, 'body': '- Updated names.\n- Another fix.',
                'assets': [{'name': record['file'], 'browser_download_url': url, 'state': 'uploaded',
                            'size': record['bytes'], 'digest': 'sha256:' + record['sha256']}]}

    def test_public_sync_verifies_new_clean_asset_and_keeps_older_credits_offline(self):
        old = self.package('1.0.72', 'CONTRIBUTORS\n- Older\n')
        new = self.package('1.0.73', 'CONTRIBUTORS\n- Player\n')
        zip_path = self.root / 'downloads' / new['file']
        asset = zip_path.read_bytes()
        zip_path.unlink()
        new['file'] = 'DQM1-2-English-v1.0.73.zip'
        self.manifest(old)
        source = self.public_source(new)
        calls = []
        def fetch(url):
            calls.append(url)
            return json.dumps(source).encode() if url == sync_release.LATEST else asset
        sync_release.sync(self.root, fetch)
        manifest = json.loads((self.root / 'downloads/releases.json').read_text('utf-8'))
        latest = manifest['releases'][0]
        self.assertEqual(calls, [sync_release.LATEST, latest['downloadUrl']])
        self.assertEqual(latest['contributors'], ['Player'])
        self.assertEqual(latest['notes'], ['Updated names.', 'Another fix.'])
        self.assertFalse((self.root / 'downloads' / new['file']).exists())
        html = self.page.read_text('utf-8')
        self.assertIn(latest['downloadUrl'], html)
        self.assertIn('<li>Older</li>', html)
        self.assertIn('<li>Player</li>', html)
        updater.update(self.root, check=True)
        sync_release.sync(self.root, fetch)
        self.assertEqual(len(calls), 3)  # Same verified release needs just its metadata.
        self.assertEqual(html, self.page.read_text('utf-8'))

    def test_sync_verified_mirror_to_public_preserves_its_name_and_reviewed_notes(self):
        release = self.package('1.0.73', 'CONTRIBUTORS\n- Player\n')
        self.manifest(release)
        source = self.public_source(release)
        source['assets'].append({**source['assets'][0], 'name': release['file'].replace('-public.zip', '.zip')})
        data = (self.root / 'downloads' / release['file']).read_bytes()
        record = sync_release.public_record(source, release, lambda url: data)
        self.assertEqual(record['file'], release['file'])
        self.assertEqual(record['notes'], release['notes'])
        self.assertTrue(record['downloadUrl'].endswith('/' + release['file']))

    def test_private_source_preserves_local_route_and_preexisting_public_failure_is_reported(self):
        release = self.package('1.0.73', 'CONTRIBUTORS\n- Player\n')
        self.manifest(release)
        page = self.page.read_bytes()
        def unavailable(url):
            raise HTTPError(url, 404, 'Not Found', {}, None)
        self.assertIn('local download', sync_release.sync(self.root, unavailable))
        self.assertEqual(self.page.read_bytes(), page)
        (self.root / 'downloads' / release['file']).write_bytes(b'damaged preview')
        with self.assertRaisesRegex(ValueError, 'Package size or SHA-256'):
            sync_release.sync(self.root, unavailable)
        release['downloadUrl'] = self.public_source(release)['assets'][0]['browser_download_url']
        self.manifest(release)
        with self.assertRaises(HTTPError) as raised:
            sync_release.sync(self.root, unavailable)
        raised.exception.close()

    def test_sync_rejects_unreleased_changed_or_unverified_bytes_before_writing(self):
        release = self.package('1.0.73', 'CONTRIBUTORS\n- Player\n')
        self.manifest(release)
        manifest_path = self.root / 'downloads/releases.json'
        before = manifest_path.read_bytes(), self.page.read_bytes()
        for change in ('draft', 'prerelease', 'digest', 'url', 'data'):
            source = self.public_source(release)
            if change in ('draft', 'prerelease'):
                source[change] = True
            elif change == 'digest':
                source['assets'][0]['digest'] = 'sha256:' + '0' * 64
            elif change == 'url':
                source['assets'][0]['browser_download_url'] = 'https://example.com/other.zip'
            with self.subTest(change=change), self.assertRaises(ValueError):
                sync_release.sync(self.root, lambda url: json.dumps(source).encode()
                                  if url == sync_release.LATEST else b'corrupt')
            self.assertEqual((manifest_path.read_bytes(), self.page.read_bytes()), before)

    def test_new_release_updates_download_and_retains_older_credits(self):
        old = self.package('1.0.63', 'PUBLIC RELEASE HIGHLIGHTS\nThanks to Older for the report!\n')
        del old['notes']  # Older manifest entries do not need current-card notes.
        latest = self.package('1.0.64', 'PUBLIC RELEASE HIGHLIGHTS\nThanks to Newer for the report!\n')
        self.manifest(latest, old)
        updater.update(self.root)
        source = self.page.read_text(encoding='utf-8')
        self.assertIn('<span class="release-version">v1.0.64</span>', source)
        self.assertIn('<li>Cats4gold</li>', source)
        self.assertIn('<li>Newer</li>', source)
        self.assertIn('<li>Older</li>', source)
        future = self.package('1.0.65', 'PUBLIC RELEASE HIGHLIGHTS\nOnly the newest fix.\n'
                              'CONTRIBUTORS\n- Future Name\nREQUIRED GAME\nRetail game.\n')
        self.manifest(future, latest, old)
        updater.update(self.root)
        source = self.page.read_text(encoding='utf-8')
        self.assertIn('<span class="release-version">v1.0.65</span>', source)
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

    def test_explicit_alias_merges_old_and_new_release_credits(self):
        self.write_contributors([{'name': 'Claude (Anthropic)', 'aliases': ['Claude Fable', 'Fable', 'Claude Opus'],
                                  'creditType': 'ai-assistance',
                                  'contribution': 'AI assistance', 'source': 'Owner correction'}])
        old = self.package('1.0.63', 'PUBLIC RELEASE HIGHLIGHTS\nThanks to Fable for testing!\n')
        latest = self.package('1.0.72', 'CONTRIBUTORS\n- CLAUDE FABLE\n- fable\n- Claude Opus\n- Other\n')
        self.manifest(latest, old)
        updater.update(self.root)
        source = self.page.read_text(encoding='utf-8')
        people = source.split(updater.CREDITS_START)[1].split(updater.CREDITS_END)[0]
        assistants = source.split(updater.AI_START)[1].split(updater.AI_END)[0]
        self.assertEqual(people.strip(), '<li>Other</li>')
        self.assertEqual(assistants.strip(), '<li>Claude (Anthropic)</li>')
        updater.update(self.root, check=True)

    def test_conflicting_or_malformed_aliases_do_not_write(self):
        self.manifest(self.package('1.0.72', 'CONTRIBUTORS\n- Other\n'))
        original = self.page.read_bytes()
        for aliases in ('Fable', ['Other']):
            with self.subTest(aliases=aliases):
                self.write_contributors([
                    {'name': 'Claude Fable', 'aliases': aliases,
                     'contribution': 'AI assistance', 'source': 'Owner'},
                    {'name': 'Other', 'contribution': 'Testing', 'source': 'Release'},
                ])
                with self.assertRaisesRegex(ValueError, 'alias'):
                    updater.update(self.root)
                self.assertEqual(self.page.read_bytes(), original)

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

    def test_local_download_fallback_ignores_release_provenance_url(self):
        release = self.package('1.0.73', 'CONTRIBUTORS\n- Player\n')
        release['releaseUrl'] = 'https://github.com/dqm-psx/patch/releases/tag/v1.0.73'
        self.manifest(release)
        updater.update(self.root)
        source = self.page.read_text(encoding='utf-8')
        attributes = f'href="downloads/{release["file"]}" download="DQM1-2-English-v1.0.73.zip"'
        self.assertEqual(source.count(attributes), 2)
        self.assertIn(f'<a {attributes}>Download</a>', source)
        self.assertIn(f'<a id="download" class="button button-gold release-action" {attributes}>Download ZIP', source)
        self.assertEqual(source.count('id="download"'), 1)
        self.assertIn(release['sha256'], source)
        self.assertNotIn(release['releaseUrl'], source)
        updater.update(self.root, check=True)

    def test_pinned_public_asset_renders_without_cross_origin_download_attribute(self):
        release = self.package('1.0.73', 'CONTRIBUTORS\n- Player\n')
        release['downloadUrl'] = f'https://github.com/dqm-psx/patch/releases/download/v1.0.73/{release["file"]}'
        self.manifest(release)
        updater.update(self.root)
        source = self.page.read_text(encoding='utf-8')
        self.assertEqual(source.count(f'href="{release["downloadUrl"]}"'), 2)
        self.assertIn(f'<a href="{release["downloadUrl"]}">Download</a>', source)
        self.assertNotIn(' download=', source)
        self.assertIn('<span class="release-version">v1.0.73</span>', source)
        self.assertIn('<li>Player</li>', source)
        updater.update(self.root, check=True)

    def test_rejects_untrusted_unpinned_or_mismatched_download_urls_before_writing(self):
        release = self.package('1.0.73', 'CONTRIBUTORS\n- Player\n')
        expected = f'https://github.com/dqm-psx/patch/releases/download/v1.0.73/{release["file"]}'
        candidates = [
            None, '', 73, 'javascript:alert(1)',
            expected.replace('https:', 'http:'),
            expected.replace('github.com', 'github.com.evil.example'),
            expected.replace('github.com', 'github.com@evil.example'),
            expected.replace('/dqm-psx/patch/', '/phakic/dqm1/'),
            expected.replace('/dqm-psx/patch/', '/dqm-psx/other/'),
            expected.replace('/v1.0.73/', '/v1.0.72/'),
            expected.replace(release['file'], 'other.zip'),
            expected.replace('/download/v1.0.73/', '/latest/download/'),
            expected + '?token=anything', expected + '#fragment',
            expected + '" onclick="alert(1)',
            ' ' + expected, expected + '\n',
            expected.replace('/v1.0.73/', '/v1.0.72/../v1.0.73/'),
        ]
        original = self.page.read_bytes()
        for url in candidates:
            with self.subTest(url=url):
                release['downloadUrl'] = url
                self.manifest(release)
                with self.assertRaisesRegex(ValueError, 'downloadUrl'):
                    updater.update(self.root)
                self.assertEqual(self.page.read_bytes(), original)

    def test_retained_release_download_url_is_validated_even_when_not_displayed(self):
        latest = self.package('1.0.73', 'CONTRIBUTORS\n- Newer\n')
        older = self.package('1.0.72', 'CONTRIBUTORS\n- Older\n')
        older['downloadUrl'] = 'https://example.com/old.zip'
        self.manifest(latest, older)
        original = self.page.read_bytes()
        with self.assertRaisesRegex(ValueError, 'downloadUrl'):
            updater.update(self.root)
        self.assertEqual(self.page.read_bytes(), original)

    def test_external_download_does_not_bypass_local_integrity_checks(self):
        original = self.page.read_bytes()
        for invalid in ('hash', 'cue'):
            with self.subTest(invalid=invalid):
                options = {'cue': 'FILE "wrong.bin" BINARY\n'} if invalid == 'cue' else {}
                release = self.package('1.0.73', 'CONTRIBUTORS\n- Player\n', **options)
                release['downloadUrl'] = f'https://github.com/dqm-psx/patch/releases/download/v1.0.73/{release["file"]}'
                if invalid == 'hash':
                    release['sha256'] = '0' * 64
                self.manifest(release)
                with self.assertRaises(ValueError):
                    updater.update(self.root)
                self.assertEqual(self.page.read_bytes(), original)

    def test_check_detects_download_destination_change_without_writing(self):
        release = self.package('1.0.73', 'CONTRIBUTORS\n- Player\n')
        self.manifest(release)
        updater.update(self.root)
        original = self.page.read_bytes()
        release['downloadUrl'] = f'https://github.com/dqm-psx/patch/releases/download/v1.0.73/{release["file"]}'
        self.manifest(release)
        with self.assertRaisesRegex(ValueError, 'stale'):
            updater.update(self.root, check=True)
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
        self.page.write_text('<!-- install-download:begin --><!-- install-download:end -->'
                             '<!-- release:begin -->old<!-- release:end -->', encoding='utf-8')
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
