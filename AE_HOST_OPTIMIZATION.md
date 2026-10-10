# AE host optimization — 2026-10-10

Baseline: `main@8606dfd`. This is a host and production workflow repair; it does not change teaching inputs, copy, motion timing, or release decisions.

## Findings and recovery

The pending opacity rebuild exceeded its 600-second transport timeout. AE continued consuming CPU, with roughly 3–4 GiB of process working set and low GPU utilization. A transport timeout did not establish that the operation had finished or that AE had crashed. Targeted Escape temporarily recovered the bridge, but a subsequent read timed out. Configuration, the on-disk project, the mutation request and recovery records were preserved before restarting that specific AE session.

The normal desktop shortcut subsequently restored AE 26.0x67 and its existing CEP bridge. Earlier accepted projects were not overwritten. The unfinished production revision was reloaded from its preserved on-disk state and checked against its previous spec before applying changes.

Instead of deleting and recreating the opacity keys, recovery updated only existing values under one undo group. The native operation changed 5,024 values and saved the production revision in 1,805 ms. It preserved key times, easing, object IDs, source references and all other properties. The previous complete project SHA remained unchanged. This validates a faster recovery operation; it does not establish the cause of every historical Adobe crash.

## Actual configuration

Hardware: 32 GB installed RAM (about 31 GiB exposed), Core Ultra 9 275HX, 24 logical processors, RTX 5070 Laptop GPU with 8 GB VRAM, NVMe cache storage.

| Setting | Previous | Applied / verified |
|---|---|---|
| RAM reserved for other applications | 10 GB | 3 GB, native Preferences UI minimum |
| RAM shared by Adobe applications | UI: 21 GB | UI: 28 GB |
| Runtime free-memory stop line | 1 GiB | Kept at 1 GiB |
| Disk cache | NVMe G volume, 100 GB | Same volume, 250 GB |
| Multi-Frame Rendering | Enabled | Kept enabled |
| CPU reserved for other applications | 10% | 0% |
| Cache frames when idle | Disabled | Kept disabled |
| Hardware accelerated viewer | Enabled | Kept enabled |
| Power plan | Turbo | Kept |

Entering 1 GB in the native reserved-RAM control was automatically clamped to 3 GB. The shared memory-balancer file independently confirmed 3 GiB. This native allocation setting is different from the pipeline's 1 GiB free-memory stop line. No unsupported bypass of the UI minimum was introduced. AE, Premiere and other Adobe applications share this memory allowance; it is not a guarantee that AE alone can occupy 28 GB.

The existing `setMemoryUsageLimits(20,96)` call was applied, but it did **not** replace the shared reserved-RAM preference; the latter was changed and verified in the native UI. The existing GPU driver and plug-ins were retained. No global preference reset or indiscriminate cache deletion was performed.

Adobe documents the [shared memory pool and disk-cache limitations](https://helpx.adobe.com/after-effects/desktop/memory-storage-performance/memory-and-storage/memory-storage1.html), and the [CPU allocation controls for Multi-Frame Rendering](https://helpx.adobe.com/after-effects/desktop/render-and-export/multi-frame-rendering/multi-frame-rendering.html).

## Native checks

A diagnostic copy of the existing 620-layer production composition rendered the same four frames at 3840×2160, 24 fps with caches purged before each run:

| Mode | Native result | Elapsed |
|---|---|---|
| Multi-Frame Rendering on | DONE, 4 TIFF frames | 3.080 s |
| Multi-Frame Rendering off | DONE, 4 TIFF frames | 3.253 s |

This short comparison shows little separation; it supports retaining the existing MFR configuration, not claiming a large speedup or long-duration stability. All eight output TIFFs were fully decoded and verified as 3840×2160, with individual SHA-256 receipts stored outside Git.

The test reproduced a separate render-receipt bug: setting `RenderQueueItem.render=false` on an already DONE item throws in this native host. The adaptive renderer now removes only its own successfully completed queue item instead. Failed or uncertain output remains subject to inspection; it is not silently retried.

Focused adaptive-frame and memory-guard regression: 15 tests passed. The recovered production revision's native text/source/font audit completed, but its motion audit reported position-key mismatches on some record objects. Those objects were not changed by this opacity recovery. The episode remains unaccepted pending reconciliation of its plan and native positions. Short native rendering and faster key updates are engineering evidence, not human taste, listening approval, or public release approval. Final episode rendering remains a separate delivery task.

## Operating workflow

1. Inspect current native operation status before dispatching another mutation. A degraded bridge is not proof that its script stopped.
2. Preserve accepted project bytes and the current request before recovery.
3. For a values-only change, verify the existing key count, times and previous values; use `setValueAtKey` instead of rebuilding the property. Group the operation for undo and retain a receipt. Use bounded batches for changes whose runtime is not yet measured.
4. Use the existing native TIFF batch renderer and 1 GiB memory monitor for full production. Preserve uncertain batches and reconcile their actual frames before continuing.
5. Keep host settings, native operation results, final-media checks and human reviews separate. These settings are the current tested configuration, not a claim of universal optimality.

Private backups, screenshots, audio, questions, Adobe projects and frames remain in ignored local directories. Only workflow code and this sanitized report are committed.
