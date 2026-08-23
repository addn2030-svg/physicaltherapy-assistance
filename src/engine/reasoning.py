"""
AI Reasoning Engine - Python version
Mirrors reasoning.ts for therapists who prefer Python / Google Colab
"""

import json
from typing import Literal

FindingType = Literal['weak', 'painful', 'limited', 'unstable', 'apprehensive', 'compensation']

def calculate_safety_gate(red_flags: str, neuro: str, irritability: str) -> str:
    if red_flags == 'positive_referral_needed':
        return 'referral_only'
    if red_flags == 'not_tested' or neuro == 'not_tested':
        return 'assessment_only_until_confirmed'
    if irritability == 'high':
        return 'gentle_assessment_and_education_only'
    return 'proceed_with_caution'

def calculate_confidence(retest_change: float = 0, dependency: str = "", compensation: str = "", adjacent: str = "", irritability: str = "medium") -> int:
    confidence = 50
    if retest_change > 50:
        confidence += 20
    elif retest_change > 30:
        confidence += 10
    if 'dependent_on' in dependency:
        confidence += 10
    if compensation:
        confidence += 10
    if 'cleared' in adjacent:
        confidence += 5
    if 'positive_driver_elsewhere' in adjacent:
        confidence -= 20
    if irritability == 'high':
        confidence -= 15
    if not retest_change:
        confidence -= 10
    return max(20, min(95, confidence))

