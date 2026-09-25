#!/usr/bin/env python3
"""token-saver-kit: Headroom + context-mode + model routing for Claude Code and Codex.

Safe to re-run. Every config file it touches is backed up first as <file>.bak-<timestamp>.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path

KIT = Path(__file__).resolve().parent
CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
CODEX_DIR = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
STAMP = time.strftime("%Y%m%d-%H%M%S")
BEGIN, END = "<!-- token-saver-kit:begin -->", "<!-- token-saver-kit:end -->"
HOOK_EVENTS = ["PreToolUse", "PostToolUse", "SessionStart", "PreCompact", "UserPromptSubmit", "Stop"]
PRETOOL_MATCHER = ("local_shell|shell|shell_command|exec_command|Bash|Shell|apply_patch|Edit|Write|grep_files|"
                   "ctx_execute|ctx_execute_file|ctx_batch_execute|ctx_fetch_and_index|ctx_search|ctx_index|mcp__")

problems = []


def step(msg):
    print(f"\n==> {msg}")


def warn(msg):
    problems.append(msg)
    print(f"  ! {msg}")


def run(*cmd):
    exe = shutil.which(cmd[0])
    if not exe:
        warn(f"'{cmd[0]}' not found on PATH")
        return None
    print("  $ " + " ".join(cmd))
    r = subprocess.run([exe, *cmd[1:]], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        warn(f"'{' '.join(cmd)}' failed: {(r.stderr or r.stdout).strip()[-300:]}")
        return None
    return r.stdout


def backup(path):
    if path.exists():
        shutil.copy2(path, path.with_name(f"{path.name}.bak-{STAMP}"))


def upsert_block(path, text):
    """Insert or replace the token-saver-kit section of a markdown file."""
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if BEGIN in old and END in old:
        head, rest = old.split(BEGIN, 1)
        old = head.rstrip() + rest.split(END, 1)[1]
    new = f"{old.rstrip()}\n\n{BEGIN}\n{text.strip()}\n{END}\n".lstrip()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new, encoding="utf-8")


# ---------------------------------------------------------------- Headroom

def install_headroom(targets):
    step("Headroom (compresses tool output, files and history before it reaches the model)")
    if not shutil.which("headroom"):
        if shutil.which("uv"):
            run("uv", "tool", "install", "headroom-ai[all]")
        else:
            run(sys.executable, "-m", "pip", "install", "--user", "headroom-ai[all]")
    if not shutil.which("headroom"):
        warn("headroom is installed but not on PATH yet. Open a new terminal and re-run this installer.")
        return
    for t in targets:
        run("headroom", "init", "-g", t)


# ---------------------------------------------------------------- Claude Code

def setup_claude(external):
    step("Claude Code: routing subagents (Haiku / Sonnet / Opus)")
    dest = CLAUDE_DIR / "agents"
    dest.mkdir(parents=True, exist_ok=True)
    for f in (KIT / "claude" / "agents").glob("*.md"):
        backup(dest / f.name)
        shutil.copy2(f, dest / f.name)
        print(f"  + {dest / f.name}")
    upsert_block(CLAUDE_DIR / "CLAUDE.md", (KIT / "claude" / "ROUTING.md").read_text(encoding="utf-8"))
    print(f"  + routing rules in {CLAUDE_DIR / 'CLAUDE.md'}")

    settings_path = CLAUDE_DIR / "settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {}
    previous = settings.get("model", "(default)")
    settings["model"] = "opusplan"  # Opus while planning, Sonnet while executing
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    print(f"  + default model: {previous} -> opusplan")

    if external:
        step("Claude Code: context-mode plugin (keeps raw tool output out of context)")
        run("claude", "plugin", "marketplace", "add", "mksglu/context-mode")
        run("claude", "plugin", "install", "context-mode@context-mode")


# ---------------------------------------------------------------- Codex

def context_mode_paths(external):
    """Return (node, cli_entry, package_dir) for the globally installed context-mode npm package."""
    node = shutil.which("node")
    if not node:
        warn("Node.js not found. context-mode for Codex needs Node >= 22.5.")
        return None
    node = os.path.realpath(node)  # version managers (fnm, nvm) put a per-shell temp link on PATH
    major, minor = (int(x) for x in subprocess.run([node, "--version"], capture_output=True, text=True)
                    .stdout.strip().lstrip("v").split(".")[:2])
    if (major, minor) < (22, 5):
        warn(f"Node {major}.{minor} is too old for context-mode (needs >= 22.5).")
        return None
    root = run("npm", "root", "-g")
    if not root:
        return None
    pkg = Path(root.strip()) / "context-mode"
    if not (pkg / "package.json").exists() and external:
        run("npm", "install", "-g", "context-mode")
    if not (pkg / "package.json").exists():
        warn("context-mode npm package not installed; skipping its Codex setup.")
        return None
    bin_field = json.loads((pkg / "package.json").read_text(encoding="utf-8"))["bin"]
    entry = bin_field if isinstance(bin_field, str) else bin_field["context-mode"]
    return node, str(pkg / entry), pkg


def setup_codex(external):
    CODEX_DIR.mkdir(parents=True, exist_ok=True)
    cm = context_mode_paths(external)
    if cm:
        step("Codex: context-mode MCP server + hooks")
        node, entry, pkg = cm
        # Calling node directly avoids npm's .cmd shims, which Codex can't spawn on Windows.
        config_path = CODEX_DIR / "config.toml"
        config_text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
        config = tomllib.loads(config_text)
        if config.get("features", {}).get("hooks") is False:
            warn("Codex hooks are disabled in config.toml ([features] hooks = false); context-mode hooks won't run.")
        if "context-mode" in config.get("mcp_servers", {}):
            print("  = MCP server already configured")
        else:
            block = (f"\n# token-saver-kit\n[mcp_servers.context-mode]\ncommand = '{node}'\nargs = ['{entry}']\n\n"
                     f"[mcp_servers.context-mode.env]\nCONTEXT_MODE_PLATFORM = \"codex\"\n")
            config_path.write_text(config_text.rstrip() + "\n" + block, encoding="utf-8")
            print(f"  + MCP server in {config_path}")

        hooks_path = CODEX_DIR / "hooks.json"
        hooks = json.loads(hooks_path.read_text(encoding="utf-8")) if hooks_path.exists() else {}
        events = hooks.setdefault("hooks", {})
        for event in HOOK_EVENTS:
            groups = events.setdefault(event, [])
            if "context-mode" in json.dumps(groups):
                continue
            group = {"hooks": [{"type": "command", "command": f'"{node}" "{entry}" hook codex {event.lower()}'}]}
            if event == "PreToolUse":
                group = {"matcher": PRETOOL_MATCHER, **group}
            groups.append(group)
        hooks_path.write_text(json.dumps(hooks, indent=2) + "\n", encoding="utf-8")
        print(f"  + hooks in {hooks_path}")

    step("Codex: routing subagents (fast / balanced / frontier)")
    available = set()
    cache = CODEX_DIR / "models_cache.json"
    if cache.exists():
        available = {m.get("slug") for m in json.loads(cache.read_text(encoding="utf-8")).get("models", [])}
    dest = CODEX_DIR / "agents"
    dest.mkdir(parents=True, exist_ok=True)
    for f in (KIT / "codex" / "agents").glob("*.toml"):
        text = f.read_text(encoding="utf-8")
        model = tomllib.loads(text).get("model")
        if available and model not in available:
            # Unknown model on this account: drop the line so the agent inherits the parent's model.
            text = "\n".join(l for l in text.splitlines() if not l.startswith("model =")) + "\n"
            warn(f"{f.name}: model '{model}' not available on this account; it will use your default model.")
        backup(dest / f.name)
        (dest / f.name).write_text(text, encoding="utf-8")
        print(f"  + {dest / f.name}")

    routing = (KIT / "codex" / "ROUTING.md").read_text(encoding="utf-8")
    if cm and (cm[2] / "configs" / "codex" / "AGENTS.md").exists():
        routing += "\n" + (cm[2] / "configs" / "codex" / "AGENTS.md").read_text(encoding="utf-8")
    upsert_block(CODEX_DIR / "AGENTS.md", routing)
    print(f"  + routing rules in {CODEX_DIR / 'AGENTS.md'}")


# ---------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--only", choices=["claude", "codex"], help="set up just one agent (default: whichever is installed)")
    p.add_argument("--files-only", action="store_true",
                   help="only write config files; don't install packages or run headroom/claude/npm")
    args = p.parse_args()

    targets = [args.only] if args.only else [t for t in ("claude", "codex") if shutil.which(t)]
    if not targets:
        sys.exit("Neither Claude Code ('claude') nor Codex ('codex') found on PATH. Install one first.")
    print(f"Setting up: {', '.join(targets)}")

    for path in [CLAUDE_DIR / "settings.json", CLAUDE_DIR / "CLAUDE.md",
                 CODEX_DIR / "config.toml", CODEX_DIR / "hooks.json", CODEX_DIR / "AGENTS.md"]:
        backup(path)

    external = not args.files_only
    if external:
        install_headroom(targets)
    if "claude" in targets:
        setup_claude(external)
    if "codex" in targets:
        setup_codex(external)

    print(f"\nBackups saved next to each file as *.bak-{STAMP}")
    if problems:
        print(f"\nFinished with {len(problems)} warning(s):")
        for m in problems:
            print(f"  - {m}")
    else:
        print("\nDone. Restart Claude Code / Codex to pick up the changes.")
    print("Check savings any time with:  headroom savings")


if __name__ == "__main__":
    main()
