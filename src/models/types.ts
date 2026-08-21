// LFS Clinical Driver Console Types

export type Region = 'Cervical' | 'Thoracic' | 'Lumbar' | 'Sacroiliac' | 'Shoulder' | 'Elbow' | 'Wrist' | 'Hip' | 'Knee' | 'Ankle' | 'Foot';

export type FindingType = 'weak' | 'painful' | 'limited' | 'unstable' | 'apprehensive' | 'compensation';

export type Status = 'not_tested' | 'cleared' | 'positive_referral_needed' | 'positive_deficit_documented' | 'positive_driver_elsewhere' | 'observed';

export type Irritability = 'low' | 'medium' | 'high';

export type SafetyGate = 'assessment_only_until_confirmed' | 'referral_only' | 'gentle_assessment_and_education_only' | 'proceed_with_caution';

export interface PatientCase {
  Patient_ID: string;
  Patient_Name?: string;
  Therapist?: string;
  Age_Gender?: string;
  Contact_Chat_ID?: string;
  ChiefComplaint: string;
  FunctionalTask?: string;
  PreviousResponse?: string;
}

export interface ComparableSign {
  CanonicalRegion: Region;
  SpecificJoint_Segment?: string;
  MovementDirection: string;
  Position: string;
  Bias_RangeGate?: string;
  Angle_Load?: string;
  FindingType: FindingType;
  PainBehavior?: string;
  BaselineMeasure?: string;
  // Lookup results
  AvailableDirectionsForRegion?: string[];
  AvailablePositionsForDirection?: string[];
  AvailableBiases?: string[];
  CandidateMuscles?: string[];
  IsolationLogic?: string;
  CompensationWatch?: string[];
  RetestRule?: string;
}

export interface DriverChecks {
  RedFlagsCleared: Status | 'not_tested' | 'cleared' | 'positive_referral_needed';
  NeuroScreen: Status | 'not_tested' | 'cleared' | 'positive_deficit_documented';
  AdjacentRegionCheck: Status | 'not_tested' | 'cleared' | 'positive_driver_elsewhere' | string;
  CompensationObserved?: string;
  DependencyResult: 'not_tested' | 'independent' | string; // dependent_on_X
  Irritability: Irritability;
  ComparableSignSelected: boolean;
  RetestComparator: {
    PostIntervention?: string;
    ChangePercent?: number;
    PainDelta?: string;
    DriverConfirmed?: boolean;
  };
}

export interface ManualTherapyOption {
  Technique: string;
  Rationale: string;
  Dosage: string;
  Precautions: string;
  Alternative?: string;
  SafetyGate?: SafetyGate;
}

export interface ExerciseItem {
  Exercise: string;
  Dosage: string;
  Cue: string;
}

export interface ExerciseIntegration {
  InClinic: string[];
  HomeProgram: ExerciseItem[];
  FunctionalIntegration: string;
  ProgressionCriteria: string;
  IrritabilityAdjustment: string;
}

export interface AIReasoning {
  PrimaryFinding: string;
  SecondaryFinding: string;
  ThirdFinding: string;
  Confidence: number;
  SafetyGate: SafetyGate;
  ManualTherapyOption: ManualTherapyOption;
  ExerciseIntegration: ExerciseIntegration;
  ReportSummary: {
    SOAP: string;
    PatientFriendlyEN: string;
    PatientFriendlyAR: string;
    ReferralNote?: string;
  };
}

export interface ClinicalDriverConsole {
  patient_case: PatientCase;
  comparable_sign: ComparableSign;
  driver_checks: DriverChecks;
  ai_reasoning: AIReasoning;
}
