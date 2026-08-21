---
name: nkt
description: NeuroKinetic Therapy complete clinical implementation - Motor Control Center, MCC neuroplastic window, binary MMT testing, compensation taxonomy (synergistic dominance, reciprocal inhibition, kinetic slings POS/AOS/DLS/Lateral), scar 8-vector protocol, ligamentous interlinks, extraocular & TMJ reflexes, 6-step corrective protocol, reverse TL, master decision hierarchy Level 1-3. Uses data/nkt_detailed_protocols.json + 4 training HTML modules.
version: 3.0.0
tags: [nkt, neurokinetic, motor-control, cerebellum, mcc, muscle-testing, compensation, scar, ligament, tmj, kinetic-sling]
data_files: [data/nkt_detailed_protocols.json, data/comprehensive_manual_therapy_directory.json]
docs: [skills/nkt/docs/nkt_learning_module.html, skills/nkt/docs/nkt_level2_level3_manual.html, skills/nkt/docs/nkt_master_training_suite.html, skills/nkt/docs/nkt_video_library.html]
author: David Weinstock - Enhanced for LFS Clinical Driver Console
---

# NKT Skill - NeuroKinetic Therapy Complete (v3)

## Purpose
Full implementation of NeuroKinetic Therapy from 4 uploaded training modules, integrated with LFS Clinical Driver Console driver checks.

### Source Files Parsed
- `nkt_learning_module.html` - Overview, MCC, MMT, compensations, corrective protocol, 4 clinical cases, 10 MSQs
- `nkt_level2_level3_manual.html` - Level 2 subsystems POS/AOS/DLS/Lateral, Core Cylinder diaphragm, TMJ stomatognathic, perturbation & joint compression/decompression, Level 3 advanced gait, multi-vector scars 8 vectors, ligamentous interlinks ATFL Sacrotuberous etc, extraocular CN III/IV/VI, hyoid, master decision matrix
- `nkt_master_training_suite.html` - Assessment kit intake form, visual photo atlas POS gait, diaphragm subcostal release, scar vector protocol, ligament ATFL pelvis, ocular testing tool, standing perturbation, clinical tools taping RockTape, IASTM, tuning fork 128Hz, certification Level 1/2/3 rubrics
- `nkt_video_library.html` - Live demo transcripts, 4-panel sequence, official video vault YouTube links

Parsed into `data/nkt_detailed_protocols.json` - 3.0.0

## Core Concepts (From Learning Module)

### Motor Control Center (MCC) - Cerebellum
- Stores automated multi-joint synergies (engrams) without conscious cortex calculation
- Learns via trial, error, adaptive failure (infant walking example)
- Traumatic substitution: After injury, injured muscle inhibited to prevent damage, MCC recruits synergists/antagonists. Even after tissue heals histologically, compensation remains burned in memory. Compensator becomes hypertonic overloaded, inhibited remains dormant. Treating only tight painful compensator without reactivating inhibited yields fleeting relief.

### 30-60 Second Neuroplastic Window
- When movement test fails, MCC opened to new learning for 30-60sec. Failed MMT is deliberate neurological probe unlocking window.

### NKT MMT vs Orthopedic Strength
- Not Kendall 0-5, but binary neurological test instantaneous recruitment rate coding within first 1-2sec
- Strictly isometric, subtle gradual ramp 0%->50%->100% over 2sec hold 1sec, never jerk
- Precise vector & joint isolation: e.g., Glute Med requires 30deg abduction slight extension slight ER. If hip flexes, TFL assumes load false positive strong
- Shortened range starting position to expose deficits
- Cue: "Hold, Don't Let Me Push You" - match pressure isometrically, don't push through
- Vigilance against substitution: trunk rotation, Valsalva breath-holding, foot gripping, shoulder hiking, limb repositioning = positive inhibition
- Binary: Facilitated hypertonic overactive driver (crisp immediate lock) vs Inhibited hypotonic underactive receiver (spongy yield delayed latency)

## Compensation Taxonomy (Critical for Driver Checks)

