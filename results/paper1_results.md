# Results reported in the paper

These are the results of the 17 runs reported in M. Iliut and A. Vijayaraghavan, *Profiling AI agents as researchers: a long-horizon advanced materials development campaign scored against human researcher capabilities* (see `CITATION.cff`). They are given here so that a run made with this kit can be placed beside them. All runs used campaigns A–C with reasoning effort set to high; the full records of every run (ledgers, raw data, reports, transcripts, score files and grades) are in the data deposit on Zenodo.

A run made with this kit is comparable with these numbers only if it follows the same protocol (one prompt, no help, a fresh harness memory, a grader from another vendor). Because the answers to campaigns A–E are now public, a new result can also have been helped by training data that includes them; see the README.

The non-LLM baselines, given the same budget and interface on campaigns A–C, met the whole specification in production in one of fifteen runs (a random-search run whose recipe passed in 77.5% of production batches) and answered none of the technical questions. An oracle with access to the hidden model passes in 100% of production batches on every campaign; its submissions are `answers/reference_submission_<campaign>.json`.

**Table 1** Capability score of each system on each campaign (out of 100; for Opus 5.5, the mean of the two runs on campaign A), with the mean over campaigns and its 90% bootstrap interval, as plotted in Fig. 3a of the paper.

| System (model, harness) | Runs | A | B | C | Capability score, mean [90% interval] |
| --- | --- | --- | --- | --- | --- |
| Fable 5.2 (Claude Code) | 3 | 87.0 | 85.2 | 98.1 | 90.1 [83.1–96.2] |
| Carbon (Antigravity) | 3 | 77.8 | 87.0 | 88.9 | 84.6 [77.8–90.9] |
| Opus 5.5 (Antigravity) | 4 | 81.4 | 88.9 | 77.8 | 82.7 [77.0–88.8] |
| Opus 5.5 (Claude Code) | 4 | 76.8 | 81.5 | 75.9 | 78.1 [72.8–83.3] |
| Hydrogen (Antigravity) | 3 | 75.9 | 81.5 | 72.2 | 76.5 [70.5–82.6] |

**Table 2** Results of every run. Capability scores are fractions of criteria met (Del., project delivery; Des., experimental design; Src., source scrutiny; Ana., data analysis; Meas., measurement judgement; Chg., response to change; Ins., scientific insight; Res., resource management; Rep., honest reporting). CC, Claude Code; AG, Antigravity.

