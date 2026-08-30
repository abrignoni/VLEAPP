# Vendored third-party readers

Code copied in from another repository, unmodified, so VLEAPP can read image
formats without asking the examiner to install anything.

## qnxprobe.py

| | |
| --- | --- |
| upstream | https://github.com/abrignoni/qnxprobe |
| commit | `3c3259a3f89a953af156eddbd0727313ccf8281f` |
| dated | 2026-08-27T02:27:13-05:00 |
| version | qnxprobe 1.3 |
| sha256 | 9f163a18db2c7b2f66cf6be09a8c6a260ead4d993f0311c56ee55945dfe0863c |
| licence | MIT, kept beside it as LICENSE-qnxprobe |

Reads QNX6 and ext2/3/4 volumes out of a raw image without mounting and with no
administrator rights. Python 3 standard library only, so vendoring it adds no
dependency to requirements.txt.

**It is copied verbatim. Do not edit it here.** Fix upstream, then re-vendor, or
the next sync silently reverts the change.

### Re-vendoring

    cp ../qnxprobe/qnxprobe.py scripts/vendor/qnxprobe.py
    python3 admin/scripts/check_vendored.py --update

### Checking for drift

`admin/scripts/check_vendored.py` compares this copy against the sha256 recorded
above and fails when they differ. It runs in CI, so a local edit or a stale copy
after an upstream release is caught rather than noticed later. Pass
`--upstream <path>` to also diff against a checkout of the upstream repo.
