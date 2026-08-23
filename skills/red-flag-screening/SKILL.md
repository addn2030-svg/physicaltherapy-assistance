---
name: red-flag-screening
description: Safety first screening for red flags. Must be cleared before any manual therapy or exercise recommendation. Implements Safety Gate logic.
version: 1.0.0
tags: [safety, red-flags, screening, physicaltherapy]
---

# Red Flag Screening Skill

## Purpose
Implements `Red flags cleared` check = `not_tested | cleared | positive_referral_needed`

If `positive` -> Safety Gate = `referral_only`, block all treatment suggestions.

## Screening Checklist (Evidence-based)

### Systemic / Medical
- Unexplained weight loss, fever, night pain unrelieved
- History of cancer
- Recent significant trauma
- Age >55 with new onset pain
- IV drug use, immunosuppression
- Constant progressive non-mechanical pain

### Region Specific

**Lumbar:**
- CES signs: saddle anesthesia, bladder/bowel changes, sexual dysfunction
- Severe/progressive neuro deficit
- Abdominal aortic aneurysm signs

**Cervical:**
- Myelopathy signs (hand clumsiness, gait disturbance, Hoffmann, hyperreflexia)
- Vertebral artery insufficiency / cranial nerve signs
- Upper cervical instability risk (RA, Down's, trauma)

**Thoracic:**
- Visceral referral patterns

**All MSK:**
- Fracture signs (major trauma, osteoporosis risk)

## Instructions for Agent

When invoked:

1. Load patient age, complaint, history
2. Ask structured questions:
   - "Any bladder/bowel changes? Saddle numbness?"
   - "Fever, chills, unexplained weight loss?"
   - "History of cancer?"
   - "Was there significant trauma?"
   - "Pain worse at night? Unrelieved by rest?"
3. If any positive -> set `RedFlagsCleared = positive_referral_needed`, output referral script.
4. If all negative -> `cleared`
5. If incomplete -> remain `not_tested` and keep Safety Gate as `assessment_only_until_confirmed`

## Output Format

```json
{
  "RedFlagsCleared": "cleared",
  "FlagsChecked": ["CES", "cancer", "infection", "fracture"],
  "QuestionsAsked": 6,
  "SafetyGateAction": "proceed_with_neuro_screen",
  "ReferralNote": ""
}
```

If referral needed:

```json
{
  "RedFlagsCleared": "positive_referral_needed",
  "SafetyGateAction": "referral_only",
  "ReferralNote": "Positive CES screen - requires immediate medical referral. Documented: patient reports..."
}
```

## Integration

Clinical Driver Console must check this BEFORE calling ai-reasoning-engine.
If `not_tested` -> Block manual therapy, allow assessment only.
