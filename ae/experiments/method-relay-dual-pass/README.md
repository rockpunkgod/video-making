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
