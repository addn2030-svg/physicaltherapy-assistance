# Use Physical Therapy Skills in VS Code — Complete Guide

Your repo is deployed at **https://github.com/addn2030-svg/physicaltherapy-assistance** and ready for VS Code.

## 1. Clone in VS Code

### Option A: Clone via VS Code UI
1. Open VS Code
2. `Ctrl+Shift+P` → `Git: Clone` → paste `https://github.com/addn2030-svg/physicaltherapy-assistance.git`
3. Open folder
4. VS Code will prompt to install recommended extensions (Copilot, Copilot Chat, Python, Live Server) — click Install

### Option B: Terminal
```bash
git clone https://github.com/addn2030-svg/physicaltherapy-assistance.git
cd physicaltherapy-assistance
code .
```

## 2. Install Dependencies

Open terminal in VS Code (`Ctrl+``):

```bash
npm install
# Python engine (optional)
pip install -r requirements.txt  # if you create one, or just python3 is enough
```

## 3. How GitHub Skills Work in VS Code Copilot

All skills are in `skills/*/SKILL.md` with frontmatter `name, description`. Copilot Chat auto-discovers them when `github.copilot.chat.skills.enabled=true` (already set in `.vscode/settings.json`).

### Enable Copilot Skills
1. Install extensions: `GitHub Copilot` + `GitHub Copilot Chat`
2. Sign in to GitHub (must be same account addn2030-svg)
3. Check `.vscode/settings.json` has:
```json
"github.copilot.chat.skills.enabled": true
```

### Use Skills via Copilot Chat

Open Copilot Chat (`Ctrl+Alt+I` or sidebar chat icon):

#### Example 1: Clinical Driver Console
```
@workspace Use clinical-driver-console skill to create new patient PT-JED-015

Chief complaint: LBP sitting >20min
Functional task: Office sitting
Region: Lumbar
Direction: Extension
Position: Standing
Finding Type: weak
Irritability: medium
Red flags: cleared
Neuro: cleared
Adjacent: Thoracic T6-8 limited
Compensation: shift left
Dependency: dependent_on_thoracic_extension
Retest: 57% after thoracic PA
```

Copilot will:
- Read `skills/clinical-driver-console/SKILL.md`
- Enforce workflow Region first → Direction/Position/Bias from registry
- Call `directional-test-registry` skill to lookup available directions, candidate muscles, isolation logic, compensation watch, retest rule
- Validate against `data/directional_test_registry.json`
- Generate AI reasoning

#### Example 2: Techniques Directory (32 techniques)
```
@workspace Use techniques-directory skill to find techniques for Lumbar extension weak medium irritability

Filter for Ali Marzok methods
```

Copilot reads `data/comprehensive_manual_therapy_directory.json` and returns top techniques with dosage, retest, safety.

#### Example 3: NKT Detailed (Your uploaded modules)
```
@workspace Use nkt skill to assess Right Gluteus Medius weak pelvic drop

Tested: Right Glute Med 30deg abduction slight extension ER -> inhibited
Challenge: Rub Right TFL
Retest: locks strong
History: C-section scar 2021, ATFL sprain 2016
```

Copilot will:
- Load `data/nkt_detailed_protocols.json` (v3 enhanced)
- Apply taxonomy: Synergistic Dominance TFL→Glute Med
- Apply 6-step protocol: Test→TL→Retest→Release TFL 45sec→Activate Glute Med 3-5x5sec→Homework Release FIRST Activate SECOND 2-3x/day 2-4 weeks
- Check Master Decision Hierarchy: Clear scars L3 first (C-section 8-vector N/S/E/W/CW/CCW/Comp/Pinch), then ligaments ATFL, then cranio-respiratory, then subsystems POS/AOS/DLS/Lateral
- Suggest taping facilitation 25-50% Origin→Insertion, IASTM 30-60deg bevel, tuning fork 128Hz over lax ATFL
- Return video links: https://www.youtube.com/watch?v=pafd2pLLtCU

#### Example 4: Manual Therapy Selector v2 with Crosswalk
```
@workspace Use manual-therapy-selector skill

Primary Finding: Lumbar extension motor control deficit L4-L5 multifidus inhibition with thoracic driver
Region: Lumbar
Finding: weak
Irritability: medium
Safety: proceed_with_caution
```

Returns:
- Primary: Maitland PA T6-8 Grade II + NKT TFL release + Glute Med activation
- Secondary: Anatomy Trains SBL release if chain
- Taping: Glute med facilitation 25%
- ANF if inflammation
- All from directory with dosage per irritability

#### Example 5: Report Generator
```
@workspace Use report-generator skill to generate SOAP for PT-JED-001 with Arabic summary for Jeddah patient
```

Generates SOAP + Patient EN + Patient AR + CSV row for your Google Sheet.

## 4. Use Tasks (Pre-configured)

VS Code → `Terminal` → `Run Task`:

- **PT Console: Run Demo Patient** (default `Ctrl+Shift+B`) → Runs `src/console/index.ts` demo from your sheet, generates report in `docs/reports/`
- **PT: Validate Skills Frontmatter** → Checks all SKILL.md have name/description
- **PT: Test NKT Engine** → Runs Python `techniques.py` + `reasoning.py`
- **PT: Open Web Console** → Starts live-server for `index.html` (3 tabs: Console, Directory 32 techniques, Integration Map)
- **PT: Search Techniques (Lumbar weak)** → Python search demo

## 5. Use Web Console Inside VS Code

1. Right-click `index.html` → `Open with Live Server` (or Run Task Open Web Console)
2. VS Code will open browser at `http://127.0.0.1:5500`
3. Features:
   - Dropdowns enforce Region first → Direction/Position/Bias from registry (replaces sheet FILTER formulas)
   - Dynamic Lookup Panel shows candidate muscles, isolation logic, compensation watch, retest rule
   - Auto-suggests techniques from 32 directory based on Finding Type + Region + Irritability
   - Generate AI Reasoning → SOAP EN + AR + CSV export button for your Google Sheet
   - Directory Tab: Search 32 techniques by `Mulligan`, `Ali Marzok`, `weak`, `Lumbar`, filter by evidence A/B/C, click card to expand dosage, retest, safety, integration
   - Integration Tab: Crosswalk map Finding Type → Techniques

## 6. Use Python Engine in VS Code

Open `src/engine/techniques.py` or `reasoning.py` → Click Run button (Python extension)

Or terminal:
```bash
python3 src/engine/techniques.py
# Total techniques: 32, Lumbar weak medium list, Ali Marzok methods

python3 src/engine/reasoning.py
# Generates PrimaryFinding etc for demo patient
```

## 7. Use TypeScript Engine

Terminal:
```bash
npx ts-node src/engine/lookup.ts
# Demo lookup panel for Lumbar Extension Standing

npx ts-node src/console/index.ts
# Full demo patient flow + saves report to docs/reports/PT-JED-001-YYYY-MM-DD.md + demo_patient_completed.json
```

## 8. How to Add New Techniques / Patients in VS Code

### Add new test to registry:
Edit `data/directional_test_registry.json` → Add region/direction per `CONTRIBUTING.md` → Copilot will auto-use new entry.

### Add new patient JSON:
Duplicate `data/clinical_driver_template.json` → Fill fields → Run `src/console/index.ts` with custom file or use Copilot Chat to process it.

### Add new technique to directory:
Edit `data/comprehensive_manual_therapy_directory.json` → Follow structure in `skills/techniques-directory/SKILL.md` → Run task Validate.

## 9. GitHub Copilot Chat Custom Instructions (Optional)

Create `.github/copilot-instructions.md` (already can be added):

```markdown
You are a physical therapy assistant for LFS Clinical Driver Console.

- Always select CanonicalRegion FIRST before direction.
- Validate all comparable sign inputs against data/directional_test_registry.json.
- Enforce Safety Gate: assessment_only_until_confirmed until red flags cleared + neuro cleared.
- Use techniques-directory skill with 32 techniques, crosswalk finding type to technique, dosage per irritability.
- For weak finding, use NKT skill 6-step protocol: Test->TL->Retest Weak->Strong = Reactive Pair Confirmed -> Release 30-60sec -> Activate 3-5x5sec -> Homework Release FIRST Activate SECOND 2-3x/day 2-4 weeks.
- For Ali Marzok methods, highlight fascia as sensory organ and visceral reflex inhibition.
- Always include retest rule and 24hr monitoring in output.
- Generate SOAP + Patient EN + Patient AR for Jeddah context.
- Never diagnose, use driver language: suggests, to be confirmed by therapist.
```

Then Copilot will follow these rules automatically.

## 10. Deploy Updates from VS Code

After editing in VS Code:

```bash
git add .
git commit -m "Update NKT protocols / add patient"
git push origin main
# Pages auto-redeploys at https://addn2030-svg.github.io/physicaltherapy-assistance/
```

If you have new token with workflow scope, workflow file `.github/workflows/skill-validation.yml` will also validate on push.

## 11. Quick Prompt Library for VS Code Copilot Chat

Copy-paste these:

```
@workspace Use clinical-driver-console skill: New patient 45F shoulder flexion painful 120deg apprehensive, region Shoulder, direction Flexion, position Standing, bias with scapular assistance, finding painful, irrit medium, red flags cleared, neuro cleared, adjacent thoracic T4-6 limited, comp scapular elevation, dependency dependent_on_scapular_control, retest 40deg improvement with scapular assistance

@workspace Use nkt skill: Patient with C-section scar 2021 + right ATFL sprain 2016 + chronic LBP, test TVA inhibited, challenge scar TL -> TVA strong, test glute med inhibited, challenge TFL -> glute med strong, apply master hierarchy scar first then ligament

@workspace Use techniques-directory skill: Search for visceral techniques for Lumbar psoas weak + lower abdominal tender + IBS history, include Ali Marzok approach dosage medium irritability

@workspace Use manual-therapy-selector skill for High irritability lumbar flexion limited with central sensitization non-mechanical night pain, include PNE BPS options

@workspace Use report-generator skill: Generate report for last patient with CSV row for Google Sheet https://docs.google.com/spreadsheets/d/1Te-dD6B9USOzURbTjMoZQgYtDeoygwR6QRGeHHGAzaQ/edit?gid=2026081801
```

## 12. Troubleshooting

- Copilot doesn't see skills: Ensure `.vscode/settings.json` has skills.enabled true, reload VS Code, ensure repo root has `skills/` folder.
- Web console not loading JSON: Use Live Server, not file:// — fetch requires http.
- Python not found: Install Python extension, select interpreter `Ctrl+Shift+P` → `Python: Select Interpreter`.
- Push rejected workflow: Token needs workflow scope — add workflow file via GitHub UI manually.

---

You now have full VS Code integration: Tasks, settings, recommended extensions, prompt library, and Pages deployment.

Open `index.html` with Live Server to see v3 NKT enhancements live.
