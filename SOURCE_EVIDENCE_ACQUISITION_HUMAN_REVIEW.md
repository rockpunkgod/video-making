# Source Evidence Acquisition — visual review

Status: **P0/P1 research; latest visual experience PENDING; P2 HOLD**.
Sound review remains deferred by the user. No teaching or release approval is
created by this document.

The accepted 0.1.1 overall visual feedback stays bound to the old Premiere
movie. Its exact viewed range was not supplied. It does not approve a new
acquisition camera, an individual V1–V6 criterion, or real-source teaching.

The first new silent synthetic Guided A/B received this exact user feedback:

> 进入完整原文扫，不是直接定到那一句

That B is **NEEDS_REVISION**. Its three supplied source sentences are insufficient
for a full-passage test; extra paragraphs were not invented.

The subsequent creative direction was further specified by the user:

> 要用镜头的焦点聚焦把人扫读时的注意力表现出来
>
> 关键字沿用之前的短暂高亮，不要划线
>
> 模拟的是人的第一视角注意力，不是人在上面批注
>
> 而且扫题的时候应该只保留从题干提取的关键词信息，画面呈现的永远是映在脑海里的，让astra评审一下我这个方案再按这个思路设计一下
>
> 画面呈现被记在脑海的信息，是第一视角做题不是第一视角讲题

Astra reviewed the proposal and native preview/calibration frames; root provided
the second review and implementation. The resulting design represents the
solver's current input and retained information using only literal frozen words.
The original question appears first. Its existing cue remains quietly in its
original position while the rest of the question and options leave view. A real
full-passage overview precedes row-order reading; native lens focus moves with
the reading point. The brief original-style filled highlight follows the hit
settle. The full existing evidence sentence then replaces the task cue in the
foreground, using its original text objects.

There are no scan lines, range lines, arrows, invented mental summaries, step
labels or persistent lecture headings. This is a creative representation, not a
measurement of a student's gaze, actual memory, reading speed or method validity.

Astra's decoded-frame review found a technical defect in r10: after the source
faded into the footer, text reappeared at the bottom image edge. Root confirmed
it at original resolution. r11 extends only the outer paper-mask edges beyond
the image; source content, objects, camera, lens settings and timings are
unchanged. Astra checked the new native 2.5/15.2 s frames and complete 9.8 s
overview: the edge defect is absent and all five paragraphs remain visible.
This repair review does not approve the new continuous movie.

The user subsequently required uniform 3840×2160 delivery. The new
`fulltext-acquisition-r12-4k` take retains the same literal content, shot timing,
reading path and proportions, with native 4K text, camera and lens scaling.
Historical files stay bound to their original sizes and SHAs. Resolution does
not transfer human approval; the new actual 4K movie needs its own feedback.
The current 12 s Guided movie SHA is
`0ec32619408a51924b80eb5382501c8b4a8eaa93cfa06665e7cf8c4d6e3a815f`;
its request SHA is
`93c7bb890bdd52084ab86833645b52bb41306659b84232060eab0cf4580d7f4e`.
Its human review remains **PENDING**.

Agent frame review and technical checks may find geometric defects. They cannot
claim the continuous movement feels like first-person problem solving. The next
human review must bind the actual new movie SHA and answer these questions:

1. Does the complete source appear before the search, rather than a preselected
   evidence sentence?
2. Does the retained question cue feel like information kept in mind?
3. Without annotation lines, can the moving clear region convey where attention
   is going?
4. Does the hit become stable before the short highlight?
5. Does the complete condition remain readable before the same words lift?
6. Does this feel like doing the problem, or watching a teacher's presentation?

Do not transfer the first synthetic A/B feedback, old overall approval or Astra's
design recommendation to the new full-source movie. New human status stays
PENDING until feedback on that exact movie arrives. P2 integration remains
blocked by the user's explicit requirement to review acquisition first.


## User revision after the first 4K preview

The user marked the r12 Guided movie
`0ec32619408a51924b80eb5382501c8b4a8eaa93cfa06665e7cf8c4d6e3a815f`
as **NEEDS_REVISION**. Exact feedback: “仍需修改，请指出具体位置”,
“物理感可适当加强一点，这个有点僵硬”, and “都有” in response to
focus, search rhythm/camera movement, and hit-to-sentence extraction choices.
No exact problem timestamp was supplied. These are requests to improve all
three areas, not a human PASS or permission to integrate the full film.

