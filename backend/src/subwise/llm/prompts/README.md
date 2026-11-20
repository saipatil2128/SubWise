# Prompts (M7)

One Markdown file per LLM node: `parse_intent.md`, `decide.md`, `explain.md`. Prompts receive only
structured data (never raw page text for `explain`), state the JSON schema in words as well as via
Ollama's `format` parameter, and forbid inventing numbers.
