# Analysis code for the paper

These scripts reproduce every number, table and figure of the paper's results from the published run records. They need Python 3.10 or later with numpy, scipy and matplotlib, and the data deposit:

> Run records of a long-horizon advanced materials development campaign: 17 agent runs (dataset), Zenodo, 2026, DOI: [to be added]

Download and unzip the deposit, then run the scripts from the repository root, giving the deposit folder with `--data` (or setting the environment variable `ARCF_DATA`). Outputs go to `analysis/out/` unless `--out` says otherwise.

```
python analysis/rescore.py     --data <deposit>   # re-scores all 17 runs with tools/capability_score.py and checks them against runs.csv
python analysis/stats.py       --data <deposit>   # system means, 90% bootstrap intervals, run-to-run spread, paired comparisons
python analysis/sensitivity.py --data <deposit>   # the 56 single-threshold moves and the all-easier and all-stricter scorings
python analysis/costs.py       --data <deposit>   # tokens and API-equivalent cost of every run, from the harness transcripts
python analysis/figures.py     --data <deposit>   # Figs 2, 3, 4 and 6 and ESI Figs S1 and S2 (run stats.py and sensitivity.py first)
```

| Script | Paper |
| --- | --- |
| `rescore.py` | ESI Table S3b (capability scores of every run) |
| `stats.py` | Section 4.2 to 4.4, Fig. 3a, Fig. 4, Fig. 6b, ESI Table S3a |
| `sensitivity.py` | Section 4.9, ESI Table S4, ESI Fig. S1 |
| `costs.py` | ESI Table S6 |
| `figures.py` | Figs 2, 3, 4 and 6, ESI Figs S1 and S2 |

Fig. 1 is a drawn schematic (`assets/fig1_campaign_schematic.svg`). Fig. 5 is drawn from the two runs' signed ledgers with the kit's trajectory tool:

```
python tools/plot_trajectory.py --truth answers/truth_C.json \
    --run "Fable 5.2 (Claude Code)|98.1|<deposit>/runs/fable52_C/run_folder/.vlab/ledger.jsonl" \
    --run "Opus 5.5 (Claude Code)|75.9|<deposit>/runs/opus55_C/run_folder/.vlab/ledger.jsonl" \
    --out analysis/out/figures/fig5_trajectories_C
```

## Notes on the method

The capability thresholds live in one place, `BASE` in `tools/capability_score.py`; the sensitivity analysis changes a copy of them and re-scores. The bootstrap uses a separately seeded generator for each quantity (the overall score and each capability), so every result is reproducible on its own and does not depend on which other quantities are computed. The paper's values come from these scripts.

`common.py` holds the system names, colours and campaign list shared by the scripts.
