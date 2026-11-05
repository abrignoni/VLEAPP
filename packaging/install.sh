#!/usr/bin/env bash
# One-line installer for VLEAPP releases.
#
#   curl -fsSL https://raw.githubusercontent.com/abrignoni/VLEAPP/main/packaging/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/abrignoni/VLEAPP/main/packaging/install.sh | bash -s -- --help
#
# What it does, in order: resolve the release (latest, or --ref), download
# SHA256SUMS.txt for it, pick the asset for this machine, check the download
# against the checksums, and install it:
#
#   Debian/Ubuntu  a .deb through dpkg (needs root: sudo or run as root)
#   Fedora/RHEL    an .rpm through dnf/yum/rpm (needs root)
#   Arch           vleapp-git from the AUR when an AUR helper exists,
#                  otherwise the AppImage below
#   other Linux    the AppImage, made executable, into ~/.local/bin
#                  (--system puts it in /usr/local/bin instead)
#   macOS          the .dmg, whose VLEAPP.app is copied to /Applications
#   Windows        the portable zip, unpacked where --to says
#
# Every download is verified and the install stops on the first failure. Pass
# --no-verify only on a machine with no SHA-256 tool and no way to get one.
set -u -o pipefail

REPO_DEFAULT="abrignoni/VLEAPP"
APP="vleapp"

REF=""            # tag, e.g. v2026.5.0; empty means the latest release
REPO="$REPO_DEFAULT"
TO=""             # install directory (AppImage/zip); empty means the default
SYSTEM=0          # install system-wide where that is an option
YES=0             # never ask
VERIFY=1          # check SHA256SUMS.txt
PRINT_ASSET=0     # only print the chosen asset URL and stop

log() { printf '%s\n' "$*"; }
err() { printf 'install.sh: %s\n' "$*" >&2; }
die() { err "$*"; exit 1; }

usage() {
    sed -n '2,/^set -u/p' "$0" | sed -e 's/^# \{0,1\}//' -e '$d'
    cat <<'EOF'

Options:
  --ref TAG     install this release tag instead of the latest (e.g. --ref v2026.5.0)
  --repo R      GitHub repository, OWNER/NAME (default: abrignoni/VLEAPP)
  --to DIR      where the AppImage or the Windows zip goes
                (default: ~/.local/bin, or /usr/local/bin with --system)
  --system      system-wide install where supported (/usr/local/bin, /Applications)
  --yes, -y     answer yes to every prompt (needed for unattended AUR installs)
  --no-verify   skip the SHA-256 check (not recommended)
  --print-asset resolve the release and print the asset URL, then stop
  --help, -h    this text
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --ref) REF="${2:?--ref needs a tag}"; shift 2 ;;
        --repo) REPO="${2:?--repo needs OWNER/NAME}"; shift 2 ;;
        --to) TO="${2:?--to needs a directory}"; shift 2 ;;
        --system) SYSTEM=1; shift ;;
        --yes|-y) YES=1; shift ;;
        --no-verify) VERIFY=0; shift ;;
        --print-asset) PRINT_ASSET=1; shift ;;
        --help|-h) usage; exit 0 ;;
        *) die "unknown option: $1 (see --help)" ;;
    esac
done

need_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "need '$1' to continue"
}

# --- fetching -----------------------------------------------------------------

if command -v curl >/dev/null 2>&1; then
    fetch() { curl -fsSL --retry 3 -o "$2" "$1"; }
    fetch_text() { curl -fsSL --retry 3 "$1"; }
elif command -v wget >/dev/null 2>&1; then
    fetch() { wget -q -O "$2" "$1"; }
    fetch_text() { wget -q -O - "$1"; }
else
    die "need 'curl' or 'wget' to continue"
fi

API="https://api.github.com/repos/$REPO/releases"

resolve_tag() {
    if [ -n "$REF" ]; then
        printf '%s\n' "$REF"
        return
    fi
    local latest tag
    latest="$(fetch_text "$API/latest")" || die "could not reach $API/latest"
    if command -v python3 >/dev/null 2>&1; then
        tag="$(printf '%s' "$latest" | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"])')"
    else
        tag="$(printf '%s' "$latest" | grep -m1 '"tag_name"' | sed 's/.*: *"//; s/".*//')"
    fi
    [ -n "$tag" ] || die "could not find the latest release tag"
    printf '%s\n' "$tag"
}

# --- this machine ---------------------------------------------------------------

