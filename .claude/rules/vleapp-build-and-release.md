# Build and release

One driver, `packaging/build.py`, on every platform, in two phases so a signed build is
possible. It replaced six PyInstaller specs, one per program and platform, each with its own
hand-kept list of hidden imports and its own copy of the version. It is a port of iLEAPP's
(abrignoni/iLEAPP#2298), by way of RLEAPP's, without the Unified Log parser. VLEAPP bundles
no executable of its own: the image readers in `scripts/vendor/` are Python, standard
library only, and ship as source with the rest of `scripts/`.

    python packaging/build.py exe               phase 1: dist/VLEAPP/ holding vleapp; on macOS also dist/VLEAPP.app
    python packaging/build.py exe --onefile     phase 1: dist/vleapp, a single file; no installer from this
    python packaging/build.py smoke             run what phase 1 built, headlessly (xvfb-run on Linux)
    python packaging/build.py installer         phase 2: Windows dist/VLEAPP-Setup-<v>.exe, macOS dist/VLEAPP-<v>.dmg,
                                                Linux dist/VLEAPP-<v>.AppImage
    python packaging/build.py installer --sign-tool NAME
                                                Windows: Inno Setup signs the installer and the uninstaller
    python packaging/build.py all               both phases, unsigned; refuses --sign-tool and --onefile
    python packaging/build.py verify PATH ...   a signature is present and valid; --subject checks the signer

## One executable, the window or the command line

The spec builds `packaging/entrypoint.py`, not `vleapp.py` or `vleappGUI.py`, which stay the
way to run from source. The result is one executable, `vleapp`, and there is no `vleappGUI`
in a build. Started without arguments, as a double-click, the Start menu or the Finder
start it, it opens the window. Given arguments it is the command line, exactly as before,
so tools that run `vleapp -t fs -i ... -o ...` see no change. Where no window can open
(Linux with no display, as over SSH) it prints the command line's help.

It is a console program. On Windows `hide_console="hide-early"`, which the old GUI build
used, hides the console when nobody started it from one. On macOS it is the bundle's own
executable, `VLEAPP.app/Contents/MacOS/vleapp`. `console=True` makes PyInstaller mark the
bundle `LSBackgroundOnly`, which leaves the window without a Dock icon or menu bar, so the
spec sets it back to false.

The bundle identifier is `org.leapps.VLEAPP`. It replaced `4n6.brigs.VLEAPP`, the earlier
GUI bundle's, so macOS treats the two as different apps: permissions granted to the old
one, Full Disk Access included, have to be granted again.

The Inno Setup `AppId` is VLEAPP's own GUID. The script was ported from RLEAPP's, and
Windows identifies an installed program by that GUID: a shared one makes installing one
LEAPP upgrade or uninstall another. A test holds it apart from iLEAPP's, ALEAPP's and
RLEAPP's.

`scripts/lavafuncs.py` records `leapp_mode` from the script name from source and, in a
build, from whether a `*leappGUI` module was loaded, which only the window's path does.
That file is shared across the LEAPPs; the check is the one iLEAPP carries.

## What goes into the bundle

Decided in `build.py`, which the spec loads, so it is tested without running PyInstaller
(`admin/test/scripts/test_packaging_build.py`, which also exec's the spec with PyInstaller
stubbed out).

- `scripts/`, `leapp_functions/` and `assets/` ship as files, without `__pycache__`. The
  plugin loader reads the artifacts from `scripts/artifacts` as source, the report copies
  `scripts/_elements`, and the window loads its images from `assets/`.
- **Every artifact module is also a hidden import**, so PyInstaller follows what they
  import. What it still cannot follow is a module imported by a name built at run time,
  and an artifact whose file name is not a valid module name.
- `compression.zstd` is named outright: `scripts/search_files.py` imports it by a name
  built at run time, and a zstd tar, SquashFS or UBIFS needs it. It exists from Python
  3.14, which the builds use.
- `PIL` and `leapp_functions` are collected whole, and the old specs' explicit list is
  kept: `bz2`, `gzip`, `tarfile` and `xml.etree.ElementTree`, standard library that only
  artifacts import and that PyInstaller pruned until a frozen run died on `xml.etree`.

## Signing goes between the phases

Sign `vleapp.exe` in `dist/VLEAPP/`, or codesign `dist/VLEAPP.app`, after phase 1 and
before phase 2, or the installer ships an unsigned executable inside a signed wrapper.
`all` refuses `--sign-tool` for exactly that reason. PyInstaller signs every macOS build
ad hoc; a Developer ID signature replaces that one. `verify` is the last step before
anything is uploaded.

On Windows, `release.yml` signs with SignPath through its GitHub action, not with
`--sign-tool`: SignPath signs only what a workflow stored as an artifact of its own run,
which is how it checks the binary was built from this repository on GitHub's runners, so
nothing on the build machine can sign. Windows releases ship only the single-file
`dist/vleapp.exe`, so it is the one file sent, in one request, as `vleapp.exe`. VLEAPP
bundles no third-party executable, so nothing else would need signing. The artifact
configuration SignPath applies, `vleapp-portable`, is kept in `packaging/signpath/` and
must be edited there and in SignPath together. Signing appends to the executable and the
single file finds its archive by reading from its end, so it is smoke-tested again once
signed. `build.py installer --sign-tool` still works on Windows for a local build;
releases do not use it.

## What the driver guarantees

The version is read from `vleapp_version` in `scripts/version_info.py` as text and passed
to the spec (the Windows version resource, the bundle's `Info.plist`) and to Inno Setup;
`installer.iss` refuses to compile without it. Windows and macOS take only numbers there,
so `2026.4.1-dev` becomes `2026.4.1` in those fields. `ONEFILE` reaches the spec through
`VLEAPP_ONEFILE`; the spec is never edited by a build. PyInstaller and dmgbuild are pinned
in `packaging/requirements-build.txt`, which phase 1 installs with `requirements.txt`.
Every artifact is asserted to exist after the step that makes it; an exit code is not
evidence. `--clean` removes `build/` and the driver's own output in `dist/`, never the rest
of `dist/`.

`dist/vleapp` and `dist/VLEAPP/` are the same path on a case-insensitive file system, the
default on macOS, and PyInstaller's `--noconfirm` deletes whatever is there. The driver
refuses to build one layout over the other; `--clean` is the explicit way.

## What `smoke` checks

`--version` against `scripts/version_info.py`; a run over an empty extraction, which loads
and runs every artifact and writes a report; a run over the NTFS raw fixture, whose log has
to show the walk; and `vleapp --selfcheck`, which takes the window's path, starts Tk, loads
the images from `assets/` and every artifact, then exits before drawing a window. The
self-check reports how many artifacts it loaded and `smoke` compares that with the count
from source, which is how a module missing from the build shows up. On Linux it also
starts `vleapp` with no arguments and no display, which must print the command line's
help. On macOS all of it runs against the `.app`, the layout that ships.

Measured on 2026-10-01, macOS arm64, Python 3.14.7, PyInstaller 6.22.3: phase 1 in 18 s
(the requirements already installed), `smoke` in 2 s, 103 artifacts loaded by the build
and from source, a 69 MB bundle and a 32 MB disk image.

## What is and is not wired up

Windows (x64 and ARM64): releases ship only a `--onefile` build, zipped alone as the
portable download so it keeps the name `vleapp.exe` that the docs and calling tools use.
There is no installer since 2026-10-10, as in RLEAPP: it was a second file to sign, as
well as the folder build inside it. The cost is that the single file unpacks itself to
`%TEMP%` on every start, so it is slower to start and blocked where AppLocker or WDAC
forbid running programs from `%TEMP%`; the footer sends those users to the source.
Rehearsals dispatched by hand are signed too; `test_builds.yml` signs nothing. The
portable zip used to hold the folder build, whose `_internal` directory confused users.
The Inno Setup script and `build.py installer` remain for local builds, the installer on
ARM64 installing only on ARM64. Unlike RLEAPP and iLEAPP, the ARM64 legs need no OpenSSL
step: nothing VLEAPP requires depends on `cryptography`, which publishes no win_arm64
wheels, and the leg built without it before this driver existed. macOS (Apple silicon and
Intel): `.app` and `.dmg`. The `.dmg` is
laid out by dmgbuild from `packaging/dmg_settings.py`: the app and an Applications link
either side of the arrow on `packaging/dmg_background.png`. The settings place the icons
for that 960x540 image, so a new background keeps its size and its arrow where it is.
VLEAPP's arrow is not where the other LEAPPs draw theirs: it sits 44 points further right
(88 pixels on the @2x image), centred at x=479, so the icons are at (304, 290) and
(654, 290) rather than the (260, 290) and (610, 290) of iLEAPP, ALEAPP and RLEAPP. A test
finds the arrow on the background and requires the two icons to straddle it, so copying
another LEAPP's settings, or moving the arrow again, fails there rather than on a Mac.
`dmg_background@2x.png` beside it, at exactly 1920x1080, is what a Retina screen shows:
dmgbuild finds it by name and joins the two into one TIFF with `tiffutil
-cathidpicheck`, which refuses a pair that is not exactly 1x and 2x. Without it the
background is scaled up and blurred on every Retina Mac. Export both from the source;
upscaling the 1x brings the blur back.
Linux (x64 and ARM64): the folder build and an AppImage, made by appimagetool 1.9.1 with the
type2 runtime 20251108, both pinned by digest in `build.py` and run with
`APPIMAGE_EXTRACT_AND_RUN` so the build machine needs no FUSE. The finished AppImage is run
once and has to report the version. Linux builds are made on Ubuntu 22.04 for its glibc
2.35. `test_builds.yml` builds and smoke-tests all six legs weekly, on dispatch, and on pull
requests that touch packaging.

`release.yml` runs the same steps when a `v*` tag is pushed, refuses a tag that is not
`v` + `vleapp_version`, names the assets `VLEAPP-<version>-<platform>-<arch>`
(portable.zip on Windows, .dmg on macOS, .AppImage on Linux; no Linux .tar.gz), stages
them in `release-assets/` (never `assets/`, which holds the window's images), adds
`SHA256SUMS.txt`, and creates a **draft** release; publishing is a click. Dispatched by
hand, it builds the assets without creating a release. `.github/release-footer.md` is
appended to the notes. macOS is signed with a Developer ID, smoke-tested again as signed
(the hardened runtime is what breaks a frozen app), notarised and stapled when the
`MACOS_CERT_P12`, `MACOS_CERT_PASSWORD`, `MACOS_SIGN_IDENTITY`, `MACOS_TEAM_ID`,
`MACOS_NOTARY_KEY`, `MACOS_NOTARY_KEY_ID` and `MACOS_NOTARY_ISSUER_ID` secrets are set.
A tag refuses to publish without them, and the macOS legs check that first, before
building; a dispatched rehearsal builds unsigned. The footer tells users the disk images
are notarised, which holds only because of that refusal.

Windows is signed by SignPath when the `SIGNPATH_API_TOKEN` repository secret is set. The
job carries `actions: read` so SignPath can download the uploaded artifact, and the SignPath
GitHub App (github.com/apps/signpath) must be installed on the repository: SignPath's
documentation calls it optional, but without it every request fails with "Failed to
retrieve GitHub App token" (seen on iLEAPP, 2026-10-10). Only the owner of this
personal-account repository can install it. Repository variables:
`SIGNPATH_ORGANIZATION_ID`, `SIGNPATH_PROJECT_SLUG`, `SIGNPATH_SIGNING_POLICY`
(`test-signing` or `release-signing`), `SIGNPATH_CERT_SUBJECT` (optional, passed to
`verify --subject`) and, under `test-signing`, `SIGNPATH_TEST_CERT_B64`, the root of the
test certificate's chain as a base64 `.cer`, which only the runner is told to trust so
`verify` still checks a chain. A test-signed binary is trusted by no Windows, so a tag
signs only under `release-signing`; under any other policy, or without the token, a tag
builds unsigned and says so in a warning, as releases did before signing was wired. A
rehearsal signs under whichever policy is set. When `release-signing` is in place, change
the footer's "not signed yet" paragraph and the README's code signing policy, and make a
tag refuse an unsigned Windows build the way macOS does, since the footer will then
promise a signature.

A repository secret is usable by a workflow on any branch of this repository, though
never by a pull request from a fork. Before `release-signing`, SignPath should require a
manual approval of each request, which shows the branch and commit it came from. The
owner can go further: rulesets requiring a pull request on `main` and restricting who
creates `v*` tags, and a `release` environment admitting only those refs, holding the
token, with `environment: release` on the build job. Only the owner can create
environments and rulesets on this personal-account repository.

Set the release version in `scripts/version_info.py` first, tag that commit, then bump to
the next `-dev`: the tag check compares the two.

These names replaced the per-program downloads (`vleappGUI-v*-Windows_x86_64.zip`,
`vleapp-v*-macOS_Apple_Silicon.zip`, `vleappGUI-v*-macOS_Mac_Intel.dmg`,
`vleapp-v*-Linux_x86_64.AppImage` and the like, up to v2026.4.1), which leapps.org links to. The footer
tells tools that launch VLEAPP what changed for them: the Windows zip holds one file and
there is no Windows installer, the macOS executable needs its folder, and `vleappGUI` is
gone. Keep that note while those names are new.
