# Method Relay × Dual-Pass Creative Proof 0.1.1

One isolated native AE / Premiere research film. Its supplied English sentence,
partitions, visual attachments and candidate outcomes are **SYNTHETIC / VISUAL-ONLY**.
This is a renderer/director experiment, not an English analyzer, new teaching
method, reviewed exam solution, measured student speed, or publication package.
The synthetic marker stays visible throughout.

The experiment reuses the approved native word cue → range → 0.25 s release →
upper/lower parking technique. The increment is one enduring source-object space:
location lifts the original sentence, peeling retains its core, that same core
aligns with the original options, and verification physically restores the
original sentence. Seventeen original text objects have unique native layer IDs;
their Source Text never animates or substitutes a new sentence.

Frozen transports supply the existing Chinese names 关键词追踪 / 长句拆骨 /
谁干的陷阱. Version 0.1.1 additionally binds the three short Guided explanations
to each method's existing `core_action`, `decision_rule` and `stop_rule`, with
artifact/version/semantic hash, field pointers, value hashes and exact copy hash.
Those general method fields do **not** certify this synthetic case's spans,
visual attachments or answer. No solver, raw Registry, teaching Markdown or
Reveal scan is used. The original R02 bounded case, G01 HOLD and old r7 approval
are untouched. Frozen 0.1.0 requests and the completed P0 remain replayable.

The Guided increment explains how to locate, read the core and compare the same
dimensions. Three small 谁 / 做什么 / 对象 headers appear only over the existing
comparison columns (27.000–33.750 s). The B-subject mark stays visible during
the supplied observation window for “换了人” (31.000–33.750 s); this is a phrase
window, not a forced word-alignment receipt. Fast, camera paths, shot order,
physical release durations and the 46.5 s running time are unchanged.

The full 46.5 s composition uses a shared supplied trace with independent Fast
and Guided directors. Fast runs 02.500–12.500 with three small Chinese stamps,
no VO and no internal IDs. Existing objects return over 12.500–15.250; Guided
starts at 15.500, with its own camera, anticipation, reading holds and five
frozen guide beats. It is not slowed encoded footage. Both physical releases
stay at 0.25 s; the holds and camera distances differ.

All projects, media, receipts, original frozen name transports and frame archives
remain under ignored `local-data/method-relay-dual-pass`. The committed fixture
is explicitly synthetic. Do not commit AEP, PR projects, audio, MP4 or model data.

## Production on the existing workstation

Start the existing AE and Premiere public bridges. Existing fonts, producer,
frozen name exports and current manifests are required. Paths below are relative
to the repository; use fresh revision directories rather than overwrite takes.

```powershell
python ae/experiments/method-relay-dual-pass/run.py build local-data/method-relay-dual-pass/p0-next
python ae/experiments/method-relay-dual-pass/run.py preview local-data/method-relay-dual-pass/p0-next
python ae/experiments/method-relay-dual-pass/run.py render local-data/method-relay-dual-pass/p0-next --label P0
```

Inspect the actual P0 movie before continuing. A full build additionally requires
the completed P0 render's native audit and unchanged movie/project fingerprints.

```powershell
python ae/experiments/method-relay-dual-pass/run.py build local-data/method-relay-dual-pass/dual-next --phase full --p0 local-data/method-relay-dual-pass/p0-next
python ae/experiments/method-relay-dual-pass/run.py preview local-data/method-relay-dual-pass/dual-next
python ae/experiments/method-relay-dual-pass/run.py render local-data/method-relay-dual-pass/dual-next --label DUAL
```

AE renders native TIFF frames; FFmpeg only packages those frames into the picture
movie. Every frame is hashed and archived, then the compressed archive is verified
before this run's loose TIFF files are removed. Adobe failures preserve the exact
official recovery evidence; no implicit retry or checkpoint restoration occurs.
If native rendering already completed before a timeout, `finish --label DUAL
--recovery-id <issued-id>` reconciles the DONE queue through `ae_execRecover`
with `retryMode=continue`, saves the dedicated project and packages existing
frames. It never rerenders. Unfinished queues require explicit inspection.

Generate the five exact `fixture.voice` texts with the already selected replaceable
producer into ordinary `voice-delivery/v1`. The experiment does not change that
contract, weights, reference or tail controls. In the 0.1.1 local revision only
locate / carry / basis were regenerated; unchanged compare / verify WAV and
transcript bytes were reused. Its assembly receipt records each source delivery
and producer receipt SHA separately, rather than claiming a five-clip TTS run.
All five clips remain PENDING; no previous acceptance transfers. Then use Premiere:

