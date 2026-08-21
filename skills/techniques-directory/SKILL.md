---
name: techniques-directory
description: Searchable browser for Comprehensive International Manual Therapy and Rehabilitation Techniques Directory (32 techniques, 10 categories). Query by finding type, region, irritability, author (Ali Marzok).
version: 2.0.0
tags: [directory, manual-therapy, techniques, ompt, fascial, visceral, nkt, ali-marzok]
data: data/comprehensive_manual_therapy_directory.json
---

# Techniques Directory Skill

## Purpose
Master searchable database of all international manual therapy and rehabilitation techniques requested. Use as lookup for manual-therapy-selector and exercise-integration.

### Source File
`data/comprehensive_manual_therapy_directory.json` - 10 categories, 32 techniques with full metadata.

### Categories Included
1.  Manual Therapy and OMPT - Mulligan MWM, McKenzie MDT, Maitland, Kaltenborn-Evjenth, Cyriax DFM
2.  Neurodynamics - Shacklock/Butler sliders/tensioners
3.  Medical Taping / Kinesiology Taping
4.  Fascial/Myofascial - Anatomy Trains, MFR, Fascial Manipulation Stecco, Dry Needling Trigger, Dry Needling Fascial System Ali Marzok Method, Fascial Distortion Model
5.  Visceral/Specialized - Visceral Ali Marzok, Barral Visceral Manipulation, Craniosacral
6.  Neuromuscular/Movement - NKT, PNF, Motor Control/Motor Relearning, Functional Movement SFMA
7.  Modalities - ANF Therapy
8.  Exercise - Therapeutic Exercise Prescription, Corrective Exercise Programming CES
9.  Specialized Rehab - Vestibular, Cardiopulmonary, Neurological, Gait Analysis, Balance & Proprioception, Sports Rehab
10. Pain Science - PNE, Pain Management Strategies, Biopsychosocial Approach

## Search API (for Agent)

The agent can query directory by:

- **By ID**: `mulligan_mwm`, `mckenzie_mdt`, `maitland`, `kaltenborn_evjenth`, `cyriax`, `neurodynamics`, `kinesio_taping`, `anatomy_trains`, `myofascial_release`, `fascial_manipulation`, `dry_needling_trigger`, `dry_needling_fascial_ali`, `fascial_distortion_model`, `visceral_ali_marzok`, `visceral_barral`, `craniosacral`, `nkt`, `pnf`, `motor_control`, `functional_movement`, `anf`, `therapeutic_exercise`, `corrective_exercise`, `vestibular`, `cardiopulmonary`, `neuro_rehab`, `gait_training`, `balance_proprioception`, `sports_rehab`, `pne`, `pain_management`, `bps`

- **By Finding Type**: 
  - weak → NKT, motor_control, pnf, dry_needling_trigger, anf, therapeutic_exercise, corrective_exercise, anatomy_trains chain
  - painful → maitland, mulligan_mwm, mckenzie_mdt, neurodynamics, fascial_manipulation, kinesio_taping, pne+bps if central
  - limited → kaltenborn_evjenth Grade III, maitland III-IV, myofascial_release, fascial_manipulation, fdm, pnf hold-relax
  - unstable → kaltenborn traction, balance_proprioception, kinesio_taping facilitation, motor_control low threshold
  - apprehensive → pne, bps, taping, gentle maitland I-II, anf
  - compensation → corrective_exercise CES, nkt, functional_movement SFMA, anatomy_trains, motor_control, gait_training

- **By Region**:
  - Lumbar: mckenzie_mdt, maitland, motor_control, dry_needling_trigger QL, visceral_ali_marzok (psoas link), anf, therapeutic_exercise
  - Cervical: mulligan SNAGs, maitland, neurodynamics ULNT, anatomy_trains, motor_control deep flexors, pne
  - Shoulder: mulligan MWM posterior glide, kaltenborn inferior glide, fascial_manipulation antemotion, nkt serratus, kinesio_taping
  - Hip: kaltenborn long axis traction, nkt glute med/TFL, corrective_exercise, gait_training
  - Ankle: mulligan MWM dorsiflexion, kaltenborn, fdm continuum distortion, balance_proprioception, kinesio_taping
  - etc.

- **By Irritability**:
  - high → Filter techniques: pne, bps, kinesio_taping light 10-15%, maitland Grade I-II, neurodynamics sliders only, motor_control gentle breathing, myofascial gentle skin rolling. Exclude: deep DN, Grade III-IV, strong FDM
  - medium → Grade II-III, MWM pain-free, MDT mid-range, gentle tensioners, gentle DN
  - low → Grade III-IV-V, tensioners, deep friction, deep fascial, plyometrics, PNF resisted

- **By Author**: Ali Marzok → `dry_needling_fascial_ali` and `visceral_ali_marzok`

## Instructions for Agent

When skill invoked with query e.g.,:

```
Use techniques-directory skill to find techniques for Lumbar extension weak medium irritability
```

Steps:

1. Load `data/comprehensive_manual_therapy_directory.json`
2. Filter by best_for_regions includes Lumbar AND finding_type_match includes weak
3. Apply crosswalk and irritability guidance
4. Return top 3 primary + 1 BPS/PNE option if chronic, plus taping and ANF options with dosage + retest + safety + integration
5. Output must include technique.id, evidence_level, dosage_template, retest_rule

### Example Query: Shoulder flexion painful limited with compensation scapular elevation

Response:
- Primary: mulligan_mwm (MWM posterior glide) pain-free rule, evidence B, dosage 3x6 with belt, retest 100% pain-free during
- Secondary: kaltenborn_evjenth caudal glide Grade II 30sec x3 for inferior capsular, retest abduction +20deg
- Neuromuscular: nkt (serratus vs upper trap) + corrective_exercise CES
- Taping: kinesio_taping serratus facilitation 25%
- Fascial: fascial_manipulation CC antemotion if antemotion plane limited
- BPS: pne if fear of overhead
- Safety: red flags cleared, check long head biceps etc.

### Example Query: All fascial techniques

Return: anatomy_trains, myofascial_release, fascial_manipulation, dry_needling_trigger, dry_needling_fascial_ali, fascial_distortion_model with their differences.

## Web UI Integration

In `index.html`, browser panel added: Search techniques by finding type, region, author. Shows dosage, isolation logic, retest.

## Data File Maintenance

To add new technique, edit `data/comprehensive_manual_therapy_directory.json`:

```json
{
  "id": "new_technique",
  "name": "New Technique Name",
  "acronym": "NT",
  "origin": "Author",
  "classification": "...",
  "evidence_level": "B",
  "best_for_regions": ["Lumbar"],
  "finding_type_match": ["weak"],
  "irritability_guidance": { "low": "...", "medium": "...", "high": "..." },
  "dosage_template": "...",
  "isolation_logic": "...",
  "retest_rule": "Retest comparable sign after - need >X% to confirm driver",
  "safety_notes": "...",
  "integration_with_exercise": "...",
  "contraindications": []
}
```

Then update crosswalk.

## Constraints

- Always screen red flags.
- For DN and visceral, highlight safety + consent + referral.
- For Ali Marzok methods, note LFS integration: fascia as sensory organ linking visceral to motor control driver.
