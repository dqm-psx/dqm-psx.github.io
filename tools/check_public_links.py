"""Check launch destinations as a signed-out visitor. Run after making the repos public."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def fetch(url, *, json_body=False):
    request = Request(url, headers={'User-Agent': 'DQM-PSX-homepage-link-check'})
    with urlopen(request, timeout=20) as response:
        return json.load(response) if json_body else response.status


def main():
    api = 'https://api.github.com/repos/dqm-psx'
    failures = []
    for repo, form in [('patch', 'bug-report.yml'), ('dqm-psx.github.io', 'screenshot.yml')]:
        try:
            settings = fetch(f'{api}/{repo}', json_body=True)
            if not settings['has_issues']:
                raise ValueError('issues are disabled')
            fetch(f'{api}/{repo}/contents/.github/ISSUE_TEMPLATE/{form}')
            print(f'Public issue form available: {repo}/{form}')
        except (HTTPError, URLError, ValueError) as error:
            failures.append(f'{repo}/{form}: {error}')
    for path in ('guide', 'translations'):
        try:
            fetch(f'https://dqm-psx.github.io/{path}/')
            print(f'Public site available: /{path}/')
        except (HTTPError, URLError) as error:
            failures.append(f'/{path}/: {error}')
    if failures:
        raise SystemExit('\n'.join(failures))


if __name__ == '__main__':
    main()
