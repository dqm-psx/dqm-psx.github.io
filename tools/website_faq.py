"""Website-owned feature explanations, staged explicitly before release publication."""
from copy import deepcopy
import json
from pathlib import Path

import release_catalog as catalog

RELATIVE_PATH = Path('data/feature-faq.json')


def validate_document(data):
    catalog.require(isinstance(data, dict) and data.get('schemaVersion') == 1
                    and isinstance(data.get('releases'), list), 'Unsupported website FAQ document')
    versions = []
    for release in data['releases']:
        catalog.require(isinstance(release, dict), 'Invalid website FAQ release entry')
        version = release.get('version')
        catalog.require(isinstance(version, str) and catalog.VERSION.fullmatch(version),
                        'Invalid website FAQ release version')
        versions.append(version)
        answers = release.get('faq')
        catalog.require(isinstance(answers, list) and answers
                        and all(isinstance(answer, dict) for answer in answers),
                        'Website FAQ release needs explanations')
        catalog.identifiers([answer.get('id') for answer in answers], 'Website FAQ anchors')
        for answer in answers:
            catalog.require(answer.get('section') in catalog.SECTIONS
                            and catalog.text(answer.get('question')), 'Incomplete website FAQ question')
            catalog.require(isinstance(answer.get('answerHtml'), str), 'Website FAQ answerHtml is missing')
            catalog.AnswerHTML(answer['answerHtml'])
            # Shared fixes can ship in every build without a selectable feature ID.
            catalog.identifiers(answer.get('features'), 'Website FAQ features')
    catalog.require(len(versions) == len(set(versions)), 'Duplicate website FAQ release version')
    return data


def load(root):
    path = Path(root) / RELATIVE_PATH
    if not path.is_file():
        raise ValueError('Website feature FAQ is missing; prepare and review it before importing the release')
    return validate_document(json.loads(path.read_text(encoding='utf-8')))


def apply(releases, root):
    """Return metadata with website-owned prose; never import or write release prose."""
    versions = {record['version']: record for record in load(root)['releases']}
    result = []
    for release in releases:
        if release.get('schemaVersion') != 2:
            continue
        version = release['version']
        catalog.require(version in versions,
                        f'Website FAQ for v{version} has not been prepared; preview and review it before publication')
        record = deepcopy(release)
        record['faq'] = deepcopy(versions[version]['faq'])
        catalog.validate_catalog(record)
        result.append(record)
    return result


def proposed_document(record, current):
    """Seed a new website revision without overwriting existing edited explanations."""
    catalog.validate_catalog(record)
    validate_document(current)
    target = next((row for row in current['releases'] if row['version'] == record['version']), None)
    prior = [row for row in current['releases']
             if tuple(map(int, row['version'].split('.'))) < tuple(map(int, record['version'].split('.')))]
    previous = max(prior, key=lambda row: tuple(map(int, row['version'].split('.')))) if prior else None
    baseline = target or previous
    incoming = {answer['id']: answer for answer in record['faq']}
    available = {feature['id'] for feature in record['features']}
    answers = []
    added = []
    suggestions = []
    for old in baseline['faq'] if baseline else []:
        proposal = incoming.pop(old['id'], None)
        answer = deepcopy(old)
        # Feature references are build facts. Updating them explicitly allows a
        # new feature to extend an existing answer without replacing its prose.
        answer['features'] = list(dict.fromkeys(
            [feature for feature in old['features'] if feature in available]
            + (proposal['features'] if proposal else [])))
        if (proposal is not None and old != proposal) or answer != old:
            suggestions.append(old['id'])
        if answer['features'] or not old['features']:
            answers.append(answer)
    for proposal in incoming.values():
        answers.append(deepcopy(proposal))
        added.append(proposal['id'])
    candidate = deepcopy(record)
    candidate['faq'] = answers
    catalog.validate_catalog(candidate)
    updated = deepcopy(current)
    if target is None:
        updated['releases'].append({'version': record['version'], 'faq': answers})
    else:
        next(row for row in updated['releases'] if row['version'] == record['version'])['faq'] = answers
    validate_document(updated)
    return updated, {'version': record['version'], 'added': added, 'suggestions': suggestions}


def prepare(record, root):
    """Explicitly add a review draft in the website checkout; performs no publication."""
    from update_release import atomic_write
    path = Path(root) / RELATIVE_PATH
    current = load(root) if path.exists() else {'schemaVersion': 1, 'releases': []}
    updated, report = proposed_document(record, current)
    if updated != current or not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(path, json.dumps(updated, ensure_ascii=False, indent=2) + '\n')
    return report
