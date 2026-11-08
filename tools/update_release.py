"""Validate retained releases and update the static download card and credits.

Run after editing downloads/releases.json. --check validates without writing.
The generated HTML is committed, so viewing the site needs no build or JS.
An optional downloadUrl selects a pinned public dqm-psx/patch release asset.
Local packages remain required for integrity checks and historical credits.
"""
import argparse
import hashlib
from html import escape
from io import BytesIO
import json
import os
from pathlib import Path
import re
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
START, END = '<!-- release:begin -->', '<!-- release:end -->'
CREDITS_START, CREDITS_END = '<!-- contributors:begin -->', '<!-- contributors:end -->'
HEADING = re.compile(r"[A-Z][A-Z0-9 '&/():-]*")
HANDLE = r'[\w][\w.-]*'
THANKS_NAMES = re.compile(rf'{HANDLE}(?:, {HANDLE})*(?:,? and {HANDLE})?')
COLLECTIVE_CREDITS = {'all', 'everyone', 'everybody', 'contributors', 'testers', 'team', 'you', 'those'}
# Recognize unnamed gratitude without mistaking it for a contributor handle.
# Keep the activity vocabulary bounded so a mixed or unfamiliar credit still fails.
CONTRIBUTION = r'(?:translation suggestions|reports|suggestions|feedback|testing)'
COLLECTIVE_THANKS = re.compile(
    rf'thanks(?: also)?(?: to)? (?:everyone|everybody) (?:who contributed|for) '
    rf'{CONTRIBUTION}(?:, {CONTRIBUTION})*(?:,? and {CONTRIBUTION})?[.!?](?= |$)',
    re.IGNORECASE,
)


def package_identity(release):
    """Keep package names and remote release paths tied to the recorded version."""
    version = release['version']
    if not isinstance(version, str) or not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Release version must contain three numeric components')
    filename = f'DQM1-2-English-v{version}-public.zip'
    if release['file'] != filename:
        raise ValueError('Package filename does not match the release version')
    return version, filename


def download_target(release):
    """Validate a configured public asset URL; availability is checked at release time."""
    version, filename = package_identity(release)
    if 'downloadUrl' not in release:
        return f'downloads/{filename}'
    expected = f'https://github.com/dqm-psx/patch/releases/download/v{version}/{filename}'
    if release['downloadUrl'] != expected:
        raise ValueError(f'downloadUrl must be the pinned dqm-psx/patch asset URL: {expected}')
    return expected


def validate_package(release, root):
    """Return the size and README from the same bytes whose hash was checked."""
    version, filename = package_identity(release)
    download_target(release)
    data = (root / 'downloads' / filename).read_bytes()
    if len(data) != release['bytes'] or hashlib.sha256(data).hexdigest() != release['sha256']:
        raise ValueError(f'Package size or SHA-256 differs from the release record: {filename}')
    stem = f'DQM1-2-English-v{version}'
    contents = [stem + '.bps', stem + '.cue', 'README.txt']
    if release['contents'] != contents:
        raise ValueError('Expected only the versioned BPS, matching CUE, and README')
    with zipfile.ZipFile(BytesIO(data)) as archive:
        if sorted(archive.namelist()) != sorted(contents) or archive.testzip() is not None:
            raise ValueError('Package file list or ZIP integrity check failed')
        cue = archive.read(stem + '.cue').decode('ascii').splitlines()
        if cue != [f'FILE "{stem}.bin" BINARY', '  TRACK 01 MODE2/2352', '    INDEX 01 00:00:00']:
            raise ValueError('CUE does not reference the matching BIN and track format')
        readme = archive.read('README.txt').decode('utf-8-sig')
    return len(data), readme


def download_card(release, package_size):
    version, filename = package_identity(release)
    target = download_target(release)
    # Cross-origin GitHub downloads use the asset response's Content-Disposition.
    download_attribute = f' download="{filename}"' if 'downloadUrl' not in release else ''
    notes = release.get('notes')
    if not isinstance(notes, list) or not notes or not all(isinstance(n, str) and n.strip() for n in notes):
        raise ValueError('The latest release needs a nonempty list of release notes')
    items = ''.join(f'<li>{escape(note)}</li>' for note in notes)
    return f'''          <div class="release-download" aria-labelledby="release-title">
            <div class="release-heading"><h3 id="release-title">{escape(release['name'])}</h3><span class="release-version">v{version}</span></div>
            <p>Includes the BPS patch, matching CUE file, and README.</p>
            <a class="button button-gold" href="{escape(target, quote=True)}"{download_attribute}><span aria-hidden="true">↓</span> Download v{version}</a>
            <span class="download-meta">ZIP archive <span aria-hidden="true">·</span> {package_size / 1_000_000:.2f} MB</span>
            <details class="release-notes"><summary>Release notes</summary><ul>{items}</ul><p>See the included README for the full change history and credits.</p></details>
          </div>
'''


def valid_name(value):
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError('Contributor names must be nonempty single-line text')
    return value.strip()


