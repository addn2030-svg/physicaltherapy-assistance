---
name: nkt-scar-8-vector
description: NKT Multi-Vector Scar Protocol - 8 directional vectors N/S/E/W/CW/CCW/Comp/Pinch, scar-to-scar and scar-to-ligament interlinks, navel/episiotomy special topologies, decompression taping cross-pattern, IASTM, tuning fork, master hierarchy STEP1 clear scars first. Uses data/nkt_detailed_protocols.json + nkt_level2_level3_manual.html + master_training_suite.html.
version: 1.0.0
tags: [nkt, scar, c-section, appendectomy, navel, episiotomy, 8-vector, decompression-taping, iastm]
data: data/nkt_detailed_protocols.json
---

# NKT Scar 8-Vector Testing Skill

## Purpose
Implements Level 3 Multi-Vector Scar Protocol from NKT Master Training Suite. Scars are Level 3 priority per Master Decision Hierarchy — **clear scars FIRST before ligaments, diaphragm, TMJ, subsystems, local pairs. Active scar resets all downstream corrections!**

### When to Suspect Scar Driver
- Patient with surgical history: C-section Pfannenstiel, appendectomy, arthroscopy portals, laparoscopy, episiotomy, perineal, navel umbilicus, any trauma scar
- Core inhibition persists: TVA, rectus abdominis, gluteus maximus weak despite hip/thoracic correction
- Pelvic instability post-cesarean, abdominal distension, inability to engage core
- Gluteal amnesia, hamstring dominance, pelvic floor weakness linked to lower abdominal scar

### 8-Vector Assessment (From Manual)

**Step1:** Find inhibited muscle in isolated shortened range (e.g., TVA, Rectus, Glute Max) → weak spongy give.

**Step2:** Test scar in 8 vectors while retesting weak muscle within 2 seconds:

| # | Vector | Direction | Hand Technique |
|---|---|---|---|
| 1 | N | Superior Cephalad Traction | Push scar up toward head |
| 2 | S | Inferior Caudad Traction | Push down toward feet |
| 3 | E | Right Lateral Shear | Shift to patient's right |
| 4 | W | Left Lateral Shear | Shift to patient's left |
| 5 | CW | Clockwise Rotation / Torsion | Two-finger torsion clockwise |
| 6 | CCW | Counter-Clockwise Rotation | Two-finger torsion counter-clockwise |
| 7 | Comp | Direct Compression | Perpendicular pressure into deep scar bed |
| 8 | Pinch | Skin Roll / Distraction Pinch | Lift and pinch scar away from underlying fascia |

**Interpretation:** If weak muscle instantly locks strong when scar challenged in specific vector (e.g., Vector 2 S inferior), that vector is reactive driver.

### Special Topologies

- **Umbilicus / Navel Scar:** Original birth scar, affects visceral fascia urachus/median umbilical ligament, drives deep lumbar/pelvic floor inhibition, test TL on navel
- **Episiotomy / Perineal Scars:** Primary drivers coccygeus, piriformis, obturator internus hypertonicity, test via obturator internus prone hip ER 90deg knee flexion
- **Scar-to-Scar Reactivity:** C-section reactive to older Appendectomy or laparoscopic portal. Test TL on Scar A while challenging Scar B. If indicator changes, scar-to-scar interlink confirmed.
- **Scar-to-Ligament:** Scar reactive to ligament e.g., C-section + Sacrotuberous ligament

### Corrective Protocol

1. **Release:** 45-60sec manual cross-fiber mobilization precisely along vector that restored strength
2. **Activate:** Immediately 3-5 reps isolated activation inhibited muscle (e.g., quadruped drawing-in TVA 5sec hold x4, sidelying glute med wall slide) leveraging 30-60sec neuroplastic window
3. **Retest & Verify:** Inhibited muscle holds strong isolated, comparable sign >30% improvement, 2min and 24hr retest

### Equipment

- **Decompression Taping:** Cross-pattern two intersecting strips 50% center tension over reactive scar to reduce fascial tension, wear 3-5 days, retest within 30min
- **IASTM:** 30-60deg bevel edge contact 30-60sec per reactive vector along scar
- **Tuning Fork 128Hz:** Vibration over scar to stimulate Pacinian corpuscles before activation if hypersensitive

### Homework (Golden Rule)

- Frequency 2-3x/day 2-4 weeks synaptic consolidation
- Sequence: **Release Scar along specific vector 60sec FIRST → Activate Inhibited Muscle SECOND strict!**
- If strengthening without releasing scar first, MCC bypasses weak and reinforces compensation!

### Safety

- Scars >5 years or decades still neurologically active until reprogrammed
- Avoid aggressive if infected, open wound, acute inflammation <6 weeks post-op, malignancy, DVT
- C-section medical clearance >6-8 weeks postpartum, avoid deep pressure acute
- Screen visceral red flags if scar linked to visceral appendectomy etc refer if acute abdomen

