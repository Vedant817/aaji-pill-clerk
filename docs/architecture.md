# Architecture

See IDEA.md §5. Overrides for this weekend:

- Fine-tuned Qwen3-8B is trained and served on **Tinker hosted API** only.
- No local adapter download, HF merge, or GGUF conversion.
- `LLM_BACKEND`, `EXTRACT_BACKEND`, `PARSER_BACKEND` select each model call.
- DigitalOcean is dropped. Gemma 4 31B is Google AI Studio (`GEMINI_API_KEY`, `gemma-4-31b-it`). This MVP uses `LLM_BACKEND=template` and `EXTRACT_BACKEND=manual`. Local `gemma4:e4b` OCR is not claimed. Public demo: **render.yaml provided; not deployed** (`$PORT`). All 3096 `train.jsonl` rows have `renderer=template`; Gemma 31B did not write the training data.
- After Tinker JSON, `copy_explicit` copies form/food/1/12/month tokens, combo-brand suffixes, surface strength, insulin `N unit`, English/Hindi time-of-day words, and written `N-N-N` or once/twice/thrice amounts from the line. Schema-fail model JSON becomes a token stub. Daily lines with no dose cue get ASK. It never invents a dose that is not written.
- Chart stays locked until every line is confirmed and `needs_check` is empty. `schedule_conflicts` surfaces duplicate drugs with different copies.
