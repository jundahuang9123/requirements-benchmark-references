# Input-label review, 1 November 2026

Assistant review of all 196 scored atoms in the supplied review workbook: 76 test
atoms (Mobility and Geo) and 120 development atoms. The original labels and
rationales were visible. This is a non-blind machine review, **not independent
human validation**, and no benchmark evidence label or score has been changed.

The complete [review table](2026-11-01-label-review.csv) retains the original label,
proposed assistant label, worksheet need, current standardized statement, reason
and source locator for every atom. `changed` marks the 21 proposed revisions.
The workbook and this table are evaluator-only and must not enter extraction
inputs, prompts, retrieval, or tuning on held-out cases.

## Scope and rules

The review evaluates the worksheet's need, applicability and status against the
frozen **raw** input allowlist. All 196 worksheet statements exactly match the
current atoms' `statement_before_standard`. This review does not adjudicate
consolidation-mode labels, the remaining 124 unscored atoms, taxonomy assignments,
or source completeness. It does not add later web sources to historical inputs.

- Supported: the input explicitly supplies the semantic information/capability
  for the relevant resource, preserving substantive scope and explicit conditions.
  Defined metadata properties and contextual requirement tables count; an isolated
  topic token is insufficient.
- Partial: an identifiable component is supported but another substantive
  component is missing. Incidental wording about a different entity is insufficient.
- Unsupported: no relevant statement of the need was found in targeted searches
  of the available raw corpus. This is not proof of absence from all possible sources.
- Uncertain: ambiguity or unavailable evidence prevents a decision. None remained
  under these rules; eliminating that category does not eliminate judgement uncertainty.

Purpose clauses can be supported by the documented use of the information.
Optional fields or examples cannot establish universal obligations. Additional
`modality` values outside the worksheet were not independently certified for every
atom. A need-level support decision must not be reported as full obligation-level
equivalence. Moving a constraint into a hint does not silently change its label.

## Results

| Case | Atoms | Original supported | Proposed supported | Proposed partial | Proposed unsupported | Changed |
|---|---:|---:|---:|---:|---:|---:|
| mobilitydcat | 39 | 31 | 29 | 10 | 0 | 4 |
| geodcat | 37 | 37 | 37 | 0 | 0 | 0 |
| healthdcat | 89 | 59 | 53 | 32 | 4 | 8 |
| statdcat | 14 | 4 | 3 | 7 | 4 | 3 |
| jrc-research | 17 | 6 | 4 | 12 | 1 | 6 |
| **Total** | **196** | **137** | **126** | **61** | **9** | **21** |

The revisions comprise 11 supported → partial, eight uncertain → partial,
one uncertain → unsupported, and one unsupported → partial. The 175 other labels
are retained. If accepted under this rubric, the supported-only denominator would
be 126 and supported-or-partial would be 187 (previously 137 and 178). These are
proposed label counts, **not recomputed benchmark scores or approved denominators**.

## Proposed changes

