---
name: manual-therapy-selector
description: Suggests manual therapy options gated by irritability, safety, region, finding type, using Comprehensive International Manual Therapy and Rehabilitation Techniques Directory (35+ techniques). Assessment only until confirmed.
version: 2.0.0
tags: [manual-therapy, mobilization, ompt, mulligan, mckenzie, maitland, fascial, visceral, dn, taping, physicaltherapy]
dependencies:
  - directional-test-registry
  - data/comprehensive_manual_therapy_directory.json
---

# Manual Therapy Selector Skill v2 — With Comprehensive Directory

## Purpose
Suggests manual therapy based on Primary Finding + Irritability + Safety Gate, now with full International Directory (32 techniques) integration.

### Data Source
`data/comprehensive_manual_therapy_directory.json` — 10 categories, 32 techniques:

**OMPT:** Mulligan MWM, McKenzie MDT, Maitland, Kaltenborn-Evjenth, Cyriax
**Neurodynamics:** Butler/Shacklock sliders/tensioners
**Taping:** Kinesiology / Medical taping, McConnell
**Fascial/Myofascial:** Anatomy Trains, Myofascial Release, Fascial Manipulation Stecco, Dry Needling Trigger Points, Dry Needling Fascial System Ali Marzok Method, Fascial Distortion Model
**Visceral:** Visceral Manual Therapy Ali Marzok Approach, Barral Visceral Manipulation, Craniosacral
**Neuromuscular:** NKT, PNF, Motor Control/Motor Relearning, Functional Movement SFMA
**Modalities:** ANF Therapy
**Exercise:** Therapeutic Exercise Prescription, Corrective Exercise Programming
**Specialized Rehab:** Vestibular, Cardiopulmonary, Neurological Neuro-Recovery, Gait Analysis & Training, Balance & Proprioception, Sports Rehab & Performance
**Pain Science:** Pain Neuroscience Education, Therapeutic Pain Management, Biopsychosocial Approach

## Gating Rules (Enforced)

- If `SafetyGate = assessment_only_until_confirmed` -> Output: "Assessment only - complete red flag + neuro clearance first. No manual therapy suggested until cleared. Can use gentle education and breathing."
- If `SafetyGate = referral_only` -> "Referral only - positive red flag. STOP"
- If `Irritability = high` -> Only Grade I-II Maitland, sliders not tensioners, gentle NKT release only, PNE/BPS priority, avoid deep fascia / DTF / Grade III-IV / strong FDM. Use lymphatic taping light.
- If `Irritability = medium` -> Grade II-III, MWM pain-free, MDT mid-range, sliders + gentle tensioners, gentle DN trigger, gentle fascial 2min per CC
- If `Irritability = low` -> Grade III-IV-V, sustained, overpressure, MWM belt, MDT end-range, tensioners, deep friction, deep fascial DN, plyometrics

## Crosswalk: Finding Type → Technique (from directory crosswalk)

Load `data/comprehensive_manual_therapy_directory.json` → `crosswalk.comparable_sign_finding_type_to_techniques`:

- **weak**: NKT, Motor Control, PNF, Dry Needling Trigger Points, ANF, Corrective Exercise, Therapeutic Exercise, Anatomy Trains if chain
- **painful**: Maitland, Mulligan MWM, McKenzie MDT, Neurodynamics sliders, Fascial Manipulation, Taping mechanical correction, PNE + BPS if central sensitization
- **limited**: Kaltenborn-Evjenth Grade III sustained, Maitland III-IV, Myofascial Release 90-120sec, Fascial Manipulation CC, FDM triggerband/continuum, PNF hold-relax, Anatomy Trains chain release
- **unstable**: Kaltenborn traction not stretch, PNF rhythmic stabilization, Balance & Proprioception, Kinesio facilitation tape, Motor Control low threshold 10% MVC
- **apprehensive**: PNE, BPS, Taping for confidence, Gentle Maitland I-II, ANF calming
- **compensation**: Corrective Exercise CES 4-phase inhibit-lengthen-activate-integrate, NKT (release facilitated + activate inhibited), Functional Movement SFMA breakout, Anatomy Trains, Motor Control, Gait Analysis

## Selection Logic

Agent must:

1. Read PrimaryFinding + region + direction + irritability + safety gate
2. Lookup `data/comprehensive_manual_therapy_directory.json`
3. Filter techniques where `best_for_regions` includes CanonicalRegion AND `finding_type_match` includes FindingType
4. Prioritize by evidence level for region: e.g., Lumbar extension painful limited → MDT + Maitland PA
5. Apply irritability guidance from technique entry → dosage template
6. Always include rationale linked to comparable sign + retest rule from technique
7. Include 2 options: Primary technique + Alternative (often less irritating or PNE/BPS if chronic)

## Examples with Directory Integration

### Lumbar Extension Weak (Medium irrit, Thoracic driver)
Primary driver = thoracic extension + multifidus inhibition

**Primary Option (OMPT + Neuromuscular):**
- Technique: Maitland Thoracic PA T6-8 Grade II-III + Mulligan? No, Maitland. + NKT protocol for glute med vs TFL
- Details: `techniques[maitland].dosage_template` = 30sec x3, + `techniques[nkt].dosage_template` = Test glute med weak -> test TFL strong -> release TFL 90sec + activate glute med 3x8
- Rationale: From directory isolation_logic: If correcting thoracic improves lumbar extension 40% immediate, thoracic driver
- Dosage: Grade II 2x30sec thoracic, then NKT activation
- Retest: From technique: Expect >30% improvement comparable, retest standing extension after
- Exercise integration: Link to Corrective Exercise Programming CES

