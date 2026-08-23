---
name: neuro-screening
description: Neurological screening for dermatomes, myotomes, reflexes, and UMN signs. Part of Driver Checks.
version: 1.0.0
tags: [neuro, screening, myotome, dermatome]
---

# Neuro Screening Skill

## Purpose
Quick neuro screen to clear radiculopathy / myelopathy before treatment.

Status: `not_tested | cleared | positive_deficit_documented`

## Tests by Region

### Cervical (C4-T1)
- Dermatomes: lateral shoulder C4, lateral forearm C5-6, middle finger C7, medial forearm C8-T1
- Myotomes: deltoid C5, biceps C5-6, triceps C7, grip C8, finger abduction T1
- Reflexes: biceps C5-6, triceps C7, brachioradialis C6
- UMN: Hoffmann, clonus, hyperreflexia

### Lumbar (L1-S2)
- Dermatomes: lateral thigh L2-3, medial calf L4, dorsum foot L5, lateral foot S1
- Myotomes: hip flex L2-3, knee ext L3-4, ankle DF L4-5, great toe ext L5, plantarflex S1
- Reflexes: patellar L3-4, Achilles S1
- SLR, slump, femoral nerve

### Thoracic
- Myotomes: quick trunk
- Reflexes: abdominal

## Instructions

Ask therapist:
- "Dermatome check - any numbness/tingling? Where?"
- "Myotome strength - test and record 0-5"
- "Reflexes - normal/diminished/brisk?"
- "Any UMN signs?"

If deficit found:
- Set `NeuroScreen = positive_deficit_documented`
- Document but may still proceed (depending on irritability and red flags)
- Include in AI Reasoning: "Consider L5 radiculopathy overlay"

## Output

```json
{
  "NeuroScreen": "cleared",
  "Findings": {
    "Sensory": "intact",
    "Motor": "5/5 all myotomes",
    "Reflexes": "2+ symmetric",
    "UMN": "negative"
  },
  "Next": "proceed_to_adjacent_region_check"
}
```
