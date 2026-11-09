"""Validate retained releases and update the static download card and credits.

Run after editing downloads/releases.json. --check validates without writing.
The generated HTML is committed, so viewing the site needs no build or JS.
An optional downloadUrl selects a pinned public dqm-psx/patch release asset.
Public-only releases keep verified credits in the manifest. Bundled releases
continue to validate their original ZIPs.
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
VERSION = re.compile(r'(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){2}')
START, END = '<!-- release:begin -->', '<!-- release:end -->'
HERO_START, HERO_END = '<!-- hero-download:begin -->', '<!-- hero-download:end -->'
INSTALL_START, INSTALL_END = '<!-- install-download:begin -->', '<!-- install-download:end -->'
CREDITS_START, CREDITS_END = '<!-- contributors:begin -->', '<!-- contributors:end -->'
AI_START, AI_END = '<!-- ai-contributors:begin -->', '<!-- ai-contributors:end -->'
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
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        raise ValueError('Release version must contain three numeric components')
    filename = release['file']
    stem = f'DQM1-2-English-v{version}'
    if filename not in (stem + '.zip', stem + '-public.zip'):
        raise ValueError('Package filename does not match the release version')
    return version, filename


def package_contents(version):
    stem = f'DQM1-2-English-v{version}'
    return [stem + '.bps', stem + '.cue', 'README.txt']


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
    _, filename = package_identity(release)
    return validate_package_bytes(release, (root / 'downloads' / filename).read_bytes())


def validate_package_bytes(release, data):
    version, filename = package_identity(release)
    download_target(release)
    if len(data) != release['bytes'] or hashlib.sha256(data).hexdigest() != release['sha256']:
        raise ValueError(f'Package size or SHA-256 differs from the release record: {filename}')
    stem = f'DQM1-2-English-v{version}'
    contents = package_contents(version)
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


def download_attributes(release):
    target = download_target(release)
    # Keep published asset names and historical URLs intact. Browsers honor a
    # suggested filename for our same-origin mirror; GitHub names its own files.
    suggested = f'DQM1-2-English-v{release["version"]}.zip'
    download_attribute = f' download="{suggested}"' if 'downloadUrl' not in release else ''
    return f'href="{escape(target, quote=True)}"{download_attribute}'


def download_card(release):
    version, _ = package_identity(release)
    notes = release.get('notes')
    if not isinstance(notes, list) or not notes or not all(isinstance(n, str) and n.strip() for n in notes):
        raise ValueError('The latest release needs a nonempty list of release notes')
    items = ''.join(f'<li>{escape(note)}</li>' for note in notes)
    release_link = (f'<p><a href="https://github.com/dqm-psx/patch/releases/tag/v{version}">'
                    'View release on GitHub</a></p>' if 'downloadUrl' in release else '')
    return f'''          <article class="release-download" aria-labelledby="release-title">
            <div class="release-heading">
              <div class="release-description">
                <h3 id="release-title">Latest patch <span class="release-version">v{version}</span></h3>
                <p>{escape(release['name'])} with restored content and quality-of-life improvements.</p>
              </div>
            </div>
            <details id="release-notes" class="release-notes"><summary>What’s new in v{version}?</summary><ul>{items}</ul>{release_link}</details>
            <details class="release-notes"><summary>Verify the ZIP download</summary><p>SHA-256 · {release['bytes']:,} bytes</p><code class="file-hash">{release['sha256']}</code></details>
          </article>
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
    aliases = {}
    ai_names = set()
    for record in data['contributors']:
        name = valid_name(record['name'])
        names.append(name)
        aliases.setdefault(name.casefold(), name)
        if record.get('creditType') == 'ai-assistance':
            ai_names.add(name.casefold())
        for field in ('contribution', 'source'):
            if not isinstance(record.get(field), str) or not record[field].strip():
                raise ValueError(f'Project contributor needs a recorded {field}')
    for record in data['contributors']:
        name = aliases[valid_name(record['name']).casefold()]
        values = record.get('aliases', [])
        if not isinstance(values, list):
            raise ValueError('Contributor aliases must be a list of names')
        for value in values:
            key = valid_name(value).casefold()
            if key in aliases and aliases[key] != name:
                raise ValueError('Contributor alias belongs to more than one name')
            aliases[key] = name
    return names, aliases, ai_names


def contributor_items(names, aliases, ai_names):
    unique = {}
    for name in names:
        name = valid_name(name)
        name = aliases.get(name.casefold(), name)
        unique.setdefault(name.casefold(), name)
    ordered = sorted(unique.values(), key=lambda name: (name.lstrip('_').casefold(), name.casefold()))
    people = []
    assistants = []
    for name in ordered:
        items = assistants if name.casefold() in ai_names else people
        items.append(f'                <li>{escape(name)}</li>\n')
    return ''.join(people), ''.join(assistants)


def replace_block(source, start, end, body, indent):
    if source.count(start) != 1 or source.count(end) != 1 or source.index(start) >= source.index(end):
        raise ValueError(f'Expected exactly one ordered pair of {start} / {end} markers in index.html')
    before, rest = source.split(start, 1)
    _, after = rest.split(end, 1)
    return before + start + '\n' + body + ' ' * indent + end + after


def rendered_page(root, manifest):
    releases = manifest.get('releases')
    if manifest.get('schemaVersion') != 1 or not isinstance(releases, list) or not releases:
        raise ValueError('Unsupported or empty release manifest')
    if len({release['version'] for release in releases}) != len(releases):
        raise ValueError('Duplicate release version in manifest')
    names, aliases, ai_names = project_contributors(root)
    for release in releases:
        version, filename = package_identity(release)
        download_target(release)
        try:
            if (root / 'downloads' / filename).is_file() or 'downloadUrl' not in release:
                _, readme = validate_package(release, root)
                names.extend(readme_contributors(readme))
            else:
                # These records are created only after the release sync verifies
                # the public ZIP, its contents, matching CUE and original README.
                if (type(release.get('bytes')) is not int or release['bytes'] <= 0
                        or not re.fullmatch(r'[a-f0-9]{64}', release.get('sha256', ''))
                        or release.get('contents') != package_contents(version)
                        or not isinstance(release.get('contributors'), list)):
                    raise ValueError('Incomplete public release record')
                names.extend(valid_name(name) for name in release['contributors'])
        except ValueError as error:
            raise ValueError(f'{release["file"]}: {error}') from error
    current = releases[0]
    attributes = download_attributes(current)
    card = download_card(current)
    credits, ai_credits = contributor_items(names, aliases, ai_names)
    page = root / 'index.html'
    source = page.read_text(encoding='utf-8')
    hero_link = (f'            <a id="download" class="button button-gold" {attributes}>'
                 f'Download v{current["version"]} · {current["bytes"] / 1_000_000:.2f} MB</a>\n')
    install_link = f'                <a {attributes}>Download</a>\n'
    updated = replace_block(source, HERO_START, HERO_END, hero_link, 12)
    updated = replace_block(updated, INSTALL_START, INSTALL_END, install_link, 16)
    updated = replace_block(updated, START, END, card, 10)
    updated = replace_block(updated, CREDITS_START, CREDITS_END, credits, 16)
    return replace_block(updated, AI_START, AI_END, ai_credits, 16)


def update(root=ROOT, check=False):
    manifest = json.loads((root / 'downloads/releases.json').read_text(encoding='utf-8'))
    page = root / 'index.html'
    updated = rendered_page(root, manifest)
    if check:
        if updated != page.read_text(encoding='utf-8'):
            raise ValueError('Download, release details, or contributor list is stale; run python tools/update_release.py')
        return
    atomic_write(page, updated)


def atomic_write(path, content):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n', dir=path.parent,
                                         prefix=f'.{path.stem}-', suffix='.tmp', delete=False) as output:
            temporary = Path(output.name)
            output.write(content)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    update(check=args.check)
    print('Release packages, download, release details, and contributor list verified.' if args.check
          else 'Updated the static download, release details, and contributor list.')


if __name__ == '__main__':
    main()
