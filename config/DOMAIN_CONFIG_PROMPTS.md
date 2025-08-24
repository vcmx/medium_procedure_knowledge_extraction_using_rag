# Domain Configuration Generation Prompts

## For Pattern Configuration (domain_patterns.json)

### Initial Generation Prompt:
```
I need to create a JSON configuration file for pattern matching in [DOMAIN] technical documentation. Please generate regex patterns for common identifiers and specifications found in [DOMAIN] manuals.

Include patterns for:
1. Part/model numbers (provide examples: [EXAMPLES])
2. Measurement specifications with units
3. Reference formats (figures, tables, sections)
4. Technical codes and identifiers
5. Standard specifications and ranges

Context:
- Industry: [SPECIFIC INDUSTRY]
- Document types: [repair manuals, service bulletins, technical specs, etc.]
- Regional standards: [US/EU/Global]
- Sample text excerpts: [PASTE RELEVANT EXCERPTS]

Output format: JSON with pattern_name: regex_pattern
Make patterns specific enough to avoid false positives but flexible enough to catch variations.
```

### Update/Refresh Prompt:
```
Review and update this existing pattern configuration for [DOMAIN] documentation:

Current configuration:
[PASTE CURRENT JSON]

Recent sample texts showing new patterns:
[PASTE NEW EXAMPLES]

Please:
1. Identify any missing pattern types
2. Improve existing patterns that might be too restrictive/broad
3. Add patterns for new standards or formats
4. Remove obsolete patterns
5. Ensure compatibility with current industry standards as of [DATE]

Explain each change and why it's needed.
```

## For Vocabulary Configuration (domain_vocabulary.json)

### Initial Generation Prompt:
```
Create a comprehensive domain vocabulary JSON file for [DOMAIN] with categories of technical terms.

Categories needed:
1. technical_terms: Core technical concepts and systems
2. component_names: Physical parts and components  
3. actions: Verbs used in procedures/instructions
4. measurements: Types of measurements and parameters
5. diagnostic_terms: Troubleshooting and testing terminology
6. [DOMAIN]_specific_terms: Industry-specific categories

Context:
- Target audience: [technicians, engineers, operators]
- Technical level: [basic/intermediate/advanced]
- Regional terminology: [US/UK/International]
- Sample documents: [PASTE EXCERPTS OR DESCRIBE]

Include both common terms and specialized jargon. Group related terms logically.
```

### Update/Refresh Prompt:
```
Update this domain vocabulary for [DOMAIN] to reflect current terminology:

Current vocabulary:
[PASTE CURRENT JSON]

Consider:
1. New technology terms (e.g., electric vehicle components, new diagnostic tools)
2. Deprecated terms that should be removed
3. Missing common terms from recent manuals
4. Alternative names/synonyms for existing terms
5. Regional variations

Reference materials:
- Recent manual excerpts: [PASTE]
- Industry updates: [DESCRIBE CHANGES]
- New standards: [LIST ANY NEW STANDARDS]

Maintain the existing structure but expand/refine as needed.
```

## Best Practices for Prompting:

### 1. Provide Context:
```
Domain: Automotive repair
Document types: Factory service manuals, TSBs, wiring diagrams
Time period: 2020-2024 model years
Manufacturers: [List specific ones if applicable]
```

### 2. Give Concrete Examples:
```
Here are actual excerpts from our documents:
- "Torque to 25 Nm (18 ft-lb) in sequence shown in Figure 4-12"
- "DTC P0301 - Cylinder 1 Misfire Detected"
- "Part #: 12345-AA123-B"
```

### 3. Specify Regional/Standard Variations:
```
Include both:
- US measurements (ft-lb, psi, °F)
- Metric measurements (Nm, kPa, °C)
- Industry-specific units (bar for European vehicles)
```

### 4. Request Validation:
```
For each pattern, provide:
1. The regex pattern
2. 2-3 example matches
3. Explanation of what it captures
4. Any edge cases to be aware of
```

### 5. Iterative Refinement:
```
After testing these patterns, I found these issues:
- Pattern X is too broad and matches [FALSE POSITIVE]
- Pattern Y misses [EXAMPLE THAT SHOULD MATCH]
- Need new pattern for [NEW FORMAT]

Please refine accordingly.
```

## Example Domain-Specific Prompts:

### For Medical Equipment:
```
Create patterns for:
- FDA device codes
- ICD-10 procedure codes  
- Medical device model numbers
- Dosage specifications
- Sterilization parameters
```

### For Industrial Machinery:
```
Create patterns for:
- ISO standard references
- Hydraulic pressure specs
- Safety lockout codes
- Maintenance interval formats
- Component lifecycle indicators
```

### For Software Documentation:
```
Create patterns for:
- Version numbers (semantic versioning)
- Error codes and messages
- API endpoint patterns
- Configuration parameters
- Log level indicators
```

## Validation Prompt:
```
Test these patterns against this sample text and identify:
1. What patterns matched (with match locations)
2. What should have matched but didn't
3. Any false positives
4. Suggested improvements

Sample text:
[PASTE REALISTIC DOCUMENT EXCERPT]
```