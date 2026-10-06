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
- `homepage.js` manages screenshots, the bug-report template, and animation preferences.
- `loading.js` provides a spinning-slime loading indicator. Call `const finish = DqmLoading.begin()` before an asynchronous task and `finish()` when it settles.
- `assets/provenance.json` records the game assets and their hashes. Sprite animation can be paused and respects reduced-motion preferences.
- `downloads/releases.json` records packages newest first. The first entry also supplies the current download card and release notes.

## Updating the patch download

Add the new public ZIP to `downloads/` and prepend its version, filename, byte size,
SHA-256, contents, and player-facing `notes` to `downloads/releases.json`. Then run:

```sh
python tools/update_release.py
python tools/update_release.py --check
```

The helper validates the ZIP and matching CUE before updating the marked download
card in `index.html`. Commit the package, manifest, and generated HTML together.
The committed page works without JavaScript; there is no visitor-time build or
GitHub API request. Existing packages are retained.

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
