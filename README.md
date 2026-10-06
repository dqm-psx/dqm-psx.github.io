# DQM PSX

The project homepage for the English fan translation of **Dragon Quest Monsters 1 & 2: The Starry Night Hero and Friends at the Ranch** for PlayStation.

[Visit the homepage](https://dqm-psx.github.io/) · [Game guide](https://dqm-psx.github.io/guide/) · [Translation reference](https://dqm-psx.github.io/translations/) · [Discord](https://discord.gg/6V9p6Y2pBt) · [ROMhacking.net](https://www.romhacking.net/translations/7734/)

## Local preview

This is a static site with no build step or package dependencies. From this repository's root, run:

```sh
python -m http.server 4173 --bind 127.0.0.1
```

Open `http://127.0.0.1:4173/`. GitHub Pages serves the root of the `main` branch at `https://dqm-psx.github.io/`.

## Site files

- `index.html` contains the game and project introduction, reference navigation, patch download, installation instructions, and community links. Historical sources are linked beside the relevant text.
- `theme.css` provides the shared colors, typography, buttons, and RPG-style panels. `homepage.css` controls the homepage layout.
- `homepage.js` manages screenshots, the bug-report template, animation preferences, and contributor rotation.
- `loading.js` provides a spinning-slime loading indicator. Call `const finish = DqmLoading.begin()` before an asynchronous task and `finish()` when it settles.
- `assets/provenance.json` records the game assets and their hashes. Sprite animation can be paused and respects reduced-motion preferences.
- `downloads/releases.json` records packages newest first. The first entry supplies the current download card and release notes; every retained package supplies its explicitly credited contributors.
- `data/contributors.json` records project contributors credited separately from release READMEs, with a contribution and its source. It currently includes Cats4gold's help with the breeding tool, confirmed by the project owner.

## Updating the patch download and contributor credits

Add the new public ZIP to `downloads/` and prepend its version, filename, byte size,
SHA-256, contents, and player-facing `notes` to `downloads/releases.json`. Then run:

```sh
python tools/update_release.py
python tools/update_release.py --check
```

The helper validates the recorded size, SHA-256, ZIP contents and integrity, and
matching CUE of **every** package in the manifest. It reads their original
`README.txt` files, merges their explicitly named contributors with
`data/contributors.json`, and updates both marked blocks in `index.html` in one
atomic replacement. Any validation or credit-parsing failure leaves the page
untouched. `--check` checks both generated blocks without writing.

Names are deduplicated without regard to case and sorted alphabetically, ignoring
leading underscores for sorting while preserving them in displayed names. The
first spelling wins: manual project entries first, then releases newest first.
Retain older packages and manifest entries so credits survive when a newer README
shortens its release history. To preserve a credit independently of a package,
add it to `data/contributors.json` with its explicit contribution and source;
do not infer contributors from commits or issue activity. Creator and historical
inspiration credits already have their own prose and are not repeated in this list.

Existing READMEs use `Thanks [also] [to] NAME for ...!` within
`PUBLIC RELEASE HIGHLIGHTS`. The parser accepts single-word handles with letters,
digits, underscores, periods or hyphens, plus comma-separated names and a final
`and NAME`. It joins hard-wrapped lines and accepts either `!`, `.` or `?` as the
closing punctuation. Unknown or ambiguous thanks wording fails with an error
instead of silently omitting or inventing a credit. For new release READMEs,
an explicit section also supports full names and other punctuation:

```text
CONTRIBUTORS
- ContributorOne
- Another Contributor

REQUIRED GAME
```

Use one name per line without appended roles; the next uppercase section heading
ends the list. Unrecognized thanks outside the supported highlights section must
also be clarified before generating the page. Published ZIPs remain unchanged;
make source README corrections before packaging a new release.

Commit the package, manifest, any project-credit updates, and generated HTML
together. The committed page includes every name and works without JavaScript;
there is no visitor-time build, GitHub API request, or background polling. The
browser's optional rotation is presentation only. Run the helper checks with:

```sh
python -m unittest discover -s tools -p 'test_*.py'
```

The credits panel shows four names at a time in a fixed-height viewport, advancing
every seven seconds. Hover, keyboard focus, hidden tabs, and offscreen panels pause
rotation; manual browsing pauses until Resume is chosen. Reduced-motion users
start paused. Show all names and the no-JavaScript fallback keep the complete list
scrollable in the same space.

## Launch navigation

The homepage presents the complete reference site intended for launch. Its links
use the full guide’s established routes; they are a destination contract, not a
statement that the currently published guide already contains every section.

| Homepage entry | Destination |
| --- | --- |
| Monsters | `/guide/#monsters` |
| Items | `/guide/#items` |
| Breeding tools | `/guide/#pair-finder` |
| Characters and dialogue | `/guide/#characters` |
| Maps and places | `/guide/#maps` |
| Breeding trees | `/guide/#team-planner` |
| Translation comparison | `/translations/` |

Before publishing the homepage, integrate and publish the complete reference
content, then check every destination above. Verify the team planner retains
recursive breeding trees when combining the guide implementations. Verify links
from recipes to monster entries and from character dialogue to maps, using shared
native game IDs. Confirm the promised sprites, dialogue, item descriptions, and
monster data are available through those pages. Keep integration status here;
the visitor-facing homepage should describe the finished experience.

The hero party is Terry with three monsters: Hale (Healslime), Dragon, and
SabreCat. Cats4gold is credited on the homepage for helping with the breeding tool.

The patch ZIP contains a BPS patch, a matching CUE file, and its original README. Follow the included README for release-specific instructions. No game disc images are included.

Dragon Quest and its characters belong to their respective owners. This is a fan project.