| Atom | Original → proposed | Reason and input locator |
|---|---|---|
| Req-17.1 | supported → partial | The inputs require a metadata date, but do not require time-of-day precision. DCAT date/dateTime alternatives and a BIBFRAME example do not establish a timestamp obligation. (inspire-metadata.html, Annex B 10.2; inspire-metadata-guidelines-1.3.pdf, PDF p.60; w3c-dcat-2-2020.html, 6.5.4) |
| Req-19.7 | supported → partial | The CMC inventory names payload location referencing, but explicitly is only a concept inventory. INSPIRE Article 7(4) governs georeferencing rules, not a metadata description of the payload georeferencing method. A bare concept name is insufficient under this review rule. (cmc-2019-concept-inventory.json, representation and CMC-11; inspire-directive.html, Article 7(4)) |
| Req-30.2 | uncertain → partial | The inputs cover identifying a data model and explaining its format, but do not specify its publication type. This is identifiable partial coverage, rather than an undecidable evidence relation. (cmc-2019-concept-inventory.json, CMC-25 and CMC-26) |
| Req-30.3 | uncertain → partial | Identifying conformed specifications/data models is supported; describing extensions of that model is missing. Multiple conformed specifications do not by themselves identify model extensions. (inspire-metadata.html, Annex B 7.1; cmc-2019-concept-inventory.json, CMC-25 and CMC-26) |
| H-12.1 | uncertain → partial | Conceptual datasets and dataset granularity are discussed, but warehouse partitioning into coherent virtual datasets with one record each is not specified. The known missing qualifier makes partial the more informative label. (w3c-dcat-2-2020.html, 5.1; landscape-analysis-ms6.1.pdf, PDF pp.13 and 16) |
| H-21.1 | supported → partial | The contact point is recommended with cardinality 0..n, not required for every dataset. Sending comments or feedback also does not establish the full helpdesk role. (dcat-ap-2.1.1.pdf, PDF p.16, 4.4.2; w3c-dcat-2-2020.html, 5.3) |
| H-23.1 | supported → partial | The proposal distinguishes personal from non-personal data, but the cited catalogue fields describe aggregation and personal identifiers. Aggregated/individual is not equivalent to non-personal/personal; an explicit dataset classification is missing. (ehds-proposal.html, Article 41(6); landscape-analysis-ms6.1.pdf, PDF pp.4 and 21) |
| H-27.1 | supported → partial | The publisher is responsible for making data available and a data holder can make data available. These separate definitions do not require the publisher to be the accountable data holder; roles can differ. (dcat-ap-2.1.1.pdf, PDF pp.28–29, section 7; ehds-proposal.html, Article 2(2)(y)) |
| H-33.1 | supported → partial | The derivation link is explicit. The additional clause asks research derivatives to cite the metadata identifier, whereas the input citation guidance names the dataset identifier. These identifiers cannot be equated without evidence. (dcat-ap-2.1.1.pdf, PDF p.18, source; w3c-dcat-2-2020.html, section 11) |
| H-37.2 | supported → partial | Population/sample size and observation-unit counts are relevant, but do not establish a count of unique individuals. One individual can contribute multiple observations; the unit and distinctness must be stated. (landscape-analysis-ms6.1.pdf, PDF pp.10, 19 and 21) |
| H-37.3 | supported → partial | Distribution byte size is explicitly defined, but the worksheet condition says mandatory for protected NSIP data. The staged profile makes byte size optional (0..1), with no NSIP-specific requirement. Content-only matching would be supported; the worksheet obligation is not. (dcat-ap-2.1.1.pdf, PDF p.19, 4.5.3; w3c-dcat-2-2020.html, 6.7.12) |
| H-45.1 | uncertain → unsupported | The input describes trusted open databases, not a trusted-data-holder designation. Neither the holder status nor a facet for it is stated. The superficially similar trust wording applies to a different entity. (ehds-proposal.html, Articles 41(6) and 49(1); searched all five raw inputs for trusted-holder status/facets) |
| S-4.1 | unsupported → partial | Data Cube explicitly discusses graphs/charts for presentation, so there is relevant partial evidence. It does not provide catalogue links to visualisations or model them as visualisation distributions. The original no-passage cell misses this evidence. (w3c-data-cube-2014.html, sections 2 and 5.3) |
| S-7.3 | uncertain → partial | Publication/update frequency is stated, but it is not necessarily the periodicity of observations in a time series. The missing meaning is identifiable; do not count publication frequency as full recovery. (w3c-dcat-2014.html, 5.3 frequency and 4.1; w3c-data-cube-2014.html, 5.3) |
| S-17.1 | supported → partial | Data Cube links a qb:DataSet to its DSD. The target instead asks for a link from an RDF distribution. The inputs do not establish that resource mapping; a dataset-structure link is relevant but not sufficient. (w3c-data-cube-2014.html, 7.1 and 11.1 IC-2; w3c-dcat-2014.html, 5.4) |
| JRC-3.1 | uncertain → partial | The sources give technical/method information and metadata that enables use, but do not explicitly provide how-to-use notes. These cover part of the intended information, with the specific usage guidance missing. (datacite-3.1-field-context.json, Description; jrc-data-policy-2015.pdf, PDF p.7, Article 5(2)) |
| JRC-6.2 | uncertain → partial | A dataset identifier can be part of its URI, but the passage does not require HTTP encoding wherever possible. Identifier representation is covered only in part. (w3c-dcat-2014.html, 5.3 identifier) |
| JRC-6.5 | supported → partial | The synopsis associates types with alternate identifiers and schemes with creators, but does not qualify every identifier, including related identifiers. The universal scope is stronger than the supplied input. (datacite-3.1-field-context.json, AlternateIdentifier, Creator and RelatedIdentifier) |
| JRC-8.1 | supported → partial | DCAT distinguishes direct downloads through downloadURL, but explicitly says a distribution implies no access-method information and API-specific properties are outside its scope. That does not fully identify service/API distributions. (w3c-dcat-2014.html, sections 4 and 5.4) |
| JRC-10.1 | uncertain → partial | Data quality and metadata supporting evaluation are discussed, but describing the assessments themselves is not required. Partial records the topic support without inventing an assessment field. (jrc-data-policy-2015.pdf, PDF pp.6–7 and 9, Articles 2(2)(c), 5(2) and 13(b)) |
| JRC-10.2 | uncertain → partial | A contact point receives dataset feedback; exposing that feedback as quality information is not stated. The input supports collecting feedback, not publishing quality annotations. (w3c-dcat-2014.html, 4.1 basic example) |

