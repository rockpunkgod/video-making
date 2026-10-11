# Reality × Cognitive Space — Native Fast-Pass Proof

One bounded, real-case native experiment. The existing approved Reality/Cognitive
Space plan supplies the question, source world and reviewed candidate action. A
new private spec supplies a single Fast Pass. This is not an Episode compiler or
a new teaching source.

`build.jsx` makes the moving-camera composition and duplicates it for the fixed
camera control. The only changed animation properties are Camera Position and
Point of Interest. Source words, projections, timing, colors, focus target,
aperture and candidate-state animation remain identical. Camera-dependent
focus distance is evaluated in each composition.

The full frozen source remains native 3D TextLayers. Each foreground projection
duplicates a real source glyph, records its native origin ID and starts at its
actual read-back position. Word wrapping uses AE's `sourceRectAtTime()` rather
than estimated font widths. Capture, comparison and return happen in the same
world. No explanatory cards or final-answer event are added.

Clarity revisions can bind per-word and label opacity tracks. Every original
word remains present; the audit compares actual native visibility with the
authored handoff so that both variants cannot silently share the wrong track.
Source text stays static and the foreground contains only selected original
words with their own origin bindings.

`text_alignment: shared_baseline` uses an AE-measured reference glyph to put
source words on a common font baseline, rather than aligning each glyph's top.
Optional `comparison_layout` rows bind projection IDs, a settled sample time,
baseline and type size. Native readback checks their actual positions, anchor
points and effective font sizes. Equal A/B tracks alone do not establish correct
typography. Older specs without these fields retain their original layout when
run with their bound execution version.

For a candidate entering comparison, first restore attention to its existing
source text and label. Hand off source/projection opacity while both occupy the
same measured origin and have 100% source scale; start spatial motion afterward.
Grow to the comparison type size during travel. A clone that fades up after
silently growing, then rushes in from the edge, breaks perceived continuity.
Keep the already accepted camera, other objects, settled comparison and reviewed
judgment unchanged. Read back the previous/new native audits to limit changes to
the candidate's source visibility and projection position/scale/opacity; inspect
native and encoded frames around recognition, handoff, travel and arrival.

### Preserve spatial and camera identity

The moving-camera B film is the production direction. Fixed-camera A remains
an experimental control. Keep the source paper as the persistent world plane,
with captured words travelling from measured origins into a nearer working
plane. Keep camera Position, Point of Interest and focus following attention
through search, capture, comparison and the return to the original question.
Readability comes from aligned word baselines, selective visibility and a
brief settled comparison within that same 3D world. Preserve perspective,
depth separation, native motion blur and continuous source-to-projection motion
while refining the layout. Use restrained depth of field with readable text.

The entry-r1 revision preserves every frame of clean-r2 camera/focus tracks and
the settled comparison. The user's positive D-entry feedback is accompanied by
an explicit requirement to retain the earlier 3D and camera feeling. Keep both
as the next revision's visual baseline; a camera change needs its own viewing
review. Engineering track identity alone does not certify perceived depth.

Carry forward all compatible earlier requirements from the
[current production baseline](../../../docs/workflows/CURRENT_PRODUCTION_WORKFLOW.md#制作要求的延续),
including Swiss tension, first-person attention, full-source search, orange/blue
attention cues, smooth restrained focus magnification, transparent extraction,
natural task language and 4K delivery. A local typography or entry revision does
not reset those requirements. Later explicit corrections take precedence over
obsolete historical defaults; preserve old proofs for replay.

`motion.jsx` adapts physical motion from Native Creative Proof r7 and camera
velocity from Method Relay Fulltext Native. Those experiments provide motion
techniques; their synthetic language analysis provides no semantic authority.

## Private inputs and execution

Author `NATIVE_SPEC.json` in a fresh, ignored `local-data` revision. It binds the
existing parent plan, upstream bundle/status, source-word ranges, projections,
candidate events, execution files and selected font bytes. Canonical spec SHA
uses the existing `video_contracts.sha()`. Exact word coverage and the unchanged
candidate action are checked before execution.

Run from the repository root with AE's existing JUNKDOGE bridge active:

```powershell
python -X utf8 ae/experiments/reality-cognitive-fast/run.py check local-data/<revision>
python -X utf8 ae/experiments/reality-cognitive-fast/run.py build local-data/<revision>
python -X utf8 ae/experiments/reality-cognitive-fast/run.py audit local-data/<revision>
python -X utf8 ae/experiments/reality-cognitive-fast/run.py preview local-data/<revision>
python -X utf8 ae/experiments/reality-cognitive-fast/run.py render local-data/<revision> --variants A B
python -X utf8 ae/experiments/reality-cognitive-fast/run.py package local-data/<revision> --variants A B
```

Use a new project and output directory. Build, preview and render refuse to
overwrite prior outputs. Preserve the current AE session in the new revision's
snapshot before creating the independent project. No Premiere project is
modified for this silent visual proof.

To replay an already delivered revision, retain its original spec and receipts.
Use the execution files from that revision's commit or its byte-matched archive;
do not refresh input hashes just to run an old spec through changed code.
Copy the spec into a new private revision, change only the output `project` and
`scratch` paths, and recompute `spec_sha` with `video_contracts.sha()` over all
other fields. Keep the parent, frozen input fingerprints, word ranges, actions
and authored tracks intact. A new output envelope gets a new spec SHA; it must
not be represented as the original delivery's receipt or human approval. The
saved AEP is also directly editable, with both named compositions retained.

Every AE write runs through `HostOwnership`, with native process/project/target
identity checked before and after the call. A timeout leaves ownership uncertain;
it never triggers replay or takeover. `recover_failed_dispatch()` supports only
an explicit, byte-bound server failure receipt and the same occupied token. It
rejects a timeout and validates the recovered native identity before restoring
ownership. The caller still supplies the inspected, server-issued recovery call.

Rendering uses native AE TIFF batches and the user's 1 GiB free-memory reserve.
Do not send a second AE call while a synchronous render is pending. If AE shows
a modal warning, inspect its actual text, verify the held ownership and current
project, and record any acknowledgement. Acknowledging a dialog does not justify
retrying the render. The tested run encountered one undo-group warning, retained
the finished frames, acknowledged that warning and continued the same call.

`package` verifies every native frame SHA, encodes those frames to 4K Rec.709 H.264
and checks the actual dimensions, rate, frame count and full decode. FFmpeg only
packages AE-rendered pixels; it does not render a substitute animation.

## Evidence and stop

Keep the native identity/audit, per-batch transfers, host receipts, input
protection, media index and human-review document beside the private project.
The audit reads all animation tracks and every output frame's candidate state.
It proves the camera control and upstream-consistent state changes. It does not
prove that a viewer understood the comparison or found the film compelling.

Deliver full-screen A/B and retain the approved parent film. Ask for separate
judgments of expert attention, continuous-world cinema and visible causality.
Stop there. Do not add a slow replay, expand the Episode or inherit the parent's
direction approval as acceptance of the new camera proof.

Real exam text, AEP, TIFFs, MP4s and private receipts remain ignored local data.
Public render readiness remains false.
