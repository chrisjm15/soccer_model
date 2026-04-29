# Local LLM Setup

*Updated 2026-04-29. Benchmarked on Chris's hardware.*

## Hardware

| Component | Spec |
|---|---|
| GPU | NVIDIA RTX 5070, 8GB GDDR7 |
| CPU | Intel Core Ultra 9 275HX, 24 cores |
| RAM | 32GB DDR5 5600 MT/s |
| OS | Windows 11 |

## Installed Models

Always use the `-16k` context variants.

| Model | Tag | Type | VRAM | Speed | Use For |
|---|---|---|---|---|---|
| Qwen3-Coder 30B | `qwen3-coder:30b-16k` | MoE (3B active) | 8GB + ~10GB RAM | 22.7 tok/s | Default. Pipeline scripts, data transforms, boilerplate |
| Gemma 4 26B | `gemma4:26b-16k` | MoE (4B active) | 8GB + ~10GB RAM | 17.0 tok/s | Correctness-critical. Async code, financial calcs |
| Qwen3 8B | `qwen3:8b-16k` | Dense | ~5.2GB | 35-40 tok/s | Quick edits. Config, single functions, test stubs |

Note: `qwen3-coder:8b` does not exist in Ollama. Use `qwen3:8b` for the 8B class.

## Prompt Settings

Include in every local model prompt:
```
temperature: 0.2
num_predict: 4096
```
Prefix all Qwen3 model prompts with `/no_think` to suppress verbose reasoning output.

## Running a Model

```powershell
ollama run qwen3-coder:30b-16k
```

Then paste your prompt. Local models have no project context — they see only what you paste. For multi-file work, use Sonnet CLI instead.

## Benchmark Comparison

Task: write `telegram_sender.py` with MarkdownV2 formatting, error handling, and rate limiting.

| | Qwen3-Coder 30B | Gemma 4 26B |
|---|---|---|
| Speed | 22.7 tok/s | 17.0 tok/s |
| Wall time | 57s | 180s |
| Output size | 820 tokens | 2679 tokens |
| Quality checks passed | 7/8 | 8/8 |
| Async API | No | Yes |
| MarkdownV2 escape handling | Missing | Correct |
| Output complete | Yes | Yes (needs 4096 cap) |

## Known Limitations

- **Qwen3-Coder 30B:** misses edge cases (e.g. MarkdownV2 escaping, async patterns). Review output for subtle bugs. Fast enough to iterate.
- **Gemma 4 26B:** verbose — truncates at `num_predict: 2048`. Always use 4096. Worth the extra time for correctness-critical modules.
- **No agentic capability:** local models generate code, they don't run it, test it, or iterate. You run the output manually.
