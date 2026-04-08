# TOCSAS: Knowledge Traceability Matrix

This file is the running audit trail for TOCSAS (Toxicology Scientific Agent Squad) workflows on preclinical toxicology metadata harmonization, MNMS alignment, and evidence synthesis.

## Epistemic Tags
- [OBSERVATION]: Directly reported measurement or finding from a cited study.
- [INTERPRETATION]: Author's or analyst's reading of an observation.
- [ADVERSITY_CLAIM]: A judgment that a finding meets adversity criteria — requires criteria citation.
- [MECHANISM]: Proposed biological mechanism — must be distinguished from association.
- [INFERENCE]: A cautious synthesis across multiple supported facts.
- [SPECULATION]: Forward-looking or unsupported extrapolation — explicitly marked as tentative.
- [MISSING_DATA]: A metadata element required for interpretation that was not reported.
- [INTERPRETATION_UNCERTAIN]: Evidence is insufficient to classify a finding as adaptive or adverse.

---

## Traceability Log

| # | Source Material (Input) | Epistemic Tag | Agent Assigned | Knowledge Extracted | Deployed In Output Section | Citation |
|---|---|---|---|---|---|---|
| 1 | OECD TG 408 (1998) | [OBSERVATION] | TOCSAS LitScout | Defines 90-day oral toxicity study design requirements for rodents including mandatory endpoints, group sizes, and tissue panels. | D. MNMS Mapping Table; E. Extension Proposal | OECD. Test No. 408: Repeated Dose 90-Day Oral Toxicity Study in Rodents. 1998. |
| 2 | ICH S3A (1994) | [OBSERVATION] | TOCSAS Exposure & Design Specialist | Defines toxicokinetic assessment requirements for systemic exposure characterization in toxicity studies. Core TK parameters: AUC, Cmax, t½. | D. MNMS Mapping Table; E. Extension Proposal | ICH. S3A: Note for Guidance on Toxicokinetics: The Assessment of Systemic Exposure in Toxicity Studies. 1994. |
| 3 | Thoolen et al. 2010 (INHAND hepatobiliary) | [OBSERVATION] | TOCSAS Pathology & Biomarker Analyst | Provides standardized INHAND nomenclature and diagnostic criteria for hepatobiliary lesions in laboratory rodents. | C. Evidence Table; D. MNMS Mapping Table | Thoolen B, et al. Toxicol Pathol. 2010;38(7 Suppl):5S-81S. PMID: 21191095. |
| 4 | mms_schema_v1.jsonld (local) | [OBSERVATION] | TOCSAS Metadata Architect | MNMS core schema covers StudyContext, AnimalDescriptors, Environment, DeviceAndSensor, BehavioralMetrics, and TimeAndProvenance. Does not cover dose, route, vehicle, clinical pathology, histopathology, TK, or adversity interpretation. | D. MNMS Mapping Table; E. Extension Proposal | Local schema file: schemas/mms_schema_v1.jsonld. |
| 5 | OECD GLP Principles (1998) | [OBSERVATION] | TOCSAS Exposure & Design Specialist | Defines GLP compliance requirements for study conduct, documentation, and QA — relevant to provenance and data integrity metadata. | D. MNMS Mapping Table | OECD. Principles of Good Laboratory Practice. ENV/MC/CHEM(98)17. 1998. |
| 6 | Sellers et al. 2007 (STP organ weights) | [OBSERVATION] | TOCSAS Pathology & Biomarker Analyst | STP position paper recommending minimum set of organs to weigh and establishing correlation requirements between organ weight changes and histopathology. | D. MNMS Mapping Table; F. Missing Metadata Report | Sellers RS, et al. Toxicol Pathol. 2007;35(5):751-755. PMID: 17849046. |

---

## MNMS Mapping Status Summary

| Metadata Category | MNMS Core Coverage | TOCSAS Extension Required | Priority |
|---|---|---|---|
| Study design (type, guideline, GLP) | Partial (GLPStatus only) | StudyType, RegulatoryGuideline | HIGH |
| Test article and formulation | Partial (BatchID only) | CompoundName, CASNumber, Purity, FormulationComposition, Stability | CRITICAL |
| Animal characteristics | Good | AgeAtStart, BodyWeightAtStart, AcclimatizationPeriod | MEDIUM |
| Housing/husbandry | Good | Temperature, Humidity | LOW |
| Dosing and exposure | None | Full DoseGroup structure, Route, Vehicle, Schedule, Duration | CRITICAL |
| Toxicokinetics | None | AUC, Cmax, Tmax, t½, DoseProportionality, NonlinearTKFlag | HIGH |
| Controls | None | ConcurrentVehicleControl, RecoveryGroup, SatelliteGroup | HIGH |
| Sampling and timing | Partial (Timestamps) | SamplingTimePoints, TerminalSacrificeDay, NecropsyProcedure | HIGH |
| Clinical pathology | None | Hematology/Chemistry/UA panels, AnalyticalMethod, HistControlAvail | HIGH |
| Organ weights | None | OrgansWeighed, AbsoluteWeight, RelativeToBodyWeight | HIGH |
| Histopathology | None | PathologyTerm, INHANDRef, SeverityGrade, GradingSystem, Incidence | CRITICAL |
| Statistics | None | StatisticalMethods, Software, SignificanceThreshold | MEDIUM |
| Interpretation | None | NOAEL, LOAEL, AdversityJudgment, AdversityCriteria, Reversibility | CRITICAL |
| Provenance | Good | QAStatus, AnalysisDate, ResponsibleAnalyst | MEDIUM |
| Missing metadata tracking | None | MissingElement, Priority, InterpretiveConsequence | HIGH |
| Epistemic tagging | None | EpistemicTag (per claim) | HIGH |

---

## Notes for Future Entries
When a new study or source is processed by TOCSAS, add a row to the log above with:
1. Sequential number.
2. Source material: title, document type, or KB file name.
3. Epistemic tag from the list above.
4. Agent that processed the source.
5. Brief statement of the knowledge extracted (1–2 sentences).
6. Which output section(s) it was used in.
7. Full citation (authors, title, journal/document, year, PMID/DOI where available).
