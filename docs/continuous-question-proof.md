# P2 continuous-question grammar proof

P4 r4 was rejected for small framing/type, disconnected option cards and missing visible glyph lift/return. This revision pauses the two-question episode and builds only its first bounded question, for visual review. It does not assert a closed answer, redesign the teaching methods, or modify ANSWER.

`ae/lib/grammar.jsx` extracts the native keyframe/carry-speed implementation from `ae/experiments/reality-cognitive-fast/motion.jsx`. Locate, lift, compare, whole-option elimination and return are shared functions. Each lift duplicates an actual original native glyph; its recorded source layer, original range and return position are inspectable. Original options remain in the same scene; only their literal keywords enter the comparison space. No option cards are created.

`ae/templates/shot-grammar-v1.jsx` is the single-question integration proof, not a completed general episode template. It uses warm paper covering the frame, 48px stem, 44px options, 46px focus text, 72px projected comparison, 100px bounded judgment and 36px captions in 1080p author coordinates. The original content recedes 600 author units in native Z, with compensating scale to preserve projected readability, 35% content opacity and native camera depth of field. The paper is not faded or replaced with a gray box. Source navigation uses a reading rail; the camera's small continuous drift preserves the fixed original question area. This does not claim the full camera choreography has passed human review.

The proof is 70 seconds: entry 0–10, fast evidence comparisons 10–22, existing D elimination 22–25, guided replay 30–56, confirmation 57–62 and frozen memory line 66–70. Replay resets only the animation of the same frozen action; it does not create another decision or revive any upstream asset. The gap between passes is a return/read hold, not additional narration. No answer is fabricated from third-party reference material.

The existing P4 builder first validates current supplied status, frozen text/action evidence, exact authored transcripts, PCM delivery and candidate closure. The new adapter accepts whole-word extraction ranges only within those actual action evidence ranges. Six existing first-question WAVs are retained unchanged, with new frame placements. Captions partition the exact transcript. Listening review and public release remain pending/false.

Preparation (private request/direction files and real output stay under ignored `local-data`):

```powershell
python -m creative_os.continuous_question REQUEST.json DIRECTION.json local-data/p4/FRESH_REVISION
```

Direction selects the existing source/action, three literal evidence subranges and six voice slots. The current proof intentionally binds the bounded D-elimination case and its fixed authored timing rather than claiming to support every method or episode. Native output records `NATIVE_GEOMETRY.json`; its project contains a 4K master and a 1080p review projection. Preview rendering uses half-resolution native master rendering to avoid unnecessarily rendering a full-resolution nested buffer. Font substitutions stop production. Production-font aliases use actual registered Source Serif 4, Noto Sans SC Medium and Noto Serif SC Bold faces.

Packaging, the second question and a full 4K movie remain deferred until this single-question direction is reviewed. Program checks do not certify viewing quality or natural speech. Real media/project files are never pushed to GitHub.

Native direct H.264 export stalled on this workstation. `shot-grammar-render.jsx` renders native lossless TIFF frames instead, in half resolution; `python -m scripts.encode_native_question REVISION` validates all 1680 frame names and their dimensions before encoding. This is a codec handoff, not a replacement compositor. The result state retains the 35% cognitive background until the judgment ends, so the 100px decision does not collide with fully bright original text. Source depth is applied through one native parent; dormant glyphs have temporal bounds covering their complete scroll intervals.

Premiere holds six independent unchanged WAV clips, not a replacement narration mix. Final normalization accepts an optional `--duration-seconds 70` after checking voice-slot ends. This removes normalizer-added tail padding and retains the 70-second picture without truncating speech. Native readback confirmed one 70-second picture clip and all six exact voice-slot placements. Targeted regression checks passed; human visual and listening review remain pending.

## Spatial revision after rejected layout

The user rejected the overall layout and space of the first continuous proof. A full-frame paper alone did not solve its main problem: large projected words still overlapped a page of dimmed original words. The revised template keeps the question at the top and original options at the right. During each lift the original reading rail moves upward by 120 author pixels and its visible window contracts to an upper context band. Evidence and option keywords occupy clean comparison baselines at 520 and 672 author pixels. Returning restores the reading window through the same cognitive-state curve. The pass label moves into the top-right margin, freeing the reading column.

This is a spatial presentation change only: frozen evidence, six exact voice clips, candidate state and 70-second timing remain unchanged. The last four return frames now fade the projected glyph into its original, and the projection ends exactly at arrival, removing the old opaque double-glyph echo. No independent option cards or replacement source summaries are introduced. The upper context is navigation context; it does not replace the fully readable original during reading. Visual approval is still required for this revision.
