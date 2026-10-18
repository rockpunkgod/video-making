# Motion Quality native experiment

This is a single existing search / comparison scene experiment. It reuses the
shared Adobe host guard and the current production inputs. Main-film production
continues through [CURRENT_PRODUCTION_WORKFLOW](../../../docs/workflows/CURRENT_PRODUCTION_WORKFLOW.md).
It does not add another production pipeline. The later explicit user instruction
authorizes established reading/return fixes as production defaults; this does
not transfer human approval to newly rendered shots.

The local `motion-quality-r01` binds the current R04 native source, SC09L's search
tail and SC10's existing comparison. A preserves original transforms. B applies
editable native temporal ease and spatial tangents, Camera + Null controllers,
continuous foreground carrying, restrained follow-through, contextual opacity
and the already-established phrase-chunk focus function. All words in a chunk
share one phase. Original text, fonts, evidence, judgment timing and the three
complete voice takes remain unchanged. The result is **A eliminated**, not the
complete question's final answer.

Both wrappers are 3840 × 2160, 24fps, 802 frames (33.416667 seconds), including
the same one-second final hold. The duration includes the existing complete
search, comparison and source-return chain rather than cutting a voice take
or ending before the physical return. All AEPs, media, reference transcripts,
private inputs and receipts are under the new local experiment directory.

The user subsequently liked B's general direction but corrected its reading
order and abrupt query-color handoff. `motion-quality-r02` preserves that B in
a separate editable AEP. `reading-focus.jsx` consumes explicit, measured native
line spans: 14 chunks across seven rows, left-to-right before the next row.
Color and 100–104% scale share the same quintic envelope (three-frame attack,
two-frame hold, three-frame release). The carried query fades to original ink
over 0.75 seconds before returning. A half-frame source-color overlap bridges
the rendered shutter boundary; a boundary-only override passed value readback
but still left a missing-word frame, so encoded-frame review is required.

`revise_reading.py` applies these two corrections only to the copied B;
`audit_reading.py` checks actual composed lines, dominant-focus order, color
values and exact preservation of the prior camera/object trajectories. All
existing evidence, copy, complete voices, 4K24 and judgment timing remain.
Four affected B segments were rendered afresh, with the other 13 segments and
A verified and reused. Actual final frames and an old-B / revised-B slider are
in the private revision's `REVIEW.html`; prior B approval does not approve the
revision or promote it to the main-film default.

## Actual consumers

`motion-quality-r03` corrects the subsequently identified full-stem pop (the
2D query margin survived until its out-point), keeps the query visible during
return, and covers all eight authored reading windows across seven source
blocks, including later revisits. The actual source uses 68 sequential phrase
chunks. The accepted B's bounded camera/extraction motion remains; outside that
range the existing source camera resumes with a short continuous transition.

The shared implementation is now `ae/rigs/reading-focus.jsx`, used both by this
revision and the default `authored_native.template_source()` build. It groups
literal words inside native composed lines; it supplies no teaching analysis.
That description records R03's historical implementation. Following the user's
phrase-boundary correction, new production first runs the existing entry's
`chunks` stage. A language author groups each complete article; the shared rig
consumes source-bound groups with native noBreak and does not split by word
count. Existing R03 files remain bound historical outputs. The new realization
is built separately as `critical-focus-r02`, retaining the current main-film
copy, evidence and clock; it is not a retroactive approval of either version.
`ae_production.reading_review` is called by production audit and render, checking
every reading window/row, dominant focus order, color/scale continuity and the
query-to-stem handoff. It does not certify visual quality. Superseded whole-line
focus was removed from the current template; bound historical experiment code
and artifacts remain available for their own replay.

The final sentence is the user's exact correction, “四项检查完，选D。”. Only that
take was regenerated through the existing producer/align/prepare entry; other
wording and complete takes remain. `revise_final_copy.py` consumes its real
caption/voice/judgment clock. The full-question native wrapper is 4K24, 3269
frames / 136.208333 seconds, including a one-second end hold. Actual media
completion is recorded in local `RENDER_COMPLETE_QUESTION.json`, never inferred
from the existence of a wrapper or source file.

- `build.jsx` duplicates the existing native master and saves a separate AEP.
  It never writes over the parent project. The B source contains the editable
  Camera / Null / 3D hierarchy and original transparent source objects.
- `motion-rig.jsx` configures semantic native keyframes and camera-space
  foreground carrying. `../read-frog-motion/motion-rig.jsx` supplies the existing
  smooth phrase-chunk function; it does not infer pedagogy or token groups.
- `run.py` reuses the existing host and ownership implementation, checks input
  bindings, renders native segments, retains complete voices and restores the
  current session's original host state. Inspect existing receipts before any
  execution; unknown results must not be blindly repeated.
- `audit.py` reads native text, hierarchy, controller keyframes, each frame's
  actual values, chunk ranges, audio placements and terminal source handoff.
- `blur_check.py` captures actual native frames with blur on and off, restores
  the intended setting and records the pixel differences. An interrupted check
  requires explicit inspection before further work.
- `verify_media.py` decodes final movies, checks frame counts/timestamps, video
  packet identity and full take audio correlations, and creates contact sheets
  and a labelled sequential comparison.
- `make_report.py` / `review-template.html` assemble the local review from the
  real native and media receipts, including an actual speed plot and encoded
  frame comparison. No report is a substitute for rendered media or review.

## Scope and review

The four specified YouTube tutorials were verified through their primary pages
and complete timestamped English transcripts. They were not downloaded and
decoded as reference videos, and no tutorial project file was obtained. The
report distinguishes transcript-based principles from this trial's own measured
values and visual observations. No original tutorial curve is claimed recovered.

The current experiment retains Swiss Cognitive POV, Reality Layer / Cognitive
Space, native 3D depth and transparent extraction. It changes movement and
attention staging. Facts and method boundaries remain fixed; r03 also consumes
the user's explicit final-sentence correction and resulting clock. The user
explicitly requested reuse of established fixes in future production; that is
the authority for this bounded shared-rig integration. Motion/visual/listening
approval of each new result stays separate from program checks.
