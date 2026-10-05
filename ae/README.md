# AE Production Layer v0.1

The V8 architecture remains unchanged. Swiss Academic Motion **v0.2** is an
explicit visual version of the same Master family: [migration and element
audit](design/V0.2_MIGRATION.md), [visual review](../AE_VISUAL_DIRECTION_REVIEW.md).
The original v0.1 files and default contract projection remain available for
historical replay. Real v0.2 artifacts live in ignored `local-data/v8.1/`.

V8 is an incremental consumer of the frozen V0–V7 Video Package. It does not
read teaching Markdown, Registry, raw questions or call teaching analyzers.
`ae_production` consumes the explicit package, manifest and current status
manifests; its references are JSON pointers plus canonical SHA-256 bindings.
Real assets, AE projects, captures, checkpoints and videos live in ignored
`local-data/v8/`. Nothing in this layer certifies teaching or grants publication.

The execution order is contract validation → current upstream validation →
official JUNKDOGE read → checkpoint/build → read → expression validation →
actual text/font/bounds audit → pixels → critique/revision → checkpoint →
internal MP4. A failed or timed-out mutation must be reconciled before retry;
pass the returned `recovery_id` explicitly, never silently run a fresh build.

## Local commands

Install the official signed JUNKDOGE panel and open its MCP server in After
Effects. No alternative AE bridge is used. `bridge.py` only transports calls to
that server's public HTTP MCP interface. The tested panel is v0.10.8, AE 26.0;
its native AEX plane is optional and was disabled in this pilot.

Create an ignored request JSON with paths relative to the request:

```json
{
  "package": "../video-package.json",
  "manifest": "../manifest.json",
  "statuses": "../status.json",
  "output": "render-contract.json",
  "contract": "render-contract.json",
  "output_dir": ".",
  "sample_times": [1, 30, 55]
}
```

```powershell
python -m ae_production contract local-data/v8/request.json
python -m ae_production validate local-data/v8/request.json
python -m ae_production build local-data/v8/request.json
python -m ae_production preview local-data/v8/request.json
python -m ae_production render local-data/v8/request.json
```

Provide current statuses again for every operation. Withdrawn/stale/missing
dependencies block dispatch. A pre-existing MP4 is never overwritten. Revision
requires a new output directory and render identity; an unchanged frozen input
and template produce the same contract. `template_sha` binds the actual JSX bytes.
No MP4 binary reproducibility is claimed across AE/hardware/encoder versions.

## Visual system and vocabulary

`design/swiss-academic-motion.json` freezes a 1080×1920 six-column layout, five
type levels, semantic colors and five motion types. Typography never shrinks to
fit; measured text paginates at fixed leading. Missing fonts, unsafe overflow,
short subtitle holds or unsupported structures block production. English wraps
at word boundaries; Chinese is measured glyph by glyph. AE measurements then
validate the rendered glyphs independently of the preflight approximation.

| Component | Visual responsibility |
| --- | --- |
| TEXT_HERO / TEXT_TITLE / TEXT_BODY | Bound scene copy at fixed hierarchy |
| METHOD_TAG / SOURCE_TAG / PROGRESS_MARKER | Provenance, role, orientation |
| QUESTION_CARD | Bound question fragment |
| OPTION_GROUP_GRID / OPTION_CARD | Neutral, labelled partition cards |
| EVIDENCE_TEXT / EVIDENCE_HIGHLIGHT | Exact quoted evidence with semantic background |
| DECISION_PATH / RELATION_ARROW | Ordered route and bounded connectors |
| STOP_RULE_CARD | Persistent explicit stopping boundary |
| SUBTITLE_LINE | Exact spoken-text projection, up to two lines |
| CANDIDATE_VERDICT / RELATION_COMPARE | Local decision and original relation operands |
| FRAMEWORK_CARD | Already supplied framework fields |

`METHOD_DEMO_MASTER` uses the same JSX for all three methods; it branches on
component/typed-output kind, never on method ID. The contract projects
candidate_partition to grouped cards, route_selection to a terminal path,
candidate_decision to a bounded verdict/relation comparison, and framework_card
to its existing fields. Missing visual structure emits a contract change
proposal; it never invents teaching evidence. Literal display fragments retain
the whole bound action/evidence payload and source pointer.

The primitive specification is data only: `type`, `duration_frames`, `easing`,
`delay_frames`, `emphasis`. Reveal, focus, compare, eliminate and connect share a
12-frame opacity/rise envelope, soft-out easing, 2-frame stagger and 24px travel.
Colors and geometry carry their distinct meanings. This is deliberately a
small native implementation; a separate expression SDK is deferred.

## Craft references and limits

- Execution: [JUNKDOGE after-effects-mcp](https://github.com/JUNKDOGE-JOE/after-effects-mcp).
- Craft: [iart motion-design-skills](https://github.com/iart-ai/motion-design-skills)
  shot-composition, motion-art-direction and after-effects skills.
- Critique: [Lobzy motion-design-with-claude-and-codex](https://github.com/LobzyJay/motion-design-with-claude-and-codex)
  motion-design-critique and visual-diagnostics.
- Research only: [Rebound](https://github.com/meszmate/rebound) and
  [eKeys](https://github.com/motiondeveloper/eKeys); no runtime dependency.

Third-party skills inform spacing, hierarchy, calm easing and pixel critique;
our own design tokens remain authoritative. No third-party teaching conclusions
are consumed. No expression library, second MCP, real Astra or publishing is
included. `catalog.py` only registers render descendants in the existing V7
dependency index; it is not V10 Content Catalog.

## Observed AE gaps

In the tested AE build imported JSON exposed null `sourceData`; expressions use
the same JSON footage's `sourceText` with `JSON.parse` as fallback. Actual
expression evaluation and text audits verify the result. Paragraph sourceRect
origins and shape default transforms required real AE read-back corrections.
Native render resets Undo state, so rendering has a checkpoint but no outer
Undo group. A native H.264 unexpected-error session required a saved-project
restart; recovery is explicit and failures are not reported as successful output.

Previews are silent and timed against existing final copy, not recorded speech.
Timing/readability is an engineering estimate. All previews visibly carry
`INTERNAL_ENGINEERING_PREVIEW`; public eligibility remains false. Actual release
reviews and user taste approval are independent of structural checks.

# V9 增量横屏层

当前 Creative Direction 为 CINEMATIC_LANDSCAPE v0.3。独立分镜、实测测试配音和
新的内部 render contract 见 [Creative OS](../creative/README.md)、
[v0.3 migration](design/V0.3_MIGRATION.md) 和 [V9 验收](../V9_CINEMATIC_HUMAN_ACCEPTANCE.md)。
旧竖屏 API 和回放路径继续保留。音纹后续调整，当前输出不具备公开资格。
