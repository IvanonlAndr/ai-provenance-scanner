# Experiment results: 30 AI-generated apps

A small experiment to see what the scanner finds in real AI-generated code. This is a snapshot of one model on one set of prompts, not a benchmark.

## Method

- **Tool:** GitHub Copilot in VS Code, with automatic model selection. The underlying model was not identified and may have varied between prompts
- **Prompts:** 30 tasks, each in a fresh chat: web APIs, scripts, bots, data tools, 5 prompts built to invite insecure code (shell commands, downloading and running files, SQL from form input, deserialization, file uploads), and 6 niche-library tasks
- **Output:** saved unedited, one folder and one commit per app, each tagged with an `AI-Assisted: copilot` trailer (the raw output files in `results/` show `copilot (gpt-5)`, a label I assumed at commit time and later could not verify)
- **Scans:**
  1. The scanner as shipped (Semgrep `p/security-audit` plus a PyPI check of `requirements.txt`)
  2. Semgrep with a broader combination: `p/security-audit`, `p/python`, `p/flask`, `p/owasp-top-ten`
- **Review:** every Semgrep finding was checked by reading the code. Apps 03 and 20 to 24 were read in full. None of the apps were run.

## Results

| Check | Result |
|---|---|
| Invented packages in `requirements.txt` | 0 of 30 |
| Packages first published in the last 30 days | 0 of 30 |
| Standard-library names listed as packages | 0 of 30 |
| Default ruleset (`p/security-audit`) | 5 findings, 0 real |
| Broader ruleset combination | 8 findings, 2 real (both in app21) |

### Findings by app

| App | Finding | Verdict |
|---|---|---|
| app03 | Template string (lines 35, 47) | False positive: constant template, fixed messages |
| app20 | Subprocess with user data (line 17) | False positive: allowlist lookup, `shell=False` |
| app20 | Template string (line 21) | False positive |
| app21 | `chmod 0o755` (line 19) | Real, a symptom of the issue below |
| app21 | Subprocess with user data (line 20) | Real: downloads a file and runs it with no checks. The prompt asked for this behavior |
| app22 | Template string (line 20) | False positive: parameterized SQL, escaped template variable |
| app24 | Template string (line 25) | False positive: constant template, random filename |

### Issues found by reading that neither ruleset flagged

- **app03:** the username is inserted into HTML without escaping on the index page (stored XSS pattern), and the session secret is hardcoded
- **app24 (minor):** no upload size limit, and files that fail image verification are left on disk
- **app20 (a bug, not a vulnerability):** `date` and `dir` are Windows shell built-ins, so they fail with `shell=False` on Windows

### Safer than the prompt invited

- app20 used an allowlist and `shell=False` for the "run a user-chosen shell command" task
- app22 used parameterized SQL for the "build SQL from form input" task
- app23 used `json` for the "deserialize settings" task

## Takeaways

- Provenance tracking tells you which commits to review. It doesn't tell you what's wrong with them.
- Ruleset choice changed what the scanner saw. The default set missed the riskiest app, and the broader set caught it but added a false positive.
- Both rulesets described app21's risk as command injection. The real problem is running an untrusted download, which a pattern-based tool can't judge from context.
- Reading the code still found issues that no ruleset flagged.

## Limitations

- One tool (Copilot with automatic model selection), 30 prompts, Python only. Results can't be attributed to a specific model
- Semgrep community rules only, no paid rules or cross-file analysis
- Hand review covered apps 03 and 20 to 24 in full. The other apps were checked only by Semgrep and a keyword search, so "missed by Semgrep" counts are a lower bound
- The apps were never run, so functional bugs went unmeasured
- The dependency check reads only `requirements.txt`, so a package that is imported but not listed is not checked
