# How to Push This to GitHub as Skills

You asked: "i want to make skills in GitHub for physicaltherapy assistance"

You now have a complete repo in `/home/user`.

## 1. Initialize Git and Push

```bash
cd /home/user
git init
git add .
git commit -m "Initial: LFS Clinical Driver Console - 9 PT Skills + engine + web console"
gh repo create physicaltherapy-assistance --public --source=. --remote=origin --push
# OR manually:
# git remote add origin https://github.com/YOURUSERNAME/physicaltherapy-assistance.git
# git branch -M main
# git push -u origin main
```

## 2. Enable GitHub Skills / Copilot

1. Go to repo Settings > Copilot > Enable Agent Skills
2. Skills are auto-discovered from `skills/*/SKILL.md`
3. In Copilot Chat (VS Code or github.com/copilot):
   ```
   @workspace Use clinical-driver-console skill to create new patient PT-JED-002 with lumbar extension driver
   ```
   Copilot will read SKILL.md instructions.

## 3. Use Locally

```bash
npm install
npm run dev
```

Will run demo patient from your sheet and generate report in `docs/reports/`

Python alternative for Colab:
```bash
python src/engine/reasoning.py
```

## 4. Use Web App

Open `index.html` directly, or deploy to GitHub Pages:

```bash
# In repo settings, enable Pages from main branch / root
# Then visit https://YOURUSERNAME.github.io/physicaltherapy-assistance/
```

The page implements:

- Dropdowns that enforce: Region first -> Direction -> Position -> Bias (from registry, not free text)
- Dynamic Lookup Panel: Available directions, positions, biases, candidate muscles, isolation logic, compensation watch, retest rule — exactly as your sheet's formula panel
- AI Reasoning that mirrors your 4th column

## 5. Integrate with Your Google Sheet

Your sheet link: https://docs.google.com/spreadsheets/d/1Te-dD6B9USOzURbTjMoZQgYtDeoygwR6QRGeHHGAzaQ/edit?gid=2026081801#gid=2026081801

The web app's "Copy CSV row for Sheet" button copies a row that matches your sheet columns:

Patient_ID, CanonicalRegion, SpecificJoint, Direction, Position, Bias, Angle/Load, FindingType, PainBehavior, RedFlags, Neuro, Adjacent, Compensation, Dependency, Irritability, PrimaryFinding, Confidence, SafetyGate, Manual, Exercise

Paste into sheet.

Full 2-way sync optional: I can add `skills/sheets-sync/SKILL.md` that uses Google Sheets API + service account to push JSON to sheet automatically.

## 6. What Files Are Which Skill?

```
skills/
  clinical-driver-console/  -> Your main frontpage skill (the 4 pillars)
  directional-test-registry/ -> Master database, replaces your sheet's Dynamic Lookup formulas
  red-flag-screening/       -> Implements Red flags cleared cell logic, Safety Gate assessment_only_until_confirmed default
  neuro-screening/          -> Neuro screen cell
  comparable-sign/          -> Comparable sign selected + Retest comparator logic (>50% = driver confirmed)
  driver-checks/            -> Adjacent region check, Compensation observed, Dependency result, Irritability
  ai-reasoning-engine/      -> Primary/Secondary/Third Finding + Confidence + Safety Gate + Report Summary
  manual-therapy-selector/  -> Manual Therapy Option, gated by irritability
  exercise-integration/     -> Exercise Integration
  report-generator/         -> SOAP + Patient EN + Patient AR (Arabic for Jeddah) + Referral letter + CSV export
```

Each has SKILL.md with frontmatter `name, description, version` following GitHub Agent Skills spec.

## 7. Customize for Your Clinic in Jeddah

- Add Arabic translations: Edit `report-generator` skill - already includes Arabic template, but you can expand
- Add new muscles/tests: Edit `data/directional_test_registry.json` - add region/direction (see CONTRIBUTING.md)
- Add WhatsApp skill: You have Contact / Chat ID field in sheet - I can build `whatsapp-bridge` skill to send home program via WhatsApp using Twilio/WhatsApp API.

## 8. Safety Disclaimer

Added LICENSE + warnings: Not a medical device, requires licensed therapist. Safety Gate defaults to assessment_only_until_confirmed until red flags cleared.

## Need More?

Tell me:

1. Do you want me to add Python notebook version for Google Colab?
2. Do you want Sheets auto-sync skill (Apps Script)?
3. Do you want video exercise library integration?
4. Do you want multi-therapist support (Therapist field in sheet)?

I can extend.