def generate_findings(data: dict) -> dict:
    region = data.get('CanonicalRegion', '')
    direction = data.get('MovementDirection', '')
    position = data.get('Position', '')
    finding = data.get('FindingType', 'weak')
    compensation = data.get('CompensationObserved', '')
    dependency = data.get('DependencyResult', 'not_tested')
    irritability = data.get('Irritability', 'medium')
    retest = data.get('RetestChangePercent', 0)
    specific = data.get('SpecificJoint', region)
    bias = data.get('Bias', '')
    functional = data.get('FunctionalTask', '')
    pain_behavior = data.get('PainBehavior', '')
    adjacent = data.get('AdjacentRegionCheck', '')

    safety_gate = calculate_safety_gate(data.get('RedFlagsCleared','not_tested'), data.get('NeuroScreen','not_tested'), irritability)
    confidence = calculate_confidence(retest, dependency, compensation, adjacent, irritability)

    # Primary finding templates
    if finding == 'weak':
        if region == 'Lumbar' and direction == 'Extension':
            primary = f"Lumbar extension motor control deficit - {specific} multifidus inhibition with {'thoracic extension driver T6-8' if 'thoracic' in dependency.lower() else 'glute max inhibition'}. Evidence: comparable sign {retest}% improved when correcting driver."
            secondary = f"Left glute med weakness allowing pelvic drop - compensatory lumbar shift {compensation}"
            third = f"Breathing strategy - apical breathing and breath holding at end-range {direction}"
        elif region == 'Shoulder':
            primary = f"Scapular upward rotation deficit - serratus anterior inhibition leading to GH impingement. Flexion limited to {bias} with comp {compensation}"
            secondary = "Thoracic extension limitation driver T4-6 reducing scapular posterior tilt"
            third = "Rotator cuff control deficit"
        else:
            primary = f"{region} {direction} motor control deficit - primary muscle inhibition, weak at {position} position"
            secondary = f"Adjacent region adaptation - {adjacent}"
            third = f"Compensation {compensation} suggests synergist dominance"
    elif finding == 'painful':
        primary = f"{region} {direction} painful at end-range - suggests joint nociceptive driver at {specific} with sensitization. Pain behavior: {pain_behavior}"
        secondary = f"Motor inhibition secondary to pain - protective guarding {compensation}"
        third = f"{'Dependent on ' + dependency if 'dependent' in dependency else 'Independent driver'}"
    elif finding == 'limited':
        primary = f"{region} {direction} stiffness driver - capsular/joint restriction at {specific}, limiting task {functional}"
        secondary = "Myofascial length limitation contributing"
        third = f"Compensatory increased mobility at adjacent - {adjacent}"
    else:
        primary = f"{region} {direction} {finding} finding - requires isolation via {position}"
        secondary = f"Check adjacent region {adjacent}"
        third = f"Compensation {compensation}"

    # Manual
    if safety_gate == 'assessment_only_until_confirmed':
        manual = f"Assessment only - complete red flag + neuro clearance first. No manual therapy until cleared."
    elif safety_gate == 'referral_only':
        manual = f"Referral only - positive red flag screening. Document and refer immediately."
    else:
        if irritability == 'high':
            manual = f"Gentle Grade I-II: {region} PA central 30sec x2 gentle oscillations to reduce pain, avoid end-range."
        elif irritability == 'medium':
            if region == 'Lumbar' and direction == 'Extension':
                manual = f"PA unilateral {specific} Grade II 2x30sec + Thoracic PA T6-8 Grade II-III to improve thoracic driver. Retest {direction} comparable after."
            else:
                manual = f"{region} joint mobilization Grade II-III targeted at {specific} to improve {direction}. Dosage 2x30sec. Retest after 2min."
        else:
            manual = f"{region} Grade III-IV sustained mobilization + overpressure at end-range to improve {direction} stiffness."

    # Exercise
    if 'referral' in safety_gate or 'assessment_only' in safety_gate:
        exercise = f"Education only until cleared: breathing, gentle active movement within comfort, avoid {functional}."
    else:
        if finding == 'weak':
            exercise = f"In clinic facilitation + driver correction. Home: (1) Activation low load 3x8 5s hold, (2) Mobility driver 2x10, (3) Functional integration task {functional}. Irritability {irritability} -> quality>quantity."
        else:
            exercise = f"Mobility: {region} {direction} mobility over roller 2x10 + control to hold 3x8. Integrate to {functional}."

    # SOAP
    soap = f"""S: {data.get('ChiefComplaint','')} with {functional}; Prev: {data.get('PreviousResponse','')}. Irritability {irritability}.
O: Comparable = {region} {direction} {position} {bias} - {finding} baseline. Red flags {data.get('RedFlagsCleared')}, neuro {data.get('NeuroScreen')}, adjacent {adjacent}, comp={compensation}, dependency={dependency}, retest change {retest}%.
A: Primary {primary}; Secondary {secondary}; Third {third}; Confidence {confidence}%; Safety {safety_gate}
P: Manual: {manual}. Exercise: {exercise}. Retest comparable + 24hr monitoring.
"""

    return {
        "PrimaryFinding": primary,
        "SecondaryFinding": secondary,
        "ThirdFinding": third,
        "Confidence": confidence,
        "SafetyGate": safety_gate,
        "ManualTherapyOption": manual,
        "ExerciseIntegration": exercise,
        "ReportSummary": soap
    }

# Demo
if __name__ == "__main__":
    demo = {
        "CanonicalRegion": "Lumbar",
        "SpecificJoint": "L4-L5",
        "MovementDirection": "Extension",
        "Position": "Standing",
        "Bias": "End-range overpressure",
        "FindingType": "weak",
        "PainBehavior": "pain eases with repetition",
        "FunctionalTask": "sitting >20min",
        "ChiefComplaint": "LBP with sitting",
        "PreviousResponse": "massage temporary",
        "RedFlagsCleared": "cleared",
        "NeuroScreen": "cleared",
        "AdjacentRegionCheck": "Thoracic extension limited T6-8",
        "CompensationObserved": "Lumbar shift left at 80% extension",
        "DependencyResult": "dependent_on_thoracic_extension",
        "Irritability": "medium",
        "RetestChangePercent": 57
    }
    result = generate_findings(demo)
    print(json.dumps(result, indent=2, ensure_ascii=False))
