# Adaptive episode native adapter

This small adapter executes an authored, source-bound episode through the existing
`cognitive-pov-v0.1.jsx` and JUNKDOGE bridge. It does not solve questions, assign
methods, decide disclosure, invent a motion library, or certify viewing quality.

The private `native-request.json` binds the Episode Plan, current upstream status
manifests, director/voice inputs, fonts, executor, source references, native glyph
identities, exact voice WAV files and an explicitly owned scratch directory. Real
inputs, projects, receipts and media belong in ignored `local-data`.

```powershell
python ae/experiments/adaptive-episode/run.py build local-data/<revision>
python ae/experiments/adaptive-episode/run.py audit local-data/<revision>
python ae/experiments/adaptive-episode/run.py preview local-data/<revision>
python ae/experiments/adaptive-episode/run.py render local-data/<revision> --pid <verified-AE-PID> --hwnd <verified-AE-window>
python ae/experiments/adaptive-episode/run.py package local-data/<revision>
```

`build` refuses an existing target. A timeout or uncertain bridge response needs
native-state reconciliation, never an automatic rebuild. `audit` checks the actual
4K composition, lexical text, fonts and source lineage. `preview` emits actual 4K
frames and a smaller diagnostic contact sheet; it is not a visual approval.

`render` uses native TIFF frames in resumable batches, verifies transferred bytes,
and follows the user's one-GiB memory reserve. Batch size limits host work per
request, not episode duration. `package` checks the actual frames and transfer
receipts again before encoding and fully decoding the 4K picture. It is a silent
picture handoff, not the final Premiere/audio delivery.

Fast, replay, inline guidance, observation and payoff timing are authored choices
in the existing direction input. There is no duration target or upper limit.
Whole voice clips determine caption and editorial placement; reading and cognitive
holds are not mechanically sped up. Final Premiere timing/media receipts must be
renewed after picture or voice changes. Human viewing, listening, source rights
and release approvals remain separate. `public_render_ready` remains false.

An authored episode may supply `spec.preview_times` instead of the original
episode's scene names. Points must be within its actual duration (at most 32).
Native key readback is batched in 48-node groups, with a small JSON input per
group, so ExtendScript does not repeatedly parse the entire episode. Two-dimensional
screen scale checks compare the visible X/Y dimensions when AE returns its fixed,
unused Z=100; real 3D scale remains fully checked. Preview requests use pages of
at most 16 frames, matching the native bridge limit. Progress receipts are partial;
only the completed audit is a PASS.

For candidate decisions, `spec.events` binds the exact frozen action and its
output. The existing adapter checks observation → decision → confirmation timing
and mechanically projects the remaining candidate set. An optional
`spec.answer_confirmations` also requires upstream full closure, the candidate's
own check and completion of all provided candidate actions. Retention alone does
not collapse the working set. This is an engineering readback, not semantic truth
certification or proof of a successful viewing experience.

Render progress monitoring is delegated to a low-tier subagent (`gpt-6-luna`,
low reasoning), including native rendering, picture encoding and editorial export.
The monitor reads the current revision's receipts and output state at 45–60-second
intervals, and reports 10-percent milestones, errors or five minutes without
progress. Pending frames are reported separately from verified transfers; a file
appearing is not completion. The monitor does not alter projects, restart jobs,
delete files or approve quality. The primary agent owns production, recovery and
final verification.


Opt-in Audience event handoff is now checked by `current()` and consumed by
`preview()` for planned observation/decision/confirmation sampling. Run the
host-free `audience_preflight` operation on a new revision with a SHA-bound
`audience_adapter` config. See [the interface and B06 execution specification](../../../docs/audience-adaptive-handoff.md).
This is code-level consumption of authored scene/event bindings; no native
execution, media anchor, aesthetic approval or duration extension is inferred.
Existing requests without the config retain their original behavior. The older
Adaptive Adobe write operations still need their existing host-ownership gap
resolved; B06 writes continue through its protected bounded executor.
