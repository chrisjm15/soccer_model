# Soccer Model — Session Constitution

## What This Is
xG-based Poisson prediction model for soccer betting markets. Big 5 European leagues via Understat, BTTS first market. GitHub: `chrisjm15/soccer_model`.

## Roles
| Context | Role |
|---|---|
| **Cowork session** | Strategic planner. Design, research, write prompts. Does NOT implement code, run scripts, or push to git. |
| **Claude Sonnet CLI** | Executor. Multi-file integration, debugging, git. Reads full project context. |
| **Local LLMs** | Single-module implementors. See tool allocation below. |

Chris has no coding background. All prompts must be copy-paste ready with exact paths and plain English explanations.

## Cowork Default Behaviour
For any coding task, the default flow is:
1. **Single module** → write fully self-contained prompt → paste to **Qwen3-Coder 30B**
2. **Multi-file / integration / debugging** → write a **Sonnet CLI prompt**
3. **Architecture, design, research** → handle in Cowork

Do not implement code in Cowork. Write the prompt and hand it off.

## Tool Allocation
| Tool | Use When |
|---|---|
| Cowork | Architecture, design, research, prompt writing |
| Sonnet CLI (`claude --model claude-sonnet-4-6`) | Multi-file work, debugging, git, full project context |
| Qwen3-Coder 30B (`qwen3-coder:30b-16k`) | Default: single-module scripts, data transforms, boilerplate |
| Gemma 4 26B (`gemma4:26b-16k`) | Correctness-critical: async code, financial calculations |
| Qwen3 8B (`qwen3:8b-16k`) | Quick edits: config, single functions, test stubs |

## Local LLM Prompt Rules
- Launch: `ollama run qwen3-coder:30b-16k`
- Always include: `temperature: 0.2`, `num_predict: 4096`
- Prefix all Qwen3 prompts with `/no_think`
- **Prompts must be fully self-contained** — local models have no project context. Include all specs, interfaces, and import signatures.

## CLI Launch
```
cd "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
claude --model claude-sonnet-4-6
/effort max
```

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