### Synergistic Dominance (Agonist-Synergist)
- Secondary accessory muscle takes over primary weak inhibited prime mover, smaller inferior leverage, overuse trigger points tendinopathies
- Classic:
  - TFL -> Glute Med = IT band syndrome lateral hip bursitis pelvic drop single leg stance
  - Hamstrings & Erector Spinae -> Glute Max = hamstring strains facet impingement lumbar extension substitution
  - Upper Trap & Levator Scapulae -> Lower Trap / Serratus Anterior = neck stiffness subacromial impingement scapular elevation compensation

### Reciprocal Inhibition (Antagonist-Agonist, Sherrington's law via Ia inhibitory interneurons)
- Chronically hypertonic facilitated creates sustained reciprocal inhibition of opposing antagonist
- Classic:
  - Psoas Major / Iliacus hypertonic -> inhibits Glute Max = anterior pelvic tilt lumbar shear hip impingement
  - Pectoralis Minor hypertonic -> inhibits Lower Trap Rhomboids = scapula protracted anterior tilt
  - Gastrocnemius Soleus hypertonic -> inhibits Tibialis Anterior = foot drop reduced DF knee hyperextension gait

### Kinetic Slings (Global)
- **POS Posterior Oblique:** Lat Dorsi -> Thoracolumbar Fascia -> Contralat Glute Max. Function propulsion push-off gait rotational power SI force closure. Dysfunction hyperactive right lat inhibits left glute max rotational pelvic torsion chronic SI instability. Test supine POS Integration: right shoulder extended IR pressed to table + left leg extended slight ER heel pressed to table, clinician attempts to flex right arm while lifting left leg. Spongy give = POS failure.
- **AOS Anterior Oblique:** External Oblique -> Abdominal Fascia Linea Alba -> Contralat Internal Oblique Adductor Longus Magnus. Function forward torso rotation deceleration throwing swinging pubic symphysis stabilization. Dysfunction overactive adductor inhibits contralateral core rotators athletic pubalgia sports hernia groin strains. Test supine AOS Diagonal Vector: right shoulder flexed across chest toward left ASIS + left hip flexed 45deg adducted midline, clinician pries right shoulder back pushes left knee abduction. Common dyssynergia overactive Adductor Longus driving inhibition contralateral External Oblique.
- **DLS Deep Longitudinal:** Erector Spinae -> Sacrotuberous Ligament -> Biceps Femoris -> Peroneus Longus -> Tibialis Anterior. Function ground reaction force transmission foot to cranium. Test prone straight-leg hip extension coupled ipsilateral foot eversion plantarflexion hamstring dominance over gluteals sacrotuberous tension.
- **Lateral Subsystem:** Glute Med Min -> TFL -> Contralateral QL Adductors. Function frontal plane pelvic stabilization single-limb stance. Test sidelying hip abduction against ipsilateral QL lateral trunk flexion. Common hypertonic QL compensating inhibited contralateral Glute Med = pelvic drop hip hiking observed in LFS driver checks.

### Specialized Drivers

#### Surgical Scars & Soft Tissue Trauma
- Incisions transect cutaneous fascial muscle mechanoreceptors creating chronic nociceptive proprioceptive noise causing central inhibition nearby stabilizers
- Examples: C-section Pfannenstiel -> TVA rectus gluteal inhibition most common driver core inhibition, Appendectomy -> psoas glute med, Arthroscopy portal -> quadriceps, Navel umbilicus visceral fascia urachus median umbilical ligament -> deep lumbar pelvic floor inhibition, Episiotomy perineal -> coccygeus piriformis obturator internus hypertonicity
- **Multi-Vector Scar Protocol Level 3:** Test scars in 8 distinct directional planes and scar-to-scar scar-to-ligament relationships
  - Vector 1 N Superior Cephalad Traction push up toward head
  - Vector 2 S Inferior Caudad push down toward feet
  - Vector 3 E Right Lateral Shear shift to right
  - Vector 4 W Left Lateral Shear shift to left
  - Vector 5 CW Clockwise Rotation Torsion two-finger
  - Vector 6 CCW Counter-Clockwise
  - Vector 7 Comp Direct Compression perpendicular into deep scar bed
  - Vector 8 Pinch Skin Roll Distraction lift pinch away from underlying fascia
  - Treatment: 45-60sec manual cross-fiber mobilization precisely along vector that restored strength, immediately 3-5 reps isolated activation inhibited muscle
  - Special: Umbilicus navel original birth scar affects visceral fascia, Episiotomy perineal, Scar-to-Scar reactivity C-section reactive to older Appendectomy or laparoscopic portal test TL on Scar A while challenging Scar B

