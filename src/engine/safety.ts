/**
 * Safety Engine - Red Flag + Neuro Screening logic
 * Enforces Safety Gate: assessment_only_until_confirmed
 */

export type RedFlagStatus = 'not_tested' | 'cleared' | 'positive_referral_needed';
export type NeuroStatus = 'not_tested' | 'cleared' | 'positive_deficit_documented';

export interface RedFlagQuestion {
  id: string;
  question: string;
  category: 'systemic' | 'lumbar' | 'cervical' | 'thoracic' | 'fracture';
  positiveMeans: string;
}

export const RED_FLAG_QUESTIONS: RedFlagQuestion[] = [
  { id: 'ces_bladder', question: 'Any bladder/bowel changes? Saddle anesthesia? Sexual dysfunction?', category: 'lumbar', positiveMeans: 'CES - emergency referral' },
  { id: 'prog_neuro', question: 'Severe or progressive weakness/numbness in legs/arms?', category: 'lumbar', positiveMeans: 'Progressive neuro deficit' },
  { id: 'weight_loss', question: 'Unexplained weight loss, fever, chills?', category: 'systemic', positiveMeans: 'Systemic - cancer/infection' },
  { id: 'cancer_hx', question: 'History of cancer?', category: 'systemic', positiveMeans: 'Cancer history' },
  { id: 'trauma', question: 'Significant recent trauma? (fall, accident)', category: 'fracture', positiveMeans: 'Fracture risk' },
  { id: 'night_pain', question: 'Constant night pain unrelieved by rest? Progressive pain?', category: 'systemic', positiveMeans: 'Non-mechanical pain' },
  { id: 'myelopathy', question: 'Hand clumsiness, gait disturbance, dropping objects? (cervical myelopathy)', category: 'cervical', positiveMeans: 'Myelopathy' },
  { id: 'vert_insuff', question: 'Dizziness, double vision, dysarthria, drop attacks with neck movement?', category: 'cervical', positiveMeans: 'VBI / cranial nerve' },
  { id: 'iv_drug', question: 'IV drug use, immunosuppression, steroids?', category: 'systemic', positiveMeans: 'Infection risk' },
  { id: 'age_onset', question: 'Age >55 with new onset pain? Age <20 with persistent pain?', category: 'systemic', positiveMeans: 'Red flag age' },
];

export function evaluateRedFlags(answers: Record<string, boolean>): { status: RedFlagStatus; referralNote: string; checked: string[] } {
  const positives = Object.entries(answers).filter(([_, v]) => v === true);
  if (positives.length > 0) {
    const notes = positives.map(([id]) => {
      const q = RED_FLAG_QUESTIONS.find(q => q.id === id);
      return `${q?.question} -> POSITIVE (${q?.positiveMeans})`;
    }).join('; ');
    return {
      status: 'positive_referral_needed',
      referralNote: `RED FLAG POSITIVE: ${notes}. Requires immediate medical referral. Documented screening.`,
      checked: Object.keys(answers)
    };
  }
  // If some questions not answered, still not_tested? Simplified -> if <5 answered, remain not_tested
  if (Object.keys(answers).length < 5) {
    return { status: 'not_tested', referralNote: '', checked: Object.keys(answers) };
  }
  return { status: 'cleared', referralNote: '', checked: Object.keys(answers) };
}

export const NEURO_SCREEN_TEMPLATE = {
  cervical: {
    dermatomes: ['C4 lateral shoulder', 'C5 lateral forearm', 'C6 thumb side', 'C7 middle finger', 'C8 medial hand', 'T1 medial forearm'],
    myotomes: ['C5 deltoid', 'C5-6 biceps', 'C7 triceps', 'C8 grip', 'T1 finger abduction'],
    reflexes: ['C5-6 biceps', 'C6 brachioradialis', 'C7 triceps'],
    umn: ['Hoffmann', 'Clonus', 'Hyperreflexia', 'Gait']
  },
  lumbar: {
    dermatomes: ['L2 anterior thigh', 'L3 medial thigh', 'L4 medial calf', 'L5 dorsum foot', 'S1 lateral foot'],
    myotomes: ['L2 hip flex', 'L3 knee ext', 'L4 ankle DF', 'L5 great toe ext', 'S1 plantarflex'],
    reflexes: ['L3-4 patellar', 'S1 Achilles'],
    special: ['SLR', 'Slump', 'Femoral nerve tension']
  }
};

export function evaluateNeuroScreen(findings: {
  sensory: 'intact' | 'deficit' | string;
  motor: string;
  reflexes: string;
  umn: 'negative' | 'positive' | string;
  slr?: string;
}): { status: NeuroStatus; summary: string } {
  const hasDeficit = findings.sensory !== 'intact' || findings.motor.toLowerCase().includes('weak') || findings.umn === 'positive' || findings.reflexes.toLowerCase().includes('diminished') || findings.reflexes.toLowerCase().includes('brisk');
  if (hasDeficit) {
    return {
      status: 'positive_deficit_documented',
      summary: `Neuro deficit documented: Sensory ${findings.sensory}, Motor ${findings.motor}, Reflexes ${findings.reflexes}, UMN ${findings.umn}. Consider radiculopathy overlay - monitor and document. Does NOT automatically block treatment unless progressive.`
    };
  }
  return {
    status: 'cleared',
    summary: `Neuro screen cleared: Sensory intact, Motor ${findings.motor}, Reflexes ${findings.reflexes}, UMN negative.`
  };
}

export function getSafetyGate(redFlagStatus: RedFlagStatus, neuroStatus: NeuroStatus, irritability: 'low'|'medium'|'high'): string {
  if (redFlagStatus === 'positive_referral_needed') return 'referral_only - immediate medical referral required. STOP';
  if (redFlagStatus === 'not_tested' || neuroStatus === 'not_tested') return 'assessment_only_until_confirmed - complete clearance first';
  if (irritability === 'high') return 'gentle_assessment_and_education_only - avoid aggravation';
  return 'proceed_with_caution - red flags cleared, neuro cleared, irritability moderate. OK to proceed with guided treatment + retest';
}