**Alternative:** Anatomy Trains SBL release (if SBL chain) + Motor Control low threshold

### Shoulder Flexion Painful Limited with Scapular Compensation
- Finding: painful at 120deg, compensation scapular elevation
- Techniques: Mulligan MWM GH posterior glide (pain-free rule), Kaltenborn-Evjenth inferior glide Grade II for capsular restriction, Fascial Manipulation CC for antemotion, NKT serratus inhibition vs upper trap facilitation, Kinesio tape serratus facilitation 25%
- Select based on retest: If MWM makes 100% pain-free during → MWM driver (positional fault). If Kaltenborn inferior glide improves abduction 20deg → capsular inferior driver.

### High Irritability Lumbar with Central Sensitization
- Finding: painful high irrit, non-mechanical, poor sleep
- Directory path: Pain Science category first
- Primary: Pain Neuroscience Education 30min + Therapeutic Pain Management pacing + Gentle Maitland Grade I-II short of resistance + Motor Control breathing 90/90
- Avoid: Deep DTF, Grade III-IV, dry needling deep, strong FDM
- Retest: Confidence and sleep not ROM initially

### Visceral Link Example (Ali Marzok Approach)
- Lumbar extension weak + psoas weak + lower abdominal tender + ileocecal region history IBS
- Technique: Visceral Manual Therapy Ali Marzok Approach
- Dosage: Gentle visceral mobilization 2min with breathing + 90/90 breathing retraining
- Retest: Psoas strength and lumbar extension after visceral release → >30% immediate = visceral contribution
- Safety: Must have cleared systemic red flags, not acute visceral inflammation

## Output Format v2 (Extended)

```json
{
  "ManualTherapyOption": {
    "PrimaryTechnique": {
      "id": "maitland",
      "name": "Maitland Mobilization Techniques",
      "category": "OMPT",
      "Technique": "PA Unilateral L4-L5 Grade II, 2x30sec + PA T6-8 Grade II",
      "Rationale": "To improve lumbar extension end-range and thoracic driver per LFS dependency. Matches finding type painful+limited.",
      "Dosage": "Grade II, 30sec x3, retest after 2min, monitor 24hr pain",
      "IsolationLogic": "If PA improves comparable 40%, joint driver confirmed",
      "RetestRule": "Retest standing extension pain/ROM immediately - need >30% for medium irrit",
      "Evidence": "B (Moderate)",
      "SafetyGate": "proceed_with_caution",
      "ContraindicationsChecked": ["No fracture", "No malignancy"]
    },
    "SecondaryTechnique": {
      "id": "nkt",
      "name": "NeuroKinetic Therapy (NKT)",
      "category": "Neuromuscular and Movement Techniques",
      "Technique": "NKT protocol: Release TFL 90sec + Activate glute med 3x8",
      "Rationale": "Motor control deficit driver - glute med inhibited by overactive TFL observed as pelvic drop",
      "Integration": "After NKT, train single leg stance with band"
    },
    "AlternativeForHighIrritability": {
      "id": "pne",
      "name": "Pain Neuroscience Education + gentle myofascial",
      "Technique": "PNE 15min + Thoracolumbar fascia gentle MFR 60sec + breathing"
    },
    "CrosswalkReference": "weak -> NKT, Motor Control, PNF, DN Trigger, etc. per directory crosswalk",
    "TapingOption": {
      "id": "kinesio_taping",
      "name": "Medical Taping",
      "Technique": "Glute med facilitation tape 25% tension origin->insertion + thoracic extension mechanical correction 50%",
      "Purpose": "Hold manual gains, proprioceptive cue for exercise"
    },
    "ANFOptionIfInflammation": {
      "id": "anf",
      "name": "ANF Therapy",
      "When": "If chronic inflammatory driver suspected per Ali Marzok fascial method"
    },
    "SafetyAndPrecautions": "Irritability medium - avoid sustained >30sec, monitor 24hr, red flags cleared"
  }
}
```

## Integration with Other Skills

- **ai-reasoning-engine**: Calls this skill, passes PrimaryFinding. Expects back two technique options with retest rules.
- **exercise-integration**: After manual window, exercise must be from Corrective Exercise Programming CES 4-phase based on same directory
- **report-generator**: Must list technique IDs + names for documentation, e.g., "Techniques used: maitland, nkt, kinesio_taping, motor_control"
- **clinical-driver-console**: Dynamic Lookup Panel now also shows `AssociatedManualTechniques` per direction from directory

## Ali Marzok Methods Special Note

Two techniques from directory are Ali Marzok Methods:

1. **Dry Needling for Fascial System - Ali Marzok Method**: Emphasizes fascia as sensory organ. Neddles along fascial planes, not just muscle trigger. Indicated when multiple muscles along chain weak (SBL, DFL). Retest all linked movements not just one.

2. **Visceral Manual Therapy - Ali Marzok Approach**: Links visceral irritation (ileocecal, sigmoid, liver) to psoas / diaphragm / glute inhibition per reflex. Retest psoas strength after 2min visceral work. Must screen medical.

Agent must flag these with `author: Ali Marzok` and highlight LFS integration.

## Compliance

- Never suggest Grade V manipulation unless therapist qualified and cervical artery cleared.
- Never suggest dry needling without consent + anatomy safety + sharps.
- Visceral work requires medical screening + not acute abdomen.
- CRITICAL: Keep Safety Gate assessment_only_until_confirmed enforcement first.
