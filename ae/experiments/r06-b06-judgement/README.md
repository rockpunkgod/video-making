# R06 B06 judgement revision

This bounded experiment prepares G0/G1 for one candidate judgement with its
preceding and following context. It reuses the existing Episode, Audience and
candidate-motion validators. It does not add another teaching source or renderer.

## Current result

The current frozen action authorizes a candidate elimination and sentence-level
reason. The proposed word-group extraction needs explicit fine annotation.
Preparation therefore produces `HOLD_MISSING_FINE_ANNOTATION`; **G2 has not run**.
An exact substring, an AI-reviewed whole action, or an existing glyph object is
not silently upgraded to a reviewed semantic partition.

## Prepare a private revision

From the repository root:

```powershell
python -X utf8 ae/experiments/r06-b06-judgement/run.py `
  local-data/free-showcase/b06-judgement-input-r2/request.json `
  local-data/free-showcase/b06-judgement-replay
```

The output directory must be new and inside ignored `local-data`. Replays use a
new directory. Inputs include the existing native baseline, exact proposed spans,
an authored Audience v0.2 direction, all-beat scene mapping, AV cues and local
documents. Real question text and media are not shipped in this repository.

The command checks current frozen statuses, the full candidate sequence, original
native/media receipts and hashes, source objects, voice PCM/transcript/duration,
music hashes, complete Audience handoff and cuts that preserve whole voice clips.
It writes the production index, annotation request, scene/source audit, planned
handoff and excerpt boundaries. The CLI exits nonzero (`2`) for the expected G1
hold, after saving those deliverables. Other validation failures raise an error.

`DIRECTOR_PROJECTION` is a separate projection; the historical direction is never
edited. Its ranges remain `PLANNED_NATIVE_DIRECTION_NOT_ACTUAL_EXPORT`. Native
object lifetimes are provenance checks, not proof of on-screen readability.
Actual media mapping remains unavailable until the existing Audience Learning
Loop has its media, timeline and external human anchor credentials.

## Annotation response

`ANNOTATION_REQUEST` preserves exact ranges, the original action/relation and
active review references. All proposed operations remain unauthorized. There is
no `approved=true` override or fabricated upstream review. A returned frozen
annotation needs its actual producer contract and binding checked before adding
the G2 consumer. The existing bounded auxiliary method-application contract is
not widened to accept a decider.

## Adobe ownership when G2 becomes eligible

`ae_production.host_ownership.HostOwnership` provides the small cooperative lock
for this revision. Use its shared default lock directory and a single owner for
each Adobe host. Targets include process ID, saved project path, comp/sequence ID
and, where available, the spec binding. Acquire before any project switch or
mutation, supply a fresh native-state reader to `mutate`, and declare the intended
destination for a deliberate switch. Release only after a successful identity read.

Timeouts, interruptions and identity changes leave `UNCERTAIN` ownership in place.
No TTL, automatic retry or takeover exists. Inspect the native host and saved
request/failure evidence before explicit recovery; elapsed time is not evidence
that the old operation stopped. Uncooperative tools or manual users are not locked
out by a filesystem record, so project identity reads remain necessary.

This guard is unit-tested with synthetic hosts; G1 hold means it has **not** been
exercised in a new live production session. Older experiments are not globally
retrofitted. G2 must wire every native write through it before using Adobe.

## Remaining delivery

After G1 is resolved, produce old/new pure judgement clips and contextual pairs
both without explanatory VO and with full AV: six full-screen 4K24 files. Preserve
the original projects and takes. New media gets its own receipts. G3 is a human
viewing decision; no whole-episode expansion or generic partial-render system is
included before that decision.