Astra's frame/code review attributes stiffness to linear row-node velocity
changes and simultaneous foreground/background lift with a linear camera.
Root's second review accepts a bounded refinement: focus precedes the camera,
row joins retain velocity, acquisition brakes without extra zoom, and the same
sentence leaves the plane before background retreat and reflow. Lens strength,
all original words, cue and evidence bindings, final poses and 20-second timing
are preserved. The first new build's native carry check caught a redundant
first-row key with zero speed; a fresh project removes it. No failed build is
represented as an accepted take.

The next exact movie requires its own visual review; sound remains deferred,
P2 remains HOLD and all release flags remain false.


## Transparent-foreground refinement — current delivery

Baseline is main@1c34c8e76ddee9be893317d52a47577740f71b67. The latest user
instruction, “把提取出来的那一段的字背景变成透明的”, supersedes the
intermediate paper-plane direction. The current isolated output is
`local-data/method-relay-dual-pass/fulltext-acquisition-r22-4k`.

Request 0.2.14 uses motion profile 0.1.0. The reading focus leads the camera by
1 Fast / 2 Guided frames at internal row nodes; the camera carries nonzero
Bezier velocity instead of stopping on each row. Acquisition settles in its
existing window before the original brief filled highlight. Lift starts with
the same original sentence departing 24 design depth units before background
retreat/reflow. The original sentence has no paper plane, border, shadow or
editorial mask and stays fully visible. Unselected source opacity retires from
28 to 0 at departure, then returns to 28 over the last two Lift frames after
clearance. This changes presentation only.

The native 20-second timing, five-paragraph overview, literal cue, evidence
span, word IDs/strings, lens strength, final positions and reading holds are
unchanged from the first 4K request. Same-object provenance, question binding
and current supplied status are revalidated. No peel, teaching conclusion,
new method action, voice or music is added.

Native audit reads actual camera carry, sentence departure, background hold
and opacity, foreground opacity and absence of source masks/paper planes.
A first build's zero-speed row node and a later background-through-text defect
were found before delivery. Paper-plane drafts and an expensive projected-mask
experiment are superseded; the latter failed preview and is absent from the
current producer. Failed/partial captures remain local and do not count as
completed previews. The current full native preview includes the formerly
problematic 18.875 and 19.042 second positions.

All 85 relevant portable tests PASS, including exact legacy request replay,
wrong source masks, foreground paper, opacity loss and row-stop rejection.
The 773-file input audit remains PASS: 769 unchanged, four already-authorized
workflow changes, no missing or unexpected modifications. Separate byte checks
keep the first 4K project and all three first 4K movies unchanged.

Engineering rendering does not certify first-person naturalness, teaching
validity or human taste. New visual review remains PENDING; the earlier viewed
Guided take remains NEEDS_REVISION. P2 full-film integration remains HOLD.
`final_voice_accepted=false`, `production_eligible=false`,
`public_render_ready=false`; listening review remains DEFERRED_BY_USER.

Exact current spec SHA: `132e308e36f67e422acef6ce8d704d8fd798c1c9f5d09cc495dfa5e8e6813d96`.

Native four-span render DONE, 480 frames, 3840 × 2160 / 24 fps; 403055 ms total.

| Movie | Duration / frames | SHA-256 |
|---|---|---|
| `FULLTEXT_LOCATION.mp4` | 20 s / 480 | `49b933c9330932d2592e5d1e45bf41cfa0f4cfd5edbbd15892ca81219e5052c4` |
| `FULLTEXT_FAST.mp4` | 7 s / 168 | `7dceea4f40c605623cba919c649a05143a49f38005f64d3232fa9b64589fdba4` |
| `FULLTEXT_GUIDED.mp4` | 12 s / 288 | `4731195ccf29c4680789c31107ca66826e94d28bfacd3e1a771b7ddbd38097a5` |

Native project SHA: `ffdcba6c98658e795fc804d04982c6bfda60e4a98649626c0dcc317700c66b51`.
Native TIFF archive SHA: `c57f724b3769a7a0ad22e57cbab5ccd7ce8993133d0f41c5b1c3d94586c25562`.
Executed template SHA: `c250ed76861c94707b2d3301be4b6f391221238eb023c1f0f8900554948a893e`.

All 480 encoded frames decode at native 4K. Local review boards sample 228
chronological frames, including dense hit/Lock/Lift samples. Root inspects
actual decoded early Lift, source recovery and final pose; this is technical
frame review, not human continuous-motion approval.


## Sentence attention — current 4K experiment

Baseline: main@ccfd972. User requested Apple-like restrained magnification,
with smoothness the priority, and explicitly authorized implementation.
Current take: local `fulltext-acquisition-r24-4k`, request 0.2.15.

