# VLEAPP on the AUR

`vleapp-git/` holds the AUR package. It follows the `main` branch, so it is
always the latest version: there is nothing to bump when VLEAPP releases.

## Install

With an AUR helper:

```
yay -S vleapp-git
```

or without one:

```
git clone https://aur.archlinux.org/vleapp-git.git
cd vleapp-git
makepkg -si
```

Staying current is the helper's `--devel` flag, which rebuilds `-git`
packages when upstream moves:

```
yay -Syu --devel
```

The package builds the PyInstaller bundle (`python packaging/build.py exe`)
and installs it to `/opt/vleapp`, with `/usr/bin/vleapp` on `PATH`, a
`.desktop` entry and the icon. No Python setup is needed to run it. `tk` is
a build dependency only: the bundle carries its own Tk.

## Publishing and updating

The AUR package lives in its own repository, `aur.archlinux.org/vleapp-git`,
separate from this one. What is kept here is the source of truth for its
content; publishing copies these files over:

```
git clone ssh://aur@aur.archlinux.org/vleapp-git.git
cp packaging/aur/vleapp-git/PKGBUILD packaging/aur/vleapp-git/.SRCINFO vleapp-git/
cd vleapp-git
makepkg --printsrcinfo > .SRCINFO   # the committed file must match this output
git add PKGBUILD .SRCINFO
git commit -m "Upstream <describe what changed>"
git push
```

Rules that keep the package accepted:

- Never edit `.SRCINFO` by hand. It is the output of
  `makepkg --printsrcinfo` in the same directory, and `.github/workflows/linux-packages.yml`
  fails the PR when the two disagree.
- The committed `pkgver` is only a placeholder. `pkgver()` recomputes it
  from `scripts/version_info.py` plus the commit count and hash at build
  time, so a user building today gets today's version whatever the file says.
- `namcap PKGBUILD` should stay quiet before pushing.
