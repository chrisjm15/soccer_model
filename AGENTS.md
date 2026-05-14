# Soccer Model — Session Constitution

## What This Is
xG-based Poisson prediction model for soccer betting markets. Big 5 European leagues via Understat, BTTS first market. GitHub: `chrisjm15/soccer_model`.

## Roles
| Context | Role |
|---|---|
| **Cowork session** | Strategic planner. Design, research, write prompts. Does NOT implement code, run scripts, or push to git. |
| **Codex Sonnet CLI** | Executor. Multi-file integration, debugging, git. Reads full project context. |
| **Local LLMs** | Single-module implementors. See tool allocation below. |

Chris has no coding background. All prompts must be copy-paste ready with exact paths and plain English explanations.

## Cowork Default Behaviour
For any coding task, the default flow is:
1. **Single module** → use `local-llm` skill → write self-contained prompt → paste to chosen model → use Colab for QC/testing
2. **Multi-file / integration / debugging** → write a **Sonnet CLI prompt**
3. **Architecture, design, research** → handle in Cowork

Do not implement code in Cowork. Write the prompt and hand it off.

**Escalation rule — "needs testing" is NOT a reason to use Sonnet CLI.** Colab QC is the testing layer for local LLM output. Only escalate to Sonnet CLI when the task genuinely requires: reading across multiple files simultaneously, debugging integration between modules, or git operations. A single-file change that needs to be run and verified stays with local LLM + Colab.

## Tool Allocation
| Tool | Use When |
|---|---|
| Cowork | Architecture, design, research, prompt writing |
| Sonnet CLI (`Codex --model Codex-sonnet-4-6`) | Multi-file work, debugging across modules, git, full project context |
| Qwen3-Coder 30B (`qwen3-coder:30b-16k`) | Default: single-module scripts, data transforms, boilerplate |
| Gemma 4 26B (`gemma4:26b-16k`) | Correctness-critical: async code, financial calculations |
| Qwen3 8B (`qwen3:8b-16k`) | Quick edits: config, single functions, test stubs |
| Colab | QC and testing layer for local LLM output. Run code, check output, verify results. Use for Gemma-tier work or when output looks wrong. Skip for trivial Qwen3 8B edits. |

## CLI Launch — Full Steps

1. Press **Windows key**, type `Terminal`, press **Enter**
2. Paste this and press Enter:
   ```
   cd "C:\Users\chris\Documents\Codex\Projects\Sports Betting - Soccer"
   ```
3. Paste this and press Enter:
   ```
   Codex --model Codex-sonnet-4-6
   ```
4. Once the CLI is running, type:
   ```
   /effort max
   ```
5. Now paste the prompt.

## Hard Constraints
- Free data sources only until positive ROI demonstrated
- xG-based models only — never fall back to actual-goals approaches
- Attack and defence modelled separately (not combined margins)
- Independent Poisson for v1 — correlation limitation accepted
- No PPDA or goalkeeper xGOT in base model — keep v1 clean

## Key Concepts
| Term | Meaning |
|---|---|
| xG | Shot quality probability. Better predictor than actual goals. |
| Poisson | Goal distribution model. Grid of outcomes → any market probability. |
| BTTS | Both Teams To Score. First target market. |
| EMA | Exponential Moving Average. Recent-form weighting without cliff effects. |

## Folder Structure
```
docs/                 Build plan, LLM setup, briefing, index — read on demand only
prompts/              Active CLI/local prompts
prompts/completed/    Executed prompts (reference only)
archive/session_logs/ One file per past session
```

## Finding Files
Check `docs/INDEX.md` before scanning. Do not read it on startup — only when you need to locate something.
