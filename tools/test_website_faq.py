"""Verify independent website wording and release publication ordering."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import prepare_website_release
import test_release_catalog as fixtures
import update_release
import website_faq


class WebsiteFAQTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.ReleaseCatalogTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.root, self.page = fixture.root, fixture.page
        self.record, self.packages = fixtures.sample_catalog()
        fixture.write_release(self.record, self.packages)
        self.path = self.root / website_faq.RELATIVE_PATH

    def read(self):
        return json.loads(self.path.read_text())

    def write(self, data):
        self.path.write_text(json.dumps(data), encoding='utf-8')

    def test_release_refresh_never_overwrites_website_only_correction(self):
        data = self.read()
        data['releases'][0]['faq'][0]['answerHtml'] = '<p>Reviewed website correction.</p>'
        self.write(data)
        self.record['faq'][0]['answerHtml'] = '<p>Unreviewed upstream wording.</p>'
        manifest = {'schemaVersion': 1, 'releases': [self.record]}
        html = update_release.rendered_page(self.root, manifest)
        self.assertIn('Reviewed website correction.', html)
        self.assertNotIn('Unreviewed upstream wording.', html)
        self.assertEqual(self.read(), data)

    def test_correcting_website_faq_changes_no_package_or_release_catalog(self):
        before = {path.name: path.read_bytes() for path in (self.root / 'downloads').iterdir()}
        data = self.read()
        data['releases'][0]['faq'][0]['answerHtml'] = '<p>Clearer controls.</p>'
        self.write(data)
        update_release.update(self.root)
        self.assertIn('Clearer controls.', self.page.read_text())
        self.assertEqual(before, {path.name: path.read_bytes() for path in (self.root / 'downloads').iterdir()})

    def test_new_release_without_prepared_faq_stops_rendering(self):
        newer, _ = fixtures.sample_catalog('1.0.75')
        for edition in newer['editions']:
            edition['downloadUrl'] = f'https://github.com/dqm-psx/patch/releases/download/v1.0.75/{edition["file"]}'
        original = self.page.read_bytes()
        with self.assertRaisesRegex(ValueError, 'v1.0.75 has not been prepared'):
            update_release.rendered_page(self.root, {'schemaVersion': 1, 'releases': [newer, self.record]})
        self.assertEqual(self.page.read_bytes(), original)

    def test_future_faq_stays_hidden_until_its_release_is_present(self):
        newer, _ = fixtures.sample_catalog('1.0.75')
        newer['faq'][0]['answerHtml'] = '<p>New behavior only in the next release.</p>'
        self.fixture.write_website_faq(self.record, newer)
        html = update_release.feature_faq([self.record], self.root)
        self.assertIn('Hold <strong>R1</strong>', html)
        self.assertNotIn('New behavior', html)
        newer['publishedAt'] = '2026-11-12T00:00:00Z'
        self.record['publishedAt'] = '2026-11-11T00:00:00Z'
        html = update_release.feature_faq([self.record, newer], self.root)
        self.assertIn('New behavior only in the next release.', html)

    def test_explicit_preparation_preserves_corrections_and_reports_source_suggestions(self):
        data = self.read()
        data['releases'][0]['faq'][0]['answerHtml'] = '<p>Reviewed wording carried forward.</p>'
        self.write(data)
        newer, _ = fixtures.sample_catalog('1.0.75')
        newer['faq'][0]['answerHtml'] = '<p>Different suggested source wording.</p>'
        newer['faq'].append({'id': 'extra-help', 'section': 'quality-of-life',
                             'question': 'Another question?', 'answerHtml': '<p>Additional help.</p>',
                             'features': ['movement']})
        report = website_faq.prepare(newer, self.root)
        new_faq = self.read()['releases'][-1]['faq']
        self.assertEqual(new_faq[0]['answerHtml'], '<p>Reviewed wording carried forward.</p>')
        self.assertIn('extra-help', report['added'])
        self.assertIn('movement-settings', report['suggestions'])
        self.assertEqual(self.read()['releases'][0], data['releases'][0])

    def test_repeated_preparation_never_replaces_target_version_edits(self):
        data = self.read()
        data['releases'][0]['faq'][0]['answerHtml'] = '<p>Later website correction.</p>'
        self.write(data)
        report = website_faq.prepare(self.record, self.root)
        self.assertEqual(self.read(), data)
        self.assertIn('movement-settings', report['suggestions'])

    def add_movement_feature(self, record):
        record['features'].append({'id': 'movement-upgrade', 'name': 'More movement options',
                                   'category': 'quality-of-life', 'requires': ['movement'],
                                   'introduced': record['version']})
        record['faq'][0]['features'].append('movement-upgrade')
        record['faq'][0]['answerHtml'] = '<p>Suggested wording for the extra movement setting.</p>'
        enhanced = next(edition for edition in record['editions'] if edition['id'] == 'enhanced')
        enhanced['features'].append('movement-upgrade')
        enhanced['build']['features'] = list(enhanced['features'])
        identity = {key: value for key, value in enhanced['build'].items() if key != 'buildId'}
        enhanced['build']['buildId'] = hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    def test_new_feature_can_extend_a_reviewed_answer_without_replacing_wording(self):
        data = self.read()
        data['releases'][0]['faq'][0]['answerHtml'] = '<p>Reviewed website wording.</p>'
        self.write(data)
        newer, _ = fixtures.sample_catalog('1.0.75')
        self.add_movement_feature(newer)
        report = website_faq.prepare(newer, self.root)
        answer = self.read()['releases'][-1]['faq'][0]
        self.assertEqual(answer['answerHtml'], '<p>Reviewed website wording.</p>')
        self.assertEqual(answer['features'], ['movement', 'movement-upgrade'])
        self.assertIn('movement-settings', report['suggestions'])
        website_faq.apply([newer], self.root)
        self.assertEqual(self.read()['releases'][0], data['releases'][0])

    def test_repreparing_changed_build_adds_facts_and_new_answers_preserving_edits(self):
        data = self.read()
        data['releases'][0]['faq'][0]['answerHtml'] = '<p>Edited during release review.</p>'
        self.write(data)
        self.add_movement_feature(self.record)
        self.record['faq'].append({'id': 'extra-setting', 'section': 'quality-of-life',
                                   'question': 'How does the extra setting work?',
                                   'answerHtml': '<p>New suggested explanation.</p>',
                                   'features': ['movement-upgrade']})
        report = website_faq.prepare(self.record, self.root)
        answers = self.read()['releases'][0]['faq']
        self.assertEqual(answers[0]['answerHtml'], '<p>Edited during release review.</p>')
        self.assertEqual(answers[0]['features'], ['movement', 'movement-upgrade'])
        self.assertIn('extra-setting', report['added'])
        self.assertIn('movement-settings', report['suggestions'])
        website_faq.apply([self.record], self.root)

    def test_later_published_backport_does_not_replace_newer_faq(self):
        newer, _ = fixtures.sample_catalog('1.0.75')
        newer['faq'][0]['answerHtml'] = '<p>Newer released behavior.</p>'
        newer['publishedAt'] = '2026-11-11T00:00:00Z'
        self.record['publishedAt'] = '2026-11-12T00:00:00Z'
        self.fixture.write_website_faq(self.record, newer)
        data = self.read()
        data['releases'][-1]['faq'][0]['answerHtml'] = '<p>Corrected newer released behavior.</p>'
        self.write(data)
        html = update_release.feature_faq([self.record, newer], self.root)
        self.assertIn('Corrected newer released behavior.', html)
        self.assertNotIn('Hold <strong>R1</strong>', html)

    def test_invalid_website_html_is_rejected_without_rendering(self):
        data = self.read()
        data['releases'][0]['faq'][0]['answerHtml'] = '<p onclick="bad()">Unsafe</p>'
        self.write(data)
        original = self.page.read_bytes()
        with self.assertRaisesRegex(ValueError, 'attributes'):
            update_release.update(self.root)
        self.assertEqual(self.page.read_bytes(), original)

    def test_preparation_checks_package_bytes_before_editing_website(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            (bundle / 'release.json').write_text(json.dumps(self.record))
            for name, data in self.packages.items():
                (bundle / name).write_bytes(data + b'corrupt')
            original = self.path.read_bytes()
            with self.assertRaisesRegex(ValueError, 'size or SHA-256 mismatch'):
                prepare_website_release.prepare(bundle, self.root)
            self.assertEqual(self.path.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
