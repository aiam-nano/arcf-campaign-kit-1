# ARCF campaign kit 1: a long-horizon advanced materials development campaign for AI agents

This kit lets you put an AI agent (a language model working through a tool-using harness such as Claude Code, Antigravity, Codex or Gemini CLI) in charge of a simulated laboratory campaign, and then score what it did against nine capabilities of a human researcher. It is the test used in:

> M. Iliut and A. Vijayaraghavan, *Profiling AI agents as researchers: a long-horizon advanced materials development campaign scored against human researcher capabilities* (2026). See `CITATION.cff`.

ARCF is the Agentic Researcher Capability Framework. This is its first campaign kit.

## What the agent faces

The agent is told it is the lead materials scientist at a company that needs a graphene-filled epoxy for electrostatic-dissipative instrument housings. It has a virtual laboratory (`vlab`), a handbook, a budget of 1,800 credits and about four simulated weeks. It chooses fillers, dispersion, surface treatment, amine ratio, degassing and cure, makes batches and runs twelve kinds of instrument. Every instrument returns raw data only, so the agent reduces everything itself. The formulation must meet a five-part specification in production, which starts on day 20 with whatever stock is then in store.

The laboratory is not well behaved. One supplier's datasheet is wrong, the best grade changes lot partway through the campaign, an instrument reads high after a service, and a logged variable correlates with the results without causing them. At the end the agent answers ten technical questions, predicts its material's properties with intervals, and writes a report that cites its evidence.

In the paper a run took the agent between 9 and 93 minutes of wall-clock time and between 33 and 161 tool calls.

## What is in the kit

