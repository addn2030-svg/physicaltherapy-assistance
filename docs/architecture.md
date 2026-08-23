# Architecture - Physical Therapy Skills

## From Google Sheet to GitHub Skills

Your original sheet had 4 pillars + Dynamic Lookup:

```
Sheet Tab: Clinical_Driver_Console
- Instruction: Use this frontpage during examination. Select region first, then direction/position/bias from Directional_Test_Registry. Keep free text only for clinical nuance.
- Columns: Patient+Case | Comparable Sign | Driver Checks | AI Reasoning
- Rows: Patient_ID, Name, Therapist, Age/Gender, etc...
- Dynamic Lookup Panel: formulas filtering registry

Sheet Tab: Directional_Test_Registry (inferred)
- Holds master list of region -> direction -> position -> bias -> muscles -> isolation -> compensation -> retest
```

## Skills Architecture

Each sheet component becomes a discrete GitHub Skill with SKILL.md:

### 1. clinical-driver-console (Orchestrator)
- Loads template JSON
- Forces workflow: Region FIRST
- Validates against registry
- Calls other skills
- Generates final report

### 2. directional-test-registry (Database)
- Single source of truth
- Replaces sheet formulas with JSON lookup
- Implemented in src/engine/lookup.ts
- `getAvailableDirections(region)` = sheet FILTER formula

### 3. red-flag-screening (Safety)
- Was `Red flags cleared` cell with dropdown not_tested/cleared/positive
- Now full checklist + referral logic
- Controls Safety Gate -> `assessment_only_until_confirmed` default

### 4. neuro-screening
- Was `Neuro screen` cell
- Dermatome/myotome/reflex checklist per region

### 5. comparable-sign
- Was `Comparable sign selected` + `Retest comparator`
- Value object with baseline + retest % change logic
- Driver confirmation requires >50% change

### 6. driver-checks
- Was adjacent region check + compensation + dependency + irritability
- Implements LFS logic:
  - If correcting adjacent improves comparable >50% -> adjacent is driver
  - Dependency test isolates driver
  - Compensation observed from registry watch list

### 7. ai-reasoning-engine
- Was `Primary Finding`, `Secondary Finding`, `Confidence`, `Safety Gate`
- Prompt template that uses driver language not pathoanatomic diagnosis
- Confidence scoring rules

### 8. manual-therapy-selector
- Was `Manual Therapy Option`
- Gated by irritability + safety
- Returns technique + rationale + dosage + precautions

### 9. exercise-integration
- Was `Exercise Integration`
- Converts driver + inhibition into home program
- Phases: in-clinic -> home -> functional -> progression

### 10. report-generator
- Was `Report Summary`
- Generates SOAP + patient-friendly EN + AR (Jeddah) + referral + CSV export for sheet

## Data Flow

```
Therapist selects Region (Lumbar)
  -> directional-test-registry skill returns: Directions [Flexion, Extension...]
Therapist selects Direction (Extension) + Position (Standing)
  -> lookup returns: biases, muscles [Multifidus...], isolation logic, compensation watch [shift left...], retest rule
Therapist selects FindingType = weak, Baseline = P6/10
  -> comparable-sign skill saves baseline, marks Selected = true
Therapist completes Driver Checks:
  -> red-flag-screening -> must be cleared
  -> neuro-screening -> cleared
  -> driver-checks -> adjacent check thoracic limited, compensation observed, dependency dependent_on_thoracic
  -> Irritability = medium
  -> AI reasoning engine:
     - Safety gate = proceed_with_caution (since red flags cleared)
     - Confidence = 50 +20 retest +10 dependency +10 compensation = 78%
     - Primary = Thoracic extension driver + Lumbar multifidus inhibition
     - Calls manual-therapy-selector -> PA T6-8 Grade II
     - Calls exercise-integration -> multifidus activation + thoracic mobility
  -> Report generator -> SOAP + patient AR summary + CSV row to append to original sheet
```

## Tech Stack

- Skills: Markdown with frontmatter (GitHub Agent Skills spec)
- Data: JSON = replacement for Google Sheets tabs
- Engine: TypeScript (Node) + Python alternative (src/engine/*.py should mirror)
- CLI: src/console/index.ts = interactive frontpage
- Future: API wrapper for WhatsApp/Chat ID integration (Contact/Chat ID field in sheet)

## Deployment Options

### GitHub-native
- Push repo, enable Copilot Skills discovery
- Agent reads SKILL.md files to understand tools

### Local / Clinic
- npm run dev -> console
- Could wrap in Electron or use Google Sheets Apps Script to call API

### WhatsApp Integration (Contact / Chat ID field)
- Your sheet has Contact / Chat ID - suggests chat integration?
- Could add skill: `whatsapp-bridge` that receives patient ID and returns home program in Arabic

## Why Skills vs Sheet?

- Sheet = free text risk, no validation, no history, hard to scale muscles/isolation logic
- Skills = validated dropdowns, repeatable, audit trail (docs/reports), safety gate enforced, AI reasoning logged, extensible registry
- Still exportable to sheet CSV for therapists who love sheets

## Future Extensions

- Add directional registry for more biases: loaded, sustained, overpressure levels
- Add video links for exercises (exercise-integration skill could include YouTube)
- Add outcome tracking: Retest comparator history per Patient_ID
- Add language skill for Arabic/English auto-translation of reports

