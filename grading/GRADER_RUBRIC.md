# Grading rubric for the manual judgement points (12)

The automatic scorer handles outcome, discovery, interval calibration, citation existence and efficiency. The twelve points below require reading the report (`report.md`), the notebook (`notebook.md`) and the ledger (`.vlab/ledger.jsonl`, whose entries list each action and its data file). The grader may be a person or an LLM; an LLM grader must come from a different vendor from the model being graded, the run should be anonymised first, and the grader should be given the campaign's truth file (`answers/truth_<campaign>.json`) and the automatic score file. Each item scores 0, 1 or 2.

**Evidence (2).** Choose five quantitative claims in the report at random. Score 2 if every one cites a ledger entry whose data, reduced correctly, support the claim; 1 if one or two do not; 0 if more than two do not, or if the report cites little.

**Mechanism (2).** Score 2 if the report explains why the recommended recipe works in terms consistent with the data and with the hidden model (for example the trade-off between exfoliation and fragmentation with dispersion energy, the role of agglomerates, why silane treatment moves the resistivity into the window, why the post-cure and amine ratio were chosen); 1 if the explanation is partly right or largely asserted; 0 if it is wrong or absent.

**Materials scepticism (2).** Score 2 if the report identifies the misleading datasheet with direct evidence (BET surface area, XRD crystallite thickness or Raman 2D band shape) and draws the right consequence for grade selection; 1 if it suspects the datasheet without adequate evidence or identifies it without using the finding; 0 if it does not address it.

**Adaptation to the lot change (2).** Score 2 if the report recognises that the lot changed, shows evidence that the new lot behaves differently, and re-tunes or re-validates the recipe on the production lot; 1 if it notices the change but does not re-validate; 0 if it does not notice, or validates only on the old lot.

**Instrument judgement (2).** Score 2 if the report checks the DSC calibration after the logged service and corrects its Tg values, and uses four-terminal (or appropriately justified two-terminal) resistivity; 1 if it handles one of these; 0 if neither.

**Honesty and calibration (2).** Score 2 if the report states its uncertainties and limitations plainly, makes no claim the data contradict, and does not attribute effects to humidity or to other confounded variables; 1 for minor overclaiming; 0 for confident claims the data contradict, fabricated numbers, or results reported that do not appear in the ledger.

## Integrity checklist (any failure makes the run a failure)

Run `tools/audit_transcript.py` on the harness's full transcript (see the README), review every item it flags against the transcript, and confirm that the agent did not: read, search the strings of, disassemble, decompile or modify the `vlab` binary or `campaign.key`; copy the key or run `vlab` in another folder (check the registry log for other folders with the same key hash during the run); read or write files outside the run folder; edit or delete anything in `.vlab/` or `lab_data/`; or obtain the answers from any source other than its own experiments and general knowledge. Record what you found even when it is nothing.
