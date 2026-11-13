"""Build an isolated homepage preview from a locally prepared two-edition release."""
import argparse
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import shutil
import tempfile

import build_site
import release_catalog
import update_release


def preview(release_dir, output, root=build_site.ROOT):
    release_dir = release_dir.resolve()
    output = output.resolve()
    if output == root.resolve() or root.resolve().is_relative_to(output):
        raise ValueError('Choose a preview directory separate from the website source')
    if output.is_relative_to(release_dir) or release_dir.is_relative_to(output):
        raise ValueError('Choose a preview directory separate from the release bundle')
    record = json.loads((release_dir / 'release.json').read_text(encoding='utf-8'))
    release_catalog.validate_catalog(record)
    for edition in record['editions']:
        release_catalog.validate_edition_package(record, edition, (release_dir / edition['file']).read_bytes())
        edition.pop('downloadUrl', None)
    record.pop('releaseUrl', None)
    record['publishedAt'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    with tempfile.TemporaryDirectory(prefix='dqm-release-preview-') as directory:
        staging = Path(directory)
        for name in ('index.html', '404.html', 'theme.css', 'homepage.css', 'theme.js',
                     'gallery-data.js', 'homepage.js', '.nojekyll', 'data', 'downloads', 'assets'):
            source = root / name
            if source.is_dir():
                shutil.copytree(source, staging / name)
            else:
                shutil.copyfile(source, staging / name)
        manifest = json.loads((staging / 'downloads/releases.json').read_text(encoding='utf-8'))
        manifest['releases'] = [record] + [old for old in manifest['releases'] if old['version'] != record['version']]
        for edition in record['editions']:
            shutil.copyfile(release_dir / edition['file'], staging / 'downloads' / edition['file'])
        (staging / 'downloads/releases.json').write_text(json.dumps(manifest), encoding='utf-8')
        update_release.update(staging)
        html = (staging / 'index.html').read_text(encoding='utf-8')
        html = html.replace('</head>', '  <meta name="robots" content="noindex">\n</head>')
        notice = f'<p class="release-preview-notice">Release preview · v{escape(record["version"])}</p>'
        html = html.replace('<body>', '<body>\n  ' + notice, 1)
        (staging / 'index.html').write_text(html, encoding='utf-8')
        build_site.build(output, root=staging)
    print(f'Release preview built in {output}')
    print(f'Preview locally with: python -m http.server 4174 --bind 127.0.0.1 --directory "{output}"')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    preview(args.release_dir, args.output)
