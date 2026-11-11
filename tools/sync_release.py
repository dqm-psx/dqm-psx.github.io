"""Import the latest publicly downloadable stable dqm-psx/patch release."""
import argparse
import copy
import hashlib
import json
import os
import re
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

import release_catalog
import update_release as site

UPSTREAM = 'https://github.com/dqm-psx/patch'
LATEST = 'https://api.github.com/repos/dqm-psx/patch/releases/latest'
RELEASES = 'https://api.github.com/repos/dqm-psx/patch/releases?per_page=100&page='
LAST_LEGACY_VERSION = (1, 0, 73)


class NoApiRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        raise ValueError('GitHub release API redirected unexpectedly')


def fetch(url):
    headers = {'User-Agent': 'dqm-psx-release-sync'}
    # The workflow token raises the public API rate limit. Asset downloads use
    # public URLs without credentials, matching the visitor's access.
    api = url.startswith('https://api.github.com/repos/dqm-psx/patch/releases')
    token = os.environ.get('GITHUB_TOKEN') if api else None
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = Request(url, headers=headers)
    opener = build_opener(NoApiRedirect()).open if api else urlopen
    with opener(request, timeout=60) as response:
        return response.read()


def release_version(release):
    tag = release.get('tag_name', '')
    version = tag.removeprefix('v')
    if (tag != 'v' + version or not site.VERSION.fullmatch(version)
            or release.get('draft') is not False or release.get('prerelease') is not False
            or not release.get('published_at')):
        raise ValueError('Expected a published stable release with a vMAJOR.MINOR.PATCH tag')
    return version


def asset_for(release, filename):
    matches = [asset for asset in release['assets']
               if asset['name'] == filename and asset['state'] == 'uploaded']
    if len(matches) != 1:
        raise ValueError(f'Release v{release_version(release)} needs exactly one uploaded {filename}')
    asset = matches[0]
    expected = f'{UPSTREAM}/releases/download/{release["tag_name"]}/{filename}'
    if (asset.get('browser_download_url') != expected or type(asset.get('size')) is not int
            or asset['size'] <= 0 or not re.fullmatch(r'sha256:[0-9a-f]{64}', asset.get('digest') or '')):
        raise ValueError(f'Invalid release asset metadata: {filename}')
    return asset


def verified_asset(asset, fetch_asset):
    data = fetch_asset(asset['browser_download_url'])
    if len(data) != asset['size'] or 'sha256:' + hashlib.sha256(data).hexdigest() != asset['digest']:
        raise ValueError(f'Release asset size or checksum failed: {asset["name"]}')
    return data


def public_catalog(release, fetch_asset, *, verify_packages=True):
    version = release_version(release)
    metadata = asset_for(release, 'release.json')
    record = json.loads(verified_asset(metadata, fetch_asset))
    release_catalog.validate_catalog(record)
    if record['version'] != version:
        raise ValueError('Release tag and release.json version disagree')
    record['releaseUrl'] = f'{UPSTREAM}/releases/tag/v{version}'
    record['publishedAt'] = release['published_at']
    record['releaseId'] = release['id']
    record['metadataSha256'] = metadata['digest'].removeprefix('sha256:')
    for edition in record['editions']:
        asset = asset_for(release, edition['file'])
        if (edition['bytes'], edition['sha256']) != (asset['size'], asset['digest'].removeprefix('sha256:')):
            raise ValueError(f'Package differs from release.json: {edition["file"]}')
        edition['downloadUrl'] = asset['browser_download_url']
        if verify_packages:
            release_catalog.validate_edition_package(record, edition, verified_asset(asset, fetch_asset))
    return record


def stable_catalogs(fetch_url):
    page_number = 1
    while True:
        page = json.loads(fetch_url(RELEASES + str(page_number)))
        if not isinstance(page, list):
            raise ValueError('Expected the public release archive')
        for release in page:
            if (release.get('draft') is False and release.get('prerelease') is False
                    and any(asset['name'] == 'release.json' for asset in release['assets'])):
                yield release
        if len(page) < 100:
            return
        page_number += 1


def public_record(release, current, fetch_asset):
    version = release_version(release)
    tag = release['tag_name']
    if tuple(map(int, version.split('.'))) > LAST_LEGACY_VERSION:
        raise ValueError('New releases need release.json with both editions and complete feature FAQ entries')

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


def sync(root=site.ROOT, fetch_url=fetch, *, dry_run=False, include_history=False):
    path = root / 'downloads/releases.json'
    previous = path.read_text(encoding='utf-8')
    manifest = json.loads(previous)
    releases = manifest['releases']
    current = releases[0]
    try:
        release = json.loads(fetch_url(LATEST))
    except HTTPError as error:
        if error.code == 404 and current.get('schemaVersion') != 2 and 'downloadUrl' not in current:
            error.close()
            site.validate_package(current, root)
            return 'No public latest release. The verified local download is active.'
        raise
    version = release_version(release)
    previous_by_version = {item['version']: item for item in releases}
    if any(asset['name'] == 'release.json' for asset in release['assets']):
        record = public_catalog(release, fetch_url)
    else:
        known = previous_by_version.get(version)
        if known is not None and known.get('schemaVersion') == 2:
            raise ValueError('A catalog release has lost release.json')
        record = public_record(release, known or current, fetch_url) or copy.deepcopy(known)
    previous_by_version[version] = record
    if include_history:
        for archived in stable_catalogs(fetch_url):
            if archived['tag_name'] != release['tag_name']:
                historical = public_catalog(archived, fetch_url, verify_packages=False)
                previous_by_version[historical['version']] = historical
    manifest['releases'] = [record] + [item for key, item in previous_by_version.items() if key != version]
    # Render before changing either file. A broken archive, credit or marker
    # must not leave a manifest that advertises an unverified patch.
    page = site.rendered_page(root, manifest)
    if manifest == json.loads(previous) and page == (root / 'index.html').read_text(encoding='utf-8'):
        return f'The site already uses the verified public v{version} release.'
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
    print(sync(dry_run=parser.parse_args().dry_run, include_history=True))
