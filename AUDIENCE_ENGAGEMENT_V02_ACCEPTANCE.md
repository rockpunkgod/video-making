# Audience Engagement Design v0.2 — engineering acceptance and real handoff

## Inspected version and PR handling

Start main: `64ee8188c857359f22f8cb0ce9e52bd701d2a6b3`. Latest integrated main: `906a0586b64b23118a399567e0e01517aba971db`. Tested implementation HEAD before this acceptance-document update: `df6e9207c8db7bc18ca48a389d0ec81362914fe2`; initial implementation commit `1da0dfc`, acceptance hardening `d28fcd5`, latest production alignment `a932893`, UTF-8 media inspection fix `df6e920`. Branch: `feat/audience-engagement-design-v02`, isolated worktree `E:/自媒体/video-making-audience-v02`.

At initial inspection PR #1 was an unmerged Draft, head `ccd1f78`. Its v0.1 implementation was reviewed and tested with real project validators and is incorporated into PR #2 (`https://github.com/rockpunkgod/video-making/pull/2`). The user requested acceptance followed by merge; #2 is the complete integration, superseding #1's implementation proposal. Latest production commits were integrated without conflicts. Main's concurrent uncommitted cognitive-design/continuity work was not staged, switched, reset or overwritten.

Acceptance conclusion: **engineering implementation can be merged after the final checks; current film experience requires revision**. A newly available, version-bound human full-film screening report says `REVISION_REQUIRED`. Engineering PASS does not replace that creative result or authorize publication.

## Implementation delivered

- Backward-compatible v0.1 Director and explicit v0.2 Viewer State, 11 functions, actionable editorial audit, unique beat checks and existing Adaptive scene handoff.
- Local append-only creative ledger: immutable prediction/copy/timeline snapshots, decoded-final-media/native-readback bindings, manual publication records, manual/CSV observations, source/windows/denominator/missing-data validation, separate comments/screening feedback and teaching issue candidates.
- Separate planned and final-cut scores; no automatic inherited grade or Human Taste PASS. Final inspection consumes actual MP4, actual subtitle/voice/music/SFX/receipt asset hashes and native timeline conformance. Actual beat anchors require full native readback and bound external viewing credential. Changed source/media/timeline invalidates reuse.
- Hypothesis-by-hypothesis descriptive retrospective with concrete next-director edits and cited available evidence. No curve means beat-level analysis UNAVAILABLE.
- Separate Evaluation Rule / Creative Pattern candidates; historical whole-comparable-pool replay, preserved pass/reject reviews, independent external-human activation and version history. Reusable suggestions stay LOW confidence and future holdout PENDING. No numeric weight training or claims of causal/statistical validation.
- Four schema documents and a runnable JSON CLI, extending the existing Showcase feedback template. No second truth authority, publishing tool, crawler, host control, motion runtime or course platform.

Independent acceptance reproduced and fixed five problems: CSV checksums previously masked blank source declarations; extra retrospective fields could replace the displayed frozen hypothesis; resealed mappings could change frame ranges without updating human-reviewed anchors; aliases/recuts of the same source problems counted as independent episodes; native media metadata failed on Windows' default GBK decoding. CSV now checks provenance first, judgement fields are closed, mappings retain and reconstruct their signed anchors, cross-episode samples use immutable source-material fingerprints and distinct final media, and FFprobe JSON is explicitly UTF-8. The synthetic second episode now contains a genuinely different frozen source problem. Historical records remain unchanged; old predictions without source identity cannot support rule promotion, and mappings without retained anchors require rebinding.

Cheat reference revision: `2d8211efb9e7ed3ef21f71a78d13f1563be6f86e`. Reused its five-stage discipline and separation of evaluation versus creative patterns, adapted the project interfaces, discarded fixed sorting thresholds, probability buckets and single-comment causal promotions. No source code, hooks or Skills were copied/installed. MIT license and authorship were inspected; attribution and precise scope are in `docs/cheat-on-content-integration.md`.

## Executed verification

