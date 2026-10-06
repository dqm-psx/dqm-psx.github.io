"""Validate the latest package and write its static download card.

Run after editing downloads/releases.json. --check validates without writing.
The generated HTML is committed, so viewing the site needs no build or JS.
"""
import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
START, END = '<!-- release:begin -->', '<!-- release:end -->'


def download_card(release):
    version = release['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Release version must contain three numeric components')
    filename = f'DQM1-2-English-v{version}-public.zip'
    if release['file'] != filename:
        raise ValueError('Package filename does not match the release version')
    package = ROOT / 'downloads' / filename
    data = package.read_bytes()
    if len(data) != release['bytes'] or hashlib.sha256(data).hexdigest() != release['sha256']:
        raise ValueError('Package size or SHA-256 differs from the release record')
    stem = f'DQM1-2-English-v{version}'
    contents = [stem + '.bps', stem + '.cue', 'README.txt']
    if release['contents'] != contents:
        raise ValueError('Expected only the versioned BPS, matching CUE, and README')
    with zipfile.ZipFile(package) as archive:
        if sorted(archive.namelist()) != sorted(contents) or archive.testzip() is not None:
            raise ValueError('Package file list or ZIP integrity check failed')
        cue = archive.read(stem + '.cue').decode('ascii').splitlines()
        if cue != [f'FILE "{stem}.bin" BINARY', '  TRACK 01 MODE2/2352', '    INDEX 01 00:00:00']:
            raise ValueError('CUE does not reference the matching BIN and track format')
    notes = release.get('notes')
    if not isinstance(notes, list) or not notes or not all(isinstance(n, str) and n.strip() for n in notes):
        raise ValueError('The latest release needs a nonempty list of release notes')
    items = ''.join(f'<li>{escape(note)}</li>' for note in notes)
    return f'''          <div class="release-download" aria-labelledby="release-title">
            <div class="release-heading"><h3 id="release-title">{escape(release['name'])}</h3><span class="release-version">v{version}</span></div>
            <p>Includes the BPS patch, matching CUE file, and README.</p>
            <a class="button button-gold" href="downloads/{filename}" download="{filename}"><span aria-hidden="true">↓</span> Download v{version}</a>
            <span class="download-meta">ZIP archive <span aria-hidden="true">·</span> {len(data) / 1_000_000:.2f} MB</span>
            <details class="release-notes"><summary>Release notes</summary><ul>{items}</ul><p>See the included README for the full change history and credits.</p></details>
          </div>
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'downloads/releases.json').read_text(encoding='utf-8'))
    if manifest.get('schemaVersion') != 1 or not manifest.get('releases'):
        raise ValueError('Unsupported or empty release manifest')
    card = download_card(manifest['releases'][0])
    page = ROOT / 'index.html'
    source = page.read_text(encoding='utf-8')
    if source.count(START) != 1 or source.count(END) != 1:
        raise ValueError('Expected exactly one pair of release markers in index.html')
    before, rest = source.split(START, 1)
    _, after = rest.split(END, 1)
    updated = before + START + '\n' + card + '          ' + END + after
    if args.check:
        if updated != source:
            raise ValueError('Download card is stale; run python tools/update_release.py')
        print('Release package and static download card verified.')
    else:
        page.write_text(updated, encoding='utf-8', newline='\n')
        print('Updated the static download card from downloads/releases.json.')


if __name__ == '__main__':
    main()