Original sentence words share one quintic envelope and geometric anchor.
Fast gain is capped at 1.5%, Guided at 2%; native same-line glyph clearance
reduces the first and target sentences to approximately 0.396% and 0.430%.
This is not a uniform 2% enlargement. Entry is four frames, ordinary exit six;
the acquired sentence retains gain until Lift and retires it through that
movement, reaching the original final pose. No bounce, page zoom, text reflow,
source masks, paper backing or new voice is added. Literal punctuation groups
are editorial visual units, not new semantic or evidence certification.

An initial draft's timing used the full last-row width. Native inspection
led to a fresh project with windows constrained to the actual shortened focus
path; the subsequent unvisited sentence does not activate. Old projects and
movies are preserved. Existing source, evidence, word/claim identity, question,
camera route, 20-second timing, final positions and frozen files are verified
unchanged against r22. No ANSWER or Registry write occurs.

87 portable tests pass. Native audit and expression validation pass; native
scale ratios prove actual execution rather than an intent-only record. The
depth-first movement is checked before the attention expression, with actual
sentence focus and magnification checked after expressions.

Astra's read-only second review finds the shared multi-line envelope and
Lift transition suitable for a conservative first trial. It notes a roughly
1.3-frame lag of the Fast short-sentence peak after focus leaves: continuous
mathematically, but a possible original-speed listening-free visual issue.
This observation is not user approval. Smoothness and the visibility of gains
limited by glyph clearance remain human review questions.

Human visual review PENDING; listening DEFERRED_BY_USER; P2 integration HOLD.
`final_voice_accepted=false`, `production_eligible=false`,
`public_render_ready=false`. No full-film integration or teaching promotion.

Spec SHA: `3f80fab16ad1db8145e11355a3e58cc71852390a1ab3ec8de6c3743b326428bb`.
Semantic binding SHA (unchanged): `e1f06096dc5feb3238ed39e041b481579df8a30d59dabf67c3f001d4a5cd3961`.
Native render: 480 frames, 3840 × 2160 / 24 fps; 754003 ms.

`FULLTEXT_LOCATION.mp4`: 480 frames; SHA `7cc9daaee829991f02fc290ec8b1c145ad4d016d9d81c36dc984817b12db1f77`.

`FULLTEXT_FAST.mp4`: 168 frames; SHA `761ab86dc01874a26ba1e5672f992284209c718212f8ae929785f362d72978fb`.

`FULLTEXT_GUIDED.mp4`: 288 frames; SHA `7ed1deaaee78b3b1d4896faee7f9d4cfd1705a4ad42944b4d9338d2c8f92dab5`.

AEP SHA: `928f4607fb890b3bdadce2710b09ce3510409f70a35003330ba53ab8ca92d524`.
Template SHA: `2e088de0a8b218f84dbc55bf336a9abd0771e18df934eea8188c19b924b949d8`.


## Row handoff refinement — current delivery

Baseline main@ec066f9. The user marked the preceding sentence-attention take
as needing refinement specifically at row-to-row transitions. Current output
is isolated in local `fulltext-acquisition-r26-4k`, request 0.2.17.

The previous focal return jumped from line-end to next line-start in one
frame. Fourteen actual adjacent-row boundaries now use quintic Hermite
transitions: two frames Fast, four Guided, preserving endpoint position and
velocity. All windows include the entire former one-frame interval. Native
audit measures actual endpoints/velocity and rejects incomplete coverage.
Astra caught two short-row windows clipped by a preliminary quarter-row cap;
that partial draft was stopped, confirmed idle in AE before fresh construction,
and does not count as completed delivery. The half-row cap fixes both joins.

Sentence magnification amounts and shared multi-line envelopes, original
words/spans, frozen evidence, question cue, camera route, total timing and
transparent Lift remain unchanged from r24. Original r24 media/project hashes
and frozen bundle/status file hashes are verified unchanged. No new teaching
fact, ANSWER/Registry write, voice, music or full-film integration is introduced.

88 relevant portable tests pass, including missing joins, endpoint/velocity
mismatch and incomplete short-row coverage. Native audit and expression
validation pass. Eleven native preview samples inspect both formerly clipped
Fast joins, a Guided return and transparent Lift. Full encoded frame decode
and dense row-boundary boards are technical evidence, not human taste approval.
Sentence activation still uses the established reading clock; any perceived
phase mismatch between that clock and the new focal handoff needs original-speed
human review. No increase in magnification or blur is claimed.

Human visual review PENDING; listening DEFERRED_BY_USER; P2 integration HOLD.
`final_voice_accepted=false`, `production_eligible=false`,
`public_render_ready=false`. Videos and Adobe files remain local only.

