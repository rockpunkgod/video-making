# Cheat on Content integration decisions

Reference: [XBuilderLAB/cheat-on-content](https://github.com/XBuilderLAB/cheat-on-content), inspected revision `2d8211efb9e7ed3ef21f71a78d13f1563be6f86e`.

Read: root SKILL, cheat-score, cheat-predict, cheat-score-blind, cheat-retro, cheat-bump, cheat-learn-from, blind-prediction protocol, bump-validation protocol, observation lifecycle and tutorial-builder-zero rubric. The reference checkout is outside this repository and was not installed.

| Upstream mechanism | Decision | Project adaptation |
|---|---|---|
| Score → frozen prediction → publication → retrospective → evolve | Reuse discipline | Project-specific small Python API and JSON CLI |
| Script scoring | Adapt | Separate Pre-production and Final-cut stages; actual media/subtitles/audio/receipts required for final evaluation |
| Immutable prediction sections/hooks | Adapt | Append-only SQLite records, UPDATE/DELETE refusal, transactional duplicate/version checks and verified hash chain |
| Blind channel allowlist | Reuse boundary | Before observation, record source/episode/copy/timeline/media and release version identities; explicit no-data-seen declaration. No automatic model scorer is claimed. Separate future scorer inputs from actuals/memos |
| Publication registration | Adapt | Manual, per platform/post/cut/title/cover/description identity; no publishing action |
| T+3 retro and source labels | Adapt | T+3/T+7/T+30 or CUSTOM; explicit windows and collection time, denominators, missing fields and actual-vs-synthetic label |
| Rubric versus script-pattern separation | Reuse | EVALUATION_RULE versus CREATIVE_PATTERN; distinct records and activation versions |
| Historical replay plus independent review | Adapt | Replay entire comparable pool; document overfit concern and holdout plan; no statistical-validation claim |
| Observation cleanup | Adapt | Immutable historical observations retained; only reviewed effective creative patterns enter Director handoff. No historical evidence deletion |
| Tutorial starter | Reference only | Cognitive breakthrough/problem clarity inform parent definitions; no fixed opening seconds, difficulty staircase or duration quota |
| Fixed rank threshold, small-sample accuracy claims, bucket priors | Discard | No imported 80% threshold, cold-start probability distribution or formula guaranteeing reach |
| Forced comment counts and causal inference from edits/plays | Discard | Missing comments remain missing; single feedback can seed a candidate, cannot prove a rule |
| Broad skill mirror, adapters, scraping and account hooks | Discard | Manual/CSV MVP, no installation or account access |
| Benchmark learning | Optional future input | Creative hypotheses only; include high/ordinary/low cases; do not overwrite Swiss identity or infer every shot worked from total views |

The implementation is original project-specific code. No upstream source, starter rubric prose, hook or Skill is copied into the repository; therefore no copied MIT source requiring a license header is distributed. Attribution and inspected revision are retained here. If later source code is copied, include the upstream MIT license and copyright notice for that source.

FREE_SHOWCASE creative-compression v2 uses this same AudienceLearning 0.2.0
ledger, rubric, freeze and retrospective discipline. The authored producer now
exports a bound input and editable freeze request draft; it does not install the
upstream system, create a second predictor, or infer observed platform outcomes.
The eight experience dimensions remain unchanged. Bilibili coins joins the
existing optional metrics; real launch and feedback validation still require
actual data. Pre-production hypotheses are not completed final-cut predictions.

Independent model review can identify reasoning mistakes; it cannot establish statistical validity or authenticate a human. A cold-start review is a low-confidence editorial judgement, with no total reach prediction.
