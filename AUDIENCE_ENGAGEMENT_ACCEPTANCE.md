# Audience Engagement Design v0.1 — delivery checkpoint

Baseline: `main@d0fabe49009f36565cf4918d203a9644a422a27b`.

This independent increment adds a source-bound creative planning and audit module without altering ANSWER, Registry, Pedagogy, student-facing Copy, native AE/PR, existing release gates, original Frozen Packages, or research grades.

The module consumes verified multi-question episodes and reflects their real source-linked narrative beats, reviewer-limited payoff and question order. It returns beat-by-beat audience attention/participation/energy and speed decisions, no generated claims.

Validation is structural only; it does not certify actual viewing enjoyment, understanding, audience retention or sharing. `human_review=PENDING`, `propagation_metrics=UNKNOWN`, `learner_comprehension=NOT_ASSESSED`, `public_render_ready=false`.

**Execution:** isolated local smoke test over a stubbed episode verifier succeeded. The full private repository regression and actual two-question cinematic pilot have **NOT** run in this environment. Complete `python -m unittest tests.test_audience_engagement -v` and affected regressions in the main development environment before accepting for production. No real exam, media or licences committed.

Next: actual human-authored engagement direction → revalidated real episode → existing Copy/Choreography/AE/PR → viewer review. Do not auto-publish or infer engagement from planning.