#### Ligamentous Interlinks (Ligamento-Muscular Reflex)
- Ligaments sensory organs densely populated Ruffini Pacinian free nerve endings that directly influence motor unit recruitment
- Inventory:
  - Pelvic Lumbar: Sacrotuberous ischial to sacral shear compensates Biceps Femoris Glute Max, Sacrospinous deep palpation medial ischial spine linked Pudendal nerve irritation, Iliolumbar L5 transverse to iliac crest glide compensates QL Psoas, Dorsal SIJ posterior SIJ seam distraction
  - Ankle Foot: ATFL plantarflexion+inversion stress drives Peroneus Glute Med inhibition most common contralateral glute med, CFL pure inversion neutral dorsiflexion, Deltoid eversion stress drives Tibialis Posterior Core inhibition, Bifurcate sinus tarsi chronic lateral foot pain, Spring plantar calcaneonavicular medial arch collapse
  - Knee: ACL anterior drawer Lachman, MCL valgus stress
  - Upper Cervical: Alar sidebend rotation stress linked Deep cervical flexors inhibition
- **Ligament-to-Ligament Interlink Protocol:** Ligaments can compensate for other ligaments! e.g., Chronic ATFL sprain compensated by ipsilateral Sacrotuberous. Test Challenge Ligament A stress ATFL -> Test indicator -> Weak. Challenge Ligament B Sacrotuberous -> Retest indicator -> Locks Strong! Correction Friction release compensating ligament 30sec -> Proprioceptively stimulate lax ligament tap vibrate 15sec.

#### Cranio-Cervical & Postural Reflexes
- **Suboccipital:** Triangle rectus capitis posterior obliquus capitis contains highest density muscle spindles in body 200-500 spindles/gram ultra-sensitive proprioceptive monitors. Hypertonic Suboccipitals -> inhibits Deep Cervical Flexors Longus Colli Capitis. Driven by visual fixation forward head posture.
- **Extraocular Muscles & Oculo-Cervical Reflex:** Extraocular have direct neural connections via tectospinal vestibulospinal tracts to suboccipital complex. Table:
  - CN III Superior Rectus Up&Out -> Posterior chain extension tone Suboccipitals Erectors
  - CN III Inferior Rectus Down&Out -> Anterior chain flexion tone Deep neck flexors Abs
  - CN III Medial Rectus Medially Inward -> Adductor line Deep Front Line activation
  - CN III Inferior Oblique Up&In -> Contralateral cervical rotation lateral sling
  - CN IV Superior Oblique Down&In -> Ipsilateral vestibular balance core stabilization
  - CN VI Lateral Rectus Laterally Outward -> Lateral subsystem Glute Med SCM coupling
  - Protocol: Identify inhibited muscle Deep Cervical Flexors or Glute Med, have patient hold max gaze in specific quadrant Eyes hard Up Right, retest inhibited muscle while gaze held, if locks strong -> Extraocular Muscle reactive driver! Correct eye-tracking smooth pursuit saccade drills coupled neck stabilizer activation
