"""Exercise publication, partial failures, historical FAQs, and explicit Latest rollbacks."""
from copy import deepcopy
import hashlib
from io import BytesIO
import json
import unittest
import zipfile

import sync_release
import preview_release
import test_release_catalog as fixtures


def public_release(record, packages, *, published='2026-11-11T01:00:00Z'):
    files = {**packages, 'release.json': json.dumps(record).encode('utf-8')}
    tag = 'v' + record['version']
    assets = []
    responses = {}
    for name, data in files.items():
        url = f'{sync_release.UPSTREAM}/releases/download/{tag}/{name}'
        assets.append({'name': name, 'state': 'uploaded', 'browser_download_url': url,
                       'size': len(data), 'digest': 'sha256:' + hashlib.sha256(data).hexdigest()})
        responses[url] = data
    return {'id': int(record['version'].replace('.', '')), 'tag_name': tag,
            'draft': False, 'prerelease': False, 'published_at': published, 'assets': assets}, responses


class CatalogSyncTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.ReleaseCatalogTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root, self.page = fixture.root, fixture.page
        self.record, self.packages = fixtures.sample_catalog()
        fixture.write_release(self.record, self.packages)
        self.manifest = self.root / 'downloads/releases.json'

    def fetcher(self, release, responses, history=None):
        def fetch(url):
            if url == sync_release.LATEST:
                return json.dumps(release).encode()
            if url == sync_release.RELEASES + '1':
                return json.dumps(history or [release]).encode()
            return responses[url]
        return fetch

    def test_preview_cannot_add_files_inside_a_release_bundle(self):
        release_dir = self.root / 'release-bundle'
        with self.assertRaisesRegex(ValueError, 'separate from the release bundle'):
            preview_release.preview(release_dir, release_dir / 'preview', root=self.root)
        self.assertFalse(release_dir.exists())

    def test_imports_two_packages_and_preserves_website_source_if_either_fails(self):
        release, responses = public_release(self.record, self.packages)
        before = self.manifest.read_bytes(), self.page.read_bytes()
        broken = dict(responses)
        broken[release['assets'][1]['browser_download_url']] += b'broken'
        with self.assertRaisesRegex(ValueError, 'checksum'):
            sync_release.sync(self.root, self.fetcher(release, broken))
        self.assertEqual((self.manifest.read_bytes(), self.page.read_bytes()), before)
        sync_release.sync(self.root, self.fetcher(release, responses), include_history=True)
        current = json.loads(self.manifest.read_text())['releases'][0]
        self.assertEqual(current['version'], self.record['version'])
        self.assertEqual(current['publishedAt'], release['published_at'])
        for edition in current['editions']:
            self.assertIn(edition['downloadUrl'], self.page.read_text())
        self.assertIn('already uses', sync_release.sync(self.root, self.fetcher(release, responses)))

    def test_missing_catalog_or_explanation_holds_the_update(self):
        release, responses = public_release(self.record, self.packages)
        before = self.manifest.read_bytes(), self.page.read_bytes()
        release['assets'] = [a for a in release['assets'] if a['name'] != 'release.json']
        with self.assertRaisesRegex(ValueError, 'lost release.json'):
            sync_release.sync(self.root, self.fetcher(release, responses))
        incomplete = deepcopy(self.record)
        incomplete['faq'].pop()
        release, responses = public_release(incomplete, self.packages)
        with self.assertRaisesRegex(ValueError, 'Missing FAQ'):
            sync_release.sync(self.root, self.fetcher(release, responses))
        self.assertEqual((self.manifest.read_bytes(), self.page.read_bytes()), before)

    def test_latest_rollback_recovers_newer_faq_from_public_history(self):
        latest, latest_responses = public_release(self.record, self.packages)
        newer, newer_packages = fixtures.sample_catalog('1.0.75')
        newer['faq'][0]['answerHtml'] = '<p>Improved instructions from the newer release.</p>'
        historical, history_responses = public_release(newer, newer_packages, published='2026-11-12T01:00:00Z')
        all_responses = latest_responses | history_responses
        fetched = []
        fetch = self.fetcher(latest, all_responses, [historical, latest])
        def tracked(url):
            fetched.append(url)
            return fetch(url)
        sync_release.sync(self.root, tracked, include_history=True)
        records = json.loads(self.manifest.read_text())['releases']
        self.assertEqual(records[0]['version'], '1.0.74')
        self.assertIn('Improved instructions', self.page.read_text())
        self.assertTrue(any(record['version'] == '1.0.75' for record in records))
        for asset in historical['assets']:
            if asset['name'].endswith('.zip'):
                self.assertNotIn(asset['browser_download_url'], fetched)

    def test_draft_or_prerelease_cannot_become_homepage_latest(self):
        release, responses = public_release(self.record, self.packages)
        before = self.page.read_bytes()
        for field in ('draft', 'prerelease'):
            invalid = {**release, field: True}
            with self.assertRaisesRegex(ValueError, 'published stable'):
                sync_release.sync(self.root, self.fetcher(invalid, responses))
            self.assertEqual(self.page.read_bytes(), before)

    def test_latest_can_return_to_an_unrecorded_legacy_release(self):
        stem = 'DQM1-2-English-v1.0.70'
        stream = BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr(stem + '.bps', b'legacy fixture')
            archive.writestr(stem + '.cue', f'FILE "{stem}.bin" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n')
            archive.writestr('README.txt', 'CONTRIBUTORS\n- Earlier Player\n')
        data = stream.getvalue()
        url = f'{sync_release.UPSTREAM}/releases/download/v1.0.70/{stem}.zip'
        release = {'id': 170, 'tag_name': 'v1.0.70', 'draft': False, 'prerelease': False,
                   'published_at': '2026-10-01T00:00:00Z', 'body': '- Earlier patch.',
                   'assets': [{'name': stem + '.zip', 'state': 'uploaded', 'browser_download_url': url,
                               'size': len(data), 'digest': 'sha256:' + hashlib.sha256(data).hexdigest()}]}
        sync_release.sync(self.root, self.fetcher(release, {url: data}))
        records = json.loads(self.manifest.read_text())['releases']
        self.assertEqual(records[0]['version'], '1.0.70')
        self.assertEqual(records[1]['version'], '1.0.74')
        self.assertIn('movement-settings', self.page.read_text())


if __name__ == '__main__':
    unittest.main()
