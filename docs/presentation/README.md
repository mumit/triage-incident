# Interactive study walkthrough

Open `incident-triage-study.html` in a browser. The single file works offline and needs no model, token, server or installation. Evidence links point to the merged study snapshot on GitHub and need internet access.

The 12 chapters cover the use case, data, policy, zero-shot comparison, first encoder, teacher training, expanded transfer, individual cases, latency, automation coverage and recommendations. Use the chapter navigation or Previous/Next buttons. Left/Right arrow keys work when a form control is not focused. “Read all chapters” shows a continuous report. “Print / save PDF” prints every chapter, with the currently selected chart and case views.

The presentation preserves the distinction between authored reference labels, teacher agreement and operational accuracy. The original post-hoc encoder guards and excluded transfer pair remain identified. It does not run a model or collect user input.

`study-walkthrough.template.html` contains the editable narrative and layout. `scripts/build_study_walkthrough.py` embeds data from the committed evidence, paired public inputs and source hashes. Rebuild from the repository root:

```bash
python3 scripts/build_study_walkthrough.py
```

The build is deterministic. The source links are pinned to merged commit `d26256b385a245073eb44b82794197d20a8022a2`; change that snapshot only when intentionally refreshing the underlying study evidence.

Validated in Chromium: all chapter navigation, chart metrics, the priority boundary, paired-case switching, batching and coverage controls, continuous reading, printing and widths from 320 to 1,440 pixels. Opening from disk produces no external requests. Large tables scroll within their container at narrow widths.