| Folder | Contents |
| --- | --- |
| `agent_kit/` | `PROMPT.md` (the only message the agent receives), `HANDBOOK.md`, and the `vlab` program for six platforms (see below) |
| `campaigns/` | Five campaign keys, A to E. Each key generates a different hidden world from the same design. The paper used A, B and C; D and E were used for development |
| `scorer/` | `vlab-score`, the automatic scorer, for the same six platforms. It scores runs on campaigns A–E only |
| `answers/` | The hidden truth of each campaign (`truth_<campaign>.json`) and a reference submission made by an oracle with access to the hidden model (`reference_submission_<campaign>.json`) |
| `grading/` | The rubric for the six manually graded items, the grader prompts, and a helper that compiles raw data for the grader |
| `tools/` | Python tools: `new_run.py` (sets up a run folder), `capability_score.py` (the nine-capability profile), `audit_transcript.py` (checks a harness transcript for rule breaches), `baselines.py` (random-search and Bayesian-optimisation agents), `plot_trajectory.py` (draws a run's campaign timeline) and `ref_analysis.py` (reference data reduction) |
| `results/` | The results of the 17 runs reported in the paper, for comparison |

The programs are in one folder per platform, in both `agent_kit/bin/` and `scorer/`:

| Folder | For |
| --- | --- |
| `windows_x64` | Windows on Intel or AMD processors (most Windows PCs) |
| `windows_arm64` | Windows on Arm (for example Snapdragon laptops) |
| `macos_arm64` | Macs with Apple silicon (M1 and later) |
| `macos_x64` | Older Macs with Intel processors |
| `linux_x64` | Linux on Intel or AMD processors |
| `linux_arm64` | Linux on Arm |

x64 is the usual name for 64-bit Intel and AMD processors; the same thing is also called x86-64 or amd64. `tools/new_run.py` picks the right folder for the machine it runs on.

The Python tools need Python 3.10 or later with `numpy` and `matplotlib` (`pip install numpy matplotlib`). The `vlab` and `vlab-score` programs have no dependencies.

## Before you start: the answers are in this repository

Everything needed to score a run, including the answers, is public. That has two consequences.

- **Keep the agent away from this repository.** Make each run folder somewhere the agent cannot browse out of into the kit, and do not give the agent web access to it. `tools/new_run.py` refuses to put a run folder inside the kit.
- **A score from this kit is a reproduction, not a sealed test.** A model trained after the kit was published may have seen the answers. Use the kit to compare your agent with the paper's results, to study how it works, or to develop it; for a clean comparison between models, use fresh campaigns that have never been published. Fresh private campaigns will be offered through the ARCF evaluation rounds.

## Running an agent

1. **Set up a run folder** outside this repository:

   ```
   python tools/new_run.py --campaign A --dest ../runs/mymodel_A
   ```

   This copies `vlab` for your machine, `HANDBOOK.md` and the campaign key (as `campaign.key`) into an empty folder. Use a new folder for every run. On macOS, clear the download quarantine on `vlab` as the script tells you.

2. **Start the harness with no memory of earlier runs.** Turn off any memory, knowledge or project-instruction features, or check that they hold nothing from earlier runs. Record whether the agent has web access; turn it off if the harness allows it.

3. **Open the run folder as the agent's workspace**, choose the model and its reasoning setting, and paste the whole of `agent_kit/PROMPT.md` as the first message. Send nothing else. If the harness stops for an output or turn limit, reply `Continue.` and nothing more. Allow up to four hours; if the agent has not submitted by then, stop it and score the run as it stands.

4. **Save the transcript.** Export the conversation, and keep the harness's own full log of tool calls if it has one (for example the session `.jsonl` file of Claude Code, or `transcript_full.jsonl` in an Antigravity conversation folder). The audit in step 6 reads it.

5. **Score the run automatically:**

   ```
   scorer/<platform>/vlab-score score --dir ../runs/mymodel_A --out mymodel_A_score.json
   ```

   The scorer checks the ledger's signature chain and the hash of every data file, makes the submitted recipe in forty virtual production batches, grades the ten technical answers, the predicted intervals and the report's citations, and writes 88 of the 100 points to the score file, with the production pass fraction for each element of the specification and for the whole.

6. **Audit the transcript:**

   ```
   python tools/audit_transcript.py --transcript <full transcript> --run-dir ../runs/mymodel_A --truth answers/truth_A.json --ledger ../runs/mymodel_A/.vlab/ledger.jsonl --out mymodel_A_audit.md
   ```

   The audit flags commands outside the run folder, attempts to inspect or modify `vlab` or the key, writes to the ledger or data, and mentions of other runs or of benchmark material. Review every flag against the transcript. A run that breaks the rules in `PROMPT.md` counts as a failure whatever it scored.

7. **Grade the six rubric items** with a grader from a different vendor from the model you tested, following `grading/GRADER_PROMPTS.md`. Save the grader's reply as `mymodel_A_manual.md`.

8. **Compute the capability profile:**

   ```
   python tools/capability_score.py --run-dir ../runs/mymodel_A --score mymodel_A_score.json --manual mymodel_A_manual.md --out mymodel_A_capability
   ```

   This writes `mymodel_A_capability.json` and a readable `mymodel_A_capability.md`: a score for each of the nine capabilities (the fraction of its six criteria met), the criteria met and missed, and the capability score out of 100 (the mean of the nine).

## Reading the results

The nine capabilities are project delivery, experimental design, source scrutiny, data analysis, measurement judgement, response to change, scientific insight, resource management and honest reporting. Each has six observable criteria, listed with their thresholds in the paper's supplementary information (Table S1) and in `tools/capability_score.py`.

Look at the profile, not only the total. In the paper, two systems with capability scores of 78.1 and 76.5 had almost mirror-image profiles: one delivered a passing formulation far more often, while the other explained its results better. The production pass fraction in the score file says how often the submitted recipe works in production; the capability profile says how the agent got there.

Run each agent on campaigns A, B and C at least, and more than once if you can. Run-to-run variation in the paper was about 5 points on the capability score, so differences smaller than that between single runs are not meaningful. `results/paper1_results.md` gives the paper's results for comparison.

## Baselines

`tools/baselines.py` runs a random-search agent and a Gaussian-process Bayesian-optimisation agent through the same `vlab` interface and budget (the work folder is created afresh, so it must not already hold anything you want to keep):

```
python tools/baselines.py random --vlab agent_kit/bin/<platform>/vlab --key campaigns/campaign_A.key --work ../runs/random_A --seed 1
```

## Reporting a result

If you publish a result made with this kit, please give the model and its version, the harness and its version, the reasoning setting, whether the agent had web access, the campaigns and number of runs, the grader model, and any `Continue.` prompts or other deviations from the protocol, and cite the paper. We would be glad to hear of results: please open an issue in this repository.

## What is not in the kit

The simulator's source code, the format of the campaign keys and the program that generates new campaigns are not published, so that future evaluation rounds can use fresh campaigns that no model has seen. The model behind the simulator is described, with its equations and parameter ranges, in the paper's supplementary information (Section S10), and the hidden values for campaigns A–E are in `answers/`.

## Licences

The code in this repository (the Python tools and the `vlab` and `vlab-score` programs) is released under the MIT licence (`LICENSE`). The data and documents (the prompt, handbook, rubric, grader prompts, campaign keys, answer files and results) are released under the Creative Commons Attribution 4.0 International licence (`LICENSE-DATA.md`).

## Contact

Aravind Vijayaraghavan, Department of Materials and National Graphene Institute, The University of Manchester (aravind@manchester.ac.uk).