OS="$(uname -s)"
MACH="$(uname -m)"
case "$MACH" in
    x86_64|amd64) DEB_ARCH="amd64"; RPM_ARCH="x86_64"; IMG_ARCH="x64"; DMG_ARCH="x64"; ZIP_ARCH="x64" ;;
    aarch64|arm64) DEB_ARCH="arm64"; RPM_ARCH="aarch64"; IMG_ARCH="arm64"; DMG_ARCH="arm64"; ZIP_ARCH="arm64" ;;
    *) die "unsupported architecture: $MACH" ;;
esac

DISTRO_ID=""; DISTRO_LIKE=""
if [ -f /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    DISTRO_ID="${ID:-}"; DISTRO_LIKE="${ID_LIKE:-}"
fi

# --- pick the asset ---------------------------------------------------------------

TAG="$(resolve_tag)"
VERSION="${TAG#v}"
BASE="https://github.com/$REPO/releases/download/$TAG"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

log "release: $TAG"
fetch "$BASE/SHA256SUMS.txt" "$TMP/SHA256SUMS.txt" \
    || die "could not download SHA256SUMS.txt for $TAG"

pick() {
    # First grep pattern that matches exactly one line wins; the asset is its last field.
    local pattern match
    for pattern in "$@"; do
        match="$(grep -E "$pattern" "$TMP/SHA256SUMS.txt" || true)"
        if [ "$(printf '%s\n' "$match" | grep -c .)" = "1" ]; then
            printf '%s\n' "$match" | awk '{print $NF}'
            return 0
        fi
    done
    return 1
}

ASSET=""
KIND=""
case "$OS" in
    Linux)
        if command -v dpkg >/dev/null 2>&1 && { [ "$DISTRO_ID" = "debian" ] || [ "$DISTRO_ID" = "ubuntu" ] \
                || [[ " $DISTRO_LIKE " == *" debian "* ]] || [[ " $DISTRO_LIKE " == *" ubuntu "* ]]; }; then
            ASSET="$(pick "vleapp_.*_${DEB_ARCH}\\.deb\$" ".*_${DEB_ARCH}\\.deb\$")" && KIND="deb"
        elif command -v rpm >/dev/null 2>&1 && { command -v dnf >/dev/null 2>&1 || command -v yum >/dev/null 2>&1 \
                || [ "$DISTRO_ID" = "fedora" ] || [ "$DISTRO_ID" = "rhel" ] || [ "$DISTRO_ID" = "centos" ] \
                || [ "$DISTRO_ID" = "opensuse"* ] || [[ " $DISTRO_LIKE " == *" rhel "* ]] \
                || [[ " $DISTRO_LIKE " == *" fedora "* ]] || [[ " $DISTRO_LIKE " == *" suse "* ]]; }; then
            ASSET="$(pick ".*\\.${RPM_ARCH}\\.rpm\$" ".*\\.rpm\$")" && KIND="rpm"
        elif [ "$DISTRO_ID" = "arch" ] || [[ " $DISTRO_LIKE " == *" arch "* ]]; then
            if command -v yay >/dev/null 2>&1; then HELPER="yay";
            elif command -v paru >/dev/null 2>&1; then HELPER="paru";
            else HELPER=""; fi
            if [ -n "${HELPER:-}" ]; then KIND="aur";
            else ASSET="$(pick "linux-${IMG_ARCH}\\.AppImage\$" ".*\\.AppImage\$")" && KIND="appimage"; fi
        else
            ASSET="$(pick "linux-${IMG_ARCH}\\.AppImage\$" ".*\\.AppImage\$")" && KIND="appimage"
        fi
        ;;
    Darwin)
        ASSET="$(pick "macos-${DMG_ARCH}\\.dmg\$" ".*\\.dmg\$")" && KIND="dmg"
        ;;
    MINGW*|MSYS*|CYGWIN*)
        ASSET="$(pick "windows-${ZIP_ARCH}-portable\\.zip\$" ".*\\.zip\$")" && KIND="zip"
        ;;
    *) die "unsupported system: $OS" ;;
esac
[ -n "$KIND" ] || die "no asset in $TAG for $OS/$MACH"

if [ "$PRINT_ASSET" = "1" ]; then
    if [ "$KIND" = "aur" ]; then
        log "vleapp-git (AUR)"
    else
        log "$BASE/$ASSET"
    fi
    exit 0
fi

as_root() {
    if [ "$(id -u)" = "0" ]; then "$@";
    elif command -v sudo >/dev/null 2>&1; then sudo "$@";
    else die "need root for this step and neither root nor sudo is available"; fi
}

confirm() {
    # confirm "question"; true when --yes or the user answers yes.
    [ "$YES" = "1" ] && return 0
    printf '%s [y/N] ' "$1" >&2
    read -r answer || return 1
    [[ "$answer" == [yY] || "$answer" == [yY][eE][sS] ]]
}

