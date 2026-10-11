# R06 B06 bounded judgement A/B

This experiment produces six native 3840×2160, 24 fps excerpts from the existing
Episode and complete candidate history. It stops at G3 human viewing and listening;
`public_render_ready=false`. Real source text, review decisions, media and Adobe
projects remain under ignored `local-data/free-showcase/b06-judgement-r3/`.

## Revision and review boundary

The committed r2 preparation and its original `ANNOTATION_REQUEST` retain
`HOLD_MISSING_FINE_ANNOTATION`. They are historical evidence and are not rewritten
to PASS. G0 was not rerun for r3.

Following explicit authorization, r3 freezes a separate host-authored AI review of
`quantity_claim`, `shared_time_context`, `screen_problem` and `nature_response`.
Each decision states its exact range, required context, allowed primitives,
purpose, basis and prohibited inferences. The producer is
`content_os.phrase_review`; this is an independent host artifact, not an ANSWER
exporter's native review type. It remains `ai_reviewed`,
`independent_human_certified=false`. No original FrozenBundle, answer or Registry
record is modified.

`ae_production.phrase_consumer` binds the original request, Action, Relation,
source fingerprints, reviewed operations and supplied current local status
manifests. It returns `READY_FOR_BOUNDED_G2` only for that exact plan. Partial
support returns HOLD; an approval boolean cannot unlock it. The whole upstream
status manifest is currently hashed: even a harmless re-export can cause a
**current bounded credential binding mismatch**, without proving that teaching
meaning changed. These reads do not certify a live external upstream service.

## Actual production scope

All intervals below are zero-based and end-exclusive. NEW source time includes
144 inserted observation frames before the B decision; complete voice takes move
as units and the captions and source-clock mapping are recalculated.

| Variant | Native source interval | Frames | Duration |
|---|---:|---:|---:|
| OLD_B06_FULL | [6905,7595) | 690 | 28.750 s |
| NEW_B06_FULL | [6905,7739) | 834 | 34.750 s |
| OLD_CONTEXT_VISUAL | [6374,7746) | 1372 | 57.167 s |
| NEW_CONTEXT_VISUAL | [6374,7890) | 1516 | 63.167 s |
| OLD_CONTEXT_FULL | [6374,7746) | 1372 | 57.167 s |
| NEW_CONTEXT_FULL | [6374,7890) | 1516 | 63.167 s |

The visual controls omit **all VO and explanatory captions**, retaining music.
Their native AE caption mask is a presentation change, including in the OLD
control. Exact source-clock correspondence therefore does not assert pixel
identity with the old whole-episode picture. The FULL files contain the complete
existing takes and explanatory captions. Music rights remain
`UNKNOWN_INTERNAL_ONLY`.

Native audit checks the actual source composition, retained text objects,
source ranges/comments/spec, motion keys and all six excerpt references. The full
candidate prefix derives B/C/D → C/D. The following retain-C action still leaves
C/D; the final answer requires all remaining actions. Static frame inspection is
agent implementation QA, not evidence of audience comprehension.

## Entry points and evidence

| Entry | Responsibility and private evidence |
|---|---|
| `run.py` | Historical prepare-only G0/G1; r2 handoff and missing-annotation request |
| `produce.py` | Revalidate exact r3 review/input bindings; native build and bounded readback audits |
| `build.jsx`, `audit.jsx` | Native source/text/geometry and actual identity/keyframe inspection |
| `render.py` | Owned AE preview and bounded render, byte-verified frames, exact 4K24 picture packaging |
| `audio.py` | Full-sample voice plan, retimed captions and music excerpts/ducking |
| `premiere.py` | Owned native PR sequences, complete source/placement/rate audit and explicit-preset export |
| `delivery.py` | Cross-variant binding checks, actual encoded color comparison, delivery and frame/sample maps |

