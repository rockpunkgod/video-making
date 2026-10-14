# Revision 2 alignment — 2026-10-14

The supplied second edition clarifies delivery rules; its sample sentences remain tone examples, not teaching credentials.

- Use a peer's present-tense working voice, without invented biography or scores.
- Treat 18 Chinese characters, 55% narration coverage and six-second silence as initial review lines. Record duration and reason for reading/cognitive pauses; never pad narration.
- Evaluate locating, reduction, decision and verification by their actual roles. Third-party answers detect conflicts; they do not grant answer permission.
- Candidate trap names require three reviewed examples before activation, and each use needs its own frozen exclusion rationale. `同题跑偏` is a candidate label, not an activated rule.
- Preserve continuous camera travel, slowing for recognition and judgment. Inspect rendered camera velocity; do not impose a full stop at every action.
- Keep foreground palette restrained and one orange attention target at a time. Visual impact still requires a supported cognitive change.

## Implemented answer-scope correction

The 0.3 compiler now accepts explicit `answer_scope: full_solution` for a `worked_example` from a frozen asset. It requires a decider, current ACTIVE dependencies, produced/reviewed selected actions covering every option, exactly the frozen answer retained, every other option eliminated, and the existing full-solution engineering gate. The Copy handoff carries that scope. No Reveal file is read.

Omitting this option preserves the old bounded-action projection and its replay hashes. A closed upstream question does not automatically turn a partial selected action into a complete solution. Version 0.4 and boundary-review paths retain their existing contracts; unsupported combinations reject rather than silently drop the request.

Schema, CLI and replay validation use the same scope. Resealing an edited answer does not pass replay. This grants neither public release nor natural-speech approval.

## Real R06 assets

The prior audit found a closed C answer for the Bond question, and only D elimination for the cat question. Both old bundles were SUPERSEDED against the audited current epoch. This code change does not refresh or revive them: production still needs current ANSWER exports. Cat A/B/C closure remains an upstream task.

Role-specific sampling, six-field move cards, new trap activation records and camera changes are subsequent work, not completed by this patch.
