# Audience Learning Loop MVP

This local, manually operated loop records creative hypotheses and real feedback. It cannot publish, approve `free_showcase_v1`, edit teaching truth or operate Adobe. Every record carries `public_render_ready=false`. Private ledger: `local-data/audience-learning/audience.sqlite3`; synthetic tests use `synthetic.sqlite3` with `SYNTHETIC TEST ONLY` labels. SQLite is the single record authority; exported JSON files are snapshots, not editable alternative facts.

## Entry points

```powershell
python -m scripts.audience_learning template REQUEST.json --output NEW-TEMPLATE.json
python -m scripts.audience_learning rubric REQUEST.json --output NEW-RUBRIC.json
python -m scripts.audience_learning design REQUEST.json --output NEW-PLAN.json
python -m scripts.audience_learning inspect REQUEST.json --output NEW-INSPECTION.json
python -m scripts.audience_learning freeze REQUEST.json --root local-data/audience-learning --output NEW-RECORD-ID.json
python -m scripts.audience_learning publish REQUEST.json --output NEW-PUBLICATION-ID.json
python -m scripts.audience_learning csv REQUEST.json --output NEW-OBSERVATION-ID.json
python -m scripts.audience_learning retro REQUEST.json --output NEW-RETRO-ID.json
python -m scripts.audience_learning handoff REQUEST.json --output NEW-DIRECTOR-SUGGESTIONS.json
```

Outputs refuse overwrite. `--synthetic` uses a separate database; synthetic observations must declare `is_real_observation=false`. Never register invented results in the real database. The CLI's `publish` command only records an operator's actual publication, not a platform operation.

### Current authored FREE_SHOWCASE input

The existing freeze/inspect commands also accept `authored-learning-context/v1`.
`prepare` emits this small folder/author-SHA/plan-SHA binding for v2 edits, along
with actual/pending-recording copy and `AUDIENCE_FREEZE_REQUEST_DRAFT.json`.
The adapter revalidates the real AV_AUTHOR, AV_PLAN and frozen source statuses;
question identities and beat IDs come from actual source questions and scenes.
It does not fabricate a legacy method-episode plan or add another ledger.

Fill the draft's episode ID, author, release-version labels and actual
`post_data_seen=false` declaration before calling the unchanged `freeze` command.
Null means unanswered. A draft title/cover version is allowed only as a clearly
labelled pre-production hypothesis, never final creative approval. Re-freeze a
new version with actual final media, independent SRT, voices, native receipts and
Premiere readback before publication; never overwrite the planning record.

Record compression choices, expected advantage, comprehension risk and what to
observe. Keep the eight existing dimensions, no reach forecast or new scoring
formula. Bilibili `coins` is an optional count metric in the existing CSV/manual
interface; absent metrics remain null. EP01 reading / EP02 C-D reading / EP03
gap-fill are an initial observation plan, not three proven independent causal
experiments. Viewer and listening tests remain PENDING until actually performed.

All input documents are JSON. `template` needs `episode_id`; `rubric`, `records` and `handoff` accept `{}`. `design` takes paths `episode`, `direction` and a `{asset_id: status_path}` mapping `statuses`. `inspect` takes paths `episode`, `copy`, `timeline`, statuses, actual `media`, and asset lists `subtitles`, `voice`, `music_sfx`, `native_receipts`, each `{path, sha256}`. `timeline` is an actual native readback envelope `{sequence, settings, voices}`, not the authored Native Spec; it must pass existing cinema timeline checks against the actual encoded video frame count and contain picture clips with available source files. Native source hashes are retained and rechecked. An explicit `music_sfx: [{silence: true}]` is permitted only when the final cut actually has no music/SFX.

`freeze` uses the same episode/status/copy/timeline paths, optional `inspection` path, and a `spec`: experiment/episode/platform/cut/rubric IDs, author, `post_data_seen=false`, title/cover/description versions, and hypotheses. Each hypothesis specifies ID, claim, affected question/beat, expected advantage, possible failure and evidence-to-collect list. Optional `creative_rule_refs` binds reviewed pattern activations to the next experiment. Freeze stores original copy/timeline snapshots and hashes; rechecks actual files and the complete inspection for final-cut predictions. Without complete media inspection the record is only `PRE_PRODUCTION_HYPOTHESIS`, which cannot be registered as a final prediction.

`publish` takes prediction ID and publication `{platform_post_id, published_at, publication_url, registrar, media_sha, actual_publication: true, title_version, cover_version, description_version}`. Publication must follow freeze, be past/present, and match all bound versions. After registering publication, another platform/version of that same episode cannot be retroactively described as blind. Changes before publication require a new cut/version record. A separately encountered outcome not registered here must still be declared via `post_data_seen=true`; the software cannot inspect a person's memory.

