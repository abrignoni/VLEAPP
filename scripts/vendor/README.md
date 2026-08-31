# Vendored third-party readers

Code copied in from another repository, unmodified, so VLEAPP can read image
formats without asking the examiner to install anything.

## qnxprobe.py

| | |
| --- | --- |
| upstream | https://github.com/abrignoni/qnxprobe |
| licence | MIT, kept beside it as LICENSE-qnxprobe |

The vendored version, upstream commit and sha256 are recorded in
`vendored.json` in this directory, which `admin/scripts/check_vendored.py`
enforces in CI. They are deliberately not repeated here: this table held them
once and went stale on the first re-vendor, because prose is checked by nobody
and the manifest is checked on every push.


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
