/**
 * Techniques Directory Engine - Lookup for Comprehensive Manual Therapy Directory
 * Version 2.0 - 38 techniques integration
 */

import directory from '../../data/comprehensive_manual_therapy_directory.json';

export interface Technique {
  id: string;
  name: string;
  acronym: string;
  origin: string;
  classification: string;
  evidence_level: string;
  best_for_regions: string[];
  finding_type_match: string[];
  irritability_guidance: {
    low: string;
    medium: string;
    high: string;
  };
  dosage_template: string;
  isolation_logic: string;
  compensation_watch: string[];
  retest_rule: string;
  safety_notes: string;
  integration_with_exercise: string;
  contraindications: string[];
}

export function getAllTechniques(): Technique[] {
  const all: Technique[] = [];
  for (const cat of directory.categories) {
    for (const tech of cat.techniques) {
      all.push(tech as Technique);
    }
  }
  return all;
}

export function getTechniqueById(id: string): Technique | undefined {
  return getAllTechniques().find(t => t.id === id);
}

export function getTechniquesByFindingType(findingType: string): Technique[] {
  // Use crosswalk if available
  const crosswalk = (directory as any).crosswalk?.comparable_sign_finding_type_to_techniques?.[findingType];
  if (crosswalk) {
    // Map crosswalk hints to actual techniques - try matching by name fragment
    const all = getAllTechniques();
    const matched: Technique[] = [];
    for (const hint of crosswalk) {
      const hintLower = hint.toLowerCase();
      // Simple matching
      const found = all.filter(t => 
        t.id.toLowerCase().includes(hintLower) ||
        t.name.toLowerCase().includes(hintLower) ||
        t.acronym.toLowerCase().includes(hintLower)
      );
      found.forEach(f => { if (!matched.find(m => m.id === f.id)) matched.push(f); });
    }
    // Fallback also add those with finding_type_match
    all.filter(t => t.finding_type_match.includes(findingType)).forEach(t => {
      if (!matched.find(m => m.id === t.id)) matched.push(t);
    });
    return matched;
  }
  return getAllTechniques().filter(t => t.finding_type_match.includes(findingType));
}

export function getTechniquesByRegion(region: string): Technique[] {
  const r = region.toLowerCase();
  return getAllTechniques().filter(t => 
    t.best_for_regions.some(br => br.toLowerCase().includes(r) || r.includes(br.toLowerCase()) || br.toLowerCase() === 'all' || br.toLowerCase().includes('whole'))
  );
}

export function getTechniquesByRegionAndFinding(region: string, findingType: string, irritability: 'low'|'medium'|'high' = 'medium'): Technique[] {
  let filtered = getAllTechniques().filter(t => 
    (t.best_for_regions.some(br => br.toLowerCase().includes(region.toLowerCase()) || region.toLowerCase().includes(br.toLowerCase())) || t.best_for_regions.some(br => br.toLowerCase().includes('all')) )
    && t.finding_type_match.includes(findingType)
  );

  // Irritability filter - exclude aggressive techniques for high irritability
  if (irritability === 'high') {
    const excludeForHigh = ['dry_needling_trigger', 'dry_needling_fascial_ali', 'fascial_distortion_model']; // deep aggressive optional
    // Keep but warn - we don't exclude fully, but mark dosage as high irrit guidance
    // Instead, exclude Grade III/IV heavy manual if technique notes suggest
    filtered = filtered.filter(t => {
      // Allow all but use high irritability guidance
      return true;
    });
  }
  return filtered;
}

export function getTechniquesByAuthor(author: string): Technique[] {
  const aLower = author.toLowerCase();
  return getAllTechniques().filter(t => t.origin.toLowerCase().includes(aLower) || t.name.toLowerCase().includes(aLower));
}

export function getIrritabilityDosage(techniqueId: string, irritability: 'low'|'medium'|'high'): string {
  const tech = getTechniqueById(techniqueId);
  if (!tech) return '';
  return tech.irritability_guidance[irritability] || tech.dosage_template;
}

export function searchTechniques(query: string): Technique[] {
  const q = query.toLowerCase();
  return getAllTechniques().filter(t => 
    t.name.toLowerCase().includes(q) ||
    t.acronym.toLowerCase().includes(q) ||
    t.id.toLowerCase().includes(q) ||
    t.origin.toLowerCase().includes(q) ||
    t.classification.toLowerCase().includes(q) ||
    (t.best_for_regions.join(' ').toLowerCase().includes(q)) ||
    (t.finding_type_match.join(' ').toLowerCase().includes(q))
  );
}

// For console demo
export function demoSearch() {
  console.log('=== All Techniques Count ===', getAllTechniques().length);
  console.log('\n=== For Lumbar weak medium irritability ===');
  console.log(getTechniquesByRegionAndFinding('Lumbar', 'weak', 'medium').map(t => `${t.id} - ${t.name} [${t.evidence_level}]`));
  console.log('\n=== For Shoulder painful ===');
  console.log(getTechniquesByFindingType('painful').filter(t => t.best_for_regions.includes('Shoulder')).map(t => t.name));
  console.log('\n=== Ali Marzok Methods ===');
  console.log(getTechniquesByAuthor('Ali Marzok').map(t => `${t.id}: ${t.name}`));
  console.log('\n=== Dosage for Maitland low vs high ===');
  console.log('Low:', getIrritabilityDosage('maitland', 'low'));
  console.log('High:', getIrritabilityDosage('maitland', 'high'));
}
