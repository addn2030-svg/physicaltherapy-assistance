---
name: ai-reasoning-engine
description: Generates Primary, Secondary, Third findings, confidence, safety gate, and integrates all checks into clinical reasoning.
version: 1.0.0
tags: [ai-reasoning, lfs, clinical-decision]
allowed-tools: [read, web_search]
---

# AI Reasoning Engine Skill

## Purpose
Takes all Inputs + Checks and generates structured clinical reasoning output. This is column 4 of your sheet.

### Inputs to reasoning:
- Patient + Case
- Comparable Sign (region, direction, position, bias, finding type)
- Driver Checks (red flags, neuro, adjacent, compensation, dependency, irritability, retest)

### Outputs:
- Primary Finding
- Secondary Finding
- Third Finding
- Confidence 0-100%
- Safety Gate
- Manual Therapy Option (delegated but summarized)
- Exercise Integration (delegated but summarized)
- Report Summary

## Reasoning Template (LFS Style)

You MUST use this structure - not free diagnosis:

**"What is the driver and what is the evidence that changing it changes the comparable sign?"**

Prompt logic:

```
Given:
- Region={CanonicalRegion}
- Direction={MovementDirection} Position={Position} Bias={Bias}
- FindingType={weak | painful | limited}
- Compensation={CompensationObserved}
- Dependency={DependencyResult}
- Adjacent={AdjacentRegionCheck}
- Irritability={medium}
- PreviousResponse={...}
- FunctionalTask={...}

Task: Generate findings using driver language:
"X driver with Y inhibition/compensations. Evidence: Z% change on retest when correcting [driver]."

Rules:
- Weak finding -> motor control / inhibition driver (e.g. multifidus, glute med, serratus)
- Painful at end-range -> joint driver (facetal, capsular) or nociceptive sensitization
- Limited early -> stiffness driver
- If Compensation observed + Dependent on adjacent -> primary is adjacent, secondary is primary region adaptation
- Confidence increases if: comparable sign clearly changes with driver correction >50%, dependency clear, no red flags.
- Confidence decreases if: multiple regions positive, poor retest, high irritability.
```

## Safety Gate Logic

```javascript
if (RedFlagsCleared !== 'cleared' || NeuroScreen === 'not_tested') {
  SafetyGate = 'assessment_only_until_confirmed';
} else if (RedFlagsCleared === 'positive_referral_needed') {
  SafetyGate = 'referral_only';
} else if (Irritability === 'high') {
  SafetyGate = 'gentle_assessment_and_education_only';
} else {
  SafetyGate = 'proceed_with_caution';
}
```

## Primary/Secondary/Third Examples

**Lumbar case:**
- Primary: "Lumbar extension motor control deficit - L4-L5 multifidus inhibition, with thoracic extension driver T6-8"
- Secondary: "Left glute med weakness allowing pelvic drop in single leg stance"
- Third: "Breathing strategy - apical, holding breath at end-range extension"

**Shoulder case:**
- Primary: "Scapular upward rotation deficit - serratus anterior inhibition, leading to GH impingement signs"
- Secondary: "Thoracic extension limitation driver"
- Third: "Rotator cuff anterior humeral translation lack of control"

## Confidence Scoring

- Start 50%
- +20% if comparable sign improves >50% with driver correction
- +10% if dependency result clear
- +10% if compensation matches logic
- -20% if multiple adjacent regions also positive
- -15% if irritability high and testing limited
- Clamp 20-95%

## Manual + Exercise Integration Summary

Call other skills but summarize here in one line each.

## Report Summary Template

```
S: 34M, LBP with sitting >20min, thoracic stiff
O: Comparable = Sitting lumbar flexion end-range P7/10 @80%. Red flags cleared, neuro intact, irritability medium. Adjacent check: thoracic ext limited. Dependency: lumbar pain decreased 40% after thoracic ext mob. Compensation: lumbar shift left.
A: Primary - Thoracic extension driver with lumbar flex sensitization; Sec - Lumbar multifidus inhibition; Confidence 78%; Safety cleared.
P: Thoracic PA T6-8 II, multifidus motor control prone + breathing, retest sitting flex. Home: thoracic extension over foam roller 2x10 + prone multifidus 3x10 + walking breaks q30min.
```

## Instructions for Agent

- Always require therapist confirmation: "Suggests, to be confirmed by therapist".
- Never output diagnosis like "disc herniation". Use driver language.
- Include % evidence.
- If SafetyGate !== proceed -> do NOT suggest Grade III+ manual therapy.
