# Free Showcase Publication Policy 1.0.0

Policy: `free_showcase_v1`. Brand: **英语有画说**. Series: **学霸这题怎么做？**. Promise: **把英语做题的关键一步，拍给你看。**

Free Showcase presents supported actions on actual questions. Paid Mastery plans broader conditions, counterexamples, combinations and independent practice. Method Validation studies generalizability. These routes cannot change ANSWER facts or borrow one another's approval.

## Highest-priority product correction: Experience First / Rigour First

`content_profile=FREE_SHOWCASE` optimizes experience, cognitive payoff and propagation after common hard gates. Creative Director leads organization. Its ordered quality rubric is Hook, Engagement, Narrative, Cognitive Payoff, Visual Impact, Voice Performance, Memorability and Shareability.

`content_profile=PAID_MASTERY` optimizes mastery and transfer after the same truth and source gates. Pedagogy / Teaching Review leads organization. Its separate ordered rubric is Teaching Accuracy, Evidence, Applicability, Boundary, Action Executability, Method Integration, Practice and Transfer. Paid content is not an elongated free episode; it needs actual teaching and practice design supporting its claims.

Truth, actual Source Rights, No Fabricated Claims and No Unsupported Final Answer are common hard gates, not free quality score components. Quality scores cannot bypass them. Do not combine both rubrics, impose research First-use on ordinary free releases, or inherit paid teaching validation from a favorable taste review. Missing human experience or real propagation data remains PENDING / UNKNOWN.

Selection → Copy → Director → Motion → Voice → Premiere → Human Review must carry the same explicit profile in the episode's editorial handoff records. The tag belongs outside frozen ANSWER and `voice-delivery/v1`; it cannot alter either contract's teaching or audio payload. Current release checker implements only Free Showcase: a Paid Mastery request must not be routed through it as if its mastery requirements had passed.

Full difference audit: [EXPERIENCE_FIRST_DIFFERENCE_AUDIT.md](EXPERIENCE_FIRST_DIFFERENCE_AUDIT.md). Complete storyboards, VO, rhythm and supported payoffs precede new technical implementation. A case with enough evidence is not automatically an engaging episode.

## Existing gate audit

At `main@3a606b26d127f4896d99cb14a78a03eb42128428`, `content_os.release.publication_check` calls scope-specific Teaching Release, then current-upstream/display/final-copy human checks. It does **not** call Evaluation. `ae_contract` rejects unapproved public handoff. `core.release.check_release`, invoked by Registry promotion validation, consumes Evaluation, verified Case slots and external method approval. First-use, Blind/Baseline and Transfer requirements apply there. `evaluation.harness` computes research recommendations; it does not approve Video Packages.

Some Cinema prose mixed independent transfer with publication gates. Its research status remains PENDING; it is not a prerequisite for an ordinary free episode. Existing package, research and Adobe handoff implementations remain unchanged. New approval lives in a separate versioned decision, never changes a legacy boolean or promotes a Method Card.

## Scope-bound truth and four reviews

`content_os.showcase` consumes validated Frozen Video Packages or the existing frozen reviewed-passage transport through a narrow adapter. It reads no teaching Markdown, Registry or raw question bank. The passage adapter keeps direct-text answer authority separate from auxiliary method actions. Current supplied status and frozen source are rechecked.

Every decision binds policy/version, teaching inputs, result scope, final Hook/voiceover/subtitles/visual text/memory, actual excerpts/images/attribution/materials, picture, audio and actual exported bytes. Every external credential binds that complete input set. Any change expires old approvals; history remains in separate files.

| Review | Required coverage |
|---|---|
| Teaching Claim | Current question, evidence, actual action, result scope, Role, necessary Stop and final-copy consistency |
| Source Display | Actual excerpts, images, attribution, display scope, music recording and voice rights |
| Editorial | Final Hook, speech, subtitles, visuals, music and scope consistency |
| Final Media | Actual picture, encoded audio, subtitles, frame integrity, display scope and version |

External human credentials require a named reviewer, review ID, timezone-aware date and evidence notes. AI and unfilled templates cannot approve. As with legacy credentials, software verifies declarations and bindings; the operator must authenticate the human and their evidence. These checks are not English truth certification or human taste review.

The checker hashes actual media/material/audio files and probes and fully decodes the export, requiring 4K24 and an audio stream. Stream presence does not prove intelligible narration or accurate subtitles; Final Media and listening reviews remain independent. Unknown/internal-only source or recording rights stays HOLD; denied rights blocks publication.

| State | Meaning |
|---|---|
| INTERNAL_ONLY | Current inputs, supported claims or actual export incomplete |
| READY_FOR_HUMAN_REVIEW | Current structurally supported export; approvals or rights still HOLD |
| APPROVED_FOR_PUBLIC_EXPORT | Four current external human approvals and explicit approved rights |
| BLOCKED | Invalid teaching/result, rejected review, denied rights or changed/missing bound media |

First-use/Transfer is deliberately not an input. Approval claims no method maturity, Efficient/Signature, learner transfer, audience preference or propagation result. No publishing operation exists. R02 local elimination cannot imply a unique answer; F01 partition cannot become elimination; G01 function cannot become word form; R09 framework cannot become answer; R01 lexical absence cannot prove semantic absence. Action/Stop references remain mandatory; humans review actual final meaning and decisive qualifiers. Prefer normal task guidance and real unresolved candidate states to disclaimer walls.

## Method-centered episodes

The unit is **one core method → one episode → two or three independently bound real questions**. Method organizes the episode; question drives narrative; action drives motion. Establish/Variation/optional Amplification are editorial roles, not certified transfer. Each question has original task, observation, first action, necessary helpers, evidence, judgment, payoff and lawful closure. Helpers retain attribution; no question borrows another question's Review.

Use shared Signature Motion with independent choreography. First-question replay may be fuller; later replay is optional. Approximately 90–180 seconds is an editorial starting point, never a hard gate. Approximately 20–45 seconds is for derivatives, which require renewed scope/display/editorial/media review. If only one supported question exists, report the missing second source.

## Lightweight interfaces

A private Free Brief records `Hook → Action → Proof → Payoff → Scope → Memory`, actual references, necessary qualifiers, prohibited claims, rights and editorial recommendation. Paid Expansion Notes mark future conditions, boundaries, counterexamples, combinations, transfer practice and correction as NOT_COMPLETED. Never withhold a decisive fact to sell the expansion.

`feedback_template` records hypotheses, Hook/Payoff types, future platform/version and T+3 review. Without publication, retention/saves/shares and results remain UNKNOWN. No prediction engine, scraper, payment or membership system is added.

```powershell
python -m scripts.free_showcase REQUEST.json --statuses STATUS.json --output NEW-DECISION.json
python -m scripts.free_showcase REQUEST.json --statuses STATUS.json --review-template teaching_claim --output NEW-PENDING-REVIEW.json
```

Contracts are `video/schemas/showcase-*.json`. Keep real questions/copy/media/Adobe files private. Commit only workflow, schemas, synthetic tests and sanitized reports.