| Command / check | Actual result | Scope |
|---|---|---|
| `python -m unittest tests.test_audience_engagement tests.test_method_episode tests.test_adaptive_native_frames tests.test_adaptive_native_motion -q` | 33 tests, 18.814 s, OK | Initial v0.1 integration on main@64ee818 |
| `python -m unittest discover -s tests -q` | 1,173 tests, 587.741 s, OK, 1 skipped | Whole-project checkpoint on main@64ee818 alignment before the final readback hardening/tests and late main color commit |
| `python -m unittest tests.test_engagement_learning -q` | 17 tests, 20.354 s, OK | Final learning controls; actual encoded synthetic 4K24 lifecycle and picture-only rejection |
| `python -m unittest tests.test_engagement_learning tests.test_audience_engagement tests.test_method_episode tests.test_free_showcase tests.test_content_profiles tests.test_adaptive_native_frames tests.test_adaptive_native_motion tests.test_adaptive_color_handoff tests.test_cinema_native -q` | **83 tests, 55.299 s, OK** | Final code at 557a697, aligned with main@b85cf51 |
| JSON CLI real `design`, `inspect`, help; schema validation; `git diff --check` | PASS | CLI and actual source-bound handoff; inspection correctly remains PENDING |
| Independent acceptance rerun of the 83 affected tests | 83 tests, 49.225 s, OK | Original f7bfea7 delivery before adversarial checks |
| Four adversarial regression cases before repairs | FAIL as expected: 6 failed assertions, 1 error | Reproduced provenance, frozen-hypothesis, mapping and sample-identity defects |
| `python -m unittest tests.test_engagement_learning -q` after initial repairs | 20 tests, 26.488 s, OK | Guard repairs and actual synthetic 4K24 lifecycle |
| `python -m unittest discover -s tests -q` during acceptance | **1,180 tests, 546.791 s, OK, 1 skipped** | Full-project checkpoint after the four learning repairs; final UTF-8 fix is covered by the later affected run |
| Affected audience/episode/Showcase/profile/native/color/cinema/lossless run on latest production alignment | 89 tests, 53.274 s, OK | main@906a058 plus repaired audience code, before the UTF-8 fix |
| Real 4K24 synthetic MP4 with Chinese title metadata | Failed before UTF-8 fix; 1 test, 0.262 s, OK after fix | Reproduced actual Windows decode failure; picture-only exports still rejected |
| `python -m unittest tests.test_engagement_learning tests.test_audience_engagement tests.test_method_episode tests.test_free_showcase tests.test_content_profiles tests.test_adaptive_native_frames tests.test_adaptive_native_motion tests.test_adaptive_color_handoff tests.test_cinema_native tests.test_lossless_editorial_handoff -q` | **89 tests, 53.681 s, OK** | Final implementation df6e920, including UTF-8 metadata, anchor reconstruction, actual retention sample selection, distinct frozen problems and latest main@906a058 |

Full runs are checkpoints, not claims that every later edit was rerun across the entire repository. The final affected run covers all changed learning/director/Showcase code and the inherited color/lossless checks. No hardware/network publication operation or actual audience success is tested.

Synthetic tests verify no teaching/status mutation, retained historical predictions, DB UPDATE/DELETE refusal, stale media/version rejection, closed blind channel after known publication, no identity-based reuse of observed media, planning/final separation, missing-vs-zero CSV behavior, sources/timestamps/windows/rates, absent/unavailable retention, AI/unwatched Human Taste rejection, single-episode activation refusal, preserved rejection history, rubric versioning, source/order/Stop/Role changes, source-derived suggestions and planned/actual map separation. Existing tests retain withdrawal/cross-question/helper-answer and `free_showcase_v1` gate coverage.

## Real production handoff: complete media available; experience revision required

Private source: existing `local-data/free-showcase/adaptive-episode-r7/` in the main worktree. Both independent frozen questions and the delivery's supplied `status-before-delivery` manifests revalidate for internal consumption. Both payoffs retain framework/interpret scope, not answer closure. No analyzer or teaching review was rerun/created.

Private delivery: `E:/自媒体/video-making-audience-v02/local-data/audience-learning/episodes/adaptive-r7-audience-v02/`:

