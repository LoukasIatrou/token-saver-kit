# token-saver-kit

**Cut the tokens your coding agent burns, with one command.** Works with Claude Code and Codex.

```powershell
# Windows
git clone https://github.com/LoukasIatrou/token-saver-kit
.\token-saver-kit\install.ps1
```

```bash
# macOS / Linux
git clone https://github.com/LoukasIatrou/token-saver-kit
sh token-saver-kit/install.sh
```

Restart Claude Code / Codex and you're done.

## What you get

Three tools, each attacking a different kind of waste:

1. **[Headroom](https://github.com/headroomlabs-ai/headroom): compresses what goes in.** A local proxy that shrinks tool output, files, logs and chat history before the model sees them.
2. **[context-mode](https://github.com/mksglu/context-mode): keeps big output out entirely.** Large command and web results are stored and indexed. The agent gets a summary and looks up details only when it needs them.
3. **Model routing: uses the cheapest model that can do the job.** Three subagents the main agent hands work to:

   | Subagent | Claude Code | Codex | For |
   |---|---|---|---|
   | quick task | Haiku | gpt-5.6-luna | searches, renames, running tests, small edits |
   | builder | Sonnet | gpt-5.6-terra | features and bug fixes with a clear plan |
   | deep reasoner | Opus | gpt-6-astra | architecture, hard bugs, security review |

   Claude Code is also set to `opusplan`: Opus while planning, Sonnet while writing code.

## Requirements

- Python 3.11+
- Claude Code and/or Codex (it sets up whichever is installed)
- Node.js 22.5+ (Codex only)

## Options

```bash
install.sh --only claude     # set up just one agent (or --only codex)
install.sh --files-only      # write config files, skip package installs
```

## See the savings

```bash
headroom savings     # tokens saved by compression
headroom doctor      # check the proxy is running
```

In Claude Code, run `/usage`. In Codex, type `ctx stats`.

## Good to know

- **Safe to re-run.** Every config file it touches is backed up first as `*.bak-<timestamp>`.
- **Codex model names differ by account.** If a model isn't available to you, that subagent uses your default model and the installer tells you. Change the tiers in [`codex/agents/`](codex/agents/).
- **Undo:** restore the `.bak` files, delete the three agent files from `~/.claude/agents` and `~/.codex/agents`, and run `claude plugin uninstall context-mode@context-mode`.
