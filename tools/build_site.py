"""Build the public static files and check the links and assets they refer to."""

import argparse
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
PAGES = ('index.html', '404.html')
SCRIPTS = ('gallery-data.js', 'homepage.js')


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.ids = set()
        self.urls = []
        self.scripts = []
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            if attrs['id'] in self.ids:
                raise ValueError(f'Duplicate HTML id: {attrs["id"]}')
            self.ids.add(attrs['id'])
        for field in ('href', 'src', 'data-animated-src'):
            if attrs.get(field):
                self.urls.append(attrs[field])
        if tag == 'script' and attrs.get('src'):
            self.scripts.append(urlsplit(attrs['src']).path)
        if 'srcset' in attrs:
            self.urls.extend(candidate.strip().split()[0] for candidate in attrs['srcset'].split(','))
        if attrs.get('property') == 'og:image':
            self.urls.append(urlsplit(attrs['content']).path)


def fingerprint(name, content):
    path = Path(name)
    digest = hashlib.sha256(content).hexdigest()[:12]
    return f'{path.stem}.{digest}{path.suffix}'


def build(output):
    output = output.resolve()
    if output == ROOT or output in ROOT.parents:
        raise ValueError('The output must be separate from the source tree')
    if output.exists() and any(output.iterdir()) and not (output / '.dqm-site-build').is_file():
        raise ValueError(f'Choose an empty directory or a previous homepage build: {output}')
    pages = {name: (ROOT / name).read_text(encoding='utf-8') for name in PAGES}
    parsed = {name: Page(html) for name, html in pages.items()}
    files = set()

    for name, page in parsed.items():
        for url in page.urls:
            parts = urlsplit(url)
            if parts.scheme or parts.netloc:
                if parts.scheme != 'https' or not parts.netloc:
                    raise ValueError(f'{name}: unexpected link {url}')
                continue
            path = unquote(parts.path).lstrip('/')
            if parts.path == '/':
                path = 'index.html'
            target = path or name
            if parts.fragment and (target not in parsed or unquote(parts.fragment) not in parsed[target].ids):
                raise ValueError(f'{name}: missing anchor {url}')
            if not (ROOT / target).resolve().is_relative_to(ROOT) or not (ROOT / target).is_file():
                raise ValueError(f'{name}: missing local file {url}')
            files.add(target)

    gallery = json.loads((ROOT / 'data/screenshots.json').read_text(encoding='utf-8'))
    files.update(scene['src'] for scene in gallery['screenshots'])
    files.update(str(Path(path).with_suffix('')).replace('\\', '/') + '-still.png'
                 for path in tuple(files) if path.endswith('.gif'))
    # Keep existing download bookmarks working when the hero switches to GitHub Releases.
    files.update(path.relative_to(ROOT).as_posix() for path in (ROOT / 'downloads').glob('*.zip'))
    files.difference_update(PAGES)
    files.add('.nojekyll')
    if tuple(parsed['index.html'].scripts) != ('theme.js', *SCRIPTS):
        raise ValueError('The homepage scripts and bundle inputs must match in load order')
    # Inline the small theme preference script so a saved choice applies before first paint.
    theme_script = (ROOT / 'theme.js').read_text(encoding='utf-8')
    files.remove('theme.js')
    files.difference_update(SCRIPTS)
    bundle = b'\n;\n'.join((ROOT / path).read_bytes() for path in SCRIPTS)
    script_name = fingerprint('site.js', bundle)
    output.mkdir(parents=True, exist_ok=True)
    (output / script_name).write_bytes(bundle)
    styles = {}
    for path in sorted(files):
        destination = path
        if path.endswith('.css'):
            destination = fingerprint(path, (ROOT / path).read_bytes())
            styles[path] = destination
        dest = output / destination
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, dest)
    for name, html in pages.items():
        theme_path = '/theme.js' if name == '404.html' else 'theme.js'
        html = html.replace(f'<script src="{theme_path}"></script>', f'<script>\n{theme_script}</script>')
        for path, fingerprinted in styles.items():
            html = re.sub(r'(href="/?)' + re.escape(path) + r'(?:\?[^"]*)?"', r'\g<1>' + fingerprinted + '"', html)
        if name == 'index.html':
            for source in SCRIPTS:
                pattern = r'  <script src="' + re.escape(source) + r'(?:\?[^"]*)?" defer></script>\n'
                replacement = f'  <script src="{script_name}" defer></script>\n' if source == SCRIPTS[-1] else ''
                html, count = re.subn(pattern, replacement, html)
                if count != 1:
                    raise ValueError(f'Missing bundle entry point: {source}')
        (output / name).write_text(html, encoding='utf-8')
    (output / '.dqm-site-build').touch()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    build(parser.parse_args().output)
