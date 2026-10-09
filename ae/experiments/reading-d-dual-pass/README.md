# Frozen real-question continuation

This incremental experiment continues the accepted native locating composition.
It consumes the existing frozen passage review and locating trace; it does not
read Registry, solve questions, create Reviews or add grammatical partitions.

`frozen_case.py` projects the existing single interpreter Action and separately
reviewed option decisions. `integration.py` validates current dependencies,
builds a new project and renders native 4K TIFF batches. `integration.jsx` retains
the original word objects and the accepted locating windows, then directs whole
sentences, evidence comparisons and original options in the same visual space.

The selected internal proof lasts 94 seconds at 3840 × 2160 / 24 fps:

| Output seconds | Function |
| --- | --- |
| 0–8 | Original question |
| 8–15 | Accepted Fast locating, source 0–7 unchanged |
| 15–32 | Fast application and direct option review |
| 32–35 | Replay entry |
| 35–47 | Accepted Guided locating, source 8–20 unchanged |
| 47–94 | Guided condition, samples, separate options, context check and answer |

Only replay entry changes playback rate. All actual locating and application
segments use their directed native timing. Whole sentences lead, other sentences
yield two frames later and the camera follows. Question/acquisition use orange;
comparison uses blue. No underlines, replacement summaries or new peeling rules.

Use an **unused** local revision folder:

```powershell
python ae/experiments/reading-d-dual-pass/integration.py prepare local-data/reading-d-dual-pass/REVISION --cue-manifest local-data/reading-d-dual-pass/LOCAL_DISPLAY_CUES.json
python ae/experiments/reading-d-dual-pass/integration.py build local-data/reading-d-dual-pass/REVISION
python ae/experiments/reading-d-dual-pass/integration.py render local-data/reading-d-dual-pass/REVISION --pid AE_PID --hwnd AE_HWND
```

Preparation currently binds the existing local frozen assets and accepted locating
revision. It deliberately fails when those dependencies are absent or changed;
there is no synthetic substitute for the real proof. Build requires an idle,
saved AE session and never overwrites an accepted project. Rendering checks
current dependencies before each batch, preserves a 1 GiB memory reserve and
records native output hashes. TIFFs may use filesystem compression, which leaves
file bytes and pixel content unchanged.

The original 3D source is rendered directly; only replay entry uses the flat outer
assembly. The declared eight-second original-question segment has constant
source time zero and reuses one native frame, with a separate hold receipt.
Native batches can use `--batch-size` from 1 to 32 and never cross segment edges.
Existing batch hashes and source-time mappings are checked before resuming.
The exact executed template is archived locally and checked against its original
SHA, so later workflow edits do not invalidate historical replay.

`--inherit-accepted-guided` reuses the accepted 288 native Guided locating frames
at their exact source times. It requires the matching patch, accepted movie SHA,
frame manifest SHA and each frame's SHA; the original frames are copied, never
moved. New native frames, inherited native frames and hold duplicates are recorded
separately. This does not extend the old locating review to the new full film.
The upstream frame-manifest SHA is canonical JSON SHA; individual frame SHAs
bind actual file bytes. These hash domains are not interchangeable.

Real highlight phrases live in an ignored local cue manifest, not this template.
Each cue provides `unit_id`, literal `span`, `text`, `text_sha`, existing
`review_refs` and source-time `windows`, alongside the manifest's
`source_binding`. Validation requires containment within both the projected unit
and an existing reviewed evidence span. This is a display projection, not a new
teaching judgment.

The original request must contain the exact frozen question and options, and its
question text pieces must reconstruct the frozen stem. This director's fixed
option choreography requires the existing retain/eliminate decisions. Revised
decisions require a new reviewed director plan; they cannot inherit this picture.

Added comparison layers explicitly cover the full application duration. Native
build audit checks their in/out points as well as their opacity in accepted
locating windows. A correct opacity expression alone is insufficient when the
layer itself ends before the application starts. Visibility must also be checked
in an actual native frame, with the original black glyphs readable over the fill.

One bound interpreter Action does not establish two-method cooperation. Final
closure belongs to `direct_text_review`; strict two-method relay remains HOLD.
Full-film visual review is PENDING, listening is deferred, voice acceptance and
public rendering remain false. Real passages, Reviews, native projects and movies
stay in ignored local data; only this workflow and synthetic tests are public.