### Documentation for LFS Console

- `CompensationObserved` = scar vector direction that restored strength e.g., "C-section Pfannenstiel Vector S inferior traction restored TVA"
- `DependencyResult` = `dependent_on_scar_Csection_VectorS` or `dependent_on_scar_to_scar_Csection_Appendectomy`
- `RetestComparator` = TVA weak → after Vector S mobilization 60sec + quadruped activation → TVA strong + lumbar extension pain -50% + pelvic drop 40% improved

### Example

**Patient:** 34F 14 months post-cesarean persistent LBP abdominal distension inability engage core

**Assessment:**
- Test Bilateral TVA Rectus Abdominis → inhibited
- Challenge Rubbing hip flexors thoracolumbar erectors → TVA remains weak (not primary)
- Challenge Patient TL two fingers touching Pfannenstiel C-section scar Vector S inferior traction → Retest TVA → instantly maximum strength! → **Reactive Pair CONFIRMED C-section Vector S → TVA**

**Protocol:** 60sec multidirectional cross-friction scar mobilization along Vector S inferior + cross-pattern decompression taping 50% center → Immediate quadruped drawing-in abdominal activation 5sec hold x4 → Homework Release scar 60sec FIRST → Activate TVA SECOND 2x/day 2-4 weeks → Core restored within 2 weeks

**Video Reference:** Scar vector protocol images in `skills/nkt/docs/nkt_master_training_suite.html` + `nkt_level2_level3_manual.html`

### Integration with Master Hierarchy

```
STEP1 CLEAR SCARS & RECENT TRAUMAS L3 - C-sections, Appendectomies, Portals, Navel, Episiotomies - If scar active it will continually reset all downstream corrections!
STEP2 CLEAR LIGAMENTOUS INSTABILITY L3 - ATFL/CFL, Sacrotuberous, SIJ
STEP3 ASSESS MASTER CRANIO-RESPIRATORY DRIVERS L2 - Diaphragm Inhalation/Exhalation, TMJ, Hyoid
STEP4 EVALUATE FUNCTIONAL KINETIC SUBSYSTEMS L2 - POS, AOS, DLS, Lateral
STEP5 REFINE LOCAL AGONIST-ANTAGONIST SYNERGIST PAIRS L1
STEP6 ADVANCED GAIT INTEGRATION & HOMEWORK Release FIRST Activate SECOND
```

### Agent Instructions

When invoked:

1. Load `data/nkt_detailed_protocols.json` scar section
2. Ask for surgical history: List all C-sections, appendectomies, portals, navel, episiotomy, trauma scars with dates
3. Test inhibited muscle per LFS candidate muscles
4. Systematically test 8 vectors N/S/E/W/CW/CCW/Comp/Pinch while retesting weak muscle within 2sec
5. Identify vector that makes weak→strong
6. Check scar-to-scar and scar-to-ligament interlinks
7. Prescribe release 45-60sec along specific vector + immediate activation + decompression taping cross-pattern + homework Release FIRST Activate SECOND 2-3x/day 2-4 weeks
8. Document per LFS fields + safety clearance + video reference

### Output Format

```json
{
  "ScarAssessment": {
    "Scar": "Pfannenstiel C-section 2021 + Appendectomy 2010",
    "TestedMuscle": "Bilateral TVA",
    "Baseline": "Inhibited spongy give",
    "VectorTests": {
      "N": "remains weak",
      "S": "instantly locks strong - REACTIVE VECTOR CONFIRMED",
      "E": "weak",
      "W": "weak",
      "CW": "weak",
      "CCW": "weak",
      "Comp": "strongish 50%",
      "Pinch": "strong - decompression needed"
    },
    "ScarToScar": "C-section TL + Appendectomy rub -> Glute Max weak->strong, interlink confirmed",
    "Diagnosis": "C-section Vector S inferior traction + Pinch decompression deficit driving TVA inhibition, scar-to-scar C-section+Appendectomy driving Glute Max inhibition",
    "Protocol": {
      "Release": "60sec cross-fiber mobilization along Vector S inferior + 30sec pinch skin roll distraction + decompression taping cross-pattern 50% center tension",
      "Activate": "Quadruped TVA drawing-in 5sec hold x4, sidelying glute med wall slide",
      "Retest": "TVA holds strong isolated, lumbar extension pain -50%, pelvic drop improved 40%, 2min and 24hr",
      "Homework": "Self scar mobilization Vector S 60sec FIRST + Pinch 30sec + TVA activation SECOND 2x/day 2-4 weeks + decompression tape 3-5 days",
      "Equipment": "RockTape cross-pattern 50%, IASTM 30-60deg bevel 30-60sec, tuning fork 128Hz optional"
    },
    "Safety": "Medical clearance >6-8 weeks postpartum, no infection, no malignancy, visceral red flags cleared",
    "MasterHierarchy": "STEP1 scars cleared first before ligaments ATFL etc"
  }
}
```
