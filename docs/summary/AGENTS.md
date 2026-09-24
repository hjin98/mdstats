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
- **Visually publication-quality.** The PDF is part of the communication contract, not a mechanical afterthought. Typography, hierarchy, mathematical typesetting, spacing, tables, callouts, diagrams, headers/footers, and page breaks must be deliberately composed for comfortable reading.

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

## Visual presentation standard

The current MLFF training-coverage summary establishes the preferred visual character for this documentation family: restrained scientific-paper styling, generous whitespace, a clear title hierarchy, calm serif body typography, blue section headings, compact well-aligned tables, shaded explanatory callouts where they add value, centered display mathematics, simple diagrams, unobtrusive running headers, and page numbers.

Treat that as a **quality reference**, not a rigid pixel template. New summaries may vary when their content calls for it, but they must remain equally polished and readable.

Required presentation rules:

- Mathematical expressions must be rendered as real typeset mathematics. Never ship raw TeX commands, broken Unicode substitutions, malformed delimiters, fragmented sums/fractions/radicals, or equations whose visual structure changes the intended mathematics.
- Display equations must have adequate whitespace, correct alignment, legible subscripts/superscripts, and sensible line breaking. Verify the rendered equation against the source definition, not merely that the PDF build succeeded.
- Use visual hierarchy to reduce cognitive load: title/subtitle, section headings, explanatory callouts, tables, and diagrams should each have a distinct but restrained role.
- Prefer a professional scientific-document typeface and comfortable body size. Do not shrink text to force a page count.
- Use color sparingly and consistently. Section color or light callout shading is appropriate; decorative or high-saturation styling is not.
- Tables must have deliberate column widths, readable wrapping, sufficient cell padding, and no clipped rows. Avoid dense full-grid styling unless it materially improves comprehension.
- Diagrams should explain a concept or flow, not decorate the page. Labels must remain readable at normal fit-to-page viewing.
- Maintain generous margins and natural vertical rhythm. Avoid stranded headings, large accidental whitespace, crowded bottoms of pages, or paragraph/table splits that damage comprehension.
- Headers, footers, page numbers, hyperlinks, and references must be visually subordinate to the scientific content but professionally composed.
- The first page should read as a deliberate publication front page rather than a raw Markdown export.

A generic renderer is acceptable only if its output meets these standards. **Do not accept renderer convenience as a reason to degrade equations or presentation.** If the generic repository Markdown renderer cannot preserve the required mathematics or visual quality, use an appropriate high-quality typesetting path and preserve the resulting PDF as the presentation-managed publication.

## Markdown/PDF publication contract

For each summary publication keep the natural pair:

```text
<name>.md
<name>.pdf
```

Treat the Markdown as the editable semantic source and the PDF as its human-facing rendered publication. Do not independently add scientific content to the PDF that is absent from the Markdown.

Summary PDFs whose presentation is deliberately managed outside the generic Markdown renderer must be listed in the `manual` section of `docs/pdf_publications.json`. The repository PDF builder must then leave that pair untouched rather than replacing it with a lower-fidelity generic rendering.

After changing a summary Markdown file:

1. re-read the applicable current authority before editing substantive claims;
2. update the Markdown source;
3. render the PDF using a typesetting path capable of meeting the visual standard above;
4. render the resulting PDF to page images and inspect **every page** at normal reading scale and at 100% where equations/tables are dense;
5. compare every substantive displayed equation against the Markdown/source authority;
6. verify tables, links, references, figure labels, line wrapping, headers/footers, and page breaks;
7. fix clipping, overlap, broken glyphs, malformed mathematics, excessive density, awkward pagination, or weak visual hierarchy before completion;
8. keep the Markdown and PDF synchronized in substantive content.

A PDF build that merely exits successfully is **not** publication acceptance.

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
- every displayed equation is mathematically and visually correct;
- the PDF has deliberate scientific-publication styling rather than generic export appearance;
- every PDF page has passed visual QA with no clipping, overlap, malformed math, broken glyphs, weak table layout, or awkward page break;
- the Markdown/PDF pair is synchronized.
