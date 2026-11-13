"""Stage website-owned FAQ copy for a release; never upload or publish anything."""
import argparse
import json
from pathlib import Path

import release_catalog
import update_release
import website_faq


def prepare(release_dir, root=update_release.ROOT, report_file=None):
    record = json.loads((release_dir / 'release.json').read_text(encoding='utf-8'))
    release_catalog.validate_catalog(record)
    for edition in record['editions']:
        release_catalog.validate_edition_package(record, edition, (release_dir / edition['file']).read_bytes())
    report = website_faq.prepare(record, root)
    if report_file:
        report_file.parent.mkdir(parents=True, exist_ok=True)
        update_release.atomic_write(report_file, json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('Website FAQ draft: ' + str(root / website_faq.RELATIVE_PATH))
    print('New answers: ' + (', '.join(report['added']) or 'none'))
    print('Source suggestions to review: ' + (', '.join(report['suggestions']) or 'none'))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-dir', type=Path, required=True)
    parser.add_argument('--website', type=Path, default=update_release.ROOT)
    parser.add_argument('--report-file', type=Path)
    args = parser.parse_args()
    prepare(args.release_dir.resolve(), args.website.resolve(), args.report_file)
