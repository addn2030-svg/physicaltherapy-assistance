# Contributing to Physical Therapy Skills

## How to Add New Tests to Registry

Edit `data/directional_test_registry.json`:

Example: Add Cervical Flexion-rotation test for C1-C2

```json
{
  "direction": "Flexion-Rotation",
  "positions": ["Sitting", "Supine"],
  "biases": ["To left", "To right", "Isolated C1-C2"],
  "candidate_muscles": ["Longus capitis"],
  "isolation_logic": "Fully flex cervical to lock lower cervical, then rotate to isolate C1-C2",
  "compensation_watch": ["Upper trap elevation", "Eye movement"],
  "retest_rule": "Should improve >15deg after manual therapy"
}
```

Then PR.

## How to Add New Skill

Create `skills/your-skill-name/SKILL.md` with frontmatter:

```
---
name: your-skill-name
description: what it does
version: 0.1.0
---
```

Add engine logic in src/engine/ if needed.

## Testing

```bash
npm run dev  # runs demo patient
python src/engine/reasoning.py
```

## Safety First

All contributions must respect Safety Gate. Never remove red flag checks.

