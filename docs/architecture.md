# Architecture

See IDEA.md §5. Overrides for this weekend:

- Fine-tuned Qwen3-8B is trained and served on **Tinker hosted API** only.
- No local adapter download, HF merge, or GGUF conversion.
- `LLM_BACKEND`, `EXTRACT_BACKEND`, `PARSER_BACKEND` select each model call.
- DigitalOcean is dropped. Gemma 4 31B is Google AI Studio (`GEMINI_API_KEY`, `gemma-4-31b-it`). This MVP uses `LLM_BACKEND=template`. Public demo is Render free (`$PORT`).
- After Tinker JSON, `copy_explicit` copies form/food/1/12 tokens from the line. It never invents a dose.
- Chart stays locked until every line is confirmed and `needs_check` is empty. `schedule_conflicts` surfaces duplicate drugs with different copies.
