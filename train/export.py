"""Local GGUF/merge export is SKIPPED this weekend (low disk).

The fine-tuned Qwen3-8B is trained and served through Tinker's hosted
sampling API (PARSER_BACKEND=tinker). Do not download the adapter, merge
into Hugging Face weights, or convert to GGUF on this laptop.
"""

from __future__ import annotations


def main() -> None:
    raise SystemExit(
        "Skipped: this laptop does not download, merge, or convert the fine-tune. "
        "Use PARSER_BACKEND=tinker and PILLCLERK_TINKER_PATH=tinker://..."
    )


if __name__ == "__main__":
    main()
