# VLEAPP ZIP literal prefilter: validation

This ports the same conservative ZIP search optimization as [iLEAPP PR #2801](https://github.com/abrignoni/iLEAPP/pull/2801). The production change adds **19 lines and changes two lines** in `scripts/search_files.py`, plus separate fabricated regression tests and this note. Other seekers, `peek`, parsers and dependencies are unchanged.

## Matching and regression checks

A normalized pattern without brackets must contain every literal segment between `*` and `?`. The longest segment is used as a necessary-substring check before the existing wildcard matcher. Filenames retain the existing normalized `root/` prefix. Any bracket syntax, including malformed classes, or an empty literal retains the original matcher path. No retained filename index is added.

The new helper and ZIP search method have the same AST as the tested iLEAPP implementation. Nine new tests cover 24,008 generated POSIX/Windows-normalization comparisons, real ZIP staging/order/bytes, bracket fallback, sidecars/directories, cached first-hit behavior, forced re-staging, no matches, corrupt-member continuation and reduced matcher calls.

- macOS arm64, Python 3.14.6 baseline: 1,036 tests, zero failures/errors, 15 skips.
- Candidate: **1,045 tests, zero failures/errors, 15 skips**, including the nine new tests.
- Native Windows 11 ARM64: **35 fabricated ZIP/filter/repeated-member/Windows-name tests passed on both Python 3.11.9 and 3.12.10**, with zero failures/errors/skips. Existing isolated interpreters were used without dependency updates; source copies were verified unchanged. A full Windows suite and native Windows corpus/performance run were not performed for this port.

## Corpus profile comparison

A hash-verified local ZIP input was read without modification. Source size and mtime remained unchanged afterward. Baseline/candidate used the same code apart from the search method, input, profile, `--hash`, output naming and instrumentation. The saved original method was compiled before the baseline run. All eight fresh-process outputs were retained: unmeasured baseline/candidate warm-ups, then B1, C1, C2, B2, B3, C3. Medians exclude warm-ups. VMs were running but native tests, unit suites and other benchmark jobs had finished before these serial timing runs. These are warm shared-machine results, not cold or isolated-hardware measurements.

All eight outputs matched in ordered search fingerprints, cache flags, match/staged counts, typed/ordered evidence database contents and relationships, manifest, artifact HTML tables, media, exports, staged paths/bytes and non-SHM filesystem mtimes. Database integrity checks passed. Artifact execution timestamps/output folders and process-local framework file IDs were canonicalized; evidence dates and artifact-row order were retained. Framework file-ID records/relations preserve full record identity and multiplicity. Runtime SHM filesystem mtimes and export SQLite storage sidecars are excluded, with logical database contents read normally. No parser-error markers were found. Detailed reports and raw logs are retained locally.

The vehicle source and reports are private. Case paths, payloads, identities and case-specific report statistics are not published here. Positive-row local profile validation passed; the public benchmark below uses fabricated names only. No large vehicle-workflow end-to-end speedup is claimed.

## Controlled large-name scan

This separate enumeration-only probe used the actual baseline/candidate methods with an already-staged identity mapping. No archive extraction or corpus payload is involved. There are 250,000 fabricated cache paths plus three known matches, for **250,003 names**. Each pattern has three warm repetitions with alternating version order. Every ordered result matched both the other method and an independent `fnmatchcase` result.

| Pattern | Matches | Baseline median, seconds | Candidate median, seconds |
| --- | ---: | ---: | ---: |
| `*/databases/History` | 1 | 0.063032 | 0.033792 |
| `*/databases/contacts2.db` | 1 | 0.066203 | 0.031797 |
| `*/settings/*.json` | 1 | 0.165319 | 0.033396 |
| `*/not-present/file.db` | 0 | 0.060881 | 0.031159 |
| `*[ab].db` | 0 | 0.139875 | 0.140855 |
| `*` | 250,003 | 0.070493 | 0.079203 |

For the four selective patterns, the sum of per-pattern medians fell from **0.355435 to 0.130143 seconds**, or **2.73x**. This is a controlled search-stage result, not a complete extraction/report speedup.

Bracket-fallback and match-all controls can pay overhead; their exact medians are included above rather than claiming every pattern improves. Larger member lists and selective literals benefit most. The change adds no second retained filename collection.

## Provenance and reproduction

- Baseline commit: `e0fa9ede72c0013ab9794537b10a14006aa64fcf`.
- Original search module SHA256: `ff56845855345d51a909a3c65cd68a6b21c6a13926cf6b9e6cefb50fb2edd865`.
- Candidate SHA256: `a24138355a84794d235cf42b7818c72eaac7f2c5cd9772b47a7164b9d9f7f90f`.

Run the same input/profile/options in separate baseline and candidate output directories, warm both versions, alternate order and retain all repetitions. The private corpus payload is not part of this PR. A profile uses `leapp: "vleapp"`, `format_version: 1` and a `plugins` array of artifact IDs.

```sh
python3 -B vleapp.py -t zip -i /path/to/image.zip -o /path/to/new-output \
  -m /path/to/profile.ilprofile --hash --custom_output_folder report
python3 -B -m unittest discover -s admin/test/scripts -p 'test_seeker_zip_literal_filter.py'
python3 -B -m unittest discover -s admin/test/scripts -p 'test_*.py'
```

The filter-only implementation is a small change with workload-dependent speed benefits. Validation supports review without extending claims to other inputs, untested runtimes or unrelated parser behavior.