verify() {
    [ "$VERIFY" = "1" ] || { err "--no-verify: skipping the checksum check"; return 0; }
    ( cd "$TMP" && grep -F " $1" SHA256SUMS.txt > "$TMP/check.txt" ) \
        || die "SHA256SUMS.txt has no line for $1"
    if command -v sha256sum >/dev/null 2>&1; then
        ( cd "$TMP" && sha256sum -c check.txt ) || die "checksum mismatch for $1"
    elif command -v shasum >/dev/null 2>&1; then
        ( cd "$TMP" && shasum -a 256 -c check.txt ) || die "checksum mismatch for $1"
    else
        die "no sha256sum or shasum to check the download (or pass --no-verify)"
    fi
    log "checksum OK: $1"
}

download_asset() {
    log "downloading: $ASSET"
    fetch "$BASE/$ASSET" "$TMP/$ASSET" || die "could not download $ASSET"
    verify "$ASSET"
}

# --- install ------------------------------------------------------------------------

install_deb() {
    need_cmd dpkg
    download_asset
    as_root dpkg -i "$TMP/$ASSET" || {
        err "'dpkg -i' failed; missing dependencies are fixed with:"
        err "  sudo apt-get install -f"
        exit 1
    }
    command -v "$APP" >/dev/null 2>&1 || die "install finished but '$APP' is not on PATH"
    log "installed: $("$APP" --version)"
}

install_rpm() {
    download_asset
    if command -v dnf >/dev/null 2>&1; then
        as_root dnf install -y "$TMP/$ASSET"
    elif command -v yum >/dev/null 2>&1; then
        as_root yum install -y "$TMP/$ASSET"
    else
        need_cmd rpm
        as_root rpm -Uvh "$TMP/$ASSET"
    fi
    command -v "$APP" >/dev/null 2>&1 || die "install finished but '$APP' is not on PATH"
    log "installed: $("$APP" --version)"
}

install_aur() {
    log "Arch: installing vleapp-git from the AUR with $HELPER"
    log "The AUR package builds the latest main branch, so --devel updates keep it current:"
    log "  yay -Syu --devel"
    if confirm "Build and install vleapp-git now?"; then
        if [ "$YES" = "1" ]; then "$HELPER" -S --noconfirm vleapp-git;
        else "$HELPER" -S vleapp-git; fi
    else
        log "Skipped. Install later with: $HELPER -S vleapp-git"
    fi
}

install_appimage() {
    download_asset
    if [ -z "$TO" ]; then
        if [ "$SYSTEM" = "1" ]; then TO="/usr/local/bin"; else TO="$HOME/.local/bin"; fi
    fi
    mkdir -p "$TO"
    DEST="$TO/$APP"
    if [ -w "$TO" ]; then cp "$TMP/$ASSET" "$DEST";
    else as_root cp "$TMP/$ASSET" "$DEST"; fi
    chmod +x "$DEST" 2>/dev/null || as_root chmod +x "$DEST"
    log "installed: $DEST"
    case ":$PATH:" in
        *":$TO:"*) "$DEST" --version ;;
        *) log "$("$DEST" --version)"; err "$TO is not on PATH; run $DEST or add $TO to PATH" ;;
    esac
}

install_dmg() {
    need_cmd hdiutil
    download_asset
    MNT="$TMP/mnt"
    mkdir -p "$MNT"
    hdiutil attach -nobrowse -mountpoint "$MNT" "$TMP/$ASSET" >/dev/null \
        || die "could not mount $ASSET"
    trap 'hdiutil detach "$MNT" -quiet 2>/dev/null; rm -rf "$TMP"' EXIT
    if [ -z "$TO" ]; then
        if [ "$SYSTEM" = "1" ] || [ -w "/Applications" ]; then TO="/Applications"; else TO="$HOME/Applications"; fi
    fi
    mkdir -p "$TO"
    cp -a "$MNT/VLEAPP.app" "$TO/" || die "could not copy VLEAPP.app to $TO"
    hdiutil detach "$MNT" -quiet
    trap 'rm -rf "$TMP"' EXIT
    log "installed: $TO/VLEAPP.app"
    log "Command line: $TO/VLEAPP.app/Contents/MacOS/vleapp --help"
}

install_zip() {
    need_cmd unzip
    download_asset
    if [ -z "$TO" ]; then TO="$HOME/vleapp"; fi
    mkdir -p "$TO"
    unzip -o "$TMP/$ASSET" -d "$TO" || die "could not unpack $ASSET"
    log "installed: $TO/vleapp.exe"
}

case "$KIND" in
    deb) install_deb ;;
    rpm) install_rpm ;;
    aur) install_aur ;;
    appimage) install_appimage ;;
    dmg) install_dmg ;;
    zip) install_zip ;;
esac
