---
name: roundtrip-measure
description: Verify kiutils roundtrip fidelity by reading and writing .kicad_sch files, detecting token-level diffs, and reporting numeric coverage. Use to measure baseline, identify regressions, and track progress toward 100% coverage.
---

# Roundtrip Measure

## Purpose

Verify that reading a KiCad file with kiutils and writing it back produces no meaningful token loss. Report coverage as a percentage and list every LOST or CHANGED token.

## Prerequisites

- kiutils source: `src/kiutils/`
- Test files: `.kicad_sch` files placed under `tmp/`
- Validation script: `tmp/roundtrip_sch.py`

## Workflow

### 1. Measure baseline

Run the roundtrip test against all .kicad_sch files:

```bash
for f in tmp/**/*.kicad_sch; do
  echo "=== $f ==="
  python3 tmp/roundtrip_sch.py "$f" 2>&1 | grep -E '(OVERALL|LOST|CHANGED|SUMMARY|Top-level|UUID|Token)'
  echo
done
```

### 2. Identify problems

Extract LOST / CHANGED from the script output. Problem categories:

| Category | Example | Severity |
|---|---|---|
| LOST (token missing) | `generator_version`, `embedded_fonts`, `exclude_from_sim` | HIGH — field must be added |
| CHANGED (value inverted) | `show_name no` becomes `show_name` | CRITICAL — meaning changes |
| CHANGED (format diff) | whitespace, numeric precision | LOW — meaning preserved |

### 3. Fix kiutils

Source files for .kicad_sch support:
- `src/kiutils/schematic.py` — Schematic class
- `src/kiutils/items/schitems.py` — SchematicSymbol, HierarchicalSheet, Text, etc.
- `src/kiutils/items/common.py` — Property, Effects, Font, etc.
- `src/kiutils/symbol.py` — Symbol (inside lib_symbols)

Fix patterns:

**Add a missing field** (LOST -> OK):
1. Add an `Optional[T] = None` field to the dataclass
2. Add parsing in `from_sexpr()`
3. Add output in `to_sexpr()` (skip when None)

**Fix value interpretation** (CHANGED -> OK):
1. Fix the condition in `from_sexpr()` (e.g. correct `yes`/`no` parsing)
2. Fix the output format in `to_sexpr()`

### 4. Re-measure

```bash
python3 tmp/roundtrip_sch.py tmp/some-file.kicad_sch
```

### 5. Repeat

Iterate steps 2-4 until OVERALL COVERAGE reaches 100%.

## Reading the script output

```
=== Top-level tokens ===
  generator_version   LOST (was: 10.0)    <- field missing from kiutils
  embedded_fonts      LOST (was: no)      <- field missing from kiutils
  version             OK                  <- preserved correctly

=== UUID-bearing elements ===
  sheet    total=3  ok=0  changed=3  lost=0  (0.0%)  <- all 3 sheets differ
    uuid=...: child 'exclude_from_sim' LOST           <- this token is dropped
    uuid=...: child 'property' CHANGED                <- property content changed

=== Token inventory ===
  LOST  kicad_sch > sheet > exclude_from_sim  orig=3  <- 3 occurrences all dropped

=== SUMMARY ===
  OVERALL COVERAGE: 53.5%                             <- target is 100%
```

## Test data

Place `.kicad_sch` files under `tmp/` (not committed to the repo). The measurement commands search for all `.kicad_sch` files under `tmp/` recursively. Use real-world KiCad project files across multiple KiCad versions (v8, v9, v10) for comprehensive coverage.