- `AUDIENCE_ENGAGEMENT_PLAN.json`, `DIRECTION.json`: 16 existing source-bound beats, complete editorial Viewer States and distinct A/B novelty/speed intentions.
- `DIRECTOR_HANDOFF.json`: exact existing Adaptive scenes and shared source refs. Times explicitly PLANNED; no execution parameters or claimed actual export anchors.
- `EDITORIAL_REVIEW.md`, `PRE_PRODUCTION_REVIEW.json`: actionable opening/reading/replay/new-question/comparison/recall edits with evidence and source constraints. AI planning reviewer recorded; all qualitative grades remain PENDING until content-specific review.
- `PLANNING_HYPOTHESIS_RECORD.json`: immutable `PRE_PRODUCTION_HYPOTHESIS`, not a finished-film blind prediction. Future advantage, failure and evidence collection are frozen.
- `MEDIA_PREFLIGHT.json`, `FINAL_CUT_INSPECTION_R2.json` retain the earlier picture-only checkpoint. Production subsequently delivered `delivery/ADAPTIVE_EPISODE_INTERNAL_4K.mp4`: 3840×2160, 24fps, **5,648 frames / 235⅓ seconds**, actual audio, media SHA `a7e83f6f602b3d16f8010416520d1f836f1c87c5057bd215eba4a399ffd682d2`.
- `FINAL_NATIVE_TIMELINE_R3.json`, `NATIVE_SOURCE_PATH_PROVENANCE_R3.json`, `FINAL_CUT_INSPECT_REQUEST_R3.json`, `FINAL_CUT_INSPECTION_R3.json`: consume the complete native readback, unchanged whole-picture reconciliation, unique current project media items, actual 15-voice timing, music stem, subtitle and receipt hashes. The actual MP4 fully decodes; native timeline conformance passes and inspection is `READY_FOR_REVIEW`.
- `FINAL_CUT_ENGAGEMENT_REVIEW_R3.json`: exact current media/copy bindings, source-bound improvement proposals and actual native voice-slot locators. The production's independently supplied human screening feedback binds the same media/copy and requires creative revision: the cut still feels like projected text and teacher explanation, without a clear reduction in the viewer's own task. This is whole-film feedback, not fabricated beat-level retention. Overall score stays null; no Human Taste PASS or teaching invalidation is created.
- `MEDIA_BEAT_ANCHOR_REVIEW_TEMPLATE_R3.json`: exact 16 question/beat identities and actual master clip ID; frame fields remain unset for external human verification. Formal actual Beat mapping is **UNAVAILABLE** pending that credential; native voice slots are not presented as Beat boundaries. Listening remains deferred by the user; reading comfort is not separately assessed.
- `HUMAN_FINAL_REVIEW_TEMPLATE.json`, prediction spec, CSV and metadata templates, feedback template and repeatable CLI request files.
- `PROTECTED_PRODUCTION_INPUTS.json`, `CONCURRENT_PRODUCTION_RECHECK.json`: the episode, direction, Native Spec/render/picture receipts, AE project and picture MP4 hashes match their captured pre-handoff snapshot and final read-only recheck. No render was restarted and no Adobe project or production receipt was written by this task.
- `FINAL_CUT_READ_ONLY_PROTECTION_R3.json`: all 27 referenced production manifest/status files are unchanged before and after final-cut inspection. The old planning prediction and both planning scores remain immutable; no finalized release identities, publication or performance are invented.

The complete dual-question audiovisual MP4 is available and inspected. Existing supplied final-frame previews were visually sampled; this is not an entire-film AI viewing claim or a human/listening pass. The old single-question r4 movie is not substituted. The real human revision request takes precedence over positive engineering checks.

## Status and smallest next action

| Stage | Status |
|---|---|
| P0 architecture/PR alignment | Engineering PASS |
| P1 real source-bound Director v0.2 and specific edits | Delivered; editorial/human quality PENDING |
| P2 local MVP and SYNTHETIC TEST ONLY end-to-end | Engineering PASS; synthetic data isolated |
| P3 actual dual-question final-cut inspection and specific review | Engineering inspection delivered; experience REVISION_REQUIRED; formal Beat anchors PENDING |
| P4 actual publication and T+3/T+7 learning | WAITING actual publication/data |
| Human Taste | **REVISION_REQUIRED** from bound full-film human screening |
| Reading / listening | Not separately assessed / deferred by user |
| Real retention, share/save results, improvement/cause | UNKNOWN |
| Learner comprehension / method generalizability | NOT_ASSESSED |
| Public render ready | **false**; existing free_showcase_v1 gates unchanged |

Next: the existing Director should address the recorded human experience complaint using the bound task/action/evidence, preserving framework scope and the ongoing production work. Review that revised exact cut and provide verified frame anchors. Once platform/title/cover/description versions are finalized, freeze a new final-cut prediction. After actual operator publication, register it, import real T+3/T+7 observations and compare H001 with available evidence. Any adopted edit must link a reviewed pattern activation into the next episode's frozen hypothesis and await its new real feedback.
