# Dark-field and original-glyph proof

This is the user's fourth-checklist experiment, not another complete episode.
The previously rejected pale-background spatial revision remains preserved.

`creative_os.dark_field_proof` consumes the same request and frozen direction
through the existing status, voice, evidence and candidate checks. It selects
the already-bound `bring gifts` range and literal `Healthy` option word. The
last judgment uses the existing D-elimination action and displays all three
existing evidence projections; it does not claim that `bring gifts` alone
closes a title question. No answer, copy, teaching review or Registry is changed.

The first build uses explicit native AE keyframes with the two new function
bodies inlined. This is direct programmatic authoring, **not GUI hand-dragging**.
After native visual inspection, the second build invokes
`transition_to_dark_field()` and `lift_phrase()` from `ae/lib/dark-field.jsx`.
Both builds consume the same frozen PLAN and authored tracks. Generated
`build.jsx` is the integration entry; the rejected 70-second episode is not
automatically regenerated before this proof is reviewed.

The 20-second native 3840×2160 / 24 fps composition includes:

- 0s: paper `#F2F0EA`, ink `#20211F`.
- 1.0s: orange source-word locate, ten-frame left-to-right fill.
- 1.6–3.5s: actual original glyph duplicates move forward 200 author units,
  enlarge to a projected 72px, and settle. This deliberately slowed test lets
  the viewer inspect the path; it is not a new production-speed prescription.
- 1.6–3.6s: the full-frame environment changes to `#17181A`; the original
  world recedes 600 author units, changes color and blurs. Original glyph
  opacity stays 100% during the field transition.
- 4.5s: settled dark field and clear paper-white foreground.
- 5.0–7.1s: blue option-word locate and source-bound lift; a blue comparison
  plane distinguishes the option from the evidence, without replacing the
  original option with a separate card.
- 10–12s: reverse path and return to reading; the duplicate hands off to its
  original at arrival.
- 15s: the three existing evidence projections appear for the mechanical
  judgment test. 17s: the whole original D group, including its letter,
  moves down by **24 projected screen pixels** and settles at 20% opacity.
- 17–20s: paper-white existing D-elimination result on the dark field.

The original world is precomposed with its matching native camera and retains
its original glyph layer identities. A single native Gaussian blur of 3.2px
in author coordinates is applied to this background, avoiding a full 4K blur
buffer for every word. The foreground remains in the main 3D composition.
The camera provides perspective; this background blur is not claimed to be
an optically calibrated depth-of-field measurement. During lift/return the
background temporarily defocuses to 12px, settling to 3.2px in the dark hold;
this prevents readable original glyphs competing with the moving copy. The
foreground switches between ink and paper at the luminance crossover instead
of interpolating through the same gray as the environment. Transform tracks
retain zero-speed Bezier easing; foreground polarity deliberately uses hold
keys so the moving word does not vanish into a gray-on-gray midpoint.

```powershell
python -m creative_os.dark_field_proof REQUEST.json DIRECTION.json FRESH_PROTOTYPE --prototype
# Execute the generated build.jsx in AE, inspect its native frames, then:
python -m scripts.dark_field_media FRESH_PROTOTYPE
# Execute generated render.jsx; after native render completes:
python -m scripts.dark_field_media FRESH_PROTOTYPE --encode

python -m creative_os.dark_field_proof REQUEST.json DIRECTION.json FRESH_REBUILD
# Execute build.jsx and inspect. Execute audit.jsx in each matching project;
# compare against the direct-authored proof:
python -m scripts.check_dark_field FRESH_PROTOTYPE FRESH_REBUILD
```

The media script requires all 480 native 4K TIFF frames and refuses overwrite.
It outputs a 20-second combined test and exact 10-second light / 5-second lift
prefixes. The judgment contrast check uses the combined test at 18s. These
are silent motion tests; they do not need new voice production or Premiere
editing. Real exam content and media stay in the explicitly selected local
output folder and never enter Git.

Checks compare every-frame position/scale/opacity samples of native lifted
glyphs and five native rendered frames between the two builds. Rendered
background pixels must be exactly the requested paper and dark values; solid
judgment glyph interiors must be paper-white, giving 15.59:1 contrast. These
are mechanical checks, not human visual approval. Public release stays false.

## Human visual feedback

2026-10-16 — After delivery of the 20-second combined, 10-second field and
5-second lift 4K proofs built from `14ab6f1`, the user replied: “可以”.
This accepts this bounded visual proof as the baseline for later integration:
the bright/dark transition, original-glyph extraction/return and elimination
gesture. Preserve these delivered versions. This feedback does not approve a
complete episode, sound, teaching certification or public release.
