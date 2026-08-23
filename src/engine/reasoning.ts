/**
 * AI Reasoning Engine - Implements column 4 of Clinical_Driver_Console
 * Primary/Secondary/Third Finding, Confidence, Safety Gate
 */

export interface ReasoningInput {
  CanonicalRegion: string;
  SpecificJoint?: string;
  MovementDirection: string;
  Position: string;
  Bias?: string;
  FindingType: 'weak' | 'painful' | 'limited' | string;
  PainBehavior?: string;
  FunctionalTask?: string;
  PreviousResponse?: string;
  ChiefComplaint?: string;
  // Checks
  RedFlagsCleared: string;
  NeuroScreen: string;
  AdjacentRegionCheck: string;
  CompensationObserved?: string;
  DependencyResult: string;
  Irritability: 'low' | 'medium' | 'high';
  RetestChangePercent?: number;
}

export interface ReasoningOutput {
  PrimaryFinding: string;
  SecondaryFinding: string;
  ThirdFinding: string;
  Confidence: number;
  SafetyGate: string;
  ManualTherapyOption: string;
  ExerciseIntegration: string;
  ReportSummary: string;
}

export function calculateSafetyGate(input: ReasoningInput): string {
  if (input.RedFlagsCleared === 'positive_referral_needed') {
    return 'referral_only';
  }
  if (input.RedFlagsCleared === 'not_tested' || input.NeuroScreen === 'not_tested') {
    return 'assessment_only_until_confirmed';
  }
  if (input.Irritability === 'high') {
    return 'gentle_assessment_and_education_only';
  }
  return 'proceed_with_caution';
}

export function calculateConfidence(input: ReasoningInput): number {
  let confidence = 50;
  if (input.RetestChangePercent && input.RetestChangePercent > 50) confidence += 20;
  else if (input.RetestChangePercent && input.RetestChangePercent > 30) confidence += 10;
  
  if (input.DependencyResult && input.DependencyResult.includes('dependent_on')) confidence += 10;
  if (input.CompensationObserved && input.CompensationObserved.length > 0) confidence += 10;
  if (input.AdjacentRegionCheck && input.AdjacentRegionCheck.includes('cleared')) confidence += 5;
  
  if (input.AdjacentRegionCheck && input.AdjacentRegionCheck.includes('positive_driver_elsewhere')) confidence -= 20;
  if (input.Irritability === 'high') confidence -= 15;
  if (!input.RetestChangePercent) confidence -= 10;

  return Math.max(20, Math.min(95, confidence));
}

