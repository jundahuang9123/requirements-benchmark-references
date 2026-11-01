# Atom types: how they were defined and assigned

Every atom has a type in the field `stratum`: content, profile or system. Only content atoms can be scored (`scored_by_default`). This file records where the types come from and who assigned them. A fact that was never recorded is marked "not recorded".

## Definitions the labels follow

The three types were defined in the coding scheme of the 75 published rows, `history/build-scripts/v2/codes.py:4-6`:

```
level:    M = metadata content (what records should carry)
          G = profile specification/engineering (principles, alignment, reuse, obligations, docs)
          S = systems and processes around the profile (governance, validation, UI, exchange, review)
```

M became `content`, G `profile` and S `system` (`history/build-scripts/v2/build_v2.py:8`, `history/build-scripts/v3/build_v3.py:44`).

- No source in the literature was used when the types were assigned. Related work found afterwards is listed under Literature below.
- `README.md:33` gives the same three definitions in longer words. That wording was written later, for the reference trace (change D1); it was not used for labelling.
- The owner decided on 1 Nov 2026 that the paper describes the benchmark's types with these definitions.

## How each atom got its type

| Step | What happened | Who | What is recorded |
|---|---|---|---|
| R4 | The 75 published rows were coded M, G or S. | Claude, single coder | The coder (R4-F01). Model and prompt: not recorded (R4-F02). |
| v2 completion | 109 rows were added from the same documents, each with a level. | Claude, 22 Oct 2026 | `history/build-scripts/v2/completion.py:1-7`. The definitions are not restated there. |
| v3 merge | 4 rows were added from audit pass A items, each with a level. | Claude, 22 Oct 2026 | `history/build-scripts/v3/build_v3.py:121` |
| R7 | Rows were split into atoms. An atom takes its row's level unless its split table sets another (`history/build-scripts/v3/build_v3.py:155,194`). | not recorded (R7-F01) | The reasons for each type: not recorded (R7-F03). |
| R9 | The independent check found Req-14.1 to be an umbrella over Mobility's content atoms; it was moved to profile. | independent check; resolution applied in v3 | `INDEPENDENT-CHECK.md`, finding 23 |
| R10 | The labelling prompts were given each atom's type; they did not set it. | — | `history/labelling/labelling-prompts.md` |

316 of the 320 atoms have their row's type. The four others:

| Atom | Row type | Atom type | Reason |
|---|---|---|---|
| H-3.2 | system | content | not recorded |
| H-15.4 | content | profile | not recorded |
| H-40.2 | content | system | not recorded |
| Req-14.1 | content | profile | umbrella over Mobility's content atoms (finding 23) |

No person has re-labelled the types. A blind second labelling of a stratified sample, with agreement reported as Cohen's kappa, is planned in the reference trace and not yet done.

## Counts

| Case | content | profile | system |
|---|---|---|---|
| JRC | 17 | 0 | 1 |
| Stat | 16 | 9 | 2 |
| Health | 91 | 11 | 19 |
| Geo | 37 | 17 | 2 |
| Mobility | 40 | 47 | 11 |
| All | 201 | 84 | 35 |

Of the 201 content atoms, 196 are scored by default: 3 are deferred in their source, 1 is merged into an equivalent atom (Req-24.1 into Req-19.7) and 1 is an umbrella.

## Literature

Looked up on 1 Nov 2026, after the labelling. Each work covers part of the scheme; none defines these three types.

- **Content versus the rest.** NeOn's ontology requirements specification separates functional requirements, which it also calls content-specific requirements and which concern the particular knowledge the ontology is to represent, from non-functional requirements, which concern characteristics, qualities and general aspects not related to the ontology's content (Suárez-Figueroa, Gómez-Pérez and Villazón-Terrazas, *How to Write and Use the Ontology Requirements Specification Document*, OTM 2009, LNCS 5871, p. 973). Content atoms correspond to its functional requirements; profile and system atoms both fall on its non-functional side, which it does not divide.
- **Systems outside the profile.** DCAT-AP 3.0.0 leaves implementation issues, such as the mechanisms for exchanging data, outside the profile, and sets no requirements on the technical environments of communicating systems beyond its conformance statement (Introduction, "Scope of the Application Profile").
- **Three groups of requirements.** The W3C note *Dataset Exchange Use Cases and Requirements* (Working Group Note, 17 January 2019) serves three deliverables: the DCAT vocabulary, guidance on application profiles, and content negotiation by profile. Its requirements fall into matching groups: dataset description (sections 6.1–6.9), profiles (6.10–6.13) and content negotiation (6.14).
- **A source's own types.** The NAPCORE requirements analysis behind the Mobility case types its 40 requirements as General, Existing Vocabularies, Content or Implementation (field `type` in `mobilitydcat.json`). All 40 Mobility content atoms come from its Content rows, but so do 15 profile atoms (for example cardinalities, value ranges, identifier guidelines and the controlled vocabulary), so its Content type is wider than this one.
- **Not a typology.** The Singapore Framework for Dublin Core Application Profiles (Nilsson, Baker and Johnston, DCMI, 2008) lists the components of a profile and makes functional requirements a mandatory one; it does not sort requirements into types.
