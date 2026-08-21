---
name: directional-test-registry
description: Master registry of canonical regions, movement directions, positions, biases, muscles, isolation logic, compensation watch, and retest rules.
version: 1.0.0
tags: [physicaltherapy, registry, lookup, directional-test]
---

# Directional Test Registry Skill

## Purpose
Single source of truth for all test combinations. Replaces free-text with validated dropdowns from your Dynamic Lookup Panel.

## Registry Schema

```json
{
  "region": "Lumbar",
  "directions": [
    {
      "direction": "Extension",
      "positions": ["Standing", "Prone", "Sitting", "Quadruped"],
      "biases": ["End-range overpressure", "Mid-range", "Loaded extension", "Sustained 5sec"],
      "candidate_muscles": ["Multifidus", "Erector Spinae", "Glute Max"],
      "isolation_logic": "Prone knee flex 90deg reduces hamstring contribution -> isolates glute vs erector",
      "compensation_watch": ["Lumbar shift left", "Hip extension substitution", "Breath holding"],
      "retest_rule": "Retest standing extension pain/function after 2min - needs >50% change to confirm driver",
      "irritability_gate": "High irritability -> test mid-range only"
    }
  ]
}
```

## Supported Regions (from your console)

- Cervical (C0-T1)
- Thoracic (T1-T12)
- Lumbar (T12-S1)
- Sacroiliac / Pelvis
- Shoulder complex (GH, AC, SC, Scapula)
- Elbow / Forearm
- Wrist / Hand
- Hip / Pelvis
- Knee
- Ankle / Foot

## Instructions for Agent

1.  When `CanonicalRegion` is selected, lookup file `data/directional_test_registry.json`
2.  Return:
    - `Available directions for selected region`
    - `Available positions for selected region + direction`
    - `Available biases / range gates`
    - `Candidate muscles`
    - `Isolation logic`
    - `Compensation watch`
    - `Retest rule`
3.  If combination not in registry, suggest closest match + prompt "Add new entry?"

## How to Extend

Edit `data/directional_test_registry.json`:

```json
{
  "region": "Shoulder",
  "directions": [
    {
      "direction": "Flexion",
      "positions": ["Supine", "Standing", "Sidelying"],
      "biases": ["With scapular assistance", "Without", "External rotation bias"],
      "candidate_muscles": ["Anterior Deltoid", "Upper Trap", "Serratus"],
      "isolation_logic": "Supine eliminates compensation",
      "compensation_watch": ["Scapular elevation", "Lumbar extension"],
      "retest_rule": "Improve overhead reach >30deg = positive driver"
    }
  ]
}
```

## Usage in Console

```
> Select region: Lumbar
Skill returns: Directions [Flexion, Extension, Rotation, Sidebend, Combined]
> Select direction: Extension
Skill returns: Positions [Standing, Prone, Sitting, Quadruped] + Biases + Muscles + Watch
```

This ensures repeatability and data for AI reasoning.

## Data File Location
`./data/directional_test_registry.json` - contains 11 regions, 80+ test combinations (starter).