Private receipts include `PRODUCTION.json`, `HOST_PHRASE_REVIEW.json`,
`G2_CONSUMPTION_RECEIPT.json`, `NATIVE_AUDIT_SUMMARY.json`, per-render receipts,
`AV_PLAN.json`, `PICTURE_INDEX.json`, `PR_WORKSPACE.json`, per-sequence native
audits, `EXPORT_INDEX.json` and `DELIVERY_INDEX.json`. Partial indexes remain
incomplete until all six named variants have actual receipts. Existing results
are never silently overwritten or duplicated.

## Adobe execution and recovery

This r3 entry wires every Adobe write through
`ae_production.host_ownership.HostOwnership`, including project switching,
activation, render configuration, native edits, Save As, save and export. AE and
PR have independent exclusive leases. Each mutation checks live process,
project and active composition/sequence before and after. Other experiments are
not globally retrofitted by this work.
Normal acquisition first compares the active project with the intended
`PRODUCTION.project` or `PR_WORKSPACE.project`. Only the build/setup call's
explicit transition to a new, absent project permits a different initial
project. This moves the intention check before acquisition and covers
preview/render/export as well as the existing pre-import check in assembly.

Timeouts or identity drift preserve UNCERTAIN ownership; there is no automatic
retry, TTL or takeover. The initial large AE build timed out but had actually
completed and saved. Read-only reconciliation checked that completed result;
the build was not replayed. Explicit reconciliation preserves the same token,
previous record, byte-bound completion evidence and two fresh identity reads.

A later render stopped between completed calls at 480 verified frames for the
memory reserve. The old controller was confirmed stopped and the completed batch
evidence reconciled under its original token. Rendering resumed in 48-frame
batches with MFR at 50%, cache purge before/after each batch and the user's 1 GiB
reserve. No in-flight operation was duplicated or cancelled.

## Sound, encoding and known color limitation

PR readback checks whole source ranges, actual source item/path, speed 1, exact
sample placement and flat native levels. A measured import snap is corrected
once by a guarded native move, then re-read to the original sample position;
tolerances are not relaxed to declare success. Export checks voice waveform
presence, duration, 4K24 frames, stereo 48 kHz and full decode. These checks do not
certify pronunciation or listening quality.
Mappings distinguish native timeline sample placement from the measured AAC
priming offset in decoded output; a native exact placement does not assert zero
codec delay. The actual offset and correlated complete-take window are retained.

The explicit, previously verified Match Source preset is revalidated against
each actual 4K24 sequence. Real encoded frame comparison reproduced Premiere's
color difference and absent Rec709 tags. Affected deliveries reuse the existing
lossless handoff: native AE picture video packets plus actual native PR audio
packets/timestamps, with explicit Rec709 and full decode verification. Original
PR exports and color captures are retained. This does not claim the PR color
problem is fixed.

The first TIFF-derived OLD visual picture also lacked two H.264 color metadata
fields. Its original bytes and PR source reference are retained. A separate
metadata-only derivative fills those missing fields; all 1372 decoded frame
hashes and timestamps match the original. The final handoff records both that
video parent and the original PR picture SHA. Later TIFF encodes set frame-level
color parameters and verify the actual decoded tags before entering PR.

## Current stopping condition

All six outputs and both saved native project identities were verified on
2026-10-11. `G2_FINAL_TECHNICAL_RECEIPT.json` records the final hashes and
`DELIVERY_INDEX.json` contains all six real media/mapping pairs. Both native
leases are released; production has stopped at G3.
`FRAME_TIMECODE_MAP.md` and `ACTUAL_EVENT_MAP.json` map audited native event
frames and complete voice takes into each delivered excerpt. No interval is
presented as proof of audience comprehension.
`G3_REVIEW.md` preserves four separate human decisions: candidate-state
recognition, difference between the compared subjects, understanding of the
whole judgement, and continuity with adjacent beats. Listening remains a
separate PENDING decision. Technical delivery and agent still-frame QA never
set these to PASS. No whole-episode expansion or public release is included.
