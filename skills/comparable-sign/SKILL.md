---
name: comparable-sign
description: Identifies, records, and tracks the comparable sign (the most meaningful movement/test that reproduces patient's complaint).
version: 1.0.0
tags: [comparable-sign, assessment, outcome]
---

# Comparable Sign Skill

## Purpose
The comparable sign is the cornerstone of LFS reasoning. It's the test that is most comparable to the patient's functional complaint and will be used to retest after each intervention.

### Definition
- The movement/position that reproduces or is closest to chief complaint
- Must be measurable (pain 0-10, ROM deg, reps, seconds)
- Repeatable

## Workflow

1. **Select from Registry** first: CanonicalRegion + Direction + Position + Bias
2. **Record Baseline**:
   - FindingType: [weak, painful, limited, unstable, apprehensive]
   - PainBehavior
   - Angle/load
   - Measurable score

3. **Set as Comparable**
   - Set `ComparableSignSelected = true`
   - Store baseline for retest

4. **Retest**
   - After driver correction, retest same sign
   - Calculate % change: `(post - pre) / pre * 100` or pain delta
   - If >50% improvement -> driver confirmed

## Instructions for Agent

When user describes complaint e.g. "pain when bending to lift":

- Suggest comparable signs:
  - "Lumbar Flexion Standing with 5kg load"
  - "Hip Flexion + Lumbar Flexion combined"
  - "Prone hip extension to test glute vs lumbar driver"

- Prompt:
  "What is baseline? Pain 0-10? ROM? Weakness?"

- Save to `RetestComparator` field.

## Example

Input: "Patient: LBP when sitting >20min, worse flexing"
Comparable: "Lumbar Flexion Sitting end-range - Pain 7/10 at 80% flexion, eases with lumbar support"

After intervention (e.g. thoracic extension mobilization + multifidus cue):
Retest: "Same sitting flexion - Pain 3/10 at 100% flexion = 57% improvement"

## Output JSON

```json
{
  "ComparableSign": {
    "Region": "Lumbar",
    "Joint": "L3-L4",
    "Direction": "Flexion",
    "Position": "Sitting",
    "Bias": "End-range",
    "Baseline": "Pain 7/10 at 80% flex",
    "FindingType": "painful",
    "Selected": true
  },
  "RetestComparator": {
    "PostIntervention": "Pain 3/10 at 100%",
    "ChangePercent": 57,
    "DriverConfirmed": true
  }
}
```
