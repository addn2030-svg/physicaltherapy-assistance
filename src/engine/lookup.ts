/**
 * Directional Test Registry Lookup Engine
 * Implements Dynamic Lookup Panel from Clinical_Driver_Console sheet
 */

import registry from '../../data/directional_test_registry.json';

export interface LookupResult {
  availableDirections: string[];
  availablePositions: string[];
  availableBiases: string[];
  candidateMuscles: string[];
  isolationLogic: string;
  compensationWatch: string[];
  retestRule: string;
}

export function getAvailableDirections(region: string): string[] {
  const regionData = registry.regions.find(r => r.canonical_region.toLowerCase() === region.toLowerCase());
  if (!regionData) return [];
  return regionData.directions.map(d => d.direction);
}

export function lookupForRegionDirection(region: string, direction?: string, position?: string): LookupResult {
  const regionData = registry.regions.find(r => r.canonical_region.toLowerCase() === region.toLowerCase());
  if (!regionData) {
    return {
      availableDirections: [],
      availablePositions: [],
      availableBiases: [],
      candidateMuscles: [],
      isolationLogic: '',
      compensationWatch: [],
      retestRule: ''
    };
  }

  const availableDirections = regionData.directions.map(d => d.direction);

  if (!direction) {
    return {
      availableDirections,
      availablePositions: [],
      availableBiases: [],
      candidateMuscles: [],
      isolationLogic: '',
      compensationWatch: [],
      retestRule: ''
    };
  }

  const dirData = regionData.directions.find(d => d.direction.toLowerCase() === direction.toLowerCase());
  if (!dirData) {
    return {
      availableDirections,
      availablePositions: [],
      availableBiases: [],
      candidateMuscles: [],
      isolationLogic: '',
      compensationWatch: [],
      retestRule: ''
    };
  }

  let availablePositions = dirData.positions;
  let filtered = [dirData];

  // If we want to be more specific, we could filter by position in future, but current JSON stores positions array per direction
  return {
    availableDirections,
    availablePositions: dirData.positions,
    availableBiases: dirData.biases,
    candidateMuscles: dirData.candidate_muscles,
    isolationLogic: dirData.isolation_logic,
    compensationWatch: dirData.compensation_watch,
    retestRule: dirData.retest_rule
  };
}

export function getCandidateMuscles(region: string, direction: string): string[] {
  const result = lookupForRegionDirection(region, direction);
  return result.candidateMuscles;
}

// For console use
export function fullLookupPanel(region: string, direction: string, position: string) {
  const result = lookupForRegionDirection(region, direction, position);
  console.log(`
=== Dynamic Lookup Panel for ${region} -> ${direction} -> ${position} ===
Available directions for selected region: ${result.availableDirections.join(', ')}
Available positions for selected region + direction: ${result.availablePositions.join(', ')}
Available biases / range gates: ${result.availableBiases.join(', ')}
Candidate muscles: ${result.candidateMuscles.join(', ')}
Isolation logic: ${result.isolationLogic}
Compensation watch: ${result.compensationWatch.join(', ')}
Retest rule: ${result.retestRule}
`);
  return result;
}
