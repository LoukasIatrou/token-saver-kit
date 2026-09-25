# token-saver-kit

One command to make Claude Code and Codex use fewer tokens.

| Layer | Tool | What it does |
|---|---|---|
| Compress input | [Headroom](https://github.com/headroomlabs-ai/headroom) | Local proxy that shrinks tool output, files, logs and history before they reach the model. Also installs Serena for symbol-level code navigation. |
| Keep output out of context | [context-mode](https://github.com/mksglu/context-mode) | Runs big tool/web output in a sandbox and indexes it; the agent gets a summary and searches for details. Saves session state across compaction. |
| Route to the right model | Built-in subagents (this repo) | Small jobs go to a cheap model, normal work to a mid model, hard problems to the frontier model. Claude Code also switches to `opusplan` (Opus plans, Sonnet codes). |

## Install

Needs Python 3.11+, plus Node.js 22.5+ for the Codex path. Have Claude Code and/or Codex installed. The installer sets up whichever it finds.

**Windows (PowerShell)**
```powershell
git clone <this-repo> token-saver-kit
.\token-saver-kit\install.ps1
```

**macOS / Linux**
```bash
git clone <this-repo> token-saver-kit
sh token-saver-kit/install.sh
```

Then restart Claude Code / Codex.

Options:
- `--only claude` or `--only codex`: set up one agent.
- `--files-only`: write the config files but skip package installs and `headroom init`.

Safe to re-run. Every config file is backed up first as `<file>.bak-<timestamp>`.

## What it changes

**Claude Code** (`~/.claude`)
- `headroom init -g claude`: routes Claude Code through the Headroom proxy.
- Installs the `context-mode` plugin.
- Adds `agents/quick-task.md` (Haiku), `agents/builder.md` (Sonnet), `agents/deep-reasoner.md` (Opus).
- Adds routing rules to `CLAUDE.md` between `token-saver-kit` markers.
- Sets `"model": "opusplan"` in `settings.json`.

**Codex** (`~/.codex`)
- `headroom init -g codex`: routes Codex through the Headroom proxy.
- `npm install -g context-mode`, then registers it in `config.toml` and `hooks.json`.
- Adds `agents/quick_task.toml`, `builder.toml`, `deep_reasoner.toml`. If a model name isn't available on your account, that agent falls back to your default model. Edit the `model =` lines to change the tiers.
- Adds routing rules and context-mode's instructions to the global `AGENTS.md`.

## Check it's working

```bash
headroom savings                 # tokens saved by compression
headroom doctor                  # proxy + client routing health
```
In Claude Code: `/context-mode:ctx-doctor` and `/usage`. In Codex: type `ctx stats`.

## Undo

Restore the `*.bak-<timestamp>` files, delete the agent files listed above, and run `claude plugin uninstall context-mode@context-mode`.
