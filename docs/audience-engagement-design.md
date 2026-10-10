# Audience Engagement Design v0.1

## v0.2 extension

The v0.1 direction contract and existing tests remain supported. New `schema_version=0.2.0` directions use PROBLEM, CURIOSITY, ORIENTATION, SEARCH, RECOGNITION, ANTICIPATION, COMPARISON, DISCOVERY, PAYOFF, PROGRESSION and RECALL. Every beat adds `viewer_state` and explicit `editorial_signals`; all other frozen bindings and restrictions remain intact.

`viewer_state` contains current_problem, information_already_seen, current_attention_object, viewer_expectation, viewer_task, unresolved_question and next_information_gain. Seen information is a list of earlier beat IDs within that same question, preventing future or cross-question references; all other entries are editorial descriptions. These states are designed viewing tasks, not measured mental states or new teaching claims.

`editorial_signals` requires booleans hook_link_clear, payoff_leaked, reading_space, motion_without_gain, repeated_explanation, method_name_dominates, voice_over_hold and information_overload. They are declared editing concerns, not observations of retention or comprehension. Local replay without new information and subsequent questions without novelty also generate concrete issues: episode/question/beat, type, reason, viewer cost, recommended edit and source constraints. No aesthetic PASS is returned.

`director_handoff` validates the audience plan against current frozen inputs and binds each beat to explicitly named existing Adaptive scenes sharing its source refs. It carries only suggestions and planned scene ranges. It does not execute Adobe, alter native events or manufacture export times. Playback meanings map to existing Fast Pass, Local Replay, Guided Inline, Observation Hold and Payoff Hold; Action/Attention/Comprehension clocks remain in the existing production system.

Release observations, final-cut reviews and rule evolution are separate from this Director. See [Audience Learning Loop](audience-learning-loop.md), [upstream mapping](cheat-on-content-integration.md) and [architecture audit](../AUDIENCE_ENGAGEMENT_ARCHITECTURE_AUDIT.md). The original v0.1 reference below describes the retained compatibility contract.

**Purpose:** Design viewer attention, curiosity, participation, new information, cognitive release and the transition between questions in a FREE_SHOWCASE episode. This is a creative editorial layer, not a solver, retention predictor, extra pedagogy gate or TTS/motion engine.

## Integration

```text
ANSWER Frozen Evidence / Action / Review
→ Method Episode (creative_os.episode; two or three separate real questions)
→ Audience Engagement Design (editorial viewing intentions)
→ existing Copy / Student POV / Method Choreography / Prosody / Director
→ AE → Premiere
→ existing free_showcase_v1 publication reviews
```

The input is a previously verified `method_centered_episode`; every editorial beat corresponds to the exact already-bound narrative beat, and every payoff stays in the original scope. The output copies only source refs, hashes and actions already present; it does not make up English conclusions, extra evidence, voice lines, or methods.

Use `design_engagement(episode, statuses, direction)` then `validate_engagement(plan, episode, statuses, direction)` before handing the editorial intentions to the current director. Input fields include:
- Episode-opening original-task beat and source-supported hook promise.
- Per-question speed strategy: `selected_replay`, `guided_inline`, `continuous_fast` or `mixed`.
- Per-question novelty: new evidence, new obstacle, different application, or audience participation.
- Each source beat's engagement function, viewer action, playback treatment, energy and whether it provides fresh information.

Question A can show a continuous fast operation and selected localized replay. Question B must provide a different reason to watch; do not repeat the full fast-and-guided template for each case. Question C is optional. The first beat must be the real task, payoff cannot arrive before its reviewed source beat, and helper actions cannot be presented as full answers.

## Editorial safeguards

The warning audit flags missing reading holds, missing payoff holds, repetitive pacing, replays with no new information, or insufficient viewer agency. These are **structural design warnings**, not measured drop-off or automatic aesthetic judgements. It imposes no artificial 8-second camera-cut quotas, does not change a source claim, and never alters existing approval logic.

Human judgement remains `PENDING`; observed retention/shares are `UNKNOWN`; independent learning outcomes are `NOT_ASSESSED`; public readiness remains false. Recompute source episode/status and directions before reuse. On stale or withdrawn material, do not reuse an old plan. Final copy/audio/picture rights are still reviewed under `free_showcase_v1`.

## Next production experiment

Use two existing source-bound questions about the same core method; derive an episode in `creative_os.episode`, design the audience curve, then direct a new 4K internal pilot in the existing AE/PR toolchain. Ask human viewers where they felt lost, where they wanted to skip, whether Question B brought novelty, and whether the actual payoff was earned. Do not claim measured audience improvement before actual comparison.
