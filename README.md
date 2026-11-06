# DQM PSX

The project homepage for the English fan translation of **Dragon Quest Monsters 1 & 2: The Starry Night Hero and Friends at the Ranch** for PlayStation.

[Visit the homepage](https://dqm-psx.github.io/) · [Discord](https://discord.gg/6V9p6Y2pBt) · [ROMhacking.net](https://www.romhacking.net/translations/7734/)

The site is being prepared as the public landing page for the English patch developed in `phakic/dqm1`. It provides a verified download, installation instructions, screenshots, project credits, a FAQ, and community support. The release home will be `dqm-psx/patch`. This preview retains a verified local v1.0.72 package until the public release destination is ready.

**Launch status:** GitHub Pages is disabled. Enable publication only after the project owner gives the go-ahead.

## Local preview

This is a static site with no build step or package dependencies. From this repository's root, run:

```sh
python -m http.server 4173 --bind 127.0.0.1
```

Open `http://127.0.0.1:4173/`.

## GitHub Pages deployment

The hosting repository is `dqm-psx/dqm-psx.github.io`. Publish its `main` branch,
`/ (root)`, at `https://dqm-psx.github.io/` using **Settings → Pages → Deploy from
a branch**. The committed `.nojekyll` file keeps this a plain static site; no
build service, framework, API key, or client-side GitHub API request is needed.

On GitHub Free, the hosting repository must be public to enable Pages. Only this
website repository needs public visibility; the patch development and release
repositories can remain private. Before changing visibility, review the hosting
repository’s files and history for anything not intended for publication.

Before pushing an update to `main`, run:

```sh
python tools/update_release.py --check
python -m unittest discover -s tools -p 'test_*.py'
node --check homepage.js
node --check loading.js
```

Then check GitHub’s Pages deployment and visit the public URL while signed out.
Confirm the download, installation links, screenshot gallery, and mobile layout.
Preview changes on a branch before merging; after Pages is enabled, pushes to
`main` publish the site.

## Site files

- `index.html` contains the patch download and installation instructions, game and project introduction, future plans, and community links. Historical sources are linked beside the relevant text.
- `theme.css` provides the shared colors, typography, buttons, and RPG-style panels. `homepage.css` controls the homepage layout.
- `homepage.js` manages screenshots, the bug-report template, animation preferences, contributor rotation, and anchor offsets for the sticky navigation.
- `loading.js` provides a spinning-slime loading indicator. Call `const finish = DqmLoading.begin()` before an asynchronous task and `finish()` when it settles.
- `assets/provenance.json` records the game assets and their hashes. Sprite animation can be paused and respects reduced-motion preferences.
- `downloads/releases.json` records packages newest first. The first entry supplies the current download card and release notes; every retained package supplies its explicitly credited contributors.
- `data/contributors.json` records project contributors credited separately from release READMEs, with a contribution and its source. It includes Cats4gold's help with the breeding tool and Nejimakipiyo's translation review, confirmed by the project owner.

## Navigation and FAQ

The top navigation stays visible while scrolling. Section links account for its
height on desktop and mobile, including wrapped navigation. FAQ topic links live
in a dropdown that opens on hover, or on click, tap, or keyboard activation. The
FAQ answers and navigation use native HTML disclosures and work without JavaScript.

FAQ content comes from the project owner's Discord FAQ and covers the project,
AI assistance, installation and updating, restored content, quality-of-life
changes, troubleshooting, and contributing. The restored content and interface
features were checked against v1.0.72. The full report template distinguishes
memory-card saves for normal play from patch-matched save states for debugging.
The bug-report button opens a prefilled issue in `dqm-psx/patch`; visitors review
and submit it on GitHub. Its URL body must match the visible `report-text`
template. Opening the issue page does not submit a report. Confirm that the
repository is public and Issues is enabled before the website launch.
The public translation comparison and breeding guide are linked from the FAQ
and Resources section. Both were verified to return HTTP 200. Translation
suggestions go through the comparison site to `dqm-psx/translations`; Discord
remains an alternative for corrections and general help.

## Screenshot gallery

The screenshot gallery rotates through fourteen screenshots every seven seconds,
including eleven original 960×720 captures shared by BalK. The new captures live
in `assets/screenshots/`, with credit, source filenames, and hashes recorded in
`assets/provenance.json`. Each appears uncropped with its own caption and credit.

Previous, Next, and the screenshot selector pause automatic rotation until Play
slideshow is chosen. Hover, keyboard focus, hidden tabs, and an offscreen gallery
also suspend rotation; reduced-motion users start paused. The first screenshot
and its BalK credit remain visible without JavaScript. To add another image,
extend `scenes` in `homepage.js` and update the initial total in `index.html`.

## Updating the patch download and contributor credits

Publish future patch releases in `dqm-psx/patch`. Once a release is ready and its
public download is verified, update the website's download destination and
release metadata together. Do not link visitors to the private development
repository or promote a draft release. v1.0.73 is being prepared by the project
owner; wait for their confirmation before replacing v1.0.72.

The current preview uses the existing local package workflow below. Retained
packages also preserve historical credits and allow integrity checks offline.

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
do not infer contributors from commits or issue activity. The creator and named AI assistants are included in the rotating list. Kingcom
and Tom are acknowledged separately as historical inspiration.

Existing READMEs use `Thanks [also] [to] NAME for ...!` within
`PUBLIC RELEASE HIGHLIGHTS`. The parser accepts single-word handles with letters,
digits, underscores, periods or hyphens, plus comma-separated names and a final
`and NAME`. It joins hard-wrapped lines and accepts either `!`, `.` or `?` as the
closing punctuation. A bounded set of unnamed thanks to everyone/everybody for
reports, suggestions, translation suggestions, feedback, or testing is accepted
without inventing a contributor name. Unknown or ambiguous thanks wording fails with an error
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

The credits panel shows four names at a time, advancing every seven seconds.
Its centered pause/play icon and previous/next arrows have accessible labels;
there are no visible page counts. Hover, keyboard focus, hidden tabs, and
offscreen panels pause rotation. Manual browsing pauses until Resume is chosen.
Reduced-motion users start paused. Without JavaScript, all names remain in the
scrollable list.

## Reference tools and future scope

The patch landing page stands on its own and links to these existing public tools:

- [Breeding reference](https://dqm-psx.github.io/guide/): recipes, pair finding, and team planning.
- [Translation comparison](https://dqm-psx.github.io/translations/): names, text, and correction proposals to `dqm-psx/translations`.

A broader wiki/game reference and decompilation/research site remain future
internal plans. The homepage intentionally shows only the two live resource links
and does not tease unfinished sections.
Future integration can connect those pages to the existing breeding and
translation tools while retaining their established routes.

Keep the homepage focused on downloading and using the patch. Other sections
can have their own pages or project sites and reuse `theme.css`; no framework
migration is needed for this launch.

## Release and support notes

The current package is v1.0.72, verified against its GitHub release asset’s size
and SHA-256. It includes only the BPS patch, CUE, and original README. Draft v1.0.73
and unreleased development features are not part of this site’s download.

The published package’s README contains an expired Discord invitation. Use the
current [website invitation](https://discord.gg/6V9p6Y2pBt) for support, and fix the
invitation in the next release’s source README. Do not rewrite existing ZIPs:
the manifest tracks their original published hashes.

The hero party is Terry with three monsters: Hale (Healslime), Dragon, and
SabreCat. Cats4gold is credited on the homepage for helping with the breeding tool.

The patch ZIP contains a BPS patch, a matching CUE file, and its original README. Follow the included README for release-specific instructions. No game disc images are included.

Dragon Quest and its characters belong to their respective owners. This is a fan project.