```powershell
python ae/experiments/method-relay-dual-pass/editorial.py prepare local-data/method-relay-dual-pass/dual-next local-data/method-relay-dual-pass/pr-next --delivery <delivery.json> --music <existing-local-recording.mp3>
python ae/experiments/method-relay-dual-pass/editorial.py assemble local-data/method-relay-dual-pass/dual-next local-data/method-relay-dual-pass/pr-next
python ae/experiments/method-relay-dual-pass/editorial.py export local-data/method-relay-dual-pass/dual-next local-data/method-relay-dual-pass/pr-next
```

One whole picture goes on V1, exact 48 kHz PCM16 mono guide clips on A1,
optional Chopin scratch on A2. Only silence is appended to voice frame boundaries;
speech is neither shortened nor stretched. Source rights remain UNKNOWN/HOLD.
Native audio placement, stored duck keys and actual encoded voice presence are
verified; these checks do not approve pronunciation, naturalness or taste.

`final_voice_accepted`, `sample_delivery_allowed`, `production_eligible` and
`public_render_ready` remain false. The playable result is an internal research
preview. Human viewing/listening and all teaching/public release reviews are
separate and cannot inherit the earlier r7 feedback.

## Validation

```powershell
python -m unittest tests.test_method_relay_dual_pass tests.test_ae_native_creative_proof
```

Tests exercise binding, protected spans, deferred work, predecessor outputs,
native object substitution, alignment, replay restoration and exact pending voice
delivery. Portable unit fixtures are not evidence that Adobe rendered successfully.
See the acceptance report for the actual local render/export receipts and limits.

## Source Evidence Acquisition 0.2

The acquisition experiment remains P0/P1, separate from full-film integration.
The first silent A/B keeps the accepted 0.1.1 picture as A, and renders only
native Fast/Guided acquisition ranges for B. `acquisition_ab.py` verifies the old
user-feedback → Premiere picture-preservation → native TIFF archive chain before
encoding comparisons at the same absolute frame times. It never manufactures A
from an unapproved newer take or slows an encoded movie.

```powershell
python ae/experiments/method-relay-dual-pass/run.py build local-data/method-relay-dual-pass/acquisition-next --phase full --p0 <completed-p0> --acquisition-v2
python ae/experiments/method-relay-dual-pass/run.py render local-data/method-relay-dual-pass/acquisition-next --label FAST_ACQUISITION
python ae/experiments/method-relay-dual-pass/run.py render local-data/method-relay-dual-pass/acquisition-next --label GUIDED_ACQUISITION
python ae/experiments/method-relay-dual-pass/acquisition_ab.py <accepted-native-directory> local-data/method-relay-dual-pass/acquisition-next <fresh-comparison-directory> --accepted-pr <accepted-pr-directory> --review <exact-old-user-feedback.json>
```

The user requested entry into the **complete original passage**, then clarified
that the picture should represent the solver's current attention and retained
information. The three supplied synthetic sentences cannot stand in for a full
article. Their comparisons and unchanged peel handover remain synthetic research,
with the new B review `NEEDS_REVISION`; that feedback never approves integration.

`fulltext.py` is one bounded real-source location experiment in the same module.
It consumes an existing frozen reviewed-passage bundle and its current provided
status. It uses an already reviewed evidence span as the endpoint, not a newly
certified locator action. There is no solver, paraphrase, new action review,
option judgment, new method, VO, music or Premiere edit in this P0.

The first frame shows the complete original question. Its three exact source
spans join to the same frozen stem; the same keyword object remains in its
original reading position during scanning, while the other stem spans and
options leave the current view. The real full passage is first established in
overview, then the camera follows actual line order from the first paragraph.
Native depth of field carries attention; the reading cursor is an invisible
geometry helper. There are no underlines, range marks, step labels or persistent
lecture headings. A short filled keyword highlight follows the camera settle.
The complete existing evidence sentence takes over the retained cue during Lift,
using the original word layers. The source background retreats into a separate
reading band rather than overlapping the lifted sentence.

```powershell
python ae/experiments/method-relay-dual-pass/fulltext.py build <fresh-local-data-directory> --bundle <frozen-bundle.json> --status <current-provided-status.json> --question <frozen-question-id> --question-cue <literal-stem-span> --hit-cue <literal-existing-evidence-span>
python ae/experiments/method-relay-dual-pass/fulltext.py preview <same-directory>
python ae/experiments/method-relay-dual-pass/fulltext.py render <same-directory>
```

