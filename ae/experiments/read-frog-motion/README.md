# Read Frog motion A/B experiment

This is a bounded native After Effects experiment, not a replacement production
entry. Continue normal production through
[CURRENT_PRODUCTION_WORKFLOW](../../../docs/workflows/CURRENT_PRODUCTION_WORKFLOW.md).

The local `read-frog-motion-ab-r02` trial contains two actually rendered
12-second, 3840 × 2160, 24fps variants and one editable AEP. A preserves the
current source transforms. B changes camera continuity, foreground carrying,
extraction, context emphasis and **phrase-chunk** focus. Original text, fonts,
source bindings, judgment timing and the complete narration take are unchanged.
The local report keeps measured checks separate from pending human review.

## Files and actual consumers

- `motion-rig.jsx`: continuous Hermite motion, native temporal ease and explicit
  chunk focus functions. All words within a chunk share one phase; chunks take
  focus in sequence. This helper does not infer teaching facts or token groups.
- `build.jsx`: duplicates the authorized current native scene into A and B,
  constructs the native controllers, then saves a separate project.
- `run.py`: existing bridge, parent-input checks, shared Adobe ownership,
  independent preview/render receipts and exact host restoration.
- `audit.py`: reads actual native curves, source identities, complete text,
  chunk ranges, expression values, projections and output specifications.
- `verify_media.py`: decodes actual output frames, checks timestamps and audio
  identity, and produces encoded-frame contact sheets and a labelled comparison.
- `make_report.py` / `review-template.html`: local review document assembled from
  actual media receipts. The template is specific to this trial, not a generic
  report generator for arbitrary cases.

Private inputs, reference video, extracted frames, render parts, media and
receipts stay outside version control. The trial needs a current, bound private
`TRIAL_INPUT.json`; a public clone does not contain production evidence or media.
Do not invent missing inputs or replay a build with an unknown result.

## Validation scope

The completed trial has native readback, full video decode, identical decoded
A/B audio, motion-blur on/off pixel checks and restoration receipts. Existing
authored-episode and shared-ownership regressions passed (41 tests). These do
not establish aesthetic approval, listening approval, student outcomes or
production integration. The comparison scene retains candidate A; it does not
claim to finish the entire question or validate a full downward search sequence.

The local `REVIEW.html` links the reference breakdown, audit, motion parameters,
actual A/B MP4s, contact sheets and ten evaluation criteria. After visual review,
the smallest integration is to reuse accepted helpers in the current readPath,
lift and candidate consumers, retaining the existing author clock and pipeline.
No experimental default has been promoted to the main film.
