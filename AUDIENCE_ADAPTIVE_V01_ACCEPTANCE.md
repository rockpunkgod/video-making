# Audience → Adaptive v0.1 engineering checkpoint

Baseline: `main@3f30b668496ce8fe6d08906daab0305cecd0d889`. Date: 2026-10-18.

Delivered: opt-in source-bound scene/event/object adapter, reconstruction at every
Adaptive `current()` check, host-free `audience_preflight`, and actual code-path
consumption of planned sample times by the existing `preview()` API. Adjacent
question progression projects earned payoff → next obstacle → later fresh gain.
No geometry, text, voices or duration is generated or modified by the adapter.

## Executed checks

```sh
python -m unittest tests.test_audience_adapter tests.test_audience_engagement tests.test_method_episode tests.test_candidate_motion tests.test_adaptive_native_frames tests.test_adaptive_native_motion tests.test_adaptive_color_handoff -q
```

Final result: **59 test executions in 59.450 seconds, OK**. These represent
**53 distinct tests**, including **15 new adapter tests**; six MethodEpisode tests
are also imported/discovered by the Audience test module and are not counted
as additional coverage. `py_compile`, CLI `--help` and whitespace checks pass.
This is affected regression, not a full-repository regression claim.

New tests use actual project Frozen Package, Episode, Audience and candidate
validators with program-only synthetic inputs. They cover B/C/D → C/D and B07
retention remaining C/D; no mutation; exact task/event projection; source and
spec tampering; withdrawal; missing, duplicated, foreign or expired objects;
read-before-decision; omitted candidate events; frozen output promotion refusal;
quiet-hold voice/camera conflicts and missing keys; ordered adjacent progression;
protected file paths; reconstructed saved output; the real `current()` preflight
path without Adobe; and passing planned sample times into `ae_previewFrame`.
The preview bridge is mocked. Existing frame-byte, JSX readback, color and
candidate-motion regressions run alongside these tests.

## Evidence boundary and next execution

| Layer | This revision |
|---|---|
| Authored shot/event timings | PLANNED_NATIVE_SPEC_NOT_ACTUAL_EXPORT |
| Adapter and affected regression | PASS, synthetic engineering evidence |
| Private B06 input availability | LOCAL_PRODUCTION_EVIDENCE_UNAVAILABLE |
| Adobe AE / PR execution | NOT_ASSESSED; no build, render or export performed |
| New actual media anchors | UNAVAILABLE |
| Viewer task simplification / Human Taste / listening | PENDING; prior REVISION_REQUIRED is not cleared |
| Public readiness | false |

The older Adaptive write lane's HostOwnership gap is not changed. New preflight
acceptance does not authorize native writes through that lane. The protected
bounded B06 producer's separate PRODUCTION interface is not automatically wired
by this change. Existing B06 r3 six-delivery evidence remains historical and
scoped; G3 is not completed and no G4 whole-episode application is claimed.

The [interface and execution specification](docs/audience-adaptive-handoff.md)
contains the seven-file request configuration, exact B06 task/event mapping,
source-frame clock warning, Adobe handoff steps and visual/sound/narrative/teaching
inheritance table. 5–8 minutes remains a program target, never a duration gate or
an instruction to add explanation. No ANSWER/Registry/review/status/release code,
real questions, private paths, media or credentials are included in the change.
