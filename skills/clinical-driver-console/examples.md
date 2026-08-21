# Examples - Clinical Driver Console

## Example 1: Lumbar Extension Weak - Thoracic Driver

**Patient:** PT-JED-001, 34M, LBP sitting >20min

**Step1 Region:** Lumbar

Dynamic Lookup returns:
- Directions: Flexion, Extension, Rotation, Sidebend
- Candidate: Multifidus, Erector, Glute Max

**Step2 Comparable:** 
- Direction: Extension, Position: Standing, Bias: End-range overpressure
- Finding: weak, Baseline: Pain 6/10 at 80%
- Compensation Watch: Lumbar shift left

**Step3 Driver Checks:**
- Red flags: cleared (asked 10 Qs)
- Neuro: cleared
- Adjacent: Thoracic T6-8 extension limited
- Compensation: shift left at 80% observed
- Dependency: dependent_on_thoracic_extension (when thoracic PA done, lumbar pain -40%)
- Irritability: medium
- Retest after thoracic PA + multifidus cue: 57% improvement

**AI Reasoning:**
- Primary: Lumbar ext motor control deficit L4-L5 multifidus inhibition with thoracic extension driver T6-8
- Confidence: 78%
- Safety: proceed_with_caution
- Manual: PA L4-L5 Grade II + Thoracic PA T6-8 Grade II
- Exercise: Prone multifidus 3x8 + foam roller thoracic 2x10

---

## Example 2: Shoulder Flexion Painful - Scapular Driver

**Patient:** 28F overhead pain

Region: Shoulder, Direction: Flexion, Position: Standing, Bias: With scapular assistance

FindingType: painful at 120deg, apprehensive

Lookup: Candidate serratus anterior, upper trap, deltoid. Isolation: Supine eliminates compensation. Compensation watch: scapular elevation, trunk lean.

Driver Checks: Red flags cleared, Neuro cleared, Adjacent thoracic extension limited, Dependency dependent_on_scapular_control (flexion improves 40deg with scapular assistance), Irritability medium

AI: Primary "Scapular upward rotation deficit - serratus inhibition leading to GH impingement. Thoracic driver"
Manual: Posterior GH glide Grade II + scapular assistance
Exercise: Serratus wall slides 3x8 + thoracic open book

Retest: flexion improves to 160deg pain 2/10 from 7/10 = 71% improvement

---

## Example 3: High Irritability - Safety Gate

Patient: 65M acute LBP, night pain, unable to sit 5min

Finding: Lumbar Flexion limited 30% pain 9/10

Driver Checks: Red flags not_tested yet, Irritability high

Safety Gate: assessment_only_until_confirmed -> NO manual therapy suggested

AI output: "Complete red flag screening first. Education + gentle breathing + avoid aggravation. No overpressure."

After red flags cleared but irritability high: Safety = gentle_assessment_and_education_only -> Grade I-II only, no sustained.

This is enforcement of your sheet's assessment_only_until_confirmed default.
