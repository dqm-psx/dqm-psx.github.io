"""Validate the public release contract produced by the game's release builder."""
import hashlib
from html.parser import HTMLParser
from io import BytesIO
import json
import re
import struct
from urllib.parse import urlsplit
import zipfile
import zlib


VERSION = re.compile(r'(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){2}')
IDENTIFIER = re.compile(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*')
SHA256 = re.compile(r'[a-f0-9]{64}')
SOURCE_IMAGE = {
    'bytes': 260975568,
    'sha256': 'a1217657786430ac1c3ad71f16cdadb65d47b0df9a7e30278900651c1f1eec29',
}
EDITION_NAMES = {'enhanced': 'Enhanced', 'translation-only': 'Translation only'}
SECTIONS = {
    'restored-content': ('faq-content', 'Restored content'),
    'quality-of-life': ('faq-quality', 'Quality of life'),
    'additional-content': ('faq-additions', 'Additional content'),
    'bug-fixes': ('faq-fixes', 'Original game bug fixes'),
}
CATEGORIES = {'restored-content', 'quality-of-life', 'additional-content', 'bug-fix'}
UPSTREAM = 'https://github.com/dqm-psx/patch'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value):
    return (isinstance(value, str) and bool(value.strip())
            and not any(ord(c) < 32 or ord(c) == 127 for c in value))


def identifiers(values, field):
    require(isinstance(values, list) and all(isinstance(v, str) and IDENTIFIER.fullmatch(v) for v in values),
            field + ' must contain feature identifiers')
    require(len(set(values)) == len(values), field + ' contains duplicates')
    return set(values)


class AnswerHTML(HTMLParser):
    """Reject executable markup while retaining the FAQ's established rich text."""
    tags = {'p', 'strong', 'em', 'a', 'ul', 'ol', 'li', 'code', 'pre', 'br', 'dl', 'dt', 'dd'}

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.content = []
        self.feed(html)
        self.close()
        require(not self.stack and ''.join(self.content).strip(), 'FAQ answer must contain complete HTML and text')

    def handle_starttag(self, tag, attrs):
        require(tag in self.tags, 'Unsupported FAQ HTML tag: ' + tag)
        require(not attrs or (tag == 'a' and len(attrs) == 1 and attrs[0][0] == 'href'),
                'Unsupported FAQ HTML attributes')
        if tag == 'a':
            require(bool(attrs), 'FAQ links need an href')
            href = attrs[0][1]
            require(text(href), 'FAQ link must be nonempty')
            url = urlsplit(href)
            fragment = href.startswith('#') and IDENTIFIER.fullmatch(href[1:])
            public = url.scheme == 'https' and bool(url.netloc) and not url.username and not url.password
            require(fragment or public, 'FAQ links must use HTTPS or a local answer anchor')
        if tag != 'br':
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        require(tag == 'br', 'Only br may be self-closing in FAQ HTML')
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        require(bool(self.stack) and self.stack[-1] == tag, 'Unbalanced FAQ HTML')
        self.stack.pop()

    def handle_data(self, value):
        self.content.append(value)

    def handle_decl(self, decl):
        raise ValueError('Declarations are not allowed in FAQ HTML')

    def handle_comment(self, data):
        raise ValueError('Comments are not allowed in FAQ HTML')


def edition_url(record, edition):
    expected = f'{UPSTREAM}/releases/download/v{record["version"]}/{edition["file"]}'
    if 'downloadUrl' in edition:
        require(edition['downloadUrl'] == expected, 'Edition downloadUrl must be the pinned public release asset')
        return expected
    return 'downloads/' + edition['file']