def readme_contributors(readme):
    """Read explicit credits only; unfamiliar thanks must be clarified, not guessed."""
    lines = readme.splitlines()
    sections = {}
    covered = set()
    for title in ('PUBLIC RELEASE HIGHLIGHTS', 'CONTRIBUTORS'):
        starts = [i for i, line in enumerate(lines) if line == title]
        if len(starts) > 1:
            raise ValueError(f'Duplicate README section: {title}')
        if not starts:
            continue
        start = starts[0] + 1
        end = next((i for i in range(start, len(lines)) if HEADING.fullmatch(lines[i])), len(lines))
        sections[title] = lines[start:end]
        covered.update(range(start, end))
    names = []
    highlights = sections.get('PUBLIC RELEASE HIGHLIGHTS', [])
    # Keep paragraph boundaries, but join the release README's hard-wrapped lines.
    for paragraph in re.split(r'\n\s*\n', '\n'.join(highlights)):
        paragraph = ' '.join(paragraph.split())
        for thanks in re.finditer(r'\bthanks\b', paragraph, re.IGNORECASE):
            if COLLECTIVE_THANKS.match(paragraph[thanks.start():]):
                continue
            match = re.match(
                r'thanks(?: also)?(?: to)? (.+?) for ([^.!?]+)[.!?](?= |$)',
                paragraph[thanks.start():], re.IGNORECASE,
            )
            if not match or not THANKS_NAMES.fullmatch(match[1]):
                raise ValueError('Ambiguous README thanks; use explicit handles or a CONTRIBUTORS section')
            credited = re.split(r',? and |, ', match[1])
            parallel_credit = re.search(rf'(?:,\s*|\band\s+)(?:to\s+)?{HANDLE}\s+for\b',
                                        match[2], re.IGNORECASE)
            if any(name.casefold() in COLLECTIVE_CREDITS for name in credited) or parallel_credit:
                raise ValueError('Ambiguous README thanks; use explicit handles or a CONTRIBUTORS section')
            names.extend(credited)
    for line in sections.get('CONTRIBUTORS', []):
        if not line.strip():
            continue
        if not line.startswith('- '):
            raise ValueError('CONTRIBUTORS must contain only one "- Name" entry per line')
        names.append(valid_name(line[2:]))
    if any(re.search(r'\bthanks\b', line, re.IGNORECASE) for i, line in enumerate(lines) if i not in covered):
        raise ValueError('README thanks outside PUBLIC RELEASE HIGHLIGHTS; use a CONTRIBUTORS section')
    return names


def project_contributors(root):
    data = json.loads((root / 'data/contributors.json').read_text(encoding='utf-8'))
    if data.get('schemaVersion') != 1 or not isinstance(data.get('contributors'), list):
        raise ValueError('Unsupported project contributors data')
    names = []
    for record in data['contributors']:
        names.append(valid_name(record['name']))
        for field in ('contribution', 'source'):
            if not isinstance(record.get(field), str) or not record[field].strip():
                raise ValueError(f'Project contributor needs a recorded {field}')
    return names


def project_contributor_aliases(root):
    """Resolve only aliases explicitly recorded with a project's named credit."""
    records = json.loads((root / 'data/contributors.json').read_text(encoding='utf-8'))['contributors']
    aliases = {}
    for record in records:
        name = valid_name(record['name'])
        aliases.setdefault(name.casefold(), name)
    for record in records:
        name = aliases[valid_name(record['name']).casefold()]
        values = record.get('aliases', [])
        if not isinstance(values, list):
            raise ValueError('Contributor aliases must be a list of names')
        for value in values:
            key = valid_name(value).casefold()
            if key in aliases and aliases[key] != name:
                raise ValueError('Contributor alias belongs to more than one name')
            aliases[key] = name
    return aliases


def contributor_list(names, aliases=None):
    aliases = aliases or {}
    unique = {}
    for name in names:
        name = valid_name(name)
        name = aliases.get(name.casefold(), name)
        unique.setdefault(name.casefold(), name)
    ordered = sorted(unique.values(), key=lambda name: (name.lstrip('_').casefold(), name.casefold()))
    items = ''.join(f'                  <li>{escape(name)}</li>\n' for name in ordered)
    return '                <ul class="contributor-list" id="contributor-list">\n' + items + '                </ul>\n'


def replace_block(source, start, end, body, indent):
    if source.count(start) != 1 or source.count(end) != 1 or source.index(start) >= source.index(end):
        raise ValueError(f'Expected exactly one ordered pair of {start} / {end} markers in index.html')
    before, rest = source.split(start, 1)
    _, after = rest.split(end, 1)
    return before + start + '\n' + body + ' ' * indent + end + after


def update(root=ROOT, check=False):
    manifest = json.loads((root / 'downloads/releases.json').read_text(encoding='utf-8'))
    releases = manifest.get('releases')
    if manifest.get('schemaVersion') != 1 or not isinstance(releases, list) or not releases:
        raise ValueError('Unsupported or empty release manifest')
    if len({release['version'] for release in releases}) != len(releases):
        raise ValueError('Duplicate release version in manifest')
    packages = [validate_package(release, root) for release in releases]
    names = project_contributors(root)
    aliases = project_contributor_aliases(root)
    for release, (_, readme) in zip(releases, packages):
        try:
            names.extend(readme_contributors(readme))
        except ValueError as error:
            raise ValueError(f'{release["file"]}: {error}') from error
    card = download_card(releases[0], packages[0][0])
    credits = contributor_list(names, aliases)
    page = root / 'index.html'
    source = page.read_text(encoding='utf-8')
    updated = replace_block(source, START, END, card, 10)
    updated = replace_block(updated, CREDITS_START, CREDITS_END, credits, 16)
    if check:
        if updated != source:
            raise ValueError('Download card or contributor list is stale; run python tools/update_release.py')
        return
    # Nothing is written until every package, credit, and marker has been checked.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n', dir=root,
                                         prefix='.index-', suffix='.tmp', delete=False) as output:
            temporary = Path(output.name)
            output.write(updated)
        os.replace(temporary, page)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    update(check=args.check)
    print('Release packages, download card, and contributor list verified.' if args.check
          else 'Updated the static download card and contributor list.')


if __name__ == '__main__':
    main()