Spec SHA: `c6f7d8ef7e20bb88c9f81aa02590dc5371453218ae753ff061f4b58dc71edbe1`.
Semantic binding (unchanged): `e1f06096dc5feb3238ed39e041b481579df8a30d59dabf67c3f001d4a5cd3961`.
Native 4K render: 480 frames, 3840 × 2160 / 24 fps; 662593 ms.

`FULLTEXT_LOCATION.mp4`: 480 frames; SHA `fff858f8f7e1a9b892cebdddbe764d1eed8b608f10aa20f44de0ca8445668f7e`.

`FULLTEXT_FAST.mp4`: 168 frames; SHA `955279515b570de34b5d4455cbfd6e7302d9bc8e30600e775c0bb99ff97aa302`.

`FULLTEXT_GUIDED.mp4`: 288 frames; SHA `60ea73e0e576b685c188fecb9a25d3261a4e340ce9ade767e5e62e98bbd3ae3b`.

Native AEP SHA: `3b6d74181951a7c3bf8df541ddca6ebf46ef1447d7865b03aced7c744ba2de87`.
Executed template SHA: `6698b1113cd55766fca483b3b1170296cc9811270bf55a2bbc0a6ddce8723732`.


## In-place attention refinement — current delivery

Baseline main@0d6b024. User feedback rejected the attention enlargement's
perceived upward pop and explicitly retained the smooth row switching.
Current isolated take is local fulltext-acquisition-r27-4k, request 0.2.18.

Attention 0.2.0 preserves original baseline Y and depth Z while gently scaling
original glyphs and adjusting horizontal spacing. Fast gain is capped at 0.8%,
Guided at 1.2%, with native clearance reducing these where necessary. Entry
uses eight frames and retirement ten frames, quintic smootherstep without
spring or overshoot. Actual sentence Lift remains a separate unchanged action.
All fourteen focal row handoffs, camera route, source content, evidence,
question cue, shot times and total duration are unchanged from r26.

89 portable tests pass, including rejection of vertical/depth displacement.
Native transform readback verifies zero baseline/depth delta and actual gain
at most 1.2%; native audit and expression validation pass. Eleven native preview
samples cover short Fast joins, a Guided return and transparent Lift. Encoded
frames are inspected separately. These checks do not establish perceptual
silkiness or human visual acceptance.

Old r26 movie and project hashes and frozen bundle/status hashes remain intact.
No ANSWER/Registry writes, new teaching claim, voice, music or full-film
integration. New visual review PENDING; listening DEFERRED_BY_USER; P2 HOLD.
final_voice_accepted=false, production_eligible=false, public_render_ready=false.
Workflow only is committed; real source, projects and videos stay local.

Spec SHA: `3b1a4ac46be49b9a31f47c7996a8d2741e0391e2a076a43c81cf31d3cfabd202`.
Semantic binding: `e1f06096dc5feb3238ed39e041b481579df8a30d59dabf67c3f001d4a5cd3961`.
Native render: 480 frames, 3840 × 2160 / 24 fps; 684856 ms.

`FULLTEXT_LOCATION.mp4`: SHA `1defa0b56b2c2e657354873021781c9799317c955f51c7c4cd2952098567cb17`.

`FULLTEXT_FAST.mp4`: SHA `0433b6dbc3d2ba62cc332576e6b6d43d199a0870cd03bd8ba7503c3b025fa3d9`.

`FULLTEXT_GUIDED.mp4`: SHA `d09f5819896a12127808cb214b037a7f28a6808aff7cb1763682720fcfa75b6a`.

Native AEP SHA: `e5cbac9474d4fab57814eb3f3005c4193c333919ea731a90659781c4960e315e`.
Executed template SHA: `bc163d7c63b513865beb41a7340bd48561286bfc8790fe7fae6da6bccc451562`.

Encoding recovery: initial H.264 encoding exhausted available memory; all
480 completed native TIFF frames and their verified archive were retained.
The producer now bounds TIFF decoder and filter parallelism independently.
After saving the current AE project and purging transient AE caches while
rendering was idle, encoding resumed from hash-verified frames without another
native render. CRF, encoder settings, dimensions, cadence and shot timing
remained unchanged. Three outputs passed complete stream decode. Twenty-four
selected encoded native frames were inspected on two chronology boards;
continuous-motion human review remains PENDING.


## Human acceptance — r27 Guided attention