Outputs are silent native-picture movies: 7 s Fast, 12 s Guided and a 20 s
continuous research preview, together with an editable AEP, executed template,
native glyph/identity/focus readbacks, expression audit and verified TIFF archive.
New full-source outputs are uniformly 3840×2160 / 24 fps under the
[`4K delivery policy`](../../../docs/video-resolution.md). The AE comp and native
text/camera scene are rendered at full 4K; the same design layout and timing are
preserved. Encoding verifies the actual 4K frame dimensions. Existing approval
and historical artifacts keep their original resolution and hashes.
The 20 s native render uses four contiguous 5 s queue spans to stay within the
public execution timeout. Each DONE result binds its comp, time span and complete
frame sequence before joining all 480 frames; no frame cadence or timing changes.
New media and actual question material stay in ignored local data. If rendering
fails or times out, retain the official failure evidence and inspect the native
queue before recovery; the command refuses an existing frame directory and
never retries a render automatically.

Only the original synthetic experiment exposes a full `DUAL` render command.
For new acquisition inputs it requires an exact new human review bound to the
two new P0 movie hashes and spec SHA. A full-source location preview cannot
certify a multi-method relay or splice a real sentence into synthetic peeling.
Old visual approval, new parameter values and program PASS do not establish
first-person experience. Human review remains PENDING and all release flags false.

```powershell
python -m unittest tests.test_source_evidence_acquisition tests.test_method_relay_dual_pass tests.test_ae_native_creative_proof
```

See `SOURCE_EVIDENCE_ACQUISITION_ACCEPTANCE.md` and
`SOURCE_EVIDENCE_ACQUISITION_HUMAN_REVIEW.md` for the actual evidence and limits.


### Physical attention refinement (request 0.2.14)

After the 0.2.8 4K preview the user marked focus, search rhythm and hit-to-lift
all as needing revision, with moderately stronger physicality. Astra recommends
and root implements a causal lead/follow: interior camera nodes carry velocity,
with Fast/Guided row nodes delayed 1/2 frames; acquisition brakes before the
existing flash. Lift begins with the same sentence moving 24 design units out
of the plane; the background and camera wait 1/2 frames, and foreground scaling
waits 2/3 frames. Existing end poses, lens strength and 20-second timing remain.
No bounce, extra zoom, annotation or new evidence is introduced.

The motion profile is spec-bound. Native audit reads actual departure poses,
background hold and nonzero Bezier camera carry velocity. A failed first build
exposed a repeated first-row pose; that redundant interior key was removed in
a fresh project. Portable checks reject synchronous reflow/background movement
and camera row stops; prior 0.2.8 4K requests remain replayable. Technical checks
do not establish improved human experience, and no P2 integration is allowed
before review of the exact new movie.


An intermediate draft used a temporary paper-colored native plane, bound to the
same sentence's actual glyph bounds, behind all retained text layers and 20
design units deeper. It has no border, shadow or independent movement. It
exists only during Lift and leaves after the background is clear. Its geometry
is sampled from native glyph transforms at at least 96 Hz during Lift; only the
production helper is baked, not the teaching objects or live focus target.

Native readback checks its actual position, extent, color, layer order and
0/100/0 visibility. Source words acquire no masks. A projected per-word mask
experiment proved too expensive and failed preview, so that production path is
removed. Intermediate failed builds remain isolated local research artifacts.
Preview transport failures are retained before inspecting public host status;
there is no automatic capture or render retry. Completed 0.2.8 and 0.2.9 request
contracts remain replayable; uncompleted intermediate contracts are not promoted.

Astra's two-frame check of that draft found no foreground washout or background-through-text,
but notices a narrow cleared band at the early Lift frame. Continuous human
review must judge whether this feels natural; engineering checks do not settle
that aesthetic question.


The user's latest instruction supersedes the paper-plane draft: the extracted
sentence has a transparent background. Request 0.2.14 creates no sentence paper
plane and adds no masks to source glyphs. Only the unselected source retires
from opacity 28 to 0 at departure, stays absent during reflow, then returns to
28 over the last two frames after its projection has cleared the foreground.
Original selected text stays fully visible. Native readback verifies this
separation and rejects a paper background or foreground opacity loss. Source
content, final positions, static reading holds and overall duration are unchanged.

### Sentence attention v0.1 — request 0.2.15

