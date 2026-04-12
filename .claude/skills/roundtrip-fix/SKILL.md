---
name: roundtrip-fix
description: Autonomously raise kiutils .kicad_sch roundtrip coverage to 100%. Runs a measure-identify-fix-verify cycle, targeting the highest-impact LOST token each iteration until all files pass or only unfixable issues remain.
---

# Roundtrip Fix

## Behavior

This skill runs an autonomous loop:

```
measure -> analyze -> fix -> verify -> next
```

Continue until OVERALL COVERAGE is 100% for all files, or only unfixable issues remain.

## Environment

- kiutils source: `src/kiutils/`
- Test files: `.kicad_sch` files placed under `tmp/`
- Validation script: `tmp/roundtrip_sch.py`

## Cycle

### Step 1: Measure

Run the roundtrip test on all files:

```bash
for f in tmp/**/*.kicad_sch; do
  python3 tmp/roundtrip_sch.py "$f" 2>&1
done
```

Record for each file:
- OVERALL COVERAGE %
- LOST tokens (token path and count)
- CHANGED tokens

**If 100% across all files, stop and report.**

### Step 2: Pick the next fix target

Prioritize LOST/CHANGED tokens:

1. **CRITICAL**: Value inversion bugs (e.g. `show_name no` becomes `show_name`)
2. **HIGH / wide scope**: LOST tokens with the most occurrences (files x count)
3. **HIGH / simple**: LOST tokens fixable by adding a single field
4. **MEDIUM**: Format differences (`hide yes` vs bare `hide`)

Focus on one token problem per cycle. Do not fix multiple at once.

### Step 3: Fix kiutils source

Read the target source file and apply the fix.

Typical fix patterns:

#### Pattern A: Add a missing field (LOST -> OK)

Add an Optional field to the dataclass:

```python
# 1. Field definition
excludeFromSim: Optional[bool] = None

# 2. Parse in from_sexpr()
if item[0] == 'exclude_from_sim':
    object.excludeFromSim = True if item[1] == 'yes' else False

# 3. Output in to_sexpr() (skip when None)
if self.excludeFromSim is not None:
    efs = 'yes' if self.excludeFromSim else 'no'
    expression += f'{indents}  (exclude_from_sim {efs})\n'
```

#### Pattern B: Fix value parsing (CHANGED -> OK)

```python
# Before (bug):
if item[0] == 'show_name': object.showName = True

# After (fix):
if item[0] == 'show_name':
    if len(item) > 1 and item[1] == 'no':
        object.showName = False
    else:
        object.showName = True
```

#### Pattern C: Fix output format

When `to_sexpr()` produces a different format than the original:

```python
# Before: bare token
expression += f'{indents}  hide\n'

# After: KiCad v8+ list format
expression += f'{indents}  (hide yes)\n'
```

### Step 4: Verify

Run the test on the most affected file:

```bash
python3 tmp/roundtrip_sch.py tmp/some-file.kicad_sch
```

Check:
- The targeted LOST/CHANGED is gone
- No new LOST/CHANGED appeared (regression)
- OVERALL COVERAGE increased

**If regression occurs**: revert the fix and retry.

### Step 5: Report and loop

Report progress in one line:
```
done: Schematic.generator_version added — cupwarmer-hw.kicad_sch: 53.5% -> 58.2%
```

Return to Step 1.

## Rules

1. **Do not break the public API**: Never change existing field types. New fields must be `Optional[T] = None` for backward compatibility.
2. **One token per cycle**: Keep fixes small. Fixing multiple tokens at once makes regressions hard to trace.
3. **Always fix from_sexpr and to_sexpr together**: Parsing without output (or vice versa) will not improve coverage.
4. **Match the original token order in to_sexpr**: KiCad S-expressions have an expected token order.
5. **Never edit the test .kicad_sch files**: Test data is immutable.

## Source file map

kiutils source tree (`src/kiutils/`):

| File | Schematic elements |
|---|---|
| `schematic.py` | Root `kicad_sch` (version, generator, generator_version, embedded_fonts, uuid, paper, lib_symbols, sheet_instances, symbol_instances) |
| `items/schitems.py` | SchematicSymbol, HierarchicalSheet, HierarchicalPin, Text, TextBox, Junction, NoConnect, BusEntry, Connection (wire/bus), LocalLabel, GlobalLabel, HierarchicalLabel |
| `items/common.py` | Property, Effects, Stroke, Font, Position |
| `symbol.py` | Symbol (lib_symbols definitions), SymbolLib |

## Exit conditions

- All files at OVERALL COVERAGE 100% -> success. Report final results.
- LOST tokens remain but are unfixable by design -> explain to the user and ask for direction.
- 5 consecutive cycles with no coverage improvement -> report status and discuss next steps.
