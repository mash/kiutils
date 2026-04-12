---
name: roundtrip-measure-pcb
description: Verify kiutils roundtrip fidelity by reading and writing .kicad_pcb files, detecting token-level diffs, and reporting numeric coverage. Use to measure baseline, identify regressions, and track progress toward 100% coverage.
---

# Roundtrip Measure (PCB)

## Purpose

Verify that reading a KiCad PCB file with kiutils and writing it back produces no meaningful token loss. Report coverage as a percentage and list every LOST or CHANGED token.

## Prerequisites

- kiutils source: `src/kiutils/`
- Test files: `.kicad_pcb` files placed under `tmp/`
- Validation script: `tmp/roundtrip_pcb.py`

## Workflow

### 1. Measure baseline

Run the roundtrip test against all .kicad_pcb files:

```bash
for f in tmp/**/*.kicad_pcb; do
  echo "=== $f ==="
  python3 tmp/roundtrip_pcb.py "$f" 2>&1 | grep -E '(OVERALL|LOST|CHANGED|SUMMARY|Top-level|UUID|Token)'
  echo
done
```

### 2. Identify problems

Extract LOST / CHANGED from the script output. Problem categories:

| Category | Example | Severity |
|---|---|---|
| LOST (token missing) | `generator_version`, `embedded_fonts`, `tenting` | HIGH — field must be added |
| CHANGED (value inverted) | `true` becomes `yes` | CRITICAL — meaning changes |
| CHANGED (format diff) | whitespace, numeric precision | LOW — meaning preserved |

### 3. Fix kiutils

Source files for .kicad_pcb support:
- `src/kiutils/board.py` — Board class (version, generator, general, layers, setup, nets, properties)
- `src/kiutils/items/brditems.py` — GeneralSettings, LayerToken, Stackup, PlotSettings, SetupData, Segment, Via, Arc, Target
- `src/kiutils/items/gritems.py` — GrText, GrTextBox, GrLine, GrRect, GrCircle, GrArc, GrPoly, GrCurve
- `src/kiutils/items/zones.py` — Zone, ZoneFillSettings, ZoneKeepout
- `src/kiutils/items/dimensions.py` — Dimension
- `src/kiutils/footprint.py` — Footprint, FpText, Pad, etc.
- `src/kiutils/items/common.py` — Property, Effects, Font, Stroke, Net, PageSettings, TitleBlock, Image, Group

Fix patterns:

**Add a missing field** (LOST -> OK):
1. Add an `Optional[T] = None` field to the dataclass
2. Add parsing in `from_sexpr()`
3. Add output in `to_sexpr()` (skip when None)

**Fix value interpretation** (CHANGED -> OK):
1. Fix the condition in `from_sexpr()` (e.g. correct `yes`/`no` vs `true`/`false` parsing)
2. Fix the output format in `to_sexpr()`

### 4. Re-measure

```bash
python3 tmp/roundtrip_pcb.py tmp/some-file.kicad_pcb
```

### 5. Repeat

Iterate steps 2-4 until OVERALL COVERAGE reaches 100%.

## Reading the script output

```
=== Top-level tokens ===
  generator_version   LOST (was: 10.0)    <- field missing from kiutils
  general             CHANGED             <- general settings differ
  version             OK                  <- preserved correctly

=== UUID-bearing elements ===
  footprint  total=12  ok=8  changed=4  lost=0  (66.7%)
    uuid=...: child 'attr' LOST              <- this token is dropped
    uuid=...: child 'property' CHANGED       <- property content changed

=== Token inventory ===
  LOST  kicad_pcb > footprint > attr  orig=12  <- 12 occurrences all dropped

=== SUMMARY ===
  OVERALL COVERAGE: 53.5%                     <- target is 100%
```

## Test data

Place `.kicad_pcb` files under `tmp/` (not committed to the repo). The measurement commands search for all `.kicad_pcb` files under `tmp/` recursively. Use real-world KiCad project files across multiple KiCad versions (v8, v9, v10) for comprehensive coverage.
