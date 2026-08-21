---
name: report-generator
description: Generates clinical reports, SOAP notes, referral letters, and patient-friendly summaries from console data.
version: 1.0.0
tags: [report, soap, documentation]
---

# Report Generator Skill

## Purpose
Takes full Clinical Driver Console state and outputs:

- SOAP Note (therapist-facing)
- Patient Summary (lay friendly, English + Arabic option for Jeddah context)
- Referral Letter if needed
- Data export JSON/CSV for sheet

## Input
Full console JSON.

## Outputs

### 1. SOAP Note

```
S: Patient_ID, Age/Gender, Chief complaint, Functional task, Previous response, Irritability
O: Comparable Sign: [Region Direction Position Bias] - Baseline. Red flags: cleared/not_tested. Neuro: intact/deficit. Adjacent: results. Compensation: observed. Dependency: result. Retest: % change.
A: Primary Finding, Secondary, Third, Confidence%, Safety Gate
P: Manual Therapy Option, Exercise Integration, Retest plan, Follow-up, Education, 24hr monitoring advice
```

### 2. Patient Friendly Summary (English)

```
Your main issue seems to be related to [region] moving into [direction]. Today we tested [comparable sign] and it was [painful/weak]. Good news - red flags cleared. When we improved [driver] mobility/control, your test improved by [%]. Plan: gentle hands-on + 3 home exercises to hold improvement.
```

### 3. Patient Friendly Summary (Arabic) - for Jeddah

```
ملخص حالتك: المشكلة الأساسية مرتبطة بـ [المنطقة] في حركة [الاتجاه]. قمنا بفحص [الاختبار] وكانت النتيجة [ألم/ضعف]. عند تحسين مرونة العمود الفقري الصدري، تحسنت حركتك بنسبة [%]. الخطة: علاج يدوي لطيف + 3 تمارين منزلية للحفاظ على التحسن.
```

### 4. Referral Letter (if positive red flag)

```
To: Physician
Re: Patient PT-JED-001 - requires medical review due to positive red flag screening: [details]
Findings: ...
```

### 5. Data Export for Google Sheet

Exports as CSV row matching your sheet structure:

`Patient_ID, CanonicalRegion, Direction, Position, Bias, FindingType, RedFlags, Neuro, Adjacent, Compensation, Dependency, Irritability, PrimaryFinding, Confidence, SafetyGate, Manual, Exercise, Report`

## Instructions for Agent

- Always generate SOAP + Patient Summary.
- If Arabic requested (location SA), generate Arabic version.
- Keep reports assessment-only language unless safety cleared: "suggests driver, to be confirmed".
- Save to `docs/reports/PT-JED-001-YYYY-MM-DD.md`

## Example

Input: Lumbar extension weak, thoracic driver, medium irritability, 57% improvement after thoracic mob.

Output SOAP:

```
S: 34/M, c/o LBP sitting >20min, worse prolonged driving. Prev: massage temporary relief.
O: Comp= Sitting lumbar flexion end P7/10 @80% ROM. Red flags cleared, neuro intact symm, irrit medium. Adjacent: Thoracic ext limited T6-8. Comp= lumbar shift left @80%. Dep= lumbar pain -40% after thoracic PA Grade II.
A: Prim - Thoracic ext stiffness driver + lumbar flex sensitization; Sec - Multifidus inhibition L4-5; Conf 78%; Safety: proceed with caution
P: Thoracic PA T6-8 2x30s GII + Prone multifidus facilitation breathing. Home: foam roller ext 2x10, prone multifidus 3x8 5s, sit break q30m + 5 ext. Retest sitting flex, monitor 24hr. Educ: posture, breathing. FU 3 days.
```
