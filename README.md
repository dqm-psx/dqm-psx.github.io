# DQM PSX

The project homepage for the English fan translation of **Dragon Quest Monsters 1 & 2: The Starry Night Hero and Friends at the Ranch** for PlayStation.

The homepage is in private preview. GitHub Pages is disabled. The public launch and repository visibility changes require the project owner’s go-ahead.

## Preview and build

Serve the checkout with `python -m http.server 4173 --bind 127.0.0.1` and open [the local preview](http://127.0.0.1:4173/). The source works directly as a static site. For the production layout, install Pillow and build it locally:

```sh
python -m pip install Pillow
python tools/update_release.py --check
python tools/update_screenshots.py --check
python -m unittest discover -s tools -p 'test_*.py'
python tools/build_site.py
python -m http.server 4174 --bind 127.0.0.1 --directory dist
```

The build checks internal anchors, local URLs, gallery and sprite assets, and the two HTML pages. It inlines the theme preference script before the stylesheets so a saved choice applies on first paint. The CSS and deferred JavaScript bundle have content hashes in their filenames. Only visitor-facing files and compatible download URLs are included in the artifact. The cover’s responsive WebPs are already optimized and committed. Rebuild them with the artwork recipe below when their source changes.

## Launch plan

1. Keep serving the verified v1.0.73 ZIP locally during private preview. The hero links directly to the package and shows its version and actual size. The release record supplies the button, notes, and credits.
2. When the owner approves launch, make the intended distribution and issue destinations accessible to visitors. On GitHub Free for organizations, the Pages hosting repository must be public. The development repository can stay private. The patch repository needs public releases and Issues, and the website repository needs its screenshot issue form. Run `python tools/check_public_links.py` to test those destinations without credentials, then verify a versioned release asset against the manifest before switching the download.
3. Select **Settings → Pages → Source → GitHub Actions** in the website repository when ready to publish. The workflow builds and checks each PR. On the default branch it deploys only when Pages is already configured for Actions. It never enables Pages. The same workflow can be run manually after changing the hosting source.
4. Check the published download, install anchors, bug and screenshot forms, compact navigation, and cover on a phone while signed out. Bring matching project navigation to the separate Guide and Translations sites when the homepage destination is reachable.

[GitHub Pages availability and Actions deployment](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)

## Navigation and FAQ

The homepage opens with the original Japanese cover, patch download, and install link. Installation and release notes lead into screenshots, the FAQ, support, and project credits. The sticky header has a compact menu on phones and a FAQ topic dropdown that supports hover, keyboard, and touch. Each FAQ answer has a fragment URL. Source-image questions link to the original Japanese BIN size and SHA-256 in the first installation step. The separate ZIP checksum identifies the translation package.

The FAQ follows the project’s Discord FAQ and the release README. It covers translation and AI assistance, installation and updating, Terry’s restored content, Colosseum monster wagers, Movement settings, and troubleshooting. Bug reports go to the issue form in `dqm-psx/patch`. Translation corrections go through the comparison site and open issues in `dqm-psx/translations`.

## Screenshot gallery

The reviewed catalog in `data/screenshots.json` includes BalK’s eleven captures, three project images, and 3xad’s title screen, field menu, and restored table conversation. The opening set highlights patch features. All approved captures are available from the selector. The first image loads from the HTML and its caption and credit remain visible without JavaScript. Visitors can swipe, use the arrows, or start the seven-second slideshow with the play button. The gallery pauses during manual browsing and while offscreen. The animated party sprites have their own motion preference.

The three Reddit captures are cropped to the actual game viewport and encoded as lossless WebP. The source URLs, dimensions, hashes, source-pixel crop rectangles, and output hashes are in `assets/provenance.json`. Other captures retain their original framing. [3xad’s original screenshot post](https://www.reddit.com/r/DragonQuestMonsters/comments/1weqzrc/dragon_quest_monsters_12_psx_english_translation/)

## Screenshot submissions and approval

The gallery's **Submit a screenshot** link opens
`.github/ISSUE_TEMPLATE/screenshot.yml` in this website repository. Visitors
attach an original image, choose their credit name, describe the scene, and
optionally enter the patch version. The form must be on the default branch and
the repository accessible to visitors at launch.

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
Optional `--crop X Y WIDTH HEIGHT` saves the selected source-pixel rectangle as lossless WebP and records the original hash and dimensions. Without a crop the file is copied byte for byte.

The helper validates the image, metadata, and provenance before copying anything.
Review the image in the local preview and commit its asset, catalog entry,
provenance, and regenerated JavaScript together. It never contacts GitHub,
commits, pushes, or deploys. Run `python tools/update_screenshots.py --check` to
verify the catalog, or omit `--check` to regenerate after an intentional edit.

## Cover artwork

The opener shows the complete printed Japanese retail front for SLPM-87050,
including its original lettering, subtitle, illustration, and platform marks.
The source is a 2,906 × 2,951, 600 dpi JPEG. Its SHA-256 is
`246108fd30f463f6b9da87c3af0d81617ab3895ed9c10ed91325e7bbe59f29c4`.
[Archival scan collection](https://archive.org/details/image-027) ·
[Original front scan](https://archive.org/download/image-027/Image001.jpg).

`cover-japanese-560.webp` and `cover-japanese-1120.webp` are full-frame display
copies of the scan. An English title overlay in matching widths covers the
printed Japanese title as visitors scroll. The overlay uses paper sampled above
the original heading and retains the visible edges of the hat pompom and tail.
It spans the full width of the cover, begins at the top left and has a 10:3
aspect ratio. The underlying scan stays fixed throughout the reveal. Without
JavaScript the Japanese cover and navigation remain available.

The English lettering comes from `cover-title-english.png`, the existing fan
title based on the [English cover's original reference](https://bdjogos.com.br/jogo.php?id=10712).
Its generation prompts are recorded in `assets/artwork/cover-layers-prompts.txt`.
The source scan, processed artwork, dimensions, and SHA-256 hashes are recorded
in `assets/provenance.json`.

To rebuild the WebPs, 1,200 × 630 social card, and static Slime icons, run
`python assets/artwork/build_cover.py` with Pillow and WebP support. The build
uses the local source images, verifies the input hashes and checks the decoded
overlay's transparency around the illustration at both output sizes. The
committed files were made with Pillow 12.1.1 and libwebp 1.6.0.

## Release-driven downloads and FAQ

The source builder prepares both editions and their public release information. Enhanced uses its default full selection. Translation only includes the translation, its required runtime support, and original-game bug fixes. The website displays those recorded selections.

Each new release in [dqm-psx/patch](https://github.com/dqm-psx/patch/releases) contains two edition ZIPs, `release.json`, and `SHA256SUMS.txt`. Each ZIP contains a versioned BPS, matching CUE, README, and `BUILD.json`. The build record identifies the version, edition, source revision, fonts, language, selected features, and output checksum. Release preparation creates a draft for review. The owner publishes it when ready.

`release.json` supplies the download identity, notes, credits, available features, and complete player-facing FAQ answers. The builder's shared feature documentation is reviewed as part of release preparation. A new feature must have its explanation before the website can adopt the release. FAQ answers cover all released project features and stay identical when a visitor chooses a different edition. Published answers and their anchors remain available when GitHub Latest intentionally returns to an older release.

The website follows GitHub's **Latest** stable release, including deliberate rollbacks. New releases after v1.0.73 require the two-edition catalog. Historical single-package releases remain supported. The current v1.0.73 preview keeps its verified local download until a new edition pair is published.

Automatic import requires publicly downloadable release assets. While the distribution repository remains private, use the prepared-bundle preview below to review new releases; the public importer retains the existing local preview. Making release downloads public remains part of the owner's launch decision.

The **Sync patch release** workflow checks every six hours and supports a manual run from Actions. The build also accepts a `patch-release` repository dispatch. The distribution repository can send that notification immediately when its `WEBSITE_DISPATCH_TOKEN` secret is configured with permission to dispatch to this website repository. The scheduled check provides automatic updates when the notification is unavailable. That secret is an optional launch setup step.

Automatic synchronization builds the website directly from the published release information. It does not require a release-update PR. It verifies the current ZIPs, their hashes, CUE filenames, BPS headers, build records, and complete feature explanations before producing an artifact. Historical catalog hashes are verified against GitHub so their FAQ entries can be retained. Failure stops deployment and reports the missing or invalid information in Actions. Each successful run provides a `homepage-preview` artifact.

Deployment uses the existing Pages configuration. Enable hosting only after the owner's launch approval. Ordinary website code changes continue through PR review.

To check the currently published release without writing source files:

```sh
python tools/sync_release.py --dry-run
```

To import its information into a local checkout for inspection:

```sh
python tools/sync_release.py
python tools/update_release.py --check
```

A prepared release bundle can be previewed before publication using an isolated build:

```sh
python tools/preview_release.py --release-dir /path/to/release-bundle --output /path/to/release-preview
python -m http.server 4174 --bind 127.0.0.1 --directory /path/to/release-preview
```

The preview validates both ZIPs, renders the edition controls and global FAQ, and labels the page as a release preview. The builder's `prepare_release.py --website /path/to/this-checkout` invokes the same preview step. The preview directory contains the public patch packages and website assets.

The gold button beside the cover, the “Latest patch” text link, and the first installation step all use the selected edition. Both edition selectors synchronize those links, the description, and the ZIP size/checksum. Without JavaScript, both named downloads remain accessible. The release archive and patch repository links remain available alongside the download.

The committed `downloads/releases.json` retains the verified legacy packages and credits. The release-sync build imports newer catalog records into the same format in its workspace. Public releases link to pinned GitHub Release assets, and compatible local download bookmarks continue to work.

Names are deduplicated without regard to case and sorted alphabetically, ignoring
leading underscores for sorting while preserving them in displayed names. The
first spelling wins: manual project entries first, then releases newest first.
Retain older packages and manifest entries so credits survive when a newer README
shortens its release history. To preserve a credit independently of a package,
add it to `data/contributors.json` with its explicit contribution and source.
Credit people only when a source explicitly names them for their work.
Entries with `"creditType": "ai-assistance"` appear in the static AI contributors
list beside the carousel. Use `aliases` to group historical model names under
one public credit. The AI FAQ can name the models and describe their roles. Kingcom
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

Commit the manifest, any bundled preview package or project-credit updates, and generated HTML together. The committed page includes every name and works without JavaScript;
there is no visitor-time build, GitHub API request, or background polling. The
browser's optional rotation is presentation only. Run the helper checks with:

```sh
python -m unittest discover -s tools -p 'test_*.py'
```

The human credits use a distinct panel beside the separate AI list, with larger
names and compact previous/pause/next controls. Four names appear at a time,
advancing every seven seconds. View all expands the same list and pauses
rotation; Show fewer restores the previous group, still paused. There are no
visible page counts. Hover, keyboard focus, hidden tabs, and offscreen panels
pause rotation. Reduced-motion users start paused. Without JavaScript, every
name remains visible. The columns stack on narrow screens.

## Reference tools and future scope

The patch landing page stands on its own and links to these existing public tools:

- [Guide](https://dqm-psx.github.io/guide/) for breeding recipes, pair finding, and team planning.
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

The bundled v1.0.73 package is `DQM1-2-English-v1.0.73-public.zip`, verified against its
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
