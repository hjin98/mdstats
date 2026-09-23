# `docs/summary` documentation-agent instructions

## Scope and purpose

These instructions govern every human-facing summary paper created or updated under `docs/summary/`.

Summary papers are **derived explanatory publications**, not D1/D2/D3/D4 authority. Their purpose is to explain a selected domain of the current accepted `mdstats` code authorities accurately, compactly, and pedagogically. Never use a summary to introduce, resolve, or silently modify scientific, numerical, architectural, or implementation semantics. When a summary conflicts with an accepted authority, the authority wins and the summary must be repaired.

Before writing or updating a summary, identify and read the complete current authority chain needed for the topic. Use D1 scientific-method, D2 numerical-method, D3 architecture, D4 specification/implementation, guides, and evidence only where they materially govern the subject being summarized. Do not reconstruct current truth from stale workplans or historical documents when a current owner exists.

## Default audience

Write for **physicists as the primary and default audience**. Assume familiarity with ordinary undergraduate/graduate physics, molecular dynamics, standard mathematical notation, probability/statistics at a working scientific level, and common atomistic-simulation concepts.

Do **not** assume expertise in machine learning, data science, software architecture, database concepts, or project-specific `mdstats` terminology. Explain those ideas when they matter.

If the user names another audience, adapt to it; otherwise keep the physicist audience.

## Required writing standard

Every summary must be:

- **Human-facing and explanatory.** Explain what the method/system is doing, why it is needed, and how the pieces fit together; do not merely paraphrase implementation identifiers.
- **Pedagogical when the concept is difficult for the target audience.** Introduce intuition before or alongside formalism. Use a small example, schematic, physical analogy, or staged derivation when it materially lowers the conceptual burden.
- **Short and focused.** Cover the authority domain of interest completely enough to understand it, while omitting lower-level detail that does not change the scientific or operational meaning.
- **Refined and easily digestible.** Prefer a coherent narrative, informative section titles, short paragraphs, and equations that advance the explanation. Avoid walls of jargon, exhaustive implementation inventories, and amendment-style prose.
- **Well written.** Use precise scientific English, stable terminology, and clean notation. Expand non-obvious abbreviations at first explanatory use.
- **Self-contained for its stated scope.** Include the background and definitions needed to understand every material concept used later in the paper. Do not depend on hidden chat context or undocumented project knowledge.

## Background and definitions

Introduce project-specific and non-common concepts before using them substantively. For each important concept, prefer the sequence:

1. plain-language physical or computational motivation;
2. precise definition or mathematical statement;
3. interpretation of the variables, units, domains, or sets;
4. what the definition means physically or operationally;
5. important limitations or distinctions that prevent common misreadings.

Use mathematics when it makes the semantics clearer, not decoratively. Define symbols near first use. Explicitly distinguish quantities that readers may otherwise conflate, such as dataset cardinality, feature-space coverage, statistical weight, model loss, and predictive accuracy.

## Relationship to current authorities

A summary must state or make clear which accepted current authority documents it summarizes. Project-specific thresholds, algorithms, defaults, policies, and invariants must be traceable to those authorities.

Do not make an implementation detail sound scientifically mandatory unless the owning authority makes it so. Conversely, do not omit a material invariant merely because it is inconvenient to explain. If the current authority is contradictory or materially unclear, stop summarizing that point as settled and surface the ambiguity for the owning-domain review.

## External references

Every substantive summary paper must include a concise **external references** or **scientific context** section.

Use references to orient the physicist reader to established external concepts, literature, and standard methods. Prefer:

- primary scientific papers for the method or representation being explained;
- authoritative review articles for broader context;
- official project/library documentation for external software behavior when relevant.

Use stable DOI or publisher links when available. Verify bibliographic details before publication.

External literature provides context and support; it does **not** become the authority for project-specific `mdstats` semantics unless an accepted authority explicitly imports it. Make that distinction explicit when a reader could otherwise infer that an `mdstats` threshold, ordering rule, feature family, or policy comes from the cited literature.

Do not fabricate citations and do not cite a paper merely because it is topically adjacent.

## Recommended paper structure

Use the minimum structure that preserves clarity. A good default is:

1. **Title and one-paragraph central idea** - what problem is being solved and the core strategy.
2. **Background and notation** - define the population/system, key objects, and why the problem is nontrivial.
3. **Representation or governing physical quantities** - explain how the relevant state space is constructed.
4. **Core definition(s)** - give the central mathematical or operational definition and interpret it in words.
5. **Algorithm or data/control flow** - explain how the desired property is achieved in practice, at the level necessary to understand the method.
6. **Physical interpretation and limitations** - explain what the result means and what it does not mean.
7. **Authority and external context** - identify the internal current owners and provide verified external references.

Adapt this structure to D3/D4 topics rather than forcing mathematical sections where architecture or interface semantics are the real subject.

## Markdown/PDF publication contract

For a summary publication, keep a sibling pair:

```text
<name>.md
<name>.pdf
```

Treat the Markdown as the editable source and the PDF as its rendered publication. Do not independently edit the PDF to create semantics absent from the Markdown.

After changing a summary Markdown file:

1. rebuild the sibling PDF using the repository documentation publication workflow where available;
2. visually inspect every rendered PDF page;
3. verify equations, tables, links, references, figure labels, line wrapping, and page breaks;
4. fix clipping, overlap, broken glyphs, excessive density, or awkward pagination before completion.

The Markdown and PDF must communicate the same substantive content even when typography differs.

## Completion check

Before declaring a summary complete, verify all of the following:

- the intended audience is a physicist unless explicitly overridden;
- the relevant current authority chain was read rather than inferred from code or history alone;
- the paper has enough background to stand on its own;
- all material project-specific terms and symbols are defined before they are needed;
- difficult concepts receive an intuitive or pedagogical explanation;
- the narrative is concise, refined, and easy to follow;
- no material authority semantics were lost or invented during compression;
- internal authority sources are identified;
- external references are relevant, verified, and clearly separated from project-specific authority;
- the Markdown/PDF pair is synchronized and the final PDF has passed visual QA.
