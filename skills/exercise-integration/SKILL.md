---
name: exercise-integration
description: Converts findings into exercise prescription - motor control, strength, mobility, and functional integration dosed by irritability.
version: 1.0.0
tags: [exercise, prescription, rehab]
---

# Exercise Integration Skill

## Purpose
Takes Primary Finding (driver + inhibition) and generates exercise program that integrates manual therapy gains.

### Principle: Manual therapy window -> Exercise to hold it.

## Classification by Finding

### 1. Motor Control Deficit (weak)
- Stage1: Isolated activation low load (e.g. prone multifidus 10% MVC)
- Stage2: Integration with functional task (e.g. multifidus + sitting posture)
- Stage3: Load / endurance / functional (e.g. single leg stance + multifidus)

Dosage low irritability: 3x10-15, 2x/day, low load
Medium: 2x8-10, 1-2x/day, focus quality
High: 1-2x5 gentle activation, many times/day, avoid fatigue

### 2. Stiffness / Mobility deficit
- Mobility exercise for driver region
- Example thoracic extension: foam roller extension 2x10 breath + reach
- Followed by control exercise to maintain new range

### 3. Compensation Pattern
- Inhibit overactive (stretch, soft tissue) + Facilitate inhibited

## Examples

**Lumbar extension driver + multifidus weak (medium irrit):**
```
Immediate (in clinic): Prone multifidus activation with breathing 2x5, then sitting extension with self-overpressure
Home Program:
1. Thoracic extension mobility - foam roller 2x10 slow with exhale
2. Prone multifidus - knee flex 90deg, gentle draw in + lift 3x8 each, hold 5sec
3. Sitting posture breaks - q30min stand + 5x lumbar extensions
4. Walking 10min 2x/day
Retest cue: Check sitting flexion pain after each
```

**Shoulder serratus inhibition:**
```
1. Serratus wall slides with exhale 3x8
2. Scapular setting in sidelying 2x10
3. Thoracic extension open book 2x10
4. No overhead heavy until retest >50% improved
```

## Output Format

```json
{
  "ExerciseIntegration": {
    "InClinic": ["PA T6-8 -> immediate scapular setting + thoracic extension"],
    "HomeProgram": [
      {"Exercise": "Prone multifidus activation", "Dosage": "3x8, 5sec hold", "Cue": "Breathe, gentle lift"},
      {"Exercise": "Thoracic foam roller extension", "Dosage": "2x10", "Cue": "Exhale on extension"}
    ],
    "FunctionalIntegration": "Link to chief complaint: Every 30min sitting -> 3 extensions + posture reset",
    "ProgressionCriteria": "When comparable sign >50% improved and pain <3/10, progress to loaded",
    "IrritabilityAdjustment": "Medium -> avoid end-range fatigue, quality over quantity"
  }
}
```

## Integration with Safety

- If SafetyGate != proceed -> only gentle activation + education, no loaded.
- Always include retest rule and 24hr pain monitoring.
