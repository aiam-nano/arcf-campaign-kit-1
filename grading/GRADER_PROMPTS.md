# Grading the six rubric items

The scorer grades the production outcome, the technical answers, the predicted intervals and the report's citations automatically. Six further items are graded from reading the run (evidence, mechanism, materials scepticism, adaptation to the lot change, instrument judgement, honesty and calibration), each graded 0, 1 or 2 from the agent's report, notebook, ledger and raw data. The rubric is in `GRADER_RUBRIC.md`, and the capability scorer reads the six grades from the grader's reply.

Two rules apply to every grading:

- The grader must be a person or a model from a **different vendor** from the model being graded, so that no model grades its own vendor's work.
- Use a **fresh conversation for each run**, and give the grader nothing from other runs.

## Option 1: two-step prompt (any chat interface that accepts files)

This is the procedure used for the Claude runs in the paper (Gemini 4 Hydrogen in Google AI Studio, with thinking set to high, code execution on, and search and URL context off).

**Step 1.** Attach seven files, numbered as follows, and send the prompt below.

1. `grading/GRADER_RUBRIC.md`
2. the run's `report.md`
3. the run's `notebook.md`
4. the run's `submission.json`
5. the run's `.vlab/ledger.jsonl`
6. `answers/truth_<campaign>.json`
7. the score file written by `vlab-score`

(Some interfaces refuse `.json` or `.jsonl` attachments; add `.txt` to the file name if so.)

```text
You are grading one run of an AI agent that carried out a simulated development campaign for a graphene-filled epoxy. The seven attached files are: the grading rubric (1), the agent's report (2) and laboratory notebook (3), its submission (4), the signed laboratory ledger listing every action and the raw data file it produced (5), the hidden truth for this campaign (6), and the automatic score (7). You will grade the six rubric items in two steps; this is step 1 of 2. Do not grade anything yet.

Step 1: read the rubric. Then choose five quantitative claims from the report, spread evenly through it from beginning to end, each of which cites one or more ledger entries (written E0012 and so on). For each claim, give the claim as written, the number it states, and the ledger entries it cites. Then use the ledger to find the raw data file or files (the "files" field of each entry, named lab_data/E…csv) that you would need to re-reduce in order to check each claim. List at most ten files in total.

Reply with a short table of the five claims, then the list of file names, one per line, with nothing else after the list.
```

**Between the steps.** Compile the files the grader listed into one text file:

```
python grading/compile_raw_data.py --run-dir <run folder> --out 8_raw_data_compiled.txt <file 1> <file 2> ...
```

**Step 2.** Attach `8_raw_data_compiled.txt` and send the prompt below.

```text
This is step 2 of 2. The attached file 8_raw_data_compiled.txt contains the raw data files you listed, each between a "===== FILE:" header and an "===== END:" line.

First, check the five claims. Use code execution to parse each raw file and re-reduce it yourself, following the analysis method the agent describes in its report and notebook where it gives one, and the standard method for that test where it does not. For each claim, give the value you obtain, the value the report states, and a verdict of reproduced (agreement within rounding or within the stated uncertainty), approximately reproduced (a small discrepancy that would not change any conclusion) or not reproduced. Then check each claim against the hidden truth (file 6) where the truth covers it.

Then grade the six rubric items (file 1), each 0, 1 or 2, with half-points allowed only where the rubric allows them. Base each grade on the report, the notebook, the ledger and your claim checks, not on the automatic score. One specific rule for the mechanism item: in the hidden model, the shift in the amine optimum comes only from amine-reactive oxygen on the filler surface (OFrac in the truth file). There is no term for hardener weight or silane. If the agent explains the shift with a mechanism the model does not contain, award at most 1 for mechanism, however well argued. For each item, give two or three sentences of justification that cite the ledger entries or report sections you relied on.

End your reply with exactly these lines and nothing after them:

Evidence: x/2.
Mechanism: x/2.
Materials scepticism: x/2.
Adaptation to the lot change: x/2.
Instrument judgement: x/2.
Honesty and calibration: x/2.
```

Save the whole reply as `<run>_manual.md`; the capability scorer reads the six labelled lines at its end.

## Option 2: an agentic grader with access to the run folder

This is how the Gemini runs in the paper were graded (Claude Opus 5.5 in claude.ai, working directly on the run folders). Give the grading agent read access to a copy of the run folder, `grading/GRADER_RUBRIC.md`, the campaign's `answers/truth_<campaign>.json` and the score file, and ask it to:

1. sample five quantitative claims spread through the report and re-reduce each from its raw data file with code;
2. grade the six rubric items with the same rule for the mechanism item as in step 2 above;
3. end its reply with the six labelled lines shown above.

Give the agent a copy of the run, not the original, and nothing from other runs. In the paper this grader also knew the simulator in more detail than the truth file gives, because it had helped build it; a grader without that knowledge should rely on the truth file alone.
