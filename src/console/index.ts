/**
 * Clinical Driver Console - CLI entry
 * npm run dev -> starts interactive console
 * 
 * This implements the Google Sheet frontpage as code
 */

import * as fs from 'fs';
import * as path from 'path';
import { lookupForRegionDirection } from '../engine/lookup';
import { generateFindings } from '../engine/reasoning';
import { evaluateRedFlags, evaluateNeuroScreen, getSafetyGate } from '../engine/safety';

const templatePath = path.join(__dirname, '../../data/clinical_driver_template.json');
let template = JSON.parse(fs.readFileSync(templatePath, 'utf-8'));

console.log(`
==============================================
LFS Clinical Driver Console - GitHub Skills Edition
==============================================
Instruction: Use this frontpage during examination.
Select region first, then direction/position/bias from Directional_Test_Registry.
Keep free text only for clinical nuance.

Current template loaded from data/clinical_driver_template.json
`);

// Demo patient to show workflow
const demoInput = {
  patient_case: {
    Patient_ID: 'PT-JED-001',
    Patient_Name: 'Ahmed',
    Therapist: 'Dr. Example',
    Age_Gender: '34/M',
    Contact_Chat_ID: 'chat-001',
    ChiefComplaint: 'LBP with sitting >20min, eases standing',
    FunctionalTask: 'Sitting for work, driving',
    PreviousResponse: 'Massage temporary relief, core exercises aggravate when high load'
  },
  comparable_sign: {
    CanonicalRegion: 'Lumbar',
    SpecificJoint_Segment: 'L4-L5',
    MovementDirection: 'Extension',
    Position: 'Standing',
    Bias_RangeGate: 'End-range overpressure',
    Angle_Load: '80% ROM pain 6/10',
    FindingType: 'weak',
    PainBehavior: 'Pain in extension, eases with repeated ext, shift left observed',
    BaselineMeasure: 'Standing extension 80% ROM Pain 6/10 weakness multifidus left'
  },
  driver_checks: {
    RedFlagsCleared: 'cleared',
    NeuroScreen: 'cleared',
    AdjacentRegionCheck: 'Thoracic extension limited T6-8 - positive driver elsewhere?',
    CompensationObserved: 'Lumbar shift left at 80% extension + breath holding',
    DependencyResult: 'dependent_on_thoracic_extension',
    Irritability: 'medium',
    ComparableSignSelected: true,
    RetestComparator: {
      PostIntervention: 'After thoracic PA T6-8 + multifidus cue - standing ext 100% ROM Pain 2/10',
      ChangePercent: 57,
      PainDelta: '-4/10',
      DriverConfirmed: true
    }
  }
};

console.log('\n--- DEMO PATIENT FLOW ---\n');
console.log('1. Patient + Case:', demoInput.patient_case);
console.log('\n2. Comparable Sign Selected:', demoInput.comparable_sign.CanonicalRegion, '->', demoInput.comparable_sign.MovementDirection, '->', demoInput.comparable_sign.Position);

// Lookup panel
const lookup = lookupForRegionDirection(demoInput.comparable_sign.CanonicalRegion, demoInput.comparable_sign.MovementDirection);
console.log('\n--- Dynamic Lookup Panel ---');
console.log(`Available directions for selected region (${demoInput.comparable_sign.CanonicalRegion}):`, lookup.availableDirections);
console.log(`Available positions:`, lookup.availablePositions);
console.log(`Available biases:`, lookup.availableBiases);
console.log(`Candidate muscles:`, lookup.candidateMuscles);
console.log(`Isolation logic:`, lookup.isolationLogic);
console.log(`Compensation watch:`, lookup.compensationWatch);
console.log(`Retest rule:`, lookup.retestRule);

console.log('\n3. Driver Checks:', demoInput.driver_checks);

// Safety
const safety = getSafetyGate(demoInput.driver_checks.RedFlagsCleared as any, demoInput.driver_checks.NeuroScreen as any, demoInput.driver_checks.Irritability as any);
console.log(`\nSafety Gate: ${safety}`);