- **TMJ & Stomatognathic System:** Jaw muscles primary somatic default whole-body overcompensation. Jaw clenching provides emergency bracing when spinal stabilizers dormant.
  - Temporalis Elevation Retrusion bite posterior molars resistance against jaw opening -> Compensates Front Line Deep Neck Flexors TVA Back Line Gluteals
  - Masseter Elevation Ipsilateral Translation lateral shearing -> Lateral Subsystem Glute Med QL Peroneals
  - Medial Pterygoid Elevation Contralateral Deviation -> Contralateral Oblique slings intrinsic pelvic floor Tinnitus
  - Lateral Pterygoid Depression Protrusion Contralateral Deviation -> Deep Cervical Flexors Upper Cervical Ligaments
  - Digastric Suprahyoids Jaw Depression Hyoid Elevation -> Diaphragm Pelvic floor Valsalva compensation
  - Protocol: Find inhibited muscle anywhere Left Glute Med, have client clench jaw or deviate right -> Retest Glute Med, if glute locks strong -> TMJ primary reactive driver! Release facilitated pterygoid masseter intra-oral or extra-oral 45sec -> Activate glute
- **Hyoid Musculature & Deglutition Swallowing Reflex:** Hyoid free-floating suspension bridge cranium mandible cervical spine thorax. Suprahyoids Mylohyoid Geniohyoid Stylohyoid Digastric tested via resisted hyoid depression jaw opening hypertonicity leads anterior neck tension thoracic outlet compression. Infrahyoids Sternohyoid Omohyoid Sternothyroid Thyrohyoid tested via resisted swallowing cervical extension linked fascial tension clavicle first rib

## Corrective Protocol - 6 Steps (From Training Suite)

1. **Baseline Muscle Test:** Test suspected victim muscle in isolated shortened range. Weak inhibited spongy give registers in cerebellar MCC. Example Right Glute Max fails to hold isometric.

2. **Therapy Localization (TL) / Tactile Challenge:** Apply sensory stimulation to hypothesized compensating driver. Patient places two fingers directly on suspected tissue (TL) or practitioner briskly rubs muscle belly tendon scar ligament. Sensory input floods MCC with afferent mechanoreceptive feedback. Types: TL patient touch, Rub muscle belly 2-3sec, Pinch scar, Stress ligament, Gaze hold for eyes.

3. **Immediate Retest - Verifying Reactive Pair:** While sensory challenge active or within 2 seconds of rubbing, immediately re-test weak muscle. If previously weak muscle suddenly rock solid strong, you have verified Reactive Pair. Sensory challenge temporarily neutralized hypertonic inhibition allowing MCC to fire inhibited muscle. Key: Weak -> Strong shift = REACTIVE PAIR CONFIRMED.

4. **Release the Facilitated Driver:** Apply targeted manual therapy ischemic compression IASTM 30-60deg bevel deep friction pin-and-stretch dry needling to facilitated driver for 30-60 seconds. Mechanically downregulates muscle spindle sensitivity and resets hyperactive afferent tone. Duration 30-60sec to optimize spindle reset within cerebellar plasticity window. Modalities: Ischemic compression, Myofascial release, IASTM stainless steel, Deep friction, Dry needling, Scar mobilization cross-fiber, Tuning fork 128Hz vibration over lax ligament.

5. **Immediately Activate / Strengthen Inhibited Muscle:** Without delay leveraging 30-60sec plasticity window, have patient perform isolated isometric activation of previously inhibited muscle (3-5 reps of 5-second isometric hold with light-to-moderate resistance). Burns newly restored neural pathway into MCC. Dosage 3-5 reps x5sec isometric hold light-moderate precision avoid fatigue.

6. **Retest & Prescribe Corrective Homework:** Retest inhibited muscle in isolation (no touch). Should hold crisp neurological strength. Prescribe specific self-care homework with strict sequence: 1. Release Driver FIRST -> 2. Activate Inhibited SECOND performed 2-3 times daily for 2-4 weeks to establish permanent synaptic consolidation. Golden Rule: If patient performs strengthening on inhibited muscle WITHOUT first releasing compensating driver, MCC will immediately bypass weak muscle and reinforce pre-existing compensation! Driver must always be downregulated immediately before receiver is upregulated.

### Reverse Therapy Localization (Reverse TL)
When you have client with severe pain in hypertonic facilitated tissue but cannot easily find what is inhibited: Touch painful hypertonic tissue Driver, Scan through potential inhibited muscles across kinetic chain Glute Max TVA Lower Trap, When you test muscle normally strong but breaks weak when touching driver you have found inhibited receiver! Release painful driver -> Activate newly uncovered inhibited muscle.

