# Audience Engagement v0.2 — architecture audit

## Baseline and PR disposition

Inspected main: `64ee8188c857359f22f8cb0ce9e52bd701d2a6b3` (local and freshly fetched origin). PR #1 is OPEN, Draft, NOT MERGED; head `ccd1f78cd523157f3a75b4061c781d3992a71f9c`. Its four commits add only the planning module, documentation and synthetic tests. The earlier stub smoke test was not production acceptance.

Final alignment refresh found `main@b85cf51612964b005dbfa0b009bd033e5053170b` (native Rec.709 picture handoff). It is merged without conflicts; aligned implementation HEAD is `557a69736373526b1577150ff0809a6bf6efcd5e`. The upstream executor/color test changes are inherited from main, not recreated by Audience Learning.

The shared main worktree contains concurrent cognitive-design and reading-continuity edits. They were preserved. New isolated worktree: `video-making-audience-v02`, branch `feat/audience-engagement-design-v02`. It starts from PR #1 and merges the inspected main without conflicts (`6cf1fb391e43e6c74a6a872ac5635eff6b15116b`). A separate v0.2 Draft PR against main incorporates the v0.1 foundations and supersedes its implementation proposal; #1 remains a historical Draft until the owner decides its disposition. Neither is treated as accepted or merged.

## Actual v0.1 review

Good foundations: calls the real episode validator, binds source beat hashes, preserves question order and result scope, cannot promote locator/helper payoffs to answers, reconstructs the whole plan to detect tampering, keeps human/public/propagation status pending. The original tests pass against real project validators after alignment (33 tests across audience, episode and adaptive-native controls; 18.814 seconds).

Gaps addressed: no viewer cognitive state; risk strings without edits; no feedback lifecycle, final-cut evaluation or immutable publication-version records. Duplicate beat identities were not rejected locally. Strict v0.1 beat fields are retained for backward compatibility; v0.2 accepts a separate explicit field set and the 11 finite engagement functions.

## Existing interfaces and additions

| Existing authority | Reused responsibility | v0.2 increment |
|---|---|---|
| `creative_os.episode.validate_episode` | Frozen package/Review/Action/Stop/Role checks; independent two/three questions | Audience plan revalidation, no extra truth producer |
| `creative_os.content_profiles.PROFILES` | FREE_SHOWCASE eight dimensions and four shared hard gates | Named operational definitions map to those parents; no second overall score |
| `creative_os.director`, Student POV and Method Choreography | Actual source geometry, copy and motion decisions | Read-only audience intentions, task states and scene handoff |
| Adaptive native episode executor | Native motion events, Fast Pass, replay, inline guidance and holds | No new motion runtime; planned ranges explicitly separated from actual export frames |
| `content_os.showcase` / `content_os.release` | Truth/source/editorial/final-media publication gates | Reuse `feedback_template`, `file_sha`, `inspect_media`; learning never grants release |
| `premiere_production.cinema.audit_timeline` | Complete 4K24/48kHz native timeline and narration conformance | Actual export inspection plus externally verified per-beat frame anchors |
| Existing local-data exclusion | Private questions, productions and credentials | One `local-data/audience-learning` ledger; separate synthetic database |

P0 reads included episode, content profiles, director, Student POV experience/realization, choreography compiler, showcase/release, cinema, content-profile docs and all six requested policy/acceptance/difference documents. Adaptive r7 is a picture export, not the old single-question r4 completed film. No single-question export is relabeled as the new dual-question episode.

## Two data domains

ANSWER → Frozen Evidence/Action/Review → Method Episode → Audience Director → existing Copy/Student POV/Choreography → existing Voice/Motion/AE/Premiere → actual export/receipts → frozen hypotheses → publication registration → observations/feedback → descriptive retrospectives → candidate Evaluation Rule or Creative Pattern → independent editorial review → next Director suggestion.

Learning writes only its own local ledger. It imports frozen validators, never a teaching/Registry writer or an Adobe mutation tool. A teaching concern produces `teaching_issue_candidate`; observed plays are not learning outcomes. Editing FREE_SHOWCASE strategy does not change `free_showcase_v1`, paid quality, method maturity or source credentials.

## Deliberately excluded

No publisher, crawler, scheduled monitor, paid-course platform, viral-probability estimator, numeric weight training, cloned Cheat skills/hooks/state, new TTS producer, new motion library, or feedback-driven AE parameters. Human identity claims remain operator-audited external declarations, consistent with existing Showcase review boundaries.