console.log('\n4. AI Reasoning - Generating...');
const reasoning = generateFindings({
  CanonicalRegion: demoInput.comparable_sign.CanonicalRegion,
  SpecificJoint: demoInput.comparable_sign.SpecificJoint_Segment,
  MovementDirection: demoInput.comparable_sign.MovementDirection,
  Position: demoInput.comparable_sign.Position,
  Bias: demoInput.comparable_sign.Bias_RangeGate,
  FindingType: demoInput.comparable_sign.FindingType,
  PainBehavior: demoInput.comparable_sign.PainBehavior,
  FunctionalTask: demoInput.patient_case.FunctionalTask,
  PreviousResponse: demoInput.patient_case.PreviousResponse,
  ChiefComplaint: demoInput.patient_case.ChiefComplaint,
  RedFlagsCleared: demoInput.driver_checks.RedFlagsCleared,
  NeuroScreen: demoInput.driver_checks.NeuroScreen,
  AdjacentRegionCheck: demoInput.driver_checks.AdjacentRegionCheck,
  CompensationObserved: demoInput.driver_checks.CompensationObserved,
  DependencyResult: demoInput.driver_checks.DependencyResult,
  Irritability: demoInput.driver_checks.Irritability as any,
  RetestChangePercent: demoInput.driver_checks.RetestComparator.ChangePercent
});

console.log(`
=== RESULT ===
Primary Finding: ${reasoning.PrimaryFinding}
Secondary Finding: ${reasoning.SecondaryFinding}
Third Finding: ${reasoning.ThirdFinding}
Confidence: ${reasoning.Confidence}%
Safety Gate: ${reasoning.SafetyGate}
Manual Therapy Option: ${reasoning.ManualTherapyOption}
Exercise Integration: ${reasoning.ExerciseIntegration}
Report Summary:
${reasoning.ReportSummary}
`);

// Save demo report
const outDir = path.join(__dirname, '../../docs/reports');
if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

const reportPath = path.join(outDir, `${demoInput.patient_case.Patient_ID}-${new Date().toISOString().split('T')[0]}.md`);
fs.writeFileSync(reportPath, `# Clinical Report ${demoInput.patient_case.Patient_ID}
Date: ${new Date().toISOString()}

## S: 
Patient ${demoInput.patient_case.Patient_Name} ${demoInput.patient_case.Age_Gender} c/o ${demoInput.patient_case.ChiefComplaint}. Functional task: ${demoInput.patient_case.FunctionalTask}.

## O:
${JSON.stringify(demoInput.comparable_sign, null, 2)}
Driver Checks: ${JSON.stringify(demoInput.driver_checks, null, 2)}
Lookup: ${JSON.stringify(lookup, null, 2)}

## A:
Primary: ${reasoning.PrimaryFinding}
Secondary: ${reasoning.SecondaryFinding}
Third: ${reasoning.ThirdFinding}
Confidence: ${reasoning.Confidence}%
Safety: ${reasoning.SafetyGate}

## P:
Manual: ${reasoning.ManualTherapyOption}
Exercise: ${reasoning.ExerciseIntegration}

---
${reasoning.ReportSummary}
`);

console.log(`\nReport saved to ${reportPath}`);

// Also show how to create new patient JSON
const newPatientTemplate = {
  ...template,
  patient_case: demoInput.patient_case,
  comparable_sign: { ...template.comparable_sign, ...demoInput.comparable_sign, ...lookup },
  driver_checks: demoInput.driver_checks,
  ai_reasoning: reasoning
};

fs.writeFileSync(path.join(__dirname, '../../data/demo_patient_completed.json'), JSON.stringify(newPatientTemplate, null, 2));
console.log(`\nDemo patient JSON saved to data/demo_patient_completed.json`);

console.log(`\n=== NEXT STEPS ===`);
console.log(`1. Push to GitHub: gh repo create physicaltherapy-skills --public --source=. --push`);
console.log(`2. Enable GitHub Skills in Copilot settings`);
console.log(`3. Use skills via @workspace /skills clinical-driver-console`);
console.log(`4. Add your own registry entries in data/directional_test_registry.json`);