### Homework Prescription
Frequency 2-3 times daily for 2-4 weeks, Sequence Release FIRST -> Activate SECOND strict, Purpose synaptic consolidation in cerebellum permanent engram storage, Compliance note frequent low-dose repetition required to replace old compensation pattern.

## Clinical Cases (From Learning Module)

**Case 1 Chronic Low Back Pain & Lumbar Extension Impingement:** 42yo desk worker runner 2yr bilateral lumbar facet pain standing running. Traditional tight erector spinae tight psoas weak glutes previous PT core planks glute bridges minimal relief. NKT Test Right Glute Max inhibited, Challenge Rub Right Lumbar Erector -> remains weak not primary, Challenge Rub Right Psoas Major -> instantly rock solid strong! Diagnosis Reciprocal Inhibition Right Glute Max driven Hypertonic Ipsilateral Psoas Major. Protocol 45sec deep release Right Psoas -> immediate isolated prone hip extension isometric 5sec hold x4 reps homework 2x/day.

**Case 2 Lateral Knee Pain & IT Band Friction Syndrome:** 28yo female marathon runner severe lateral right knee pain mile 4. Traditional lateral femoral condyle tenderness positive Ober tight IT band. NKT Test Right Glute Med 30deg abduction slight extension slight ER -> inhibited, observation hip flexes internally rotates to utilize TFL, Challenge Firm tactile challenge rubbing over Right TFL belly -> immediately locks strong! Diagnosis Synergistic Dominance Right TFL over Right Glute Med. Protocol Myofascial release foam rolling Right TFL 45sec -> immediate sidelying pure glute med abduction holds wall slide eliminate hip flexion pain-free 10-mile trial.

**Case 3 Post-Cesarean Pelvic Instability & Core Weakness:** 34yo female 14 months post-cesarean persistent LBP abdominal distension inability engage core. Test Bilateral TVA Rectus Abdominis -> inhibited, Challenge Rubbing hip flexors thoracolumbar erectors -> TVA remains weak, Challenge Patient TL two fingers touching Pfannenstiel C-section scar -> instantly maximum strength! Diagnosis Neurological core inhibition driven afferent nociceptive mechanoreceptive disruption at surgical scar. Protocol 60sec multidirectional cross-friction scar mobilization -> immediate quadruped drawing-in activation core restored within 2 weeks.

**Case 4 Cervicogenic Headaches & Scapular Dyskinesis:** 39yo software architect chronic suboccipital throbbing headaches burning medial scapular pain. Test Deep Cervical Flexors Longus Colli Capitis -> inhibited Lower Trap -> inhibited, Challenge Rubbing bilateral Suboccipital -> Deep Neck Flexors immediately locks strong! Kinetic Sling Retest Rubbing Upper Trap -> Lower Trap locks strong! Diagnosis Multi-tiered compensation Suboccipitals driving Deep Neck Flexor inhibition Upper Trap driving Lower Trap inhibition. Protocol Suboccipital release -> supine chin tuck isometric holds Phase1 Upper Trap release -> prone Y-raise isometric holds Phase2.

## Level 2 Modules

