"""Scan recent Claude Code transcripts for Bash + PowerShell + MCP tool calls."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

TRANSCRIPTS = Path(r"C:\Users\hangy\.claude\projects\C--Users-hangy-Documents-2026-FRC-2960-1")

def leading_token(cmd: str) -> str:
    cmd = cmd.strip()
    # Strip leading env-var assignments
    while re.match(r"^[A-Za-z_][A-Za-z0-9_]*=\S+\s+", cmd):
        cmd = re.sub(r"^[A-Za-z_][A-Za-z0-9_]*=\S+\s+", "", cmd)
    # Drop leading sudo / timeout
    cmd = re.sub(r"^(sudo|timeout(\s+\S+)?)\s+", "", cmd)
    # First pipe / && segment
    cmd = re.split(r"\s*(\||&&|;)\s*", cmd, maxsplit=1)[0]
    tokens = cmd.split()
    if not tokens:
        return ""
    head = tokens[0]
    # Pair with first subcommand for git/gh/docker/kubectl/gradle
    if head in ("git", "gh", "docker", "kubectl") and len(tokens) > 1:
        return f"{head} {tokens[1]}"
    if head == ".\\gradlew.bat" and len(tokens) > 1:
        return f".\\gradlew.bat {tokens[1]}"
    return head

def ps_leading(cmd: str) -> str:
    cmd = cmd.strip()
    # PowerShell — first cmdlet or .\xxx
    tokens = re.split(r"[\s;|]+", cmd)
    if not tokens:
        return ""
    head = tokens[0]
    # & "path\to\exe" arg — strip the & and the path
    if head == "&" and len(tokens) > 1:
        # follow with the called exe basename
        called = tokens[1].strip('"\'')
        called_base = Path(called).name
        if called_base.lower().startswith("python"):
            # include the script if present
            if len(tokens) > 2 and tokens[2].endswith(".py"):
                return f"& python {Path(tokens[2]).name}"
            return "& python"
        return f"& {called_base}"
    if head.lower() in ("get-childitem", "import-csv", "measure-object",
                        "select-object", "sort-object", "where-object",
                        "foreach-object", "stop-process", "test-path",
                        "new-item", "remove-item"):
        return head
    if head == ".\\gradlew.bat" and len(tokens) > 1:
        return f".\\gradlew.bat {tokens[1]}"
    return head

bash_counts = Counter()
ps_counts = Counter()
mcp_counts = Counter()
other = Counter()

files = sorted(TRANSCRIPTS.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:50]
print(f"Scanning {len(files)} files...", file=sys.stderr)

for fp in files:
    try:
        for line in fp.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                obj = json.loads(line)
            except Exception:
                continue
            msg = obj.get("message")
            if not isinstance(msg, dict):
                continue
            for item in msg.get("content", []) or []:
                if not isinstance(item, dict) or item.get("type") != "tool_use":
                    continue
                name = item.get("name", "")
                inp = item.get("input", {}) or {}
                if name == "Bash":
                    bash_counts[leading_token(inp.get("command", ""))] += 1
                elif name == "PowerShell":
                    ps_counts[ps_leading(inp.get("command", ""))] += 1
                elif name.startswith("mcp__"):
                    mcp_counts[name] += 1
                else:
                    other[name] += 1
    except Exception as e:
        print(f"skip {fp.name}: {e}", file=sys.stderr)

print("\n=== Bash ===")
for k, v in bash_counts.most_common(30):
    print(f"{v:4d}  {k}")
print("\n=== PowerShell ===")
for k, v in ps_counts.most_common(30):
    print(f"{v:4d}  {k}")
print("\n=== MCP ===")
for k, v in mcp_counts.most_common(30):
    print(f"{v:4d}  {k}")
print("\n=== Other tools (informational) ===")
for k, v in other.most_common(15):
    print(f"{v:4d}  {k}")
