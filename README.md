# Physical Therapy Assistance - GitHub Skills v2

A modular, AI-augmented clinical reasoning system based on the **LFS Clinical Driver Console** + **Comprehensive International Manual Therapy and Rehabilitation Techniques Directory (32 techniques)**. This repo turns your Google Sheet workflow into reusable **GitHub Skills** (Copilot / Agents compatible).

> Original Sheet: [Clinical_Driver_Console](https://docs.google.com/spreadsheets/d/1Te-dD6B9USOzURbTjMoZQgYtDeoygwR6QRGeHHGAzaQ/edit?gid=2026081801#gid=2026081801) - Clinical Driver Console

> **NEW v2**: Integrated your requested directory: OMPT (Mulligan MWM, McKenzie MDT, Maitland, Kaltenborn-Evjenth, Cyriax), Neurodynamics, Taping, Fascial/Myofascial (Anatomy Trains, MFR, FM Stecco, Dry Needling Trigger, Dry Needling Fascial Ali Marzok Method, FDM), Visceral (Ali Marzok Approach, Barral, Craniosacral), Neuromuscular (NKT, PNF, Motor Control, SFMA), ANF, Therapeutic/Corrective Exercise, Specialized Rehab (Vestibular, Cardio-pulm, Neuro, Gait, Balance, Sports), Pain Science (PNE, Pain Management, BPS). See `data/comprehensive_manual_therapy_directory.json`

## What does it do?

During examination:

1.  **Select Region first** (e.g., Lumbar, Cervical, Shoulder, Hip, Knee)
2.  Then select **Direction / Position / Bias** from the `Directional_Test_Registry`
3.  Keep free text only for clinical nuance
4.  Run **Driver Checks** (Red flags, Neuro screen, Adjacent region)
5.  Get **AI Reasoning** (Primary/Secondary Finding, Confidence, Safety Gate, Manual Therapy + Exercise Integration, Report Summary)

## Repository Structure v2

```
├── skills/                          # GitHub Agent Skills (SKILL.md format)
│   ├── clinical-driver-console/     # Main frontpage skill - 4 pillars
│   ├── directional-test-registry/   # Lookup: region -> directions -> positions -> bias
│   ├── techniques-directory/        # NEW v2 - Searchable 32 techniques directory
│   ├── red-flag-screening/          # Safety gate
│   ├── neuro-screening/             # Neuro screen
│   ├── comparable-sign/             # Comparable sign finder & tracker
│   ├── driver-checks/               # Adjacent region, compensation, dependency, irritability
│   ├── ai-reasoning-engine/         # Primary/Secondary/Third finding logic
│   ├── manual-therapy-selector/     # Manual therapy options v2 with crosswalk to 32 techniques
│   ├── exercise-integration/        # Exercise prescription integrator (CES 4-phase)
│   └── report-generator/            # SOAP note / summary generator
├── src/
│   ├── engine/                      # TypeScript/Python reasoning + techniques lookup engine
│   │   ├── lookup.ts
│   │   ├── reasoning.ts/.py
│   │   ├── techniques.ts/.py        # NEW v2 - 32 techniques search
│   │   └── safety.ts
│   ├── models/                      # Type definitions
│   └── console/                     # Clinical Driver Console implementation
├── data/
│   ├── directional_test_registry.json
│   ├── clinical_driver_template.json
│   ├── comprehensive_manual_therapy_directory.json  # NEW v2 - 32 techniques
│   └── ...
└── docs/
    ├── COMPREHENSIVE_DIRECTORY.md   # NEW v2 - Mapping of your list to IDs
    ├── architecture.md
    ├── workflow.md
    └── GOOGLE_SHEET_MAPPING.md
```

## Quick Start

### Option 1: Use as GitHub Skills (Copilot)

1. Push this repo to GitHub: `physicaltherapy-skills`
2. In Copilot Chat: `@skills Use clinical-driver-console skill`
3. Skills are auto-discovered from `skills/*/SKILL.md`

### Option 2: Run Local Console Engine

```bash
npm install
npm run dev
# or
python src/engine/reasoning.py --patient demo
```

### Option 3: Use as GitHub Pages App

```bash
npm run build
```

The console will be at `https://<username>.github.io/physicaltherapy-skills`

## The 4 Pillars (from your sheet)

| Pillar | Input | Status | Output |
|---|---|---|---|
| **1. Patient + Case** | Patient_ID, Name, Therapist, Age/Gender, Contact, Chief complaint, Functional task, Previous response | - | - |
| **2. Comparable Sign** | Canonical Region, Specific Joint/Segment, Movement Direction, Position, Bias/Range Gate, Angle/load, Finding Type (weak/painful/limited), Pain behavior | - | - |
| **3. Driver Checks** | - | Red flags cleared, Neuro screen, Adjacent region check, Compensation observed, Dependency result, Irritability, Comparable sign selected, Retest comparator | - |
| **4. AI Reasoning** | - | - | Primary Finding, Secondary Finding, Third Finding, Confidence, Safety Gate (assessment_only_until_confirmed), Manual Therapy Option, Exercise Integration, Report Summary |

## Safety

- `Safety Gate` defaults to `assessment_only_until_confirmed` until Red Flags + Neuro Screen = cleared.
- All manual therapy suggestions are gated by irritability and safety.

## Contributing

Add new regions/directions in `data/directional_test_registry.json` and PR.

## License

MIT - Clinical use requires licensed therapist oversight. Not a medical device.

---
Created in Jeddah, SA | LFS Model