- **Kinetic Subsystems:** POS, AOS, DLS, Lateral (see above)
- **Core Cylinder:** Roof Respiratory Diaphragm, Anterior Lateral Walls TVA Internal Obliques, Posterior Wall Lumbar Multifidi QL, Floor Pelvic Floor Levator Ani Coccygeus Pubococcygeus. Diaphragm assessment inhalation vs exhalation testing: baseline indicator strong Anterior Deltoid or Psoas, patient inhales deeply holds breath retest if breaks -> Inhalation Diaphragm Facilitation, exhales completely holds breath out retest if breaks -> Exhalation Diaphragm Facilitation, challenge palpate subcostal margin crus 45sec manual subcostal release followed 3-5 exhalation core drawing-in activations. Pelvic floor via coupling Obturator Internus Adductor Magnus Longus prone hip ER 90deg knee flexion.
- **TMJ Stomatognathic:** See table above
- **Perturbation:** A/P Perturbation standing seated tall sudden gentle sternal push posterior or thoracic pull anterior observe trunk corrects via intrinsic core vs superficial neck hip gripping. Rotational Oblique Perturbation gentle rotational displacement shoulders pelvis test contralateral oblique sling engagement.
- **Joint Compression vs Decompression:** Compression patient supine flex hip 90deg apply axial compressive force down shaft femur into acetabulum 2sec retest key indicator Psoas or Glute Med if weakens -> pathological capsule compression sensitivity hypertonic deep rotators. Decompression gentle axial long-axis traction joint hip ankle GH retest indicator if weakens -> ligamentous instability capsular laxity driving protective splinting.

## Level 3 Modules

- **Advanced Multi-Phasic Gait:** Phase matrix Heel Strike Initial Contact -> Ankle DF + Contralat Arm Extension, Loading Response Mid-Stance -> Glute Med + Contralat QL, Terminal Stance Push-Off -> Glute Max + Contralat Lat POS, Swing Phase -> Iliopsoas + Contralat Shoulder Extension. Tests: Reciprocal Humeral-Femoral Gait Vector supine Flex Right Humerus 90deg while extending Left Hip pressing heel down, MMT attempt push right arm extension while lifting left leg flexion assess opposite pair Left Humerus Flexion + Right Hip Extension uncovers cross-body sling breakdown undetectable isolated single-joint testing. Propulsion Vector prone terminal knee extension ankle plantarflexion inversion hip extension test against resisted contralateral lat extension identifies loss push-off force transmission.
- **Multi-Vector Scars:** See 8 vectors above + special topologies navel episiotomy scar-to-scar
- **Ligamentous Interlinks:** See inventory + ligament-to-ligament interlink protocol friction release compensating ligament 30sec proprioceptively stimulate lax ligament tap vibrate 15sec
- **Eyes & Cranio-Cervical:** See extraocular table 6 CN + clinical testing protocol + hyoid musculature supra infra deglutition swallowing reflex

## Master Decision Hierarchy (Clinical Flowchart Level 1-2-3 Priority)

```
STEP1 CLEAR SURGICAL SCARS & RECENT TRAUMAS L3 C-sections Appendectomies Portals Navel Episiotomies - If scar active it will continually reset all downstream corrections!
STEP2 CLEAR LIGAMENTOUS INSTABILITY L3 Check history ankle sprains ATFL/CFL pelvic trauma Sacrotuberous SIJ restore ligamento-muscular baseline
STEP3 ASSESS MASTER CRANIO-RESPIRATORY DRIVERS L2 Diaphragm Inhalation Exhalation challenge TMJ Masseter Temporalis Pterygoids & Hyoid system
STEP4 EVALUATE FUNCTIONAL KINETIC SUBSYSTEMS L2 POS AOS DLS Lateral Subsystem
STEP5 REFINE LOCAL AGONIST-ANTAGONIST / SYNERGIST PAIRS L1 Local muscle-to-muscle tests joint isolation vectors
STEP6 ADVANCED GAIT INTEGRATION & HOMEWORK PRESCRIPTION Multi-phasic gait pattern activation Enforce homework rule Release Culprit FIRST -> Activate Victim SECOND
Reverse TL: Touch painful hypertonic tissue Driver Scan inhibited muscles across chain Glute Max TVA Lower Trap When normally strong muscle breaks weak when touching driver found receiver Release driver -> Activate receiver
```

## Equipment & Taping (From Master Training Suite)

