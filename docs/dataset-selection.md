# Dataset decision — 3 October 2026

Keep the repository's synthetic lines as training input. Use previously unused
HMR-100 pages for a separate, locally annotated acceptance set. No suitable,
ready-to-train public schedule corpus was identified in this search. This is a
scoped search and sample audit, not a claim that none exists.

| Public source | What was checked | Decision |
|---|---|---|
| [medicine_parser_alpaca](https://huggingface.co/datasets/AshwinManohar/medicine_parser_alpaca) | 10,000 text rows; no license declared in Hub metadata; first 20 viewer rows inspected. Two sampled inputs receive an unwritten empty-stomach instruction in their targets. Targets also infer ingredients and routes. | Reject for training: incompatible with copying only written instructions and unresolved reuse permission. |
| [medocr-vision-dataset](https://huggingface.co/datasets/naazimsnh02/medocr-vision-dataset) | Declared MIT; 1,969 train / 246 validation / 246 test. First 20 viewer rows inspected: six prescription markers, with receipts, invoices and lab records among the remainder. Image/text OCR, no complete MedLine schedule gold. | Reject direct import. Public samples also contain identifying text; none was saved here. |
| [RxHandBD](https://zenodo.org/records/18478741) | 5,578 cropped handwritten word images; 1,559 word labels. | Useful for word OCR research, not full-line schedule supervision. Not downloaded. |
| [IndicRxNorm-LexMap-15K](https://huggingface.co/datasets/AXONVERTEX-AI-RESEARCH/IndicRxNorm-LexMap-15K) | Declared CC BY-NC 4.0; generated terminology/NER normalization examples. | No schedule gold. Not imported. |
| [RxScribe Bench paper](https://arxiv.org/html/2609.13280v1) | Describes 200 Indian outpatient prescriptions and double annotation; no public dataset download was identified in the paper. Includes inferred pharmacology in its schema. | Research reference, not an available training artifact. |
| [HMR-100](https://huggingface.co/datasets/chaithanyakota/100-handwritten-medical-records) | Declared CC BY-ND 4.0; 100 doctor-handwritten simulated records. Already downloaded locally. Supplied labels give medicine names, not complete schedules. | Select original local images for human annotation and evaluation only. Images and new annotation/gold files remain gitignored. |

Hub revisions checked: medicine_parser_alpaca
`f7549f5c9bc338faf97a100a2e5b65078ce9df33`; medocr
`0ef1e2525b83d030878d8c234fa6f8592d961d19`; HMR
`afcca9f163561af54fcd145003e550d2d320aafb`.
Only metadata and small public viewer samples were fetched; no new dataset,
model, or paid inference was downloaded/run.

## Frozen candidate

`data/candidates/clean_v4/` contains **3,079 training and 249 validation rows**,
prepared from the original 3,096 / 250 synthetic rows. Nine training rows overlap
validation/evaluation after normalization; eight more are internal duplicates.
One validation row overlaps evaluation. No contradictory-label groups or invalid
targets were found in these inputs. Rejections record source row indexes; original
training, validation, published gold and evaluation results are preserved.

The cleaner requires explicit synthetic provenance and aligned user/assistant/gold
targets. It rebuilds chat messages with the current schema prompt, deduplicates,
quarantines all conflicting duplicate labels, and freezes byte hashes and counts.
It checks SYNTH, generated realistic, existing HMR/BD gold, and any finalized new
acceptance gold. These are exact normalized-text checks; shared templates,
near-duplicate meanings and earlier checkpoint exposure remain limitations.
The candidate has not been trained. Human synthetic-sample review is pending.

```powershell
uv run python -m train.prepare_candidate
uv run python -m train.sft --train data/candidates/clean_v4/train.jsonl --val data/candidates/clean_v4/val.jsonl --check-data
```

Repeating preparation with unchanged inputs is idempotent. Changed inputs, code,
or finalized acceptance gold require a new candidate directory (`--out`); frozen
artifacts are never silently overwritten. Input hashes describe this checkout's
bytes, including line endings. No automatic model or `.env` update occurs.

## Human acceptance labels

`data/acceptance/hmr_v1/manifest.json` reserves **20 pages**, deterministically
ranked with seed 20261003. All first 30 development-queue pages and already
labelled pages are excluded, as are identical image bytes. Medicine-name metadata
is used only to select pages containing medicines; those names are hidden from
annotators. Original photo hashes are checked on every read.

```powershell
uv run python -m scripts.prepare_acceptance
uv run streamlit run app/Home.py
# After two people complete and reconcile all pages:
uv run python -m scripts.prepare_acceptance --finalize
```

Open **Independent prescription labels**. Person A and person B each use their
own consistent ID and round, read the original photo, transcribe medicine lines
top to bottom starting at 1, and enter complete MedLine gold explicitly. Use null
and the relevant `needs_check` flags for uncertainty. Copy only written content;
do not expand a brand into an ingredient or guess food, dose, duration or timing.
Hourly spacing is not an unwritten daily maximum. Mark unsupported notation ASK.

Both people attest that every visible medicine line has been entered. No model,
medicine-name prefill, or other-round answer is shown. Saving a revision invalidates
the completion attestation. Finalization requires complete unchanged rounds,
consecutive matching line coverage, different annotator IDs, identical source
transcriptions and agreeing clinical fields/ASK flags. Differences must be resolved
by humans against the photo; the script never adjudicates them. Finalized gold is
frozen locally. Reserved pages are blocked from development-label writes.

IDs are self-declared, not authenticated identity verification. Two matching
annotations cannot prove that neither person missed a line. This is page separation
within one simulated public source, not an independent clinical population or
family acceptance. The 20 pages have **no gold labels or model scores yet**.
No accuracy improvement is claimed by preparing them. Human review and labels
come next; hosted retraining/fresh evaluation still need spending approval.
The new set is not added to Gemini's outbound allowlist.
