"""Import the latest publicly downloadable stable dqm-psx/patch release."""
import argparse
import json
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import update_release as site

UPSTREAM = 'https://github.com/dqm-psx/patch'
LATEST = 'https://api.github.com/repos/dqm-psx/patch/releases/latest'


def fetch(url):
    # Public visitors must be able to follow the same link. Do not send credentials.
    request = Request(url, headers={'User-Agent': 'dqm-psx-release-sync'})
    with urlopen(request, timeout=60) as response:
        return response.read()


def public_record(release, current, fetch_asset):
    tag = release['tag_name']
    version = tag.removeprefix('v')
    if (tag != 'v' + version or not site.VERSION.fullmatch(version)
            or release.get('draft') is not False or release.get('prerelease') is not False
            or not release.get('published_at')):
        raise ValueError('Expected a published stable release with a vMAJOR.MINOR.PATCH tag')
    if tuple(map(int, version.split('.'))) < tuple(map(int, current['version'].split('.'))):
        raise ValueError('Upstream latest is older than the current site release')

    stem = f'DQM1-2-English-{tag}'
    filenames = (stem + '.zip', stem + '-public.zip')
    assets = {a['name']: a for a in release['assets'] if a['name'] in filenames and a['state'] == 'uploaded'}
    if not assets or len({a.get('digest') for a in assets.values()}) != 1:
        raise ValueError('Expected a versioned patch ZIP with an unambiguous SHA-256')
    same_version = version == current['version']
    if same_version and current['file'] not in assets:
        raise ValueError('The previously published release asset is missing')
    filename = current['file'] if same_version else next(name for name in filenames if name in assets)
    asset = assets[filename]
    digest = re.fullmatch(r'sha256:([0-9a-f]{64})', asset.get('digest') or '')
    if not digest or type(asset['size']) is not int or asset['size'] <= 0:
        raise ValueError('The uploaded ZIP must declare its byte size and SHA-256')
    target = asset['browser_download_url']
    if target != f'{UPSTREAM}/releases/download/{tag}/{filename}':
        raise ValueError('Unexpected release asset URL')
    if same_version:
        if (digest[1], asset['size']) != (current['sha256'], current['bytes']):
            raise ValueError('The published package differs from the previously verified package')
        if current.get('downloadUrl') == target:
            return None
        record = current.copy()  # Preserve reviewed notes and historical provenance.
    else:
        notes = [line[2:].strip() for line in (release.get('body') or '').splitlines()
                 if line.startswith(('- ', '* ')) and line[2:].strip()]
        record = {'version': version, 'name': 'English translation', 'file': filename,
                  'bytes': asset['size'], 'sha256': digest[1], 'contents': site.package_contents(version),
                  'notes': notes or ['See the included README for the changes in this release.']}
    record['downloadUrl'] = target
    record['releaseUrl'] = f'{UPSTREAM}/releases/tag/{tag}'
    _, readme = site.validate_package_bytes(record, fetch_asset(target))
    record['contributors'] = site.readme_contributors(readme)
    return record


def sync(root=site.ROOT, fetch_url=fetch, *, dry_run=False):
    path = root / 'downloads/releases.json'
    previous = path.read_text(encoding='utf-8')
    manifest = json.loads(previous)
    releases = manifest['releases']
    current = releases[0]
    try:
        release = json.loads(fetch_url(LATEST))
    except HTTPError as error:
        if error.code == 404 and 'downloadUrl' not in current:
            error.close()
            site.validate_package(current, root)
            return 'No public latest release. The verified local download is active.'
        raise
    record = public_record(release, current, fetch_url)
    if record is None:
        return f'The site already uses the verified public v{current["version"]} asset.'
    if record['version'] == current['version']:
        releases[0] = record
    else:
        releases.insert(0, record)
    # Render before changing either file. A broken archive, credit or marker
    # must not leave a manifest that advertises an unverified patch.
    page = site.rendered_page(root, manifest)
    if dry_run:
        return f'Public v{record["version"]} verified and ready to import.'
    site.atomic_write(path, json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    try:
        site.atomic_write(root / 'index.html', page)
    except OSError:
        site.atomic_write(path, previous)
        raise
    return f'Updated the site to the verified public v{record["version"]} asset.'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Verify and render in memory')
    print(sync(dry_run=parser.parse_args().dry_run))