- **Kinesio Taping RockTape with NKT:** Facilitation inhibited Origin->Insertion 25-50% tension enhance spindle recruitment, Inhibition facilitated Insertion->Origin 0-15% light tension downregulate hyperactive spindle discharge, Decompression scar cross-pattern two intersecting strips 50% center tension over reactive surgical scar reduce fascial tension
- **IASTM Stainless steel:** 30-60deg bevel edge contact 30-60sec per reactive site aligned with 30-60s cerebellar learning window
- **Sensory Tuning Forks 128Hz & Proprioceptive Stimulators:** Applying 128Hz vibrating tuning fork over lax ligament e.g., ATFL or Sacrotuberous provides immediate high-frequency Pacinian corpuscle stimulation re-awakening proprioceptive afferents prior to motor re-education

## Certification Pathway (From Master Suite)

- Level1: 15 Contact Hours 3 Written Clinical Case Studies 1-on-1 Practical Examination In-Person or Zoom
- Level2: 15 Contact Hours 6 Written Case Studies Subsystems TMJ Diaphragm Perturbation 1-on-1 Practical covering whole-body functional chains
- Level3 Master: 15 Contact Hours 5 Written Case Studies Scars Ligaments Eyes Multi-Phasic Gait Advanced Master Practical
- Rubric: Patient Demographics Chief Complaint Age activity level onset prior treatments, Global Movement Screen Gait assessment postural deviations AROM limitations, NKT Protocol Breakdown Exact muscle tested weak -> Specific tissue challenged -> Immediate retest verification -> Identified Reactive Pair, Corrective Intervention Exact release modality duration 30-60sec -> Exact isolated isometric activation prescribed, Sequential Homework Clear evidence Release FIRST -> Activate SECOND prescription, 2-Week Objective Follow-Up Pre vs post outcome measures functional retest status pain score changes

## Video Library (From Video Library HTML)

- Live Seminar Workshop David Weinstock: Exact biomechanical vector positioning client coaching differentiating structural weakness from central neurological inhibition, leverage alignment forearm perpendicular limb lever arm eliminate shear, stabilizing hand contralateral ASIS gently stabilized prevent pelvic roll, engram reset moment test fails 30-60sec plasticity window open
- Frame-by-Frame 4-Step NKT Corrective Sequence Anterior Shoulder Impingement: Panel1 Baseline MMT Middle Trap isolated prone supine delayed recruitment spongy collapse, Panel2 TL Patient touches ipsilateral Pec Minor belly or clinician briskly rubs origin ribs 3-5 Retesting Middle Trap immediately rock solid strong Reactive Pair confirmed, Panel3 45-Second Manual Myofascial Release targeted deep tissue ischemic compression pin-and-stretch Pec Minor 45sec reset spindle, Panel4 Isolated Isometric Activation 4 reps 5sec isometric Middle Trap retraction hold burn restored engram into cerebellum
- Official Video Vault:
  - Low Back Pain & SI Joint Assessment: https://www.youtube.com/watch?v=2Xaix3lIK8g
  - IT Band Tightness Relieved by Glute Max: https://www.youtube.com/watch?v=pafd2pLLtCU
  - Exact Manual Muscle Testing Angles: https://www.youtube.com/watch?v=V_ubd0XhXOQ
  - Motor Control Theory & Neuroscience: https://www.youtube.com/watch?v=P1vsqv72_-s

## Integration with LFS Clinical Driver Console

- Comparable Sign = NKT muscle test binary weak/strong immediate retest >30% shift confirms driver. LFS retest comparator % change maps to NKT Weak->Strong shift
- Candidate muscles = Registry candidate muscles become NKT inhibited candidates. Isolation logic from registry e.g., prone knee flex 90 reduces hamstring to isolate glute = NKT precise vector rule
- Compensation watch = Registry compensation_watch list = NKT substitution watch trunk rotation Valsalva foot gripping shoulder hiking limb repositioning
- Dependency = Dependency result dependent_on_X = NKT reactive pair. If psoas TL makes glute max strong -> dependent_on_psoas
- Irritability = High irritability -> gentle release only avoid deep DN use sliders not tensioners use PNE BPS priority per golden rule release must be tolerable to allow plasticity window
- Safety Gate = Assessment only until confirmed = complete red flag + neuro + scar screening first
- Homework = Release FIRST -> Activate SECOND 2-3x/day 2-4 weeks same as LFS exercise integration CES 4-phase but strict sequence

