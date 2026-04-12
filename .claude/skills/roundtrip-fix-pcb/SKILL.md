---
name: roundtrip-fix-pcb
description: Autonomously raise kiutils .kicad_pcb roundtrip coverage to 100%. Runs a measure-identify-fix-verify cycle, targeting the highest-impact LOST token each iteration until all files pass or only unfixable issues remain.
---

# Roundtrip Fix (PCB)

## Behavior

This skill runs an autonomous loop:

```
measure -> analyze -> fix -> verify -> next
```

Continue until OVERALL COVERAGE is 100% for all files, or only unfixable issues remain.

## Environment

- kiutils source: `src/kiutils/`
- Test files: `.kicad_pcb` files placed under `tmp/`
- Validation script: `tmp/roundtrip_pcb.py`

## Cycle

### Step 1: Measure

Run the roundtrip test on all files:

```bash
for f in tmp/**/*.kicad_pcb; do
  python3 tmp/roundtrip_pcb.py "$f" 2>&1
done
```

Record for each file:
- OVERALL COVERAGE %
- LOST tokens (token path and count)
- CHANGED tokens

**If 100% across all files, stop and report.**

### Step 2: Pick the next fix target

Prioritize LOST/CHANGED tokens:

1. **CRITICAL**: Value inversion bugs (e.g. `true` written as `yes` or vice versa)
2. **HIGH / wide scope**: LOST tokens with the most occurrences (files x count)
3. **HIGH / simple**: LOST tokens fixable by adding a single field
4. **MEDIUM**: Format differences

Focus on one token problem per cycle. Do not fix multiple at once.

### Step 3: Fix kiutils source

Read the target source file and apply the fix.

Typical fix patterns:

#### Pattern A: Add a missing field (LOST -> OK)

Add an Optional field to the dataclass:

```python
# 1. Field definition
generatorVersion: Optional[str] = None

# 2. Parse in from_sexpr()
if item[0] == 'generator_version':
    object.generatorVersion = item[1]

# 3. Output in to_sexpr() (skip when None)
if self.generatorVersion is not None:
    expression += f'  (generator_version "{self.generatorVersion}")\n'
```

#### Pattern B: Fix value parsing (CHANGED -> OK)

```python
# Before (bug): PlotSettings uses true/false for some, yes/no for others
if item[0] == 'disableapertmacros':
    object.disableApertMacros = True if item[1] == 'true' else False

# After (fix): normalize using a helper
_b = lambda v: v in ('true', 'yes')
if item[0] == 'disableapertmacros':
    object.disableApertMacros = _b(item[1])
```

#### Pattern C: Fix output format

When `to_sexpr()` produces a different format than the original:

```python
# Before: Python bool lowercase
expression += f'  (viasonmask {str(self.viasOnMask).lower()})\n'

# After: KiCad yes/no format
_yn = lambda v: 'yes' if v else 'no'
expression += f'  (viasonmask {_yn(self.viasOnMask)})\n'
```

### Step 4: Verify

Run the test on the most affected file:

```bash
python3 tmp/roundtrip_pcb.py tmp/some-file.kicad_pcb
```

Check:
- The targeted LOST/CHANGED is gone
- No new LOST/CHANGED appeared (regression)
- OVERALL COVERAGE increased

**If regression occurs**: revert the fix and retry.

### Step 5: Report and loop

Report progress in one line:
```
done: Board.generatorVersion added — cupwarmer-hw.kicad_pcb: 53.5% -> 58.2%
```

Return to Step 1.

## Rules

1. **Do not break the public API**: Never change existing field types. New fields must be `Optional[T] = None` for backward compatibility.
2. **One token per cycle**: Keep fixes small. Fixing multiple tokens at once makes regressions hard to trace.
3. **Always fix from_sexpr and to_sexpr together**: Parsing without output (or vice versa) will not improve coverage.
4. **Match the original token order in to_sexpr**: KiCad S-expressions have an expected token order.
5. **Never edit the test .kicad_pcb files**: Test data is immutable.

## Source file map

kiutils source tree (`src/kiutils/`):

| File | Board elements |
|---|---|
| `board.py` | Root `kicad_pcb` (version, generator, generator_version, uuid, paper, general, layers, setup, nets, properties, footprints, graphicItems, traceItems, zones, groups) |
| `items/brditems.py` | GeneralSettings, LayerToken, Stackup, StackupLayer, StackupSubLayer, PlotSettings, SetupData, Segment, Via, Arc, Target |
| `items/gritems.py` | GrText, GrTextBox, GrLine, GrRect, GrCircle, GrArc, GrPoly, GrCurve |
| `items/zones.py` | Zone, ZoneFillSettings, ZoneKeepout |
| `items/dimensions.py` | Dimension |
| `footprint.py` | Footprint, FpText, FpTextBox, FpLine, FpRect, FpCircle, FpArc, FpPoly, FpCurve, Pad, Model |
| `items/common.py` | Property, Effects, Stroke, Font, Net, PageSettings, TitleBlock, Image, Group |

## Exit conditions

- All files at OVERALL COVERAGE 100% -> success. Report final results.
- LOST tokens remain but are unfixable by design -> explain to the user and ask for direction.
- 5 consecutive cycles with no coverage improvement -> report status and discuss next steps.
