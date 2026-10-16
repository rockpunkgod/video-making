# Cinematic rhythm proof — internal R02 revision

Baseline: `main@3f30b668496ce8fe6d08906daab0305cecd0d889`.
This is a bounded creative revision, not a new motion system or a release approval.
The current user feedback is negative: the work still feels like PPT and the rhythm
does not yet work. Successful native execution does not resolve that feedback.

## Identify the actual baseline

Use the local `reality-cognitive-r03-eliminate-r2` native project and media, not the
date of the newest public commit. The baseline movie is 19.5 seconds, 468 frames,
3840 × 2160 at 24 fps. Its SHA-256 is
`436b66d37aadcbd3f21f8b688b0c3258b8cc1ec9eb00748d069caf4fe2d8ab44`.
Its AEP SHA-256 is
`22ad3e1fd7c90b14dcfd36fc3c9a82b0568b745abc58aec6d33e5f6d2ef48b4d`.

The positive direction and entry feedback belongs to earlier revisions. The
latest elimination revision remains pending; approval is not inherited.

## Diagnosis and director clock

Times below are seconds in the actual baseline, not assumed template times.

| Baseline A | Issue | B and C clock | Reason |
|---|---|---|---|
| 1.60–4.70 | Search spends 3.1 s crossing already visible paragraphs | 1.75–3.65 | Carry camera velocity across the intermediate waypoint; settle at the evidence |
| 5.40–6.90 | Evidence completes its entry before the candidate starts to arrive | 4.50–5.65 | A shorter extraction prepares the comparison |
| 6.90–9.50 | Candidate restoration and transit leave the evidence waiting | 5.65–6.90 | Source recognition and candidate approach overlap |
| 9.50–12.20 | Two settled rows; camera no longer changes attention | 6.90–11.60 | Give the actual English comparison 4.7 s, with owner/pronoun attention cues |
| 12.20–12.85 | Rejection is primarily shrink, downshift and opacity | 11.60–12.10 | Decisive gesture; candidate identity remains attached |
| 12.85–14.45 | Result waits before the return begins | 12.10–12.70 | Brief recognition, then handoff |
| 14.45–17.70 | Long camera return; projected words disappear by opacity | 12.70–14.90 | In C, actual glyphs return to their native origins |
| 17.70–19.50 | Ending remains on the result | 14.90–16.50 | Show the unchanged remaining candidates, then end |

The new duration follows these beats. It is not a new fixed format. B/C are
16.5 s (396 frames); the comparison is longer even though the whole excerpt is
shorter. The state mask changes from 15 to 7 at the first rendered frame at or
after 12.10 s (frame 291, zero based).

## Three actual versions

- **A:** retain the original baseline file byte for byte. A separate 1080p review
  copy can carry the same scratch narration and captions as B/C, retimed to A's
  original picture events. This does not replace the baseline.
- **B:** duplicate the native baseline composition and retime native keys. Keep
  its object arrangement and basic treatment. No global video speed change.
- **C:** duplicate B, retaining its judgment clock. Give the evidence-owner
  assembly and the candidate assembly separate depth planes and parent pivots.
  Fold the complete candidate, including its identity, behind the persistent
  Reality plane. Keep the question subject outside the rejected parent. Return
  the evidence glyphs to their actual source positions.

The extra expression in C must be demonstrable in the native layer tree and
intermediate frames: parented motion, opaque depth crossing, retained subject,
and continuous return. Camera motion or blur alone is insufficient.

## Native execution

Reuse the existing AE project, measured glyphs, frozen proof validator, camera
functions and `HostOwnership`. In multiple worktrees, explicitly use the same
host-ownership directory. Save a host snapshot and a new revision before edits.
Never overwrite the baseline AEP or movie.

This run uses AE 26.0x67 and the existing Classic 3D renderer (native ID
`ADBE Advanced 3d`). Do not confuse that historical ID with a claim that the newer
Advanced 3D renderer was used. The installed renderer list is recorded in the
native receipt; this proof does not claim Advanced 3D materials or extrusion.
Actual C uses native parent transforms, camera/POI/focus, depth of field and lights.
Native cast shadows were tested in the prototype but disabled in the final
low-cost preview after the render became expensive. Do not claim that the final
movie contains cast shadows or Advanced 3D materials. Keep paper and glyphs thin.

The JUNKDOGE endpoint was initially unavailable. A task-local File → Scripts
dispatcher used the existing open AE process, with native identity readback
before and after each mutation and the existing shared ownership lock. This is
not a new bridge service. When the existing bridge became available, a pending
GUI read was reconciled against live state and the completed batches, and the
remaining operations resumed through that existing bridge. A failed light-property lookup was inspected in the
native host before a specific correction; no blind project rebuild was used.

First render native keyframes and check scale, occlusion and contrast. For this
proof, background text initially competed with the comparison; its paper/ink
contrast and native focus treatment were corrected before moving render output.
The first B preview used a 1920 × 1080 nested proxy; inspection caught its black
transparent surround, which was not present in the baseline movie. C's first
nested render encountered an actual AE memory-allocation failure. Retain these
intermediate outputs and receipts. Both final previews use direct native 1080p
duplicates with the same 3D world coordinates and half the camera zoom; the
canvas-relative 2D background and camera aperture are scaled accordingly. This
keeps the framing while avoiding a 4K intermediate. B explicitly restores its
original opaque background. Recovery first used single-frame rendering. After
removing expensive shadows, final C uses bounded multi-frame rendering with a
25% CPU request, purges between batches, and retains the existing 1 GiB reserve.
Use native TIFF batches, verify their counts, and encode H.264 review media.
Do not substitute generated stills for native motion.

Continuous-frame inspection also caught a foreground subject drifting over the
source text before the comparison. Final C reuses B's peripheral memory position
and switches the paper to its dark state over 12 frames near extraction. The
comparison and candidate-decision clocks remain unchanged.

## Narration and teaching boundary

Use one shared set of scratch clips for all three review movies. B/C use identical
WAV bytes and placement. A uses those same clips at its original event times.
Keep the unchanged silent pictures available to isolate visual rhythm.
Do not retrain a voice, change its reference, or treat scratch narration as an
accepted final voice. No music or final mix is required for this comparison.

All new spoken and contextual text must point into the frozen bundle. Do not
announce the ownership comparison before the viewer can see its objects.
The only candidate result remains the existing bounded D elimination. The other
three candidates remain unresolved; no final answer, extra elimination, or new
interpretation of the option's verb is introduced.

## Private evidence and review stop

Keep the AEP, real source material, scratch transcripts, media and execution
recipes in ignored local data. Save input hashes, native readback, render receipts,
camera samples, glyph origins, candidate event frames and delivery hashes there.
Only workflow and redacted production notes belong in public Git.

Verify frozen input hashes, all source glyphs, projection origins, the identical
B/C candidate clock, decoded frame counts and actual encoded audio. These are
mechanical checks, not a creative verdict.

Deliver A/B/C playable movies and ask only:

1. Is the new version clearly more economical?
2. Does it still feel like a teacher presenting PPT?
3. Does it feel like following someone skilled as they search and judge?
4. Does the native spatial/physical expression help understanding?
5. Does the result make the next judgment feel like a natural continuation?

Keep human creative and listening review `PENDING`, and public release false.
Stop for viewing; do not expand into a complete R06 episode or a release package.