## Instructions for Agent

When this skill invoked:

1. Load `data/nkt_detailed_protocols.json` for full protocols
2. If user describes weak muscle e.g., "glute med weak pelvic drop" -> identify classic synergistic dominance TFL -> Glute Med or reciprocal inhibition psoas -> glute max per taxonomy
3. Apply 6-step protocol: Test -> TL/Challenge (patient fingers on suspected driver scar TFL psoas upper trap suboccipital) -> Retest Weak->Strong confirms reactive pair -> Release driver 30-60sec (myofascial, IASTM, DN, scar mobilization along vector, tuning fork for lax ligament) -> Activate inhibited 3-5 reps x5sec isometric light-moderate -> Retest verify holds strong -> Prescribe homework Release FIRST Activate SECOND 2-3x/day 2-4 weeks
4. Use Master Decision Hierarchy: Always clear scars Level3 first, then ligamentous instability Level3, then cranio-respiratory drivers Level2 diaphragm TMJ hyoid, then kinetic subsystems Level2 POS/AOS/DLS/Lateral, then local Level1 agonist-antagonist synergist pairs, then advanced gait integration
5. For scar assessment, use 8-vector protocol N S E W CW CCW Comp Pinch and test which vector restores strength
6. For ligament assessment, use ligament inventory ATFL plantarflexion+inversion etc and ligament-to-ligament interlink protocol
7. For eyes, use extraocular table gaze vectors and oculo-cervical reflex protocol
8. For TMJ, use TMJ table and jaw clench deviation challenge
9. For equipment, suggest taping facilitation 25-50% Origin->Insertion inhibited, inhibition 0-15% Insertion->Origin facilitated, decompression scar cross-pattern 50% center, IASTM 30-60deg bevel 30-60sec, tuning fork 128Hz over lax ligament
10. Always include golden rule and neuroplastic window 30-60sec in output
11. Link to LFS console fields: CompensationObserved = substitution watch, DependencyResult = reactive pair, RetestComparator = Weak->Strong shift, Irritability determines release dosage gentle vs deep
12. Provide video links from official vault for technique demonstration

## Output Format

```json
{
  "NKT_Assessment": {
    "TestedMuscle": "Right Gluteus Medius",
    "Position": "Sidelying 30deg abduction slight extension slight ER",
    "Result": "Inhibited - spongy give, hip flexes internally rotates to use TFL",
    "Challenge": "Rub Right TFL belly 3sec",
    "Retest": "Immediately locks strong - REACTIVE PAIR CONFIRMED",
    "Diagnosis": "Synergistic Dominance TFL -> Glute Med",
    "Protocol": {
      "Release": "Myofascial release / foam rolling Right TFL 45sec IASTM 30-60deg bevel",
      "Activate": "Sidelying pure glute med abduction holds with wall slide to eliminate hip flexion 3-5 reps x5sec isometric",
      "RetestVerify": "Glute Med holds strong isolated",
      "Homework": "Release TFL foam roll 90sec FIRST -> Activate Glute Med 3x8 5sec hold SECOND 2x/day 2-4 weeks",
      "Taping": "Facilitation Glute Med Origin->Insertion 25-50% tension, Inhibition TFL Insertion->Origin 0-15% light",
      "RetestComparable": "Single leg stance pelvic drop <50% drop, walking pain distance +50%, retest after 2min"
    },
    "Level": "L1 local, but check L2 Lateral Subsystem QL involvement and L3 ATFL history",
    "MasterHierarchy": "Step1 scar check, Step2 ligament ATFL, Step3 diaphragm TMJ, Step4 subsystems POS AOS DLS Lateral, Step5 local pairs, Step6 gait",
    "VideoReference": "https://www.youtube.com/watch?v=pafd2pLLtCU IT Band Tightness Relieved by Glute Max"
  }
}
```

## Files

- Detailed protocols JSON: `data/nkt_detailed_protocols.json`
- Training HTMLs: `skills/nkt/docs/` 4 files
- This SKILL.md
