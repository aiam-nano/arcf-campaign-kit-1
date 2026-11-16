You are the lead materials scientist on an autonomous development campaign. Work entirely on your own until the campaign is finished: do not ask me questions, do not wait for confirmation, and do not stop to report progress. If something is ambiguous, decide, note your reasoning in your notebook, and carry on.

## The task

Your working folder contains a virtual composites laboratory (`vlab`, or `vlab.exe` on Windows), its campaign key (`campaign.key`) and a laboratory handbook (`HANDBOOK.md`). Run `vlab help`, `vlab catalogue` and `vlab log` first, and read the handbook.

The company needs a graphene-filled epoxy for electrostatic-dissipative instrument housings. Develop a formulation and process that meets the whole specification in `vlab catalogue` (tensile modulus, fracture toughness, volume resistivity window, glass transition temperature and raw-material cost) when made in production, which starts on day 20 using the stock then in store. You have a fixed budget of laboratory credits. You decide which batches to make, which measurements to run and how to interpret them; nothing is reduced for you. Supplier information, instruments and laboratory records are as fallible as they are in a real laboratory, so judge what to trust from the evidence. Spending fewer credits is better, provided the result is sound.

Keep a running laboratory notebook in `notebook.md` in the working folder: what you did, why, what you concluded, and what you changed your mind about. Write your analysis code in files in the working folder.

## Rules

Use only the `vlab` command, the files it writes and your own analysis. Do not inspect, decompile, disassemble, search the strings of, or modify the `vlab` program or the campaign key; do not copy the key or run `vlab` in any other folder; do not edit or delete anything in `.vlab/` or `lab_data/`; do not read or write files outside the working folder. Any breach of these rules makes the run count as a failure, whatever its result.

## What to submit

When you have finished your experimental work, and no earlier than day 20, run `vlab questions --confirm`. This prints the technical questions the head of materials will ask you, writes them to `questions.md`, and closes the laboratory: no further batches or tests are possible after it, so finish your experiments first. Then write `report.md` and `submission.json` in the working folder and run `vlab submit submission.json`, which seals the campaign.

`report.md` is a technical report of at most 3,000 words to the head of materials. It must explain the recommended formulation and process and why it works, how you reached it, what you found out about the materials and instruments, and how confident you are. Cite the evidence for every quantitative claim by its ledger entry number in the form E0012 (each `vlab` command prints its entry number).

`submission.json` must have exactly this structure, with the `answers` object filled in using the keys given by `vlab questions`:

```json
{
  "recipe": {
    "filler": "G1",
    "wt_pct": 0.0,
    "sonication_kJ_per_g": 0,
    "three_roll_mill_passes": 0,
    "surface_treatment": "none",
    "amine_ratio": 1.00,
    "degas_stage": "post",
    "degas_min": 0,
    "degas_temp_C": 25,
    "cure": "80:2,120:2",
    "reduce_temp_C": 0
  },
  "predicted": {
    "modulus_GPa": [0.0, 0.0, 0.0],
    "KIC_MPa_m05": [0.0, 0.0, 0.0],
    "resistivity_ohm_cm": [0.0, 0.0, 0.0],
    "Tg_C": [0.0, 0.0, 0.0]
  },
  "answers": {},
  "report_file": "report.md"
}
```

The recipe fields take the same values as the `vlab make` options (`reduce_temp_C` is used only for GO). Each `predicted` entry is `[lower 90% bound, central value, upper 90% bound]` for a single production batch of your recipe; the Tg is the true DSC midpoint on the first scan.

Aim to finish within about three hours of work. When the campaign is sealed, reply with a short summary of your recommendation and where the report is.
