---
name: driver-checks
description: Executes adjacent region check, compensation observation, dependency result, irritability classification, and retest logic.
version: 1.0.0
tags: [driver, checks, lfs, compensation]
---

# Driver Checks Skill

## Purpose
Validates whether the identified region is truly the driver (source) or just victim.

## Checks (from sheet - Status column)

### 1. Adjacent Region Check (not_tested | cleared | positive_driver_elsewhere)
Ask: If lumbar extension is limited/painful, check:
- Hip extension (is it the driver?)
- Thoracic extension
- SIJ

Rule: If correcting adjacent region improves comparable sign > adjacent correction of primary, adjacent is driver.

### 2. Compensation Observed (free text)
Use registry's `compensation_watch` list.

Examples:
- Lumbar: hip hiking, lumbar shift, breath hold, rib flare
- Shoulder: scapular elevation, trunk lean, elbow flex
- Hip: knee valgus, pelvic drop

Document: What, when (at what % ROM/load), consistent?

### 3. Dependency Result (not_tested | independent | dependent_on_X)
Test: Does performance of comparable sign change when you block/change adjacent joint?

- Example: Standing lumbar extension improves when you cue glute max activation -> dependent on glute driver? Or hip?
- Example: Shoulder flexion improves with thoracic extension mobilization -> dependent on thoracic driver.

### 4. Irritability Classification
- **low**: Pain eases quickly, >50% ROM before pain, no night pain, AROM > PROM limitation minimal
  -> Can test end-range, overpressure, more vigorous manual therapy Grades III-IV
- **medium**: Pain at mid-range, lingers < few hours after aggravation
  -> Test mid-range, gentle overpressure, Grades I-II, avoid sustained
- **high**: Pain early, lingers > hours, night pain, minimal tolerance
  -> Test only mid-range, no overpressure, gentle Grades I-II, assessment only

Set `Irritability` field, affects all other skills.

### 5. Retest Comparator Tracking
- Save baseline before intervention
- Retest immediately after
- Record % change and pain delta

## Instructions for Agent

After Comparable Sign selected:

1. Lookup registry's `compensation_watch` and prompt therapist to observe.
2. Prompt for adjacent region check: "Have you checked [adjacent region]? What happens if you correct it first?"
3. Determine dependency.
4. Classify irritability based on pain behavior and previous response.
5. Output summary:

```json
{
  "AdjacentRegionCheck": "Hip extension cleared - not driver",
  "CompensationObserved": "Lumbar shift left at 80% standing extension",
  "DependencyResult": "Dependent on thoracic T6-8 extension limitation",
  "Irritability": "medium",
  "RetestRule": "Retest after thoracic PA grade II + scapular setting"
}
```

If `Irritability=high`, enforce gentle handling in downstream skills.