On 2026-10-09, after the current 12-second native 4K Guided preview was
presented, the user replied “可以可以”. This is external human visual PASS
for the displayed r27 Guided acquisition clip, request 0.2.18, spec SHA
`3b1a4ac46be49b9a31f47c7996a8d2741e0391e2a076a43c81cf31d3cfabd202`.
Reviewed movie SHA:
`d09f5819896a12127808cb214b037a7f28a6808aff7cb1763682720fcfa75b6a`.

The accepted visual baseline is subtle baseline-locked magnification with
smooth row switching, brief filled keyword highlights, transparent extraction
and the original-source attention route. Preserve this behavior in subsequent
integration work. Local human-visual-review.json records the exact user feedback
and movie binding separately from generation receipts, which retain their
historical PENDING state.

This feedback is scoped to the displayed Guided clip. Fast and the integrated
full film have no new human PASS; the existing two-clip integration gate is
unchanged. Listening remains deferred. Teaching certification and source,
editorial and public-release states are unchanged; public_render_ready=false.


## Scoped Fast acceptance and reopened Guided camera pacing

The user explicitly approved the r27 Fast preview: “可以，快版也通过”.
Movie SHA `0433b6dbc3d2ba62cc332576e6b6d43d199a0870cd03bd8ba7503c3b025fa3d9`;
spec SHA `3b1a4ac46be49b9a31f47c7996a8d2741e0391e2a076a43c81cf31d3cfabd202`.
This preserves Fast approval without treating it as acceptance of subsequent
Guided camera concerns. Local review history retains both explicit approvals.

The user subsequently identified scan camera speed changes as unnatural and
jerky, and proposed a Guided attention rhythm: rapid transition between
predicates, slower recognition with brief highlights and comparison against
the retained question keyword, until the corresponding expression appears.
Whole-film integration remains HOLD while this Guided revision is open.

Read-only sampling of the actual r27 native camera obtained 117 frame samples
between 10.4167 and 15.25 seconds. Inside the scan (10.6–14.65 seconds),
central-difference speed ranges from 14.4836 to 359.6330 native world pixels/s,
with a peak at 11.9167 seconds. Scan camera depth is constant; the issue
concerns uneven vertical transport, not continued depth zoom. This is measured
motion evidence, not a perceptual metric or a proof of the proposed fix.

Preserve accepted baseline-locked magnification, smooth focal row handoffs and
Fast pacing. No new render or teaching inference is authorized by this report.
Existing q33 export binds the hit expression and complete evidence sentence,
but provides no reviewed sequence of predicate spans or q33 R12 action.
Video-side timing may not invent those labels or synonym judgments. Astra
creative review is requested; any implementation must retain source bindings,
original objects and release separation. No ANSWER/Registry or frozen input
changes. Sound remains deferred and public_render_ready=false.


Terminology correction from the user: attention candidates are not restricted
to predicates. They are locating expressions of the same part of speech as
the retained question keyword. Fast transport and slower recognition apply
to these candidate expressions. Same POS is not semantic correspondence or
answer evidence. The current frozen export has no reviewed per-candidate POS
and correspondence bindings; this remains a creative direction requiring
those inputs rather than a newly certified grammar or solving rule.


## Astra direction and root second review — locating expressions

Astra recommends separating lens transport from attention rhythm. For Guided
only, replace per-row camera speed resets with one continuous monotonic
longitudinal progression, near-uniform through the middle, with gentle entry
and final acquisition deceleration. Retain column center, depth of field and
endpoint framing. Fast remains the explicitly accepted take.

After upstream supplies candidate source spans and correspondence evidence,
trial attention intervals at 24 fps: 3–5 frames focal transfer; 4–6 frames
brief filled-highlight activation; 5–7 frames recognition dwell; 2–3 frames
retirement. Only one passage expression is active at a time; the literal
question keyword stays quietly present. Camera transport does not stop at
every candidate. Preserve existing hit (14.75–15.5s), full-sentence confirmation
(15.5–16.5s), subtle attention magnification and transparent Lift.

Root second review accepts this as a bounded creative direction, with these
constraints: same POS does not establish synonymy; the visual layer cannot
choose or certify candidate spans; viewed candidates cannot be crossed out or
presented as excluded answers. No VO grammar lecture, visible POS labels,
annotation underlines, extra zoom or modification of the retained question
phrase. Suggested durations are trial values, not human-approved motion.

Execution order: isolate the Guided camera-speed fix first; obtain explicitly
bound candidate spans and correspondence inputs second; trial attention
highlights third. No new render or camera change has been executed in this
advisory step. Full-film integration remains HOLD for the open Guided revision;
listening remains deferred and public_render_ready=false.