def validate_catalog(record):
    require(isinstance(record, dict) and record.get('schemaVersion') == 2, 'Expected release catalog schemaVersion 2')
    version = record.get('version')
    require(isinstance(version, str) and VERSION.fullmatch(version), 'Invalid release catalog version')
    require(record.get('defaultEdition') == 'enhanced', 'Release catalog default edition must be enhanced')
    require(record.get('sourceImage') == SOURCE_IMAGE, 'Release catalog source image differs from the Japanese original')
    notes = record.get('notes')
    require(isinstance(notes, list) and notes and all(text(note) for note in notes), 'Release catalog needs release notes')
    contributors = record.get('contributors')
    require(isinstance(contributors, list) and all(text(name) for name in contributors), 'Invalid release contributors')
    if 'releaseUrl' in record:
        require(record['releaseUrl'] == f'{UPSTREAM}/releases/tag/v{version}', 'Unexpected release URL')
    features = record.get('features')
    require(isinstance(features, list) and features and all(isinstance(f, dict) for f in features),
            'Release catalog needs feature information')
    all_ids = identifiers([f.get('id') for f in features], 'Features')
    for feature in features:
        require(text(feature.get('name')) and feature.get('category') in CATEGORIES, 'Incomplete feature information')
        requires = identifiers(feature.get('requires'), 'Feature dependencies')
        require(requires <= all_ids and feature['id'] not in requires, 'Unknown or self-referencing feature dependency')
        introduced = feature.get('introduced')
        require(introduced is None or (isinstance(introduced, str) and VERSION.fullmatch(introduced)),
                'Invalid feature introduction version')
    faq = record.get('faq')
    require(isinstance(faq, list) and faq and all(isinstance(answer, dict) for answer in faq),
            'Release catalog needs FAQ explanations')
    identifiers([answer.get('id') for answer in faq], 'FAQ anchors')
    explained = set()
    for answer in faq:
        require(answer.get('section') in SECTIONS and text(answer.get('question')), 'Incomplete FAQ question')
        require(isinstance(answer.get('answerHtml'), str), 'FAQ answerHtml is missing')
        AnswerHTML(answer['answerHtml'])
        covered = identifiers(answer.get('features'), 'FAQ features')
        require(covered <= all_ids, 'FAQ references an unknown feature')
        explained.update(covered)
    require(explained == all_ids, 'Missing FAQ explanations for: ' + ', '.join(sorted(all_ids - explained)))
    editions = record.get('editions')
    require(isinstance(editions, list) and len(editions) == 2 and all(isinstance(e, dict) for e in editions),
            'Both release editions must be present')
    require({e.get('id') for e in editions} == set(EDITION_NAMES), 'Both release editions must be present')
    available = set()
    for edition in editions:
        name = edition['id']
        stem = f'DQM1-2-English-v{version}-{name}'
        require(edition.get('name') == EDITION_NAMES[name] and text(edition.get('description')),
                'Invalid edition name or description')
        require(edition.get('file') == stem + '.zip', 'Edition ZIP name differs from its version and edition')
        require(type(edition.get('bytes')) is int and edition['bytes'] > 0
                and isinstance(edition.get('sha256'), str) and SHA256.fullmatch(edition['sha256']),
                'Edition needs a positive byte size and SHA-256')
        require(edition.get('contents') == [stem + '.bps', stem + '.cue', 'README.txt', 'BUILD.json'],
                'Edition file list must contain its BPS, CUE, README and BUILD.json')
        selected = identifiers(edition.get('features'), 'Edition features')
        require(selected <= all_ids, 'Edition references an unknown feature')
        available.update(selected)
        for feature in features:
            if feature['id'] in selected:
                require(set(feature['requires']) <= selected, 'Edition omits dependencies for ' + feature['id'])
        edition_url(record, edition)
        build = edition.get('build')
        require(isinstance(build, dict) and build.get('schemaVersion') == 1
                and build.get('version') == version and build.get('edition') == name,
                'Build identity differs from its release edition')
        require(isinstance(build.get('buildId'), str) and SHA256.fullmatch(build['buildId']), 'Missing build identifier')
        identity = {key: value for key, value in build.items() if key != 'buildId'}
        expected_id = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
        require(build['buildId'] == expected_id, 'Build identifier differs from its recorded configuration')
        if 'sourceModified' in build:
            require(type(build['sourceModified']) is bool, 'sourceModified must be a boolean')
        require(isinstance(build.get('sourceRevision'), str) and re.fullmatch(r'[a-f0-9]{40}', build['sourceRevision']),
                'Missing build source revision')
        require(text(build.get('translation')) and text(build.get('language')), 'Missing translation or language edition')
        fonts = build.get('fonts')
        require(isinstance(fonts, dict) and set(fonts) == {'dialogue', 'menu', 'battle'}
                and all(text(font) for font in fonts.values()), 'Missing build font choices')
        require(build.get('features') == edition['features'] and build.get('sourceImage') == SOURCE_IMAGE,
                'Build features or original image differ from the edition')
        output = build.get('output')
        require(isinstance(output, dict) and output.get('file') == stem + '.bin'
                and type(output.get('bytes')) is int and output['bytes'] > 0
                and isinstance(output.get('sha256'), str) and SHA256.fullmatch(output['sha256']),
                'Missing output image identity')
    require(available == all_ids, 'Catalog describes features unavailable in either release edition')


def bps_sizes(patch):
    require(len(patch) >= 19 and patch.startswith(b'BPS1'), 'Package does not contain a BPS patch')
    require(zlib.crc32(patch[:-4]) == struct.unpack('<I', patch[-4:])[0], 'BPS patch checksum mismatch')
    at = 4
    sizes = []
    for _ in range(2):
        value, shift = 0, 1
        while True:
            require(at < min(len(patch) - 12, 24), 'Invalid BPS size header')
            byte = patch[at]
            at += 1
            value += (byte & 0x7f) * shift
            if byte & 0x80:
                break
            shift <<= 7
            value += shift
        sizes.append(value)
    return sizes


def validate_edition_package(record, edition, data):
    require(len(data) == edition['bytes'] and hashlib.sha256(data).hexdigest() == edition['sha256'],
            'Edition package size or SHA-256 mismatch: ' + edition['file'])
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            require(sorted(archive.namelist()) == sorted(edition['contents']) and archive.testzip() is None,
                    'Edition ZIP contents or integrity differ from its manifest')
            bps, cue = edition['contents'][:2]
            output = edition['build']['output']
            require(archive.read(cue).decode('ascii').splitlines() ==
                    [f'FILE "{output["file"]}" BINARY', '  TRACK 01 MODE2/2352', '    INDEX 01 00:00:00'],
                    'Edition CUE differs from its output BIN')
            require(json.loads(archive.read('BUILD.json').decode('utf-8')) == edition['build'],
                    'BUILD.json differs from its release metadata')
            require(bool(archive.read('README.txt').decode('utf-8-sig').strip()), 'Edition README is empty')
            require(bps_sizes(archive.read(bps)) == [SOURCE_IMAGE['bytes'], output['bytes']],
                    'BPS source or output size differs from the build record')
    except (zipfile.BadZipFile, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError('Invalid release package: ' + edition['file']) from error
