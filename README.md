# DQM PSX

The project homepage for the English fan translation of **Dragon Quest Monsters 1 & 2: The Starry Night Hero and Friends at the Ranch** for PlayStation.

[Visit the homepage](https://dqm-psx.github.io/) · [Discord](https://discord.gg/6V9p6Y2pBt) · [ROMhacking.net](https://www.romhacking.net/translations/7734/)

The site is being prepared as the public landing page for the English patch developed in `phakic/dqm1`. It provides a verified download, installation instructions, screenshots, project credits, a FAQ, and community support. The release home is `dqm-psx/patch`, which remains private. The website bundles the exact published v1.0.73 package locally so its download does not require access to that repository.

**Launch status:** GitHub Pages is disabled and the launch PR remains unmerged. Enable publication only after the project owner gives the go-ahead.

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

On GitHub Free, the hosting repository must be public to enable Pages. The patch
development repository can remain private. Public release-asset downloads and
bug submissions in `dqm-psx/patch` require that repository to be publicly accessible;
the website currently uses its bundled package while the release repository is
private. Before changing visibility, review each repository’s files and history
for anything not intended for publication.

Before pushing an update to `main`, run:

```sh
python tools/update_release.py --check
python tools/update_screenshots.py --check
python -m unittest discover -s tools -p 'test_*.py'
node --check homepage.js
node --check cover-intro.js
node --check gallery-data.js
node --check loading.js
```

Then check GitHub’s Pages deployment and visit the public URL while signed out.
Confirm the download, installation links, screenshot gallery, and mobile layout.
Preview changes on a branch before merging; after Pages is enabled, pushes to
`main` publish the site.

## Site files

- `index.html` contains the patch download and installation instructions, game and project introduction, FAQ, live reference links, and community support. Historical sources are linked beside the relevant text.
- `theme.css` provides the shared colors, typography, buttons, and RPG-style panels. `homepage.css` controls the homepage layout.
- `homepage.js` manages screenshots, the bug-report template, animation preferences, contributor rotation, and anchor offsets for the sticky navigation.
- `cover-intro.js` reveals the English title over shared cover artwork during ordinary page scrolling, with a reduced-motion alternative.
- `data/screenshots.json` is the reviewed gallery catalog. `tools/update_screenshots.py` validates it and generates `gallery-data.js`, loaded before `homepage.js`.
- `loading.js` provides a spinning-slime loading indicator. Call `const finish = DqmLoading.begin()` before an asynchronous task and `finish()` when it settles.
- `assets/provenance.json` records asset sources, dimensions, hashes, and screenshot display crops. Sprite animation can be paused and respects reduced-motion preferences.
- `downloads/releases.json` records packages newest first. The first entry supplies the current download card and release notes; every retained package supplies its explicitly credited contributors.
- `data/contributors.json` records project contributors credited separately from release READMEs, with a contribution and its source. Optional aliases preserve corrected names such as Claude Fable when an older release says Fable. It includes Cats4gold's help with the breeding tool and Nejimakipiyo's translation review, confirmed by the project owner.

## Navigation and FAQ

The top navigation stays visible while scrolling. Section links account for its
height on desktop and mobile, including wrapped navigation. FAQ topic links live
in a dropdown that opens on hover, or on click, tap, or keyboard activation. The
FAQ answers and navigation use native HTML disclosures and work without JavaScript.

FAQ content comes from the project owner's Discord FAQ and covers the project,
AI assistance, installation and updating, restored content, quality-of-life
changes, troubleshooting, and contributing. The FAQ covers v1.0.73, including
Terry’s restored table conversations and special dungeon floors, plus restored
monster wagers and expanded rules in the title-screen Colosseum. It explains the prize
transfer’s effect on both Adventure Logs and the need for save backups.
Movement settings under **Tactics → Movement** let each adventure choose independent
Walk and R1 speeds of 1×, 2×, or 4×, with Hold or Toggle controls. The defaults are
1× walking and 2× while holding R1. **Time** encounters, the default, preserve roughly
the usual encounter frequency per minute of travel; **Distance** uses the normal
rate per step. The full report template distinguishes
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

The screenshot gallery rotates through seventeen screenshots every seven seconds,
including eleven original 960×720 captures shared by BalK and three screenshots
posted by [3xad on Reddit](https://www.reddit.com/r/DragonQuestMonsters/comments/1weqzrc/dragon_quest_monsters_12_psx_english_translation/).
The added 3xad images show the title screen, field item menu and HP/MP status,
and a monster table conversation. They live in `assets/screenshots/`, with
credit, source URLs, dimensions, and SHA-256 hashes in `assets/provenance.json`.

All three 3xad PNGs are byte-for-byte copies of their downloaded sources. CSS
shows only their game viewports, hiding black side margins, the title screenshot's
emulator bars, and the table screenshot's fast-forward overlay. The source-pixel
crop rectangles are recorded in the provenance file. The other fourteen images
appear uncropped. No generated or repainted screenshot is used.

The screenshot footer contains the selector, credit, and previous/pause/next
icons. The selected option is the single visible caption; the standalone caption
is retained only as the no-JavaScript fallback. All icon buttons keep accessible
labels and tooltips. Previous, Next, and the screenshot selector pause automatic
rotation until the play icon is chosen. Hover, keyboard focus, hidden tabs, and an offscreen gallery
also suspend rotation; reduced-motion users start paused. The first screenshot
and its credit remain visible without JavaScript. The dropdown count updates
automatically from the reviewed screenshot catalog.

## Screenshot submissions and approval

The gallery's **Submit a screenshot** link opens
`.github/ISSUE_TEMPLATE/screenshot.yml` in this website repository. Visitors
attach an original image, choose their credit name, describe the scene, and
optionally enter the patch version. Opening the form does not submit the issue.
The template becomes available after this PR is merged into the default branch;
public submissions also require the planned public repository launch.
The link has no accompanying submission teaser; the approval process is unchanged.

Submissions never enter the slideshow automatically. A maintainer reviews the
issue and image, then prepares an approved addition in a branch for review and
merge. Closing an issue or adding a label does not publish an image. The website
only reads its committed gallery catalog; it does not fetch issues or uploads.

For maintainer checks and imports, install Pillow with
`python -m pip install Pillow`. This dependency is not used by the website.
After reviewing a submission, download its original image and run, for example:

```sh
python tools/update_screenshots.py --image "path/to/screenshot.png" --name player-gate --credit PlayerName --caption "Through the gate" --alt "Terry approaches a Travelers’ Gate with three monsters." --issue https://github.com/dqm-psx/dqm-psx.github.io/issues/123 --patch-version v1.0.72
```

Replace the example issue URL with the real submission. Omit `--patch-version`
when unknown. A known version displays as `Screenshot by PlayerName (v1.0.72)`;
an unknown version displays as `Screenshot by PlayerName`. Existing screenshot
versions are deliberately left unknown rather than inferred from a release date.
Optional `--crop X Y WIDTH HEIGHT` hides emulator borders using source-pixel
coordinates without modifying the original image.

The helper validates the image, metadata, and provenance before copying anything.
Review the image in the local preview and commit its asset, catalog entry,
provenance, and regenerated JavaScript together. It never contacts GitHub,
commits, pushes, or deploys. Run `python tools/update_screenshots.py --check` to
verify the catalog, or omit `--check` to regenerate after an intentional edit.

## Cover artwork

The opening panel assembles a Japanese title over shared artwork from the English
fan cover and a fixed paper background. Scrolling replaces only the title and
subtitle with their English counterparts, from top to bottom with a soft edge;
older browsers blend the title layers. The artwork and paper stay fixed throughout.
The cover stays in view during the transition, then ordinary scrolling continues
into the patch homepage. Navigation and **Explore the English patch** bypass the
intro. Direct section URLs still work. Reduced-motion mode swaps the title without
a blend or extra scroll distance; without JavaScript, the assembled Japanese-title
cover and direct link remain available. There is no separate cover caption.

The shared background uses `assets/artwork/cover-paper-base.png`, a generated
1254×1254 version of the English cover with its title removed. This plate is not
pixel-identical to its source: its upper paper area and small portions of the
highest artwork remain visible. A static overlay of `dqm-1-2-english-cover.png`
restores the existing lower artwork, beginning at 28.6% of the cover height and
becoming fully opaque at 29.2%. Neither background layer participates in the
scroll reveal.

`cover-title-japanese.png` and `cover-title-english.png` are generated 2172×724
transparent PNGs, based on the supplied Japanese cover and the English fan cover
respectively. The Japanese PNG's generated subtitle contains a duplicated character,
so its bottom 23% is hidden and an inline SVG renders the exact text
`星降りの勇者と牧場の仲間たち`. Both title compositions occupy the same frame: 6%
from the left, 2% from the top, 88% wide, and 25.4% high. Only these title layers
receive the scroll masks. The original
640×640 Japanese cover remains as a source asset; it is no longer displayed in
full. The layer-generation and Japanese refinement prompts are retained in
`assets/artwork/cover-layers-prompts.txt`.

The English fan adaptation was made with the built-in image generation tool from the
[735×735 BD Jogos source](https://bdjogos.com.br/jogo.php?id=10712).
`assets/artwork/dqm-1-2-english-cover.png` is the 1254×1254 generated output;
that size is not the resolution of an original scan. The edit localizes the title
and subtitle. Its exact prompt is retained in
`assets/artwork/english-cover-prompt.txt`. Sources, dimensions, hashes, transparency,
and display roles for the cover assets are recorded in `assets/provenance.json`.
Historical source links on the homepage sit beside the relevant text.

## Updating the patch download and contributor credits

`dqm-psx/patch` is the release home. v1.0.73 is published and verified, but the
repository remains private. The website therefore serves the exact release ZIP
from its own `downloads/` directory. A manifest entry’s `releaseUrl` records the
upstream release as provenance; it does not change the download destination.

The release repository now contains all 28 packages from the source repository’s
root and archive, copied unchanged with verified hashes. Its
[`release-manifest.json`](https://github.com/dqm-psx/patch/blob/main/release-manifest.json)
records the source snapshot and every migrated package. v1.0.73 is marked latest.

Only after a release asset is accessible without signing in and its downloaded
bytes match the recorded size and SHA-256 should an entry gain `downloadUrl`.
The helper accepts only the pinned form
`https://github.com/dqm-psx/patch/releases/download/v{version}/{filename}`,
matching that entry’s version and package filename. It rejects other destinations,
floating latest-release links, queries, and fragments. Omit `downloadUrl` while
the repository is private to retain the local download. Public availability is
verified separately; the helper performs its validation offline. Do not link
visitors to the private development repository or promote a draft release.

The current preview uses the existing local package workflow below. Retained
packages also preserve historical credits and allow integrity checks offline.

Copy the published ZIP unchanged to `downloads/` and prepend its version, filename, byte size,
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

The current package is `DQM1-2-English-v1.0.73-public.zip`, verified against its
published release asset: **7,558,537 bytes**, SHA-256
`652ae16c06cc2291495b592bde5a2737e68e483879b4dc684ed4d58a56e1493a`.
The local copy is byte-for-byte identical and includes only the BPS patch, matching
CUE, and original README. Published release status does not make the private
release repository publicly accessible; the website’s download remains local.

Some retained release READMEs contain an expired Discord invitation. Use the
current [website invitation](https://discord.gg/6V9p6Y2pBt) for support, and make
any invitation corrections in a future release’s source README. Do not rewrite
existing ZIPs: the manifest tracks their original published hashes.

The hero party is Terry with three monsters: Hale (Healslime), Dragon, and
SabreCat. Cats4gold is credited on the homepage for helping with the breeding tool.

The patch ZIP contains a BPS patch, a matching CUE file, and its original README. Follow the included README for release-specific instructions. No game disc images are included.

Dragon Quest and its characters belong to their respective owners. This is a fan project.
