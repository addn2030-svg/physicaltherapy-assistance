---
name: clinical-driver-console
description: Main examination frontpage for Physical Therapy. Orchestrates Patient+Case, Comparable Sign, Driver Checks, AI Reasoning from LFS Clinical Driver Console.
version: 1.0.0
license: MIT
author: LFS PT
tags: [physicaltherapy, clinical-reasoning, examination, lfs]
allowed-tools: [read, write, bash, web_search]
---

# Clinical Driver Console Skill

## Purpose
Use this as frontpage during examination. Workflow: **Select region first, then direction/position/bias from Directional_Test_Registry. Keep free text only for clinical nuance.**

This skill creates and manages the 4-pillar structure from your Google Sheet.

## The 4 Pillars

### 1. Patient + Case (Input)
Collect:
- `Patient_ID` (auto or manual)
- `Patient_Name`
- `Therapist`
- `Age_Gender` e.g. "34 / M"
- `Contact_Chat_ID`
- `ChiefComplaint` (free text, limited)
- `FunctionalTask` (e.g. lifting, sitting >30min, overhead reach)
- `PreviousResponse` (what helped/worsened)

### 2. Comparable Sign (Input)
Must be selected from registry, not free-text:
- `CanonicalRegion`: [Cervical, Thoracic, Lumbar, Sacroiliac, Shoulder, Elbow, Wrist, Hip, Knee, Ankle, Foot]
- `SpecificJoint_Segment`: e.g. C5-C6, L4-L5, GH joint
- `MovementDirection`: Flexion, Extension, Rotation, Sidebend, Abduction, etc.
- `Position`: Standing, Sitting, Supine, Prone, Sidelying, 90/90, Closed chain
- `Bias_RangeGate`: e.g. Overpressure, Underpressure, End-range, Mid-range, Loaded 5kg
- `Angle_Load`: e.g. "45 deg" or "10kg"
- `FindingType`: enum [weak, painful, limited, unstable, apprehensive, compensation]
- `PainBehavior`: e.g. "catch at end range", "pain easing with repetition"

### 3. Driver Checks (Status)
Track status: `not_tested | cleared | positive | observed | negative`

- `RedFlagsCleared`: mandatory first - if not cleared, Safety Gate blocks treatment suggestions
- `NeuroScreen`: dermatome/myotome/reflex
- `AdjacentRegionCheck`: check region above/below
- `CompensationObserved`: e.g. scapular hiking, lumbar extension shift
- `DependencyResult`: e.g. does shoulder limitation depend on thoracic?
- `Irritability`: low / medium / high
- `ComparableSignSelected`: boolean
- `RetestComparator`: after intervention, % change

### 4. AI Reasoning (Output)
Generate:
- `PrimaryFinding`: e.g. "L lumbar extension driver with L4 multifidus inhibition"
- `SecondaryFinding`
- `ThirdFinding`
- `Confidence`: 0-100%
- `SafetyGate`: `assessment_only_until_confirmed` unless red flags + neuro = cleared
- `ManualTherapyOption`
- `ExerciseIntegration`
- `ReportSummary`: SOAP style

## Instructions for Agent

When this skill is invoked:

1.  If no patient file exists, create `/data/clinical_driver_template.json` instance with all fields.
2.  Prompt therapist to select `CanonicalRegion` FIRST.
3.  Use `directional-test-registry` skill to lookup available directions/positions/biases for that region.
4.  Validate all Comparable Sign inputs against registry. If free text not in registry, warn: "Please add to registry or keep nuance in Chief Complaint only".
5.  Check Driver Checks - if any = not_tested, prompt to complete.
6.  Call `ai-reasoning-engine` skill to generate findings. Do NOT generate manual therapy if SafetyGate is assessment_only.
7.  Always output a Report Summary.

## Example Input JSON

```json
{
  "Patient_ID": "PT-JED-001",
  "ChiefComplaint": "LBP with sitting >20min",
  "CanonicalRegion": "Lumbar",
  "MovementDirection": "Extension",
  "Position": "Standing",
  "FindingType": "weak",
  "Irritability": "medium"
}
```

## Example Output

```
Primary Finding: Lumbar extension motor control deficit - L multifidus weak at end-range
Confidence: 78%
Safety Gate: cleared - proceed with caution
Manual: PA mobilization L4-L5 Grade II + motor control cueing
Exercise: Prone extension with multifidus activation 3x10
Retest: Standing extension comparable sign 40% improved
```

## Constraints
- Never diagnose - always use "suggests" language, requires therapist confirmation.
- Not a medical device.
- Safety first: if RedFlags not tested -> block treatment.