`performance` takes publication ID and observation; `csv` takes publication ID, CSV path and the observation metadata without metrics. `source`, timezone-aware collection/window dates, exact platform/cut and window label are mandatory. CSV validates the operator's source before appending a file hash; a checksum cannot substitute for provenance. Named T+3/T+7/T+30 windows are cumulative from publication to the exact age; other windows use CUSTOM. Empty metric values are missing. Rates use unit `ratio` (0–1), average time `seconds`, counts `count`. Numerator and denominator must agree; counts have integer numerator and null denominator. Original CSV SHA is recorded.

```csv
metric,value,numerator,denominator,unit
views,100,100,,count
completion_rate,0.4,40,100,ratio
average_watch_time,12,1200,100,seconds
saves,,,,count
```

Numbers above are illustrative synthetic values, not account observations. Retention stays null unless actual source samples exist. A curve records source, `time_basis=MEDIA_SECONDS`, bound media SHA and ordered `{second,rate,numerator,denominator}` points. No interpolation or inferred per-question exits are created. Traffic source may be null; missing fields include absent metrics, curve and traffic source.

`feedback` takes prediction ID and actual watched media SHA, feedbacker, question/beat, original text or confirmed summary, experience issue, channel (`PLATFORM_COMMENT` or `EDITORIAL_SCREENING`), watched-final/confirmed-summary/rechecked/teaching-issue booleans. A comment requires registered publication. Feedback never automatically creates Human Taste PASS.

`score` takes prediction ID and review (reviewer identity/kind/version/date/stage/watched flag and all rubric dimensions), optional inspection. Each dimension has grade (0–5 or LOW/MEDIUM/HIGH/PENDING), evidence, edit, timecode and basis (PLANNED/ACTUAL_MEDIA). Final-cut without actual inspected media or viewing remains PENDING and stores pending grades. Human Taste requires a separately bound external-human credential, actual viewing and matching reviewer. No overall score or traffic distribution is computed.

`retro` takes performance ID and a judgement for every frozen hypothesis: INCONCLUSIVE/CONSISTENT/CONTRADICTED, reason, available evidence refs (`metric:views` etc. or actual feedback IDs), next-director-edit. Only those four judgement fields are accepted; the hypothesis identity and original frozen claim are copied from the ledger. Status is descriptive, never causal verification. Missing evidence cannot be cited. Notes and suggestions preserve Evidence/Stop/Role/scope.

## Actual media mapping

`map` needs current episode/status/direction/plan, actual media, complete Premiere sequence/settings/voice readback, frame ranges and external-human frame-anchor credential. Each range names question, beat, native clip ID, start/end frame. Ranges are half-open and must lie inside the verified actual clip and export. A master picture clip may contain multiple beats, but those subranges require verified actual frame anchors. All beats need exact per-question identities. The credential binds episode/plan/timeline/settings/media/range hashes and declares actual viewing. Operator authentication of its identity remains necessary, as with Showcase credentials.

The API reuses `audit_timeline` and actual media decoding, retains the exact input as `frame_anchors`, and rejects stale timelines/media/settings/plans. Validation verifies the anchors against the human credential's range hash and reconstructs every output range against the native clips and actual frame count. Recomputing a JSON seal after changing displayed ranges does not update that credential. Legacy mappings without retained anchors must be rebound. `beat-retro` revalidates source plan, mapping and published media identity before selecting actual observed curve points. With no curve or no samples in a beat, output is UNAVAILABLE. No plan estimate becomes actual MP4 time.

## Evolution and independent review

`propose` takes rule kind, rule, source, applicability, proposer, supporting/opposing retrospective IDs, change log, optional new rubric. One episode produces only SINGLE_EPISODE_OBSERVATION. Frozen predictions include `episode_identity_sha`, derived from the normalized source problem materials independently of episode labels, opening/recall text, ordering or render bytes. Renamed/re-exported versions of the same source problems count as one sample; reusable activation needs distinct source identities and distinct final media. Existing records lacking this fingerprint remain immutable and cannot support rule promotion; only newly frozen experiments carry it. Evaluation changes are qualitative, preserve the eight parent dimensions/four gates and carry a new rubric version; creative patterns carry no rubric.

`review-rule` archives independent pass/reject declarations with exact proposal hash; it never activates anything. `activate` requires an independent external-human pass, all supporting/opposing historical re-evaluations, whole comparable-pool replay, overfit check, holdout plan and new effective version. Different platforms/windows cannot be silently pooled. At least two independent episode identities are required for reusable activation; this is an engineering minimum, not proof of statistical stability. Activated patterns remain LOW confidence with future validation PENDING_HOLDOUT. No historic score, prediction or observation changes.

`handoff` emits only reviewed creative suggestions, provenance IDs and applicability for the next Director. No AE parameters, speed multipliers, teaching facts or publication permissions are emitted. To test an adopted suggestion, reference its activation ID in a new episode's frozen hypotheses and repeat the real publication/observation loop.
