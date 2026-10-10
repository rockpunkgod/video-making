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