For S-4.1 the additional passage is in the frozen W3C Data Cube 2014 input,
section 5.3, Introducing Slices: slices help a consuming application construct a
graph or chart for presentation. This supports the visualisation topic, but not
catalogue links to visualisations or modelling them as distributions.

## Checks and limits

- All 564 worksheet quotations match the current raw-evidence records and were
  found in their frozen allowlisted inputs after the validator's text normalization.
  The additional S-4.1 passage was also verified. Quote existence is distinct from
  semantic support; that distinction accounts for several proposed downgrades.
- All original worksheet columns A–L, its 48 count formulas, freeze panes and
  decision validation were preserved in the checked copy. Each row has exactly one
  assistant decision and a source-located note. Both affected sheets were rendered.
- No external human annotator participated. Existing model labels/rationales were
  visible, so this review cannot supply blinded inter-annotator agreement.
- Original source versions remain decisive. For example, JRC uses the staged
  DataCite factual synopsis, not an unavailable original PDF; Health uses the staged
  EHDS proposal, not later adopted legislation.

## Paper-facing assessment

The standardized statements, preserved earlier wording, explicit atom types and
recorded-versus-reconstructed trace distinctions make the set easier to explain
and audit. The 320 atoms and the 196 default scoring units are unchanged.

Three issues remain before treating it as a finalized benchmark:

1. Freeze the matching contract: specify whether the statement, conditions,
   modality and hints all participate in equivalence. The current methodology
   includes obligation while the standardized sentence deliberately omits it.
   Do not reinterpret inherited evidence labels or historical mock results silently.
2. Independently review a source-grounded sample of content/profile/system coding
   and evidence labels. The documented curator batch review of wording is useful,
   but it is not independent human validation of the labels or taxonomy.
3. Keep release verification scoped accurately. The trace checker requires the
   baseline tag/history; a history-free anonymous export cannot currently rerun
   that full check. The older corpus-validator issues remain recorded in the
   [import archive](../import/IMPORT-VALIDATION.md).

## Snapshot identity

The reviewed content is the standardized reference snapshot of 1 November 2026.
Public Git identifiers and workstation paths are omitted from this distributed
report; the content hashes below identify the review target without author history.

Supplied workbook SHA-256: `9c6f5638af35d7cbb68507bfdd5f901227927b23ae6728b2c0df1b0210cf37f0`.

| File | SHA-256 |
|---|---|
| `benchmark-data/runtime-inputs.json` | `a719e64c2d1d906e0081cfc61ef9d29e220ea4c75ec1a80b83e750b812184761` |
| `benchmark-data/reference-sets-v3/mobilitydcat.json` | `250a1bbb28ecbea804c75cfce2b5e81e806e40d824664626694084ec4597668a` |
| `benchmark-data/reference-sets-v3/geodcat.json` | `a88694bb2158fd3c7475f397b56567e7bd3e9c380a9631d82f7f52a8d44f64f7` |
| `benchmark-data/reference-sets-v3/healthdcat.json` | `ad04a7bb68bd2b76ae3fa323bc1f1ea3aa8fd430adf30db9e3f47234480ebde9` |
| `benchmark-data/reference-sets-v3/statdcat.json` | `1083d9a8762e2f317dfc094910c6371b565c3168beee1a89df7e997a7f5b9423` |
| `benchmark-data/reference-sets-v3/jrc-research.json` | `a50429ad55c85c68b12343443f8cdb9559867cceb59ce0c6b0e558d009bc6014` |

Raw-input inventory digest (31 paths, sorted `path\tsha256\n`, UTF-8): `14dbceba011f2890b951a8d923455fbb35c7030dfe74590fa41d0c7770db7e16`. Individual input hashes remain in `IMPORT-PROVENANCE.json`.