The current experiment adds restrained same-object sentence magnification.
Literal punctuation and paragraph breaks group existing source word IDs;
these groups are visual units, not newly certified semantic spans. Native
glyph geometry maps them to the actual focus path, including the final row's
shortened scan. A sentence beyond that path never activates.

One shared quintic smootherstep envelope affects the original sentence's
position and scale: four frames to enter, six to retire. Maximum gain is 1.5%
Fast / 2% Guided. Measured same-line glyph gaps lower this ceiling, reserving
two design pixels and room for the neighboring sentence's own expansion.
Multi-line sentences share one envelope and anchor; no per-word bounce,
reflow, extra camera zoom, paper backing or new narration is added.
The acquired sentence holds its attention gain into Lift, then smoothly joins
the existing final size and position at Lift completion. The page overview
and rewind retain their original geometry. Native audit records actual scale
ratios as well as expression errors; declaring the intent alone cannot pass.
The physical departure audit uses pre-expression transforms for the original
depth-first movement, while attention and sentence-focus audits inspect the
result after expressions. Visual smoothness still needs human movie review.

### Continuous row handoff — request 0.2.17

Row returns previously moved the focus from line-end to the following line's
start in one frame. The current refinement replaces each such interval with
a bounded quintic Hermite transition, matching both endpoint positions and
incoming/outgoing velocities. Fast uses two frames, Guided up to four, with
the half-window limited to half of the shorter neighboring row's dwell.
The window must cover the complete original one-frame return. A preliminary
quarter-row cap left two Fast short-row joins outside the window; that partial
draft was stopped and is not a completed delivery.

Only focal handoffs change. Existing sentence gains, text geometry, camera
route, reading order, highlights, transparent Lift, final poses and 20-second
timing remain bound to the preceding take. Multi-line sentences keep their
single envelope. Native readback verifies every visited adjacent row, actual
endpoints and numerical endpoint velocity. New short-row coverage regressions
reject a window that smooths only part of the original return. These checks
do not substitute for original-speed human visual review.


### Baseline-locked attention revision

Request 0.2.18 keeps the accepted 0.2.17 focal row handoffs and all shot times.
Sentence attention 0.2.0 caps Fast at 0.8% and Guided at 1.2%, further limited
by native glyph clearance, with eight-frame entry and ten-frame exit using
quintic smootherstep. Attention changes scale and horizontal spacing only;
original baseline Y and depth Z stay equal to their pre-expression values.
This removes attention-induced upward/depth displacement without removing the
separate, previously established transparent sentence Lift. No spring,
overshoot, whole-page zoom, new words, voice or teaching facts are introduced.
Native audit verifies actual baseline/depth invariance and bounded gain.
Older completed requests retain their original attention behavior for replay.
Silky perception still requires human visual review; technical PASS is not
approval for full-film integration.


### Guided camera transport revision

Request 0.2.19 separates Guided lens transport from focal reading events.
During Guided scan start through hit-settle, camera position and point of
interest share one normalized monotonic trajectory. Six-frame quintic
velocity ramps at entry/exit enclose a uniform-speed middle, replacing
rowwise speed resets. The literal source, focus row handoffs, attention
magnification, camera column/depth, endpoint views, Fast behavior and shot
times remain unchanged. The native audit reads all 109 transport frames,
checks actual executed poses, middle velocity and endpoint settling.

This implements the camera-speed step only. Same-POS locating candidates,
source spans and correspondence evidence must be upstream supplied before
candidate recognition highlights can be rendered; the renderer does not
infer grammar or synonymy. A local teaching_issue_candidate records missing
inputs without creating any ANSWER review. Human review for the revised
Guided output remains independent of prior Fast acceptance.

After completed native rendering, transient AE caches are purged while the
queue is idle before encoding verified frames. This limits competition for
memory; original media, projects and frozen inputs are retained.


### Locating-expression recognition timing preparation

recognition_timing.py schedules supplied candidate IDs in frame intervals:
editor-supplied transfer and slower recognition durations per expression.
Uniform defaults are trial values only. Actual geometry must drive transfer
duration, and camera/focus/highlight must share the same recognition events. Retirement clears the highlight; it never eliminates a sentence or
option. Final acquired identity and order must be caller supplied. Overflow
requires explicit retiming; unused frames are left unallocated. The 0.1.0
policy is provisional and every timing plan remains non-renderable until
upstream span/classification/correspondence and director bindings exist.
This module does not tag English or provide a real q33 recognition sequence.
