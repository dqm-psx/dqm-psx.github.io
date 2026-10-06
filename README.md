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

- `index.html` contains the homepage, patch download, installation instructions, and community links.
- `theme.css` provides the shared colors, typography, buttons, and RPG-style panels. `homepage.css` controls the homepage layout.
- `homepage.js` manages screenshots, the bug-report template, and animation preferences.
- `loading.js` provides a spinning-slime loading indicator. Call `const finish = DqmLoading.begin()` before an asynchronous task and `finish()` when it settles.
- `assets/provenance.json` records the game assets and their hashes. Sprite animation can be paused and respects reduced-motion preferences.
- `downloads/releases.json` records the included patch package's size, SHA-256 checksum, and contents.

The patch ZIP contains a BPS patch, a matching CUE file, and its original README. Follow the included README for release-specific instructions. No game disc images are included.

Dragon Quest and its characters belong to their respective owners. This is a fan project.