| Run | System | Campaign | Capability score | Del. | Des. | Src. | Ana. | Meas. | Chg. | Ins. | Res. | Rep. | Production pass (%) | Credits | Batches |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fable52_A | Fable 5.2 (CC) | A | 87.0 | 0.33 | 1.00 | 1.00 | 1.00 | 1.00 | 0.83 | 1.00 | 0.67 | 1.00 | 42.5 | 1,373 | 13 |
| fable52_B | Fable 5.2 (CC) | B | 85.2 | 1.00 | 1.00 | 0.83 | 1.00 | 0.83 | 1.00 | 0.83 | 0.17 | 1.00 | 100 | 1,758 | 16 |
| fable52_C | Fable 5.2 (CC) | C | 98.1 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.83 | 1.00 | 1.00 | 100 | 1,314 | 12 |
| carbon_A | Carbon (AG) | A | 77.8 | 0.33 | 1.00 | 1.00 | 1.00 | 0.67 | 1.00 | 0.83 | 0.33 | 0.83 | 25 | 1,800 | 14 |
| carbon_B | Carbon (AG) | B | 87.0 | 1.00 | 0.83 | 1.00 | 1.00 | 0.83 | 1.00 | 0.83 | 0.50 | 0.83 | 100 | 1,624 | 11 |
| carbon_C | Carbon (AG) | C | 88.9 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.83 | 0.17 | 1.00 | 100 | 1,769 | 12 |
| opus55ag_A | Opus 5.5 (AG) | A | 79.6 | 0.83 | 0.83 | 0.83 | 1.00 | 0.83 | 1.00 | 0.67 | 0.17 | 1.00 | 95 | 1,680 | 16 |
| opus55ag_A2 | Opus 5.5 (AG) | A | 83.3 | 0.67 | 1.00 | 0.83 | 1.00 | 0.83 | 0.83 | 0.83 | 0.50 | 1.00 | 85 | 1,740 | 16 |
| opus55ag_B | Opus 5.5 (AG) | B | 88.9 | 1.00 | 1.00 | 0.83 | 1.00 | 0.83 | 1.00 | 0.83 | 0.50 | 1.00 | 100 | 1,734 | 15 |
| opus55ag_C | Opus 5.5 (AG) | C | 77.8 | 0.67 | 0.67 | 0.83 | 1.00 | 0.83 | 1.00 | 0.83 | 0.17 | 1.00 | 75 | 1,690 | 14 |
| opus55_A | Opus 5.5 (CC) | A | 72.2 | 0.33 | 1.00 | 0.83 | 1.00 | 0.67 | 0.83 | 0.67 | 0.33 | 0.83 | 35 | 1,698 | 15 |
| opus55_A2 | Opus 5.5 (CC) | A | 81.5 | 0.33 | 1.00 | 1.00 | 1.00 | 1.00 | 0.83 | 0.83 | 0.33 | 1.00 | 27.5 | 1,665 | 15 |
| opus55_B | Opus 5.5 (CC) | B | 81.5 | 0.83 | 0.83 | 1.00 | 1.00 | 0.67 | 0.83 | 0.83 | 0.50 | 0.83 | 97.5 | 1,566 | 12 |
| opus55_C | Opus 5.5 (CC) | C | 75.9 | 0.67 | 0.83 | 0.83 | 1.00 | 0.83 | 1.00 | 0.50 | 0.17 | 1.00 | 82.5 | 1,665 | 15 |
| hydrogen_A | Hydrogen (AG) | A | 75.9 | 1.00 | 0.83 | 0.83 | 1.00 | 1.00 | 0.83 | 0.33 | 0.00 | 1.00 | 100 | 1,798 | 16 |
| hydrogen_B | Hydrogen (AG) | B | 81.5 | 1.00 | 0.67 | 1.00 | 1.00 | 0.83 | 0.83 | 0.83 | 0.33 | 0.83 | 100 | 1,800 | 17 |
| hydrogen_C | Hydrogen (AG) | C | 72.2 | 0.67 | 0.67 | 0.83 | 1.00 | 0.83 | 1.00 | 0.33 | 0.17 | 1.00 | 82.5 | 1,774 | 16 |

**Table 3** Response to the planted events, by system. Every run named the misleading datasheet, gave the correct DSC offset and made no batch on the old lot after the lot change; those columns are omitted. Days are simulated laboratory days after the event; ranges are over runs. Production pass is the share of forty virtual production batches meeting the whole specification, averaged over campaigns.

| System | Runs | New lot characterised (days after delivery) | Indium check (days after DSC service) | Humidity judged to have no effect | Aspect ratio correct | Amine optimum correct | Production pass (%) | Credits spent (of 1,800) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Fable 5.2 (Claude Code) | 3 | 1.3–3.3 | 0.7–2.3 | 3/3 | 0/3 | 3/3 | 81 | 1,314–1,758 |
| Carbon (Antigravity) | 3 | 1.2–2.5 | 0.1–2.4 | 1/3 | 3/3 | 3/3 | 75 | 1,624–1,800 |
| Opus 5.5 (Antigravity) | 4 | 2.4–4.5 | 2.4–6.3 | 4/4 | 0/4 | 4/4 | 88 | 1,681–1,740 |
| Opus 5.5 (Claude Code) | 4 | 2.5–4.8 | 1.9–15.3 | 2/4 | 0/4 | 4/4 | 70 | 1,566–1,698 |
| Hydrogen (Antigravity) | 3 | 1.1–6.3 | 0.7–6.7 | 2/3 | 0/3 | 1/3 | 94 | 1,775–1,800 |
