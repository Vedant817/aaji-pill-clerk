# Architecture

See IDEA.md §5. Overrides for this weekend:

- Fine-tuned Qwen3-8B is trained and served on **Tinker hosted API** only.
- No local adapter download, HF merge, or GGUF conversion.
- `LLM_BACKEND`, `EXTRACT_BACKEND`, `PARSER_BACKEND` select each model call.
- Big-model calls go to DigitalOcean (`gemma-4-31B-it`). Backboard is optional.
