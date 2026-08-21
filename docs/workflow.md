# Clinical Workflow - How to Use Skills in Real Examination

> Instruction from sheet: Use this frontpage during examination. Select region first, then direction/position/bias from Directional_Test_Registry. Keep free text only for clinical nuance.

## Step-by-Step (5 minutes per patient typical)

### 0. Before Patient - Create Case

```
In Copilot Chat:
@skills clinical-driver-console create new patient
- Enter Patient_ID: PT-JED-015
- Chief complaint: "LBP sitting >20min"
- Functional task: "Office work"
- Previous response: "Massage helps 1 day"
```

Skill creates JSON from template.

### 1. Region First

**Ask:** "Where is comparable sign most relevant?"

Select from: Cervical, Thoracic, Lumbar, Sacroiliac, Shoulder, Hip, Knee, Ankle...

**Skill action:** Calls directional-test-registry

```
> Region: Lumbar
Available directions: Flexion, Extension, Rotation, Sidebend, Combined
Candidate general: Mull...
```

### 2. Direction + Position + Bias

Therapist picks directional tests:

```
Direction: Extension
Position: Standing
Bias: End-range overpressure
Angle/load: 80% ROM Pain 6/10

Registry returns:
- Candidate muscles: Multifidus L4-L5, Erector, Glute Max
- Isolation logic: Prone knee flex 90deg reduces hamstring -> isolates glute
- Compensation watch: Lumbar shift left, Hip substitution, Breath holding
- Retest rule: Retest standing extension + sitting flexion after correction needs >50%
```

You test and record Finding Type: weak / painful / limited...

### 3. Driver Checks (Status)

You must fill:

- **Red flags cleared**: invoke red-flag-screening skill - asks 10 questions. Must be cleared.
- **Neuro screen**: invoke neuro-screening - check sensory/motor/reflex
- **Adjacent region check**: Check region above/below. Example: If lumbar extension limited, check thoracic extension, hip extension, SIJ.
- **Compensation observed**: Observe from watch list. Example: "Shift left at 80%"
- **Dependency result**: Does blocking adjacent change comparable?
  - Example test: "Hold lumbar neutral and retest hip extension" or "Cue thoracic extension then retest lumbar extension pain"
  - Record: independent vs dependent_on_X
- **Irritability**: low/medium/high based on pain behavior, night pain, easing time.
- **Comparable sign selected**: true/false
- **Retest comparator**: after mini intervention, retest.

### 4. AI Reasoning (Output)

After checks, call ai-reasoning-engine

```
Input: all above
Output:
- Primary Finding: "Lumbar extension motor control deficit L4-L5 multifidus inhibition with thoracic extension driver T6-8"
- Secondary: "Left glute med weakness"
- Third: "Apical breathing"
- Confidence: 78%
- Safety Gate: proceed_with_caution (since red flags cleared)
- Manual: "PA T6-8 Grade II + multifidus facilitation"
- Exercise: "3 home exercises"
- Report: SOAP
```

Confidence logic:
- >50% retest improvement = true driver
- <30% = maybe not driver, check elsewhere.

### 5. Safety Gate Enforcement

From your sheet `Safety Gate: assessment_only_until_confirmed`

- If red flags = not_tested -> skill blocks manual therapy suggestions, returns "Complete screening first"
- If red flags = positive -> "referral_only"
- If irritability high -> gentle only

This replaces human forget risk.

### 6. Manual + Exercise

Skills manual-therapy-selector and exercise-integration generate dosed program based on irritability.

Medium irrit example:
```
Manual: PA unilateral L4-L5 Grade II 2x30sec + Thoracic PA T6-8 Grade II
Dosage: 30sec x3, retest after, monitor 24hr pain
Alternative: If not tolerated, prone press-up breathing

Exercise:
In clinic: Prone multifidus 2x5 + thoracic extension
Home:
1. Foam roller thoracic ext 2x10 slow with exhale
2. Prone multifidus knee flex 90deg lift 3x8 5s hold
3. Sitting microbreaks q30min + 5 lumbar ext
Functional: Link to sitting >20min
Progression: When comparable >50% improved and pain <3/10
```

### 7. Report + Documentation

report-generator skill creates:

- SOAP note for EMR
- Patient-friendly English explanation
- Patient-friendly Arabic (for Jeddah context)
- CSV row to paste back into Google Sheet if you still want sheet backup
- JSON saved docs/reports/PT-JED-015-2026-08-21.md

Patient Arabic example:
```
ملخص: مشكلتك الأساسية مرتبطة بمفصل أسفل الظهر في حركة المد. تحسنت نسبة 57% عند تحسين مرونة منتصف الظهر. الخطة: علاج يدوي لطيف + 3 تمارين.
```

### 8. Next Visit

Load previous JSON, compare RetestComparator history, progress exercises.

## Integration with Existing Sheet

If you still want Google Sheet backup:

- Export demo_patient_completed.json -> CSV
- Or use Apps Script to call engine API (future skill: sheets-sync)

## Tips for Therapists (LFS)

- Always select region FIRST before direction - prevents victim vs driver confusion
- Keep free text only for nuance: e.g. "Patient anxious about bending after episode"
- Use comparables that matter to patient: If complaint is sitting >20min, comparable should be sitting flexion not prone
- Irritability determines dosage: low can go aggressive, high be gentle and many mini breaks
- Retest everything: If no change after driver correction, driver wrong - go back to registry.

