# VLEAPP

Vehicle logs, events and properties parser. Parses infotainment and telematics data pulled
from vehicle systems, not from a phone.

## What that changes

- **The input is a vehicle extraction**, typically from a tool that dumps an infotainment
  head unit or a telematics module. Layout is manufacturer-specific and there is no common
  filesystem convention across makes.
- **A vehicle carries data about more than one person.** Paired phones, contacts synced
  from those phones, and call logs may belong to passengers rather than the driver. Do not
  write descriptions that attribute an event to "the driver" or "the user". Say what the
  record contains and let the examiner attribute it. `.claude/rules/leapp-claims.md`
  applies with particular force here.

## Before changing an artifact

This repo does not carry the module-authoring docs. **iLEAPP's
[`admin/docs/artifact_info_block.md`](https://github.com/abrignoni/iLEAPP/blob/main/admin/docs/artifact_info_block.md)
is the reference for the `__artifacts_v2__` block** and applies here unchanged: same
loader, same seekers, same glob semantics.

## Repo-specific things worth knowing

- This is the smallest extractor. Much of the shared infrastructure arrives here last, so
  when porting a change from another core, expect the surrounding helper to be older than
  the one you copied from and read before pasting.
- `scripts/report_icons.py` is local to this repo.
- No protobuf dependency, and it should stay that way.

## Rules

`.claude/rules/` holds the detail. Files prefixed `leapp-` are shared across all five
extractors and `lava-` across all six repos. **Edit those at their canonical source, not
here**, or the next sync overwrites you.
