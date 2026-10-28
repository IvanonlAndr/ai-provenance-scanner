import json, re, subprocess, sys
from datetime import datetime, timezone
import requests
import os

def sh(*args):
    return subprocess.run(args, capture_output=True, text=True).stdout

def ai_commits(base):
    fmt = "%H%x1f%(trailers:key=AI-Assisted,valueonly,unfold)%x1e"
    out = sh("git", "log", f"{base}..HEAD", f"--format={fmt}")
    commits = []
    for rec in out.split("\x1e"):
        if "\x1f" not in rec:
            continue
        sha, tool = rec.strip().split("\x1f")
        if tool.strip():
            files = sh("git", "show", "--name-only", "--format=", sha).split()
            commits.append({"sha": sha[:8], "tool": tool.strip(), "files": files})
    return commits

def semgrep_scan(files):
    files = [f for f in files if os.path.exists(f)]
    if not files:
        return []
    out = sh("semgrep", "--config", "p/security-audit", "--json", "--quiet", *files)
    results = json.loads(out).get("results", [])
    return [
        {"file": r["path"], "line": r["start"]["line"],
         "severity": r["extra"]["severity"], "msg": r["extra"]["message"]}
        for r in results
    ]

def check_package(name):
    r = requests.get(f"https://pypi.org/pypi/{name}/json", timeout=10)
    if r.status_code == 404:
        return f"'{name}' does not exist on PyPI (possible hallucination)"
    uploads = [
        datetime.fromisoformat(f["upload_time_iso_8601"].replace("Z", "+00:00"))
        for files in r.json()["releases"].values() for f in files
    ]
    if uploads:
        age = (datetime.now(timezone.utc) - min(uploads)).days
        if age < 30:
            return f"'{name}' first published {age} days ago (suspicious)"
    return None

def dependency_findings(files):
    issues = []
    for f in files:
        if f.endswith("requirements.txt") and os.path.exists(f):
            for line in open(f):
                m = re.match(r"^([A-Za-z0-9_.-]+)", line.strip())
                if m and not line.startswith("#"):
                    issue = check_package(m.group(1))
                    if issue:
                        issues.append({"file": f, "msg": issue})
    return issues

def main(base="origin/main"):
    commits = ai_commits(base)
    total = 0
    for c in commits:
        findings = semgrep_scan(c["files"]) + dependency_findings(c["files"])
        print(f"\n{c['sha']}  (AI: {c['tool']})  {len(c['files'])} files")
        for f in findings:
            print(f"  [{f.get('severity', 'DEP')}] {f['file']}:{f.get('line', '-')} {f['msg']}")
        total += len(findings)
    print(f"\n{len(commits)} AI-attributed commits, {total} findings")
    sys.exit(1 if total else 0)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "origin/main")