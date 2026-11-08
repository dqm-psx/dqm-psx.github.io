"""Validate the reviewed screenshot manifest and generate gallery-data.js.

Requires Pillow only for maintainer checks/imports: python -m pip install Pillow
Run with --check to verify without writing. Use --image and the metadata options
to import an already-reviewed local image. This tool never downloads attachments,
opens GitHub issues, commits, pushes, or publishes anything.
"""
import argparse
from copy import deepcopy
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import warnings

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'data/screenshots.json'
PROVENANCE = 'assets/provenance.json'
OUTPUT = 'gallery-data.js'
MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 40_000_000
FORMATS = {'PNG': '.png', 'JPEG': '.jpg', 'WEBP': '.webp'}
VERSION = re.compile(r'(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)')
ISSUE = re.compile(r'https://github\.com/dqm-psx/dqm-psx\.github\.io/issues/[1-9]\d*')
FIELDS = {'src', 'alt', 'caption', 'credit', 'patchVersion', 'viewport', 'sourceIssue'}


def text(value, field, limit=500):
    if (not isinstance(value, str) or not value.strip() or value != value.strip()
            or len(value) > limit or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError(f'{field} must be nonempty, trimmed, single-line text (up to {limit} characters)')
    return value


def normalize_version(value):
    """CLI input accepts a v prefix; unknown versions are omitted, never inferred."""
    if value is None or (isinstance(value, str) and value.strip().casefold() in {'', 'unknown'}):
        return None
    value = value.strip().removeprefix('v') if isinstance(value, str) else value
    if not isinstance(value, str) or not VERSION.fullmatch(value):
        raise ValueError('Patch version must be three numeric components, such as 1.0.72')
    return value


def inspect_image(data):
    if not data or len(data) > MAX_BYTES:
        raise ValueError('Screenshot must be nonempty and no larger than 10 MB')
    try:
        from PIL import Image
    except ImportError as error:
        raise ValueError('Screenshot checks require Pillow: python -m pip install Pillow') from error
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as picture:
                if picture.format not in FORMATS:
                    raise ValueError('Only PNG, JPEG, and WebP screenshots are supported')
                if getattr(picture, 'n_frames', 1) != 1:
                    raise ValueError('Use a still screenshot, not an animated image')
                width, height = picture.size
                if width < 1 or height < 1 or width * height > MAX_PIXELS:
                    raise ValueError('Screenshot dimensions must be positive and at most 40 megapixels')
                extension = FORMATS[picture.format]
                picture.verify()
            # verify() alone does not decode all image data for every format.
            with Image.open(BytesIO(data)) as picture:
                picture.load()
    except (OSError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ValueError(f'Cannot decode screenshot: {error}') from error
    return {'width': width, 'height': height, 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest(), 'extension': extension}


def image_path(root, src):
    if not isinstance(src, str) or not re.fullmatch(r'assets/(?:screenshots/)?[a-z0-9][a-z0-9._-]*\.(?:png|jpe?g|webp)', src):
        raise ValueError('Screenshot src must be a local image path under assets/ or assets/screenshots/')
    if str(PurePosixPath(src)) != src:
        raise ValueError('Screenshot src is not a canonical relative path')
    path = (root / src).resolve()
    if not path.is_relative_to((root / 'assets').resolve()) or not path.is_relative_to(root.resolve()):
        raise ValueError('Screenshot path escapes the site assets directory')
    return path


def validate_crop(crop, width, height):
    if not isinstance(crop, dict) or set(crop) != {'x', 'y', 'width', 'height'}:
        raise ValueError('viewport needs exactly x, y, width, and height')
    if any(type(value) is not int for value in crop.values()):
        raise ValueError('viewport coordinates must be integer source pixels')
    if (crop['x'] < 0 or crop['y'] < 0 or crop['width'] <= 0 or crop['height'] <= 0
            or crop['x'] + crop['width'] > width or crop['y'] + crop['height'] > height):
        raise ValueError('viewport must stay inside the original screenshot')


def read_data(root):
    return (json.loads((root / MANIFEST).read_text(encoding='utf-8')),
            json.loads((root / PROVENANCE).read_text(encoding='utf-8')))


def validate(manifest, provenance, root, pending=None):
    if (not isinstance(manifest, dict) or manifest.get('schemaVersion') != 1
            or not isinstance(manifest.get('screenshots'), list) or not manifest['screenshots']):
        raise ValueError('Unsupported or empty screenshot manifest')
    if not isinstance(provenance, list):
        raise ValueError('Asset provenance must be a list')
    sources = {}
    for record in provenance:
        if not isinstance(record, dict) or not isinstance(record.get('file'), str):
            raise ValueError('Each provenance record needs a file path')
        if record['file'] in sources:
            raise ValueError(f'Duplicate provenance file: {record["file"]}')
        sources[record['file']] = record
    paths, hashes = set(), set()
    for scene in manifest['screenshots']:
        if not isinstance(scene, dict) or set(scene) - FIELDS:
            raise ValueError('Unexpected screenshot fields')
        src = scene.get('src')
        path = image_path(root, src)
        if src in paths:
            raise ValueError(f'Duplicate screenshot path: {src}')
        paths.add(src)
        text(scene.get('alt'), 'alt')
        text(scene.get('caption'), 'caption', 160)
        if 'credit' in scene:
            text(scene['credit'], 'credit', 100)
        if 'patchVersion' in scene:
            if not isinstance(scene['patchVersion'], str) or not VERSION.fullmatch(scene['patchVersion']):
                raise ValueError('Manifest patchVersion must omit v and contain three numeric components; omit unknown versions')
        if 'sourceIssue' in scene and (not isinstance(scene['sourceIssue'], str) or not ISSUE.fullmatch(scene['sourceIssue'])):
            raise ValueError('sourceIssue must identify an issue in dqm-psx/dqm-psx.github.io')
        record = sources.get(src.removeprefix('assets/'))
        if record is None:
            raise ValueError(f'Missing asset provenance: {src}')
        data = pending[src] if pending and src in pending else path.read_bytes()
        info = inspect_image(data)
        if info['sha256'] in hashes:
            raise ValueError(f'Duplicate screenshot content: {src}')
        hashes.add(info['sha256'])
        expected_extensions = {info['extension']} | ({'.jpeg'} if info['extension'] == '.jpg' else set())
        if path.suffix not in expected_extensions:
            raise ValueError(f'Image extension does not match decoded format: {src}')
        for key in ('width', 'height', 'sha256'):
            if record.get(key) != info[key]:
                raise ValueError(f'Provenance {key} differs from original screenshot: {src}')
        if 'bytes' in record and record['bytes'] != info['bytes']:
            raise ValueError(f'Provenance bytes differs from original screenshot: {src}')
        for key in ('patchVersion', 'sourceIssue'):
            if record.get(key) != scene.get(key):
                raise ValueError(f'{key} differs between screenshot manifest and provenance: {src}')
        if 'credit' in scene and record.get('contributor') != scene['credit']:
            raise ValueError(f'Credit differs between screenshot manifest and provenance: {src}')
        crop = scene.get('viewport')
        recorded_crop = record.get('displayCrop')
        if crop is not None:
            validate_crop(crop, info['width'], info['height'])
            if not isinstance(recorded_crop, dict) or any(recorded_crop.get(key) != value for key, value in crop.items()):
                raise ValueError(f'Viewport differs from provenance displayCrop: {src}')
        elif recorded_crop is not None:
            raise ValueError(f'Provenance has a displayCrop missing from the screenshot manifest: {src}')
    return manifest['screenshots']


def generated(scenes):
    data = json.dumps(scenes, ensure_ascii=False, indent=2).replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    return '// Generated by tools/update_screenshots.py; edit data/screenshots.json instead.\nwindow.DqmScreenshots = ' + data + ';\n'


def atomic_write(path, data):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.' + path.name + '-', suffix='.tmp', delete=False) as output:
            temporary = Path(output.name)
            output.write(data)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def update(root=ROOT, check=False):
    manifest, provenance = read_data(root)
    output = generated(validate(manifest, provenance, root))
    path = root / OUTPUT
    if check:
        if not path.exists() or path.read_text(encoding='utf-8') != output:
            raise ValueError('gallery-data.js is stale; run python tools/update_screenshots.py')
    else:
        atomic_write(path, output.encode('utf-8'))


def import_screenshot(image, name, credit, caption, alt, issue, patch_version=None, crop=None, root=ROOT):
    """Prepare a local, reviewed image for a maintainer's commit. Preserve its bytes."""
    if not isinstance(name, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name):
        raise ValueError('name must use lowercase letters/numbers separated by single hyphens')
    if not isinstance(issue, str) or not ISSUE.fullmatch(issue):
        raise ValueError('issue must identify the reviewed submission in dqm-psx/dqm-psx.github.io')
    data = Path(image).read_bytes()
    info = inspect_image(data)
    src = f'assets/screenshots/{name}{info["extension"]}'
    destination = image_path(root, src)
    if destination.exists():
        raise ValueError(f'Destination already exists; refusing to overwrite: {src}')
    scene = {'src': src, 'alt': text(alt, 'alt'), 'caption': text(caption, 'caption', 160),
             'credit': text(credit, 'credit', 100), 'sourceIssue': issue}
    record = {'file': src.removeprefix('assets/'), 'description': alt, 'contributor': credit,
              'width': info['width'], 'height': info['height'], 'bytes': info['bytes'],
              'sha256': info['sha256'], 'sourceFile': Path(image).name, 'sourceIssue': issue,
              'processing': 'Original screenshot copied unchanged after maintainer review.'}
    version = normalize_version(patch_version)
    if version is not None:
        scene['patchVersion'] = record['patchVersion'] = version
    if crop is not None:
        scene['viewport'] = dict(zip(('x', 'y', 'width', 'height'), crop)) if isinstance(crop, (list, tuple)) and len(crop) == 4 else crop
        validate_crop(scene['viewport'], info['width'], info['height'])
        record['displayCrop'] = {**scene['viewport'], 'units': 'source pixels', 'method': 'CSS viewport crop'}
    manifest, provenance = read_data(root)
    validate(manifest, provenance, root)
    manifest, provenance = deepcopy(manifest), deepcopy(provenance)
    manifest['screenshots'].append(scene)
    provenance.append(record)
    output = generated(validate(manifest, provenance, root, pending={src: data}))
    # All validation happens before any file is changed. This is local preparation,
    # not an approval service: review and merge the resulting diff before publication.
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as target:
        target.write(data)
    atomic_write(root / MANIFEST, (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    atomic_write(root / PROVENANCE, (json.dumps(provenance, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    atomic_write(root / OUTPUT, output.encode('utf-8'))
    return src


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--image', type=Path, help='Already-reviewed local PNG, JPEG, or WebP; never a URL')
    parser.add_argument('--name', help='New filename stem, for example terry-travelers-gate')
    parser.add_argument('--credit', help='Display name supplied by the contributor')
    parser.add_argument('--caption', help='Short visible gallery caption')
    parser.add_argument('--alt', help='Description for visitors who cannot see the image')
    parser.add_argument('--issue', help='Reviewed screenshot submission issue URL in the website repository')
    parser.add_argument('--patch-version', help='Optional known version, for example v1.0.72; omit when unknown')
    parser.add_argument('--crop', type=int, nargs=4, metavar=('X', 'Y', 'WIDTH', 'HEIGHT'), help='Optional CSS viewport in original image pixels')
    args = parser.parse_args()
    if args.image is not None:
        if args.check:
            parser.error('--check cannot be combined with an import')
        for field in ('name', 'credit', 'caption', 'alt', 'issue'):
            if getattr(args, field) is None:
                parser.error(f'--image requires --{field}')
        src = import_screenshot(args.image, args.name, args.credit, args.caption, args.alt,
                                args.issue, args.patch_version, args.crop)
        print(f'Prepared {src}. Review the local diff; nothing has been committed or published.')
    else:
        if any(getattr(args, field) is not None for field in ('name', 'credit', 'caption', 'alt', 'issue', 'patch_version', 'crop')):
            parser.error('Import metadata options require --image')
        update(check=args.check)
        print('Screenshot files, provenance, and gallery data verified.' if args.check else 'Updated gallery-data.js.')


if __name__ == '__main__':
    main()
