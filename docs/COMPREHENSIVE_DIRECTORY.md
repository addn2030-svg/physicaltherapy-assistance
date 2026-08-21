# Comprehensive International Manual Therapy and Rehabilitation Techniques Directory v2

**Loaded from `data/comprehensive_manual_therapy_directory.json` — 32 techniques, 10 categories**

This integrates your requested list into the LFS Clinical Driver Console.

## Full List Requested → Mapped

You provided:

### Manual Therapy and Orthopedic Manual Physical Therapy (OMPT)
- ✅ Mulligan Concept and Mobilization with Movement (MWM) → `mulligan_mwm`
- ✅ McKenzie Method of Mechanical Diagnosis and Therapy (MDT) → `mckenzie_mdt`
- ✅ Maitland Mobilization Techniques → `maitland`
- ✅ Kaltenborn-Evjenth Orthopedic Manual Therapy → `kaltenborn_evjenth`
- ✅ Cyriax Orthopedic Medicine and Deep Friction Massage → `cyriax`

### Neurodynamics and Neural Mobilization Techniques
- ✅ Neurodynamics and Neural Mobilization Techniques (Butler/Shacklock sliders/tensioners) → `neurodynamics`

### Medical Taping and Kinesiology Taping Applications
- ✅ Medical Taping and Kinesiology Taping Applications → `kinesio_taping` (includes Kinesio, McConnell, Dynamic, Lymphatic)

### Fascial and Myofascial Approaches
- ✅ Anatomy Trains Structural Integration → `anatomy_trains`
- ✅ Myofascial Release Therapy → `myofascial_release`
- ✅ Fascial Manipulation Technique → `fascial_manipulation` (Stecco Method CC/CF points)
- ✅ Dry Needling for Myofascial Trigger Points → `dry_needling_trigger`
- ✅ Dry Needling for Fascial System - Ali Marzok Method → `dry_needling_fascial_ali` **(Ali Marzok Method)**
- ✅ Fascial Distortion Model → `fascial_distortion_model`

### Visceral and Specialized Manual Therapy
- ✅ Visceral Manual Therapy - Ali Marzok Approach → `visceral_ali_marzok` **(Ali Marzok Approach)**
- ✅ Visceral Manipulation Techniques → `visceral_barral` (Barral)
- ✅ Craniosacral Therapy → `craniosacral`

### Neuromuscular and Movement Techniques
- ✅ NeuroKinetic Therapy (NKT) → `nkt`
- ✅ Proprioceptive Neuromuscular Facilitation (PNF) → `pnf`
- ✅ Motor Control and Motor Relearning Programs → `motor_control`
- ✅ Functional Movement Assessment and Correction → `functional_movement` (FMS, SFMA, DNS, Janda)

### Therapeutic Modalities and Adjunctive Therapies
- ✅ ANF (Amino Neuro Frequency) Therapy → `anf`

### Therapeutic Exercise Prescription
- ✅ Therapeutic Exercise Prescription → `therapeutic_exercise`
- ✅ Corrective Exercise Programming → `corrective_exercise` (NASM CES 4 phases)

### Specialized Rehabilitation Approaches
- ✅ Vestibular Rehabilitation Therapy → `vestibular`
- ✅ Cardiopulmonary Rehabilitation → `cardiopulmonary`
- ✅ Neurological Rehabilitation and Neuro-Recovery → `neuro_rehab`
- ✅ Gait Analysis and Gait Training → `gait_training`
- ✅ Balance and Proprioception Training → `balance_proprioception`
- ✅ Sports Rehabilitation and Performance Enhancement → `sports_rehab`

### Pain Science and Education
- ✅ Pain Neuroscience Education → `pne`
- ✅ Therapeutic Pain Management Strategies → `pain_management`
- ✅ Biopsychosocial Approach to Rehabilitation → `bps`

**Total: 32 techniques — all your requested items are present (including 2 Ali Marzok Methods).**

---

## How It Links to LFS Console

### Original Sheet → New Linkage

| Sheet Field | Old Techniques (v1) | New Directory Linkage (v2) |
|---|---|---|
| **Finding Type weak** | multifidus activation only | NKT (glute med vs TFL), Motor Control 10% MVC, PNF, DN Trigger, DN Fascial Ali Marzok if chain, ANF, Corrective Exercise, Therapeutic Exercise, Anatomy Trains |
| **Finding Type painful** | PA mobilization only | Maitland, Mulligan MWM pain-free, McKenzie MDT centralization, Neurodynamics sliders, Fascial Manipulation CC, Taping mechanical correction 50-75%, plus PNE+BPS if central sensitization (high irrit, widespread, non-mechanical) |
| **Finding Type limited** | Grade III-IV sustained | Kaltenborn-Evjenth Grade III sustained 30-60sec, Maitland III-IV, Myofascial Release 90-120sec, FM Stecco, FDM triggerband/continuum, PNF hold-relax, Anatomy Trains chain release |
| **Compensation Observed** | Observe only | Corrective Exercise CES inhibit-lengthen-activate-integrate 4-phase, NKT release facilitated 90sec + activate inhibited, Functional Movement SFMA breakout, Gait Analysis if walking functional task |
| **Irritability** | Grade guidance only | Full directory irritability_guidance per technique: low/medium/high specific dosage from JSON |
| **Dependency Result** | dependent_on_thoracic | Now includes dependent_on_visceral_psoas → Visceral Ali Marzok Approach retest psoas strength after 2min visceral work |

### Ali Marzok Methods Highlight

Two techniques are Ali Marzok Methods integrating LFS driver concept with fascia/visceral:

1. **DN Fascial System - Ali Marzok Method**
   - Concept: Fascia as sensory organ linking multiple muscle inhibitions along chain
   - When to suspect: Multiple muscles along SBL (plantar fascia, calf, hamstring, erector spinae) weak/limited together + fascial densification palpable
   - Technique: Superficial fascial needling along planes, gentle rotation, 5min retention
   - Retest: SLR + lumbar extension + ankle dorsiflexion all improve >15% → fascial system driver not isolated muscle
   - Integration: Immediately load fascial chain (SBL stretch, ankle DF loading)

2. **Visceral Manual Therapy - Ali Marzok Approach**
   - Concept: Visceral irritation (ileocecal valve, sigmoid, liver fascia) reflex inhibits psoas, diaphragm, glute med motor control
   - When to suspect: Psoas weak + lower abdominal tenderness + history IBS/diet + glute inhibition + lumbar shift
   - Technique: Gentle visceral mobilization 90-120sec with breathing, listening hand
   - Retest: Psoas strength + lumbar extension comparable → >30% immediate = visceral contribution
   - Safety: Screen red flags acute visceral pathology (appendicitis etc), AAA, pregnancy, recent surgery → refer

Both are searchable in directory via `Ali Marzok` keyword in web console Directory tab.

---

## Search Examples (Web Console Directory Tab)

- Search `Ali Marzok` → 2 techniques
- Search `Mulligan` → MWM technique with PILL rule, 3x6 dosage, retest 100% pain-free during
- Filter Finding `weak` + Region `Lumbar` → NKT, Motor Control, PNF, DN Trigger, Corrective Ex, etc.
- Filter Region `Shoulder` + Finding `painful` → Mulligan posterior glide MWM, Kaltenborn inferior glide, Fascial Manipulation antemotion, NKT serratus
- Filter Irritability `high` → Only techniques allowing high irrit: PNE, BPS, gentle Maitland I-II, sliders not tensioners, light taping 10-15%, breathing

---

## Evidence Levels in Directory

- **A**: Strong - McKenzie MDT (centralization), PNF (stroke, ROM), Motor Control (LBP), Therapeutic Exercise, Specialized Rehab Vestibular (BPPV Epley), Cardiopulmonary, Neurological Task-specific, Gait, Balance, Sports, Pain Science PNE+BPS
- **B**: Moderate - Mulligan MWM (peripheral, cerv headache), Maitland, Kaltenborn-Evjenth, Neurodynamics, Myofascial Release, Fascial Manipulation, Dry Needling Trigger Points, Kinesio Taping (short-term proprioception)
- **C**: Emerging / Clinical Expert - Cyriax DFM, Anatomy Trains, Fascial Distortion Model, Visceral (Barral + Ali Marzok Approach), Craniosacral, NKT model, DN Fascial Ali Marzok, ANF

Evidence level used to sort suggestions in auto-matching (A/B first).

---

## Dosage Templates Examples

All techniques have 3 irritability dosages:

**Maitland:**
- low: Grade III-IV end-range sustained 30-60sec x3-4
- medium: Grade II-III mid to end 30sec x2-3 rhythmical
- high: Grade I-II short of resistance 20-30sec x2 gentle

**Mulligan MWM:**
- Must be pain-free during (PILL principle) - 3x6 reps sustained glide, belt-assisted peripheral, SNAGs/NAGs spinal

**McKenzie MDT:**
- low: End-range repeated extensions 10x 5x/day overpressure
- medium: Mid-range 5-10x no overpressure test preference
- high: Gentle mid 3-5x sustained postures

**Dry Needling Trigger:**
- low: Deep pistoning 10-15 LTR, retain 2-5min
- medium: Gentle pistoning 5-10 no strong twitch
- high: Avoid deep, superficial or defer

**ANF:**
- Apply discs per protocol without touching, wear 72h, no drugs

See JSON full for each.

---

## Integration Workflow v2

1. Select Region (Lumbar) → Direction (Extension) → Position (Standing) → Bias (End-range) → Finding Type (weak) → Irritability medium (from sheet)
2. Console calls `getTechniquesByRegionAndFinding(Lumbar, weak, medium)` → returns NKT, motor_control, pnf, dry_needling_trigger, corrective_exercise, anatomy_trains, etc.
3. AI Reasoning Engine generates PrimaryFinding (multifidus inhibition) → passes to Manual Therapy Selector v2
4. Manual Therapy Selector v2 filters best techniques where region matches + finding matches + applies irritability_guidance
5. Output: Primary techniques list with dosage, isolation logic, retest rule, safety, integration
6. Exercise Integration uses CES 4-phase: Inhibit (SMR TFL 90sec) + Lengthen (static 30sec) + Activate (glute med 3x8) + Integrate (single leg stance gait)
7. Report Generator lists technique IDs used for documentation: `maitland, nkt, corrective_exercise, kinesio_taping`

All techniques exportable via CSV techniques matched pipe-separated `maitland|nkt|corrective_exercise`

---

## Files Updated

- New: `data/comprehensive_manual_therapy_directory.json` (32 techniques full metadata)
- Updated: `skills/manual-therapy-selector/SKILL.md` v2 with crosswalk + selection logic
- New: `skills/techniques-directory/SKILL.md` - searchable browser skill
- New: `src/engine/techniques.ts` + `techniques.py` - lookup engines
- Updated: `index.html` v2 - now has 3 tabs: Console + Directory Search (32 techniques) + Integration Map, auto-suggests techniques based on region/finding/irritability, includes Ali Marzok quick filters
- This doc: explanation

---

## Next Extensions (if needed)

- Add technique videos links (YouTube for each)
- Add technique contraindication checker (interacts with Red Flags)
- Add exercise videos for CES phases
- Add WhatsApp integration to send home program with technique names in Arabic

All requested techniques added to database and integrated.