export function generateFindings(input: ReasoningInput): ReasoningOutput {
  const safetyGate = calculateSafetyGate(input);
  const confidence = calculateConfidence(input);

  // Build findings based on FindingType
  let primary = '';
  let secondary = '';
  let third = '';
  let manual = '';
  let exercise = '';
  let report = '';

  // Driver logic
  const region = input.CanonicalRegion;
  const direction = input.MovementDirection;
  const compensation = input.CompensationObserved || 'none noted';
  const dependency = input.DependencyResult;
  const irritability = input.Irritability;

  // Primary finding templates
  if (input.FindingType === 'weak') {
    if (region === 'Lumbar' && direction === 'Extension') {
      primary = `Lumbar extension motor control deficit - ${input.SpecificJoint || 'L4-L5'} multifidus inhibition with ${dependency.includes('thoracic') ? 'thoracic extension driver T6-8' : 'glute max inhibition'}. Evidence: comparable sign ${input.RetestChangePercent || 0}% improved when correcting driver.`;
      secondary = `Left glute med weakness allowing pelvic drop in single leg stance - compensatory lumbar shift ${compensation}`;
      third = `Breathing strategy - apical breathing and breath holding at end-range ${direction}`;
    } else if (region === 'Shoulder' && direction === 'Flexion') {
      primary = `Scapular upward rotation deficit - serratus anterior inhibition leading to GH impingement signs. Flexion limited to ${input.Bias || '120deg'} with compensation ${compensation}`;
      secondary = `Thoracic extension limitation driver T4-6 reducing scapular posterior tilt`;
      third = `Rotator cuff control deficit - anterior humeral translation lack of control`;
    } else if (region === 'Hip') {
      primary = `Hip ${direction} motor control deficit - glute med/max inhibition, TFL dominance. Observed ${compensation}`;
      secondary = `Lumbar compensatory mechanism due to primary hip driver`;
      third = `Pelvic stability deficit - contralateral drop`;
    } else {
      primary = `${region} ${direction} motor control deficit - primary muscle inhibition, candidate from registry. Evidence: weak at ${input.Position} position`;
      secondary = `Adjacent region adaptation - ${input.AdjacentRegionCheck}`;
      third = `Compensation pattern ${compensation} suggests synergist dominance`;
    }
  } else if (input.FindingType === 'painful') {
    primary = `${region} ${direction} painful at end-range - suggests joint nociceptive driver (facetal/capsular) at ${input.SpecificJoint || region} with sensitization. Pain behavior: ${input.PainBehavior || 'catch at end-range'}`;
    secondary = `Motor inhibition secondary to pain - protective guarding ${compensation}`;
    third = `${dependency.includes('dependent') ? `Dependent on ${dependency}` : 'Independent driver - not dependent on adjacent'}`;
  } else if (input.FindingType === 'limited') {
    primary = `${region} ${direction} stiffness driver - capsular/joint restriction at ${input.SpecificJoint || region}, limiting functional task ${input.FunctionalTask || ''}`;
    secondary = `Myofascial length limitation contributing - candidate muscles tight`;
    third = `Compensatory increased mobility at adjacent region - ${input.AdjacentRegionCheck}`;
  } else {
    primary = `${region} ${direction} ${input.FindingType} finding - requires further isolation via ${input.Position}`;
    secondary = `Check adjacent region ${input.AdjacentRegionCheck}`;
    third = `Compensation ${compensation}`;
  }

  // Manual therapy gated
  if (safetyGate === 'assessment_only_until_confirmed') {
    manual = `Assessment only - complete red flag (${input.RedFlagsCleared}) + neuro screen (${input.NeuroScreen}) first. No manual therapy until cleared. Can use gentle education and breathing.`;
  } else if (safetyGate === 'referral_only') {
    manual = `Referral only - positive red flag screening. Document and refer immediately. No manual therapy.`;
  } else {
    if (irritability === 'high') {
      manual = `Gentle Grade I-II: ${region} PA central 30sec x2 gentle oscillations to reduce pain, avoid end-range. Alternative: positional release. Rationale: high irritability needs calming.`;
    } else if (irritability === 'medium') {
      if (region === 'Lumbar' && direction === 'Extension') {
        manual = `PA unilateral ${input.SpecificJoint || 'L4-L5'} Grade II 2x30sec + Thoracic PA T6-8 Grade II-III to improve thoracic extension driver. Retest ${input.MovementDirection} comparable sign after.`;
      } else if (region === 'Shoulder') {
        manual = `Posterior GH glide Grade II-III to improve flexion + Scapular assistance mobilization. If thoracic driver, add PA T4-6 Grade II.`;
      } else {
        manual = `${region} joint mobilization Grade II-III targeted at ${input.SpecificJoint || 'primary segment'} to improve ${direction}. Dosage 2x30sec. Retest comparable sign after 2min.`;
      }
    } else { // low
      manual = `${region} Grade III-IV sustained mobilization + overpressure at end-range to improve ${direction} stiffness. Consider Grade V if qualified and cleared. Dosage: 30sec x3 with breathing.`;
    }
  }

  // Exercise integration
  if (safetyGate.includes('referral') || safetyGate.includes('assessment_only')) {
    exercise = `Education only until cleared: breathing, gentle active movement within comfort, avoid aggravating ${input.FunctionalTask}. Monitor 24hr pain response.`;
  } else {
    if (input.FindingType === 'weak') {
      exercise = `In clinic: facilitation of inhibited muscle + driver correction. Home: (1) Activation low load 3x8 5sec hold, (2) Mobility for driver region 2x10, (3) Functional integration task ${input.FunctionalTask} with new control. Irritability ${irritability} -> quality>quantity.`;
    } else if (input.FindingType === 'painful') {
      exercise = `Pain reduction first: gentle activation + mobility driver correction. Home: pain-free ROM 2x10, isometrics if irritable, breathing. Progress when pain <3/10.`;
    } else {
      exercise = `Mobility: ${region} ${direction} mobility over roller/band 2x10 + control exercise to hold new range 3x8. Integrate to functional task ${input.FunctionalTask}.`;
    }
  }

  // Report summary SOAP
  report = `S: ${input.ChiefComplaint || 'c/o pain'} with ${input.FunctionalTask || 'functional task'}; Prev: ${input.PreviousResponse || 'none'}. Irritability ${irritability}.
O: Comparable = ${region} ${direction} ${input.Position} ${input.Bias || ''} - ${input.FindingType} baseline. Red flags ${input.RedFlagsCleared}, neuro ${input.NeuroScreen}, adjacent ${input.AdjacentRegionCheck}, comp=${compensation}, dependency=${dependency}, retest change ${input.RetestChangePercent || 0}%.
A: Primary ${primary}; Secondary ${secondary}; Third ${third}; Confidence ${confidence}%; Safety ${safetyGate}
P: Manual: ${manual}. Exercise: ${exercise}. Retest comparable sign + 24hr monitoring. FU plan.`;

  return {
    PrimaryFinding: primary,
    SecondaryFinding: secondary,
    ThirdFinding: third,
    Confidence: confidence,
    SafetyGate: safetyGate,
    ManualTherapyOption: manual,
    ExerciseIntegration: exercise,
    ReportSummary: report
  };
}

// For Node usage
if (require.main === module) {
  const demo: ReasoningInput = {
    CanonicalRegion: 'Lumbar',
    MovementDirection: 'Extension',
    Position: 'Standing',
    Bias: 'End-range overpressure',
    FindingType: 'weak',
    PainBehavior: 'pain eases with repetition',
    FunctionalTask: 'sitting >20min',
    ChiefComplaint: 'LBP with sitting',
    PreviousResponse: 'massage temporary',
    RedFlagsCleared: 'cleared',
    NeuroScreen: 'cleared',
    AdjacentRegionCheck: 'Thoracic extension limited T6-8',
    CompensationObserved: 'Lumbar shift left at 80% extension',
    DependencyResult: 'dependent_on_thoracic_extension',
    Irritability: 'medium',
    RetestChangePercent: 57
  };
  console.log(generateFindings(demo));
}
