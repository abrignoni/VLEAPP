# Raw image input, and what it changed in core

For maintainers, and for whoever ports this to the other LEAPP cores.

`-t raw` takes a raw disk image and reads its QNX6 and ext2/3/4 volumes without
mounting it and without administrator rights. Vehicle head units need it: the Ford
Sync units are QNX6, the BMW MGU is ext4, and no filesystem type The Sleuth Kit
supports can walk QNX6 at all, so those images were previously unreadable here.

## The whole core surface

Two files. Nothing existing was modified in either.

**`vleapp.py`**, three edits totalling 8 lines:

    choices=['fs', 'tar', 'zip', 'gz', 'file', 'raw']   # one enum entry
    ...one sentence added to the -t help text...
    elif extracttype == 'raw':                          # one dispatch branch
        seeker = FileSeekerRaw(input_path, out_params.data_folder)

**`scripts/search_files.py`**, one new class, 66 added lines, 0 changed:

    class FileSeekerRaw(FileSeekerZip):

Everything else in both pull requests is outside core: `scripts/vendor/` holds a
verbatim copy of the reader, and `admin/scripts/check_vendored.py`, the
`lint_changed.py` exclusion and the CI step are tooling.

## Why it subclasses rather than walks

The vendored reader exposes usable walkers (`Qnx6Walker`, `ExtWalker`, both with
`listdir` / `entry` / `read_file`), so a seeker that walked the image lazily and
staged only matched files was the obvious design and is not what this does.

Deciding *which* partitions hold *which* filesystem, and which superblock
generation is current, is not behind a callable seam in that tool; it is threaded
through its command line flow. Reimplementing it here would copy non-trivial logic
that then drifts from the vendored file, which is the exact failure the vendoring
hash guard exists to catch.

So `FileSeekerRaw` runs the vendored tool to produce a zip, then calls
`FileSeekerZip.__init__` on it. Every staging, matching, disambiguation and
timestamp decision stays on the path the zip seeker already runs on every zip
input. The cost is an up-front extraction instead of lazy reads.

**The seam to improve later** is exactly this: if the reader grows a callable
"enumerate the volumes in this image" entry point, `FileSeekerRaw` can stop
shelling out and stage lazily, and the class is the only thing that changes.

## Porting it to another core

The core part is small and generic. `FileSeekerRaw` references nothing
VLEAPP-specific: it uses `logfunc`, `FileSeekerZip` and the vendored path, all of
which exist or have equivalents in every core. Copying the class and the three
`vleapp.py` edits is the whole job.

What is worth deciding once, rather than five times:

- **Where the vendored reader lives.** Here it is `scripts/vendor/`, resolved
  relative to `search_files.py`. If the cores consolidate, this should be one
  shared location, not five copies of a copy.
- **Whether the staged zip is kept.** It goes to a temp directory and `cleanup()`
  removes it. For a large volume the extraction is the slow part of the run, so
  keeping it would make re-runs cheap. Deliberately not done yet, because the
  report folder is shared and silently growing it by gigabytes is worse.
- **Whether raw should be auto-detected** rather than selected with `-t`. The
  reader can already tell whether an image holds anything it can read, so
  detection is possible; it is a separate change and a shared one.

## What was measured

The same image was run three ways: through the vendor's own extracted file set,
through a zip made by hand with the vendored reader, and through `-t raw`. All six
artifacts common to the branches returned identical row counts, and two of the
underlying stores were byte-identical by SHA-256 between the first two routes.

`-t raw` found four QNX6 volumes on the test image, one more than the vendor's
export carried extracted files for.
