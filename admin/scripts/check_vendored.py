#!/usr/bin/env python3
"""Confirm the vendored third-party files still match what was vendored.

Vendored code is a copy, so it drifts in two directions and both are silent. A
local edit looks like a fix until the next re-vendor reverts it, and an upstream
release leaves this copy quietly old. Neither shows up in a diff of this repo.

The recorded hash lives in scripts/vendor/vendored.json, written when the file was
vendored. This compares the file on disk against that record, and can additionally
diff against a checkout of the upstream repository.

    python3 admin/scripts/check_vendored.py                     # CI: has the copy changed?
    python3 admin/scripts/check_vendored.py --upstream ../qnxprobe
    python3 admin/scripts/check_vendored.py --update            # after a deliberate re-vendor
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MANIFEST = os.path.join(REPO, 'scripts', 'vendor', 'vendored.json')


def sha256(path):
    with open(path, 'rb') as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--upstream', metavar='DIR',
                        help='a checkout of the upstream repo, to compare against as well')
    parser.add_argument('--update', action='store_true',
                        help='rewrite the recorded hashes from the files on disk, '
                             'for use only after a deliberate re-vendor')
    args = parser.parse_args()

    with open(MANIFEST, encoding='utf-8') as handle:
        manifest = json.load(handle)

    problems = []
    for entry in manifest['vendored']:
        path = os.path.join(REPO, entry['path'])
        if not os.path.isfile(path):
            problems.append(f"{entry['path']}: recorded in the manifest but not on disk")
            continue
        actual = sha256(path)
        if args.update:
            entry['sha256'] = actual
            print(f"  recorded {entry['path']} at {actual}")
            continue
        if actual != entry['sha256']:
            problems.append(
                f"{entry['path']}: does not match what was vendored\n"
                f"    recorded {entry['sha256']}\n"
                f"    on disk  {actual}\n"
                f"    Either it was edited here, which is not the place to fix it, or it was\n"
                f"    re-vendored without running --update.")
            continue
        print(f"  {entry['path']}  matches {entry['name']} {entry['version']} "
              f"({entry['commit'][:7]})")

        if args.upstream:
            up = os.path.join(args.upstream, entry['upstream_file'])
            if not os.path.isfile(up):
                problems.append(f"{entry['path']}: --upstream given but {up} is not there")
            elif sha256(up) != actual:
                problems.append(
                    f"{entry['path']}: upstream has moved on\n"
                    f"    vendored {actual}\n"
                    f"    upstream {sha256(up)}\n"
                    f"    Re-vendor if the upstream change is wanted here.")
            else:
                print(f"    and matches the upstream checkout at {args.upstream}")

    if args.update:
        with open(MANIFEST, 'w', encoding='utf-8') as handle:
            json.dump(manifest, handle, indent=2)
            handle.write('\n')
        print('manifest updated')
        return 0

    if problems:
        print('\nVendored files have drifted:\n')
        for p in problems:
            print(f'  {p}\n')
        return 1

    print(f"\n{len(manifest['vendored'])} vendored file(s), all matching what was recorded.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
