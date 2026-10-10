# First-person cinema: technical gaps and implementation ledger

This ledger separates missing engineering from human experience and teaching authority. Real production receipts stay local.

| Gap observed | Required implementation | Current evidence/status |
|---|---|---|
| Project-open reply timed out although host project changed | Reconcile expected path against a fresh host read; never replay the mutation blindly | Implemented `reconcile_open`; current project subsequently confirmed by live host |
| XML import retained malformed UNC drive paths and duplicate display names | Resolve actual absolute media paths, reject ambiguous matches; rebuild a fresh native sequence from verified source items | Implemented `resolve_media`; fresh native sequence made and saved |
| Audio stream existed but native export was silent | Verify each complete voice slot in fresh timeline, then correlate each WAV with actual decoded export | Latest two native exports: 15 voices each PASS, minimum correlation 0.9999018; failed takes retained |
| Default encoder preset was unavailable | Bind an explicit installed Adobe preset and validate actual encoded format | Installed H.264 Match Source preset used; final media must pass conformance, not preset-name inference |
| Timeline readback could be partial, shifted or stale | Reject pagination truncation, changed sequence IDs and incomplete/shifted voice endpoints | Implemented `audit_timeline` and synthetic regression tests |
| Three-clock action ranges were generic VO offsets | Map concrete native movement windows through the actual frame mapping; stationary reading has no Action Clock | Implemented `map_event`; 38 concrete existing native events mapped; detailed Fast locating action coverage remains incomplete |
| Guided comparison supplied its conclusion before participation | Split existing comparison into question, quiet recognition and existing conclusion; fit complete WAVs with settled holds | Implemented question → one-second quiet recognition → existing conclusion; source-bound new takes |
| New narration changes invalidate caption/timing approval | New take IDs, exact script review, updated captions, picture mapping, native placement and receipts | Implemented new script, fifteen slots, captions, native AE mapping, Premiere placement and encoded verification; historical takes retained |
| Independent transfer and subjective quality lacked actual evidence | Keep independent reviews PENDING/HOLD; supply grounded review materials | Human work, not a technical capability gap; no invented success |

Reusable implementation: `premiere_production/cinema.py` and `ae/experiments/reading-d-dual-pass/cinema.py`. These checks certify provenance, native placement and encoded signal, never semantic truth, natural speech or learner outcomes.

Remaining bounded technical work:

- The registered Premiere API has no add-audio-track operation. Current production uses separately retained stems and a derived music/SFX bed; independent native SFX track editing needs upstream adapter support.
- Host restart does not guarantee connector panels resume. This run recovered using the existing panel controls and verified live host state; unattended restart recovery is not claimed.
- Fast-search segment timing is source-bound, but its detailed action-event clock is not yet projected. Guided locating has concrete reviewed event mapping. Keep the gap explicit rather than synthesize movement timestamps from narration.
- Full pixel comparison between the saved AE derivative and captioned encoded picture is not certified. Native frame mapping, sampled picture inspection and complete decode are available.

These limits do not prevent the completed internal native cut. Audience quality, teaching permissions and recording rights are independent review work, not engineering defects.
