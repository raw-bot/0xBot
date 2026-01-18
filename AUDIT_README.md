# 0xBot Comprehensive Audit - Using Ralph Loop

This document explains how to run the 0xBot comprehensive audit using the Ralph autonomous loop.

---

## What is Ralph?

Ralph is an autonomous AI agent loop that:
1. Reads `AUDIT_PRD.md` and finds incomplete tasks (marked `[ ]`)
2. Implements ONE task per iteration
3. Learns from previous iterations via `progress.txt`
4. Runs tests/checks to verify work
5. Commits successful results
6. Repeats until all tasks are complete (marked `[x]`)

Ralph automates iterative work, making it perfect for comprehensive audits where each audit task builds on previous findings.

---

## Files Needed

Before running Ralph, ensure these files exist:

- ✅ `AUDIT_PRD.md` - Audit task definitions (created)
- ✅ `progress.txt` - Tracks iterations and learnings (created)
- ✅ `AGENTS.md` - Discovered patterns & knowledge (created)
- ✅ `scripts/ralph/ralph.sh` - Ralph loop executable (installed)

---

## Quick Start

### 1. Start the Audit Loop

```bash
cd /Users/cube/Documents/00-code/0xBot

# Run with default settings (10 iterations, 2 second sleep between)
./scripts/ralph/ralph.sh

# Or specify custom iterations:
./scripts/ralph/ralph.sh 20   # Run 20 iterations max
./scripts/ralph/ralph.sh 20 1 # Run 20 iterations, 1 second sleep between
```

### 2. Watch Ralph Work

Ralph will:
- Read AUDIT_PRD.md
- Find the first incomplete task `[ ]`
- Call Claude API to implement that task
- Verify implementation (run checks)
- If successful: mark task complete `[x]`, commit, continue
- If failed: log issue to progress.txt, try again next iteration
- Stop when all tasks are complete or max iterations reached

### 3. Review Results

After Ralph completes:

```bash
# View the generated audit report
cat AUDIT_REPORT.md

# View the scoring summary
cat AUDIT_SCORES.json

# View learnings from each iteration
cat progress.txt

# View discovered patterns
cat AGENTS.md

# View git history of audit commits
git log --oneline | head -15
```

---

## How Ralph Works (Technical)

### The Loop

```bash
for iteration in 1..MAX:
    1. Find first incomplete task in AUDIT_PRD.md [ ]
    2. Create prompt with:
       - Task description from AUDIT_PRD.md
       - Learnings from progress.txt
       - Patterns from AGENTS.md
    3. Call: claude --dangerously-skip-permissions -p "<prompt>"
    4. Claude reads files and implements task
    5. If tests pass:
       - Mark task [x] in AUDIT_PRD.md
       - Commit changes
       - Append learnings to progress.txt
    6. If tests fail:
       - Do NOT mark complete
       - Append failure details to progress.txt
    7. Sleep 2 seconds
    8. Next iteration
```

### Completion Signal

Ralph stops when Claude outputs: `<promise>COMPLETE</promise>`

This happens when:
- All tasks in AUDIT_PRD.md are marked `[x]`
- AUDIT_REPORT.md is created
- Claude verifies all audit findings are documented

---

## What Gets Generated

### AUDIT_REPORT.md
Comprehensive audit findings:
- Executive summary with overall health score
- Scoring matrix (Architecture, Code Quality, Testing, Security, etc.)
- Issues categorized by severity (Critical, High, Medium, Low)
- What's working well
- What needs work
- Prioritized recommendations
- Next steps

### AUDIT_SCORES.json
Metrics in machine-readable format:
```json
{
  "overall_health_score": 7.2,
  "categories": {
    "architecture": 8.0,
    "code_quality": 6.5,
    "testing": 5.0,
    "performance": 6.0,
    "security": 4.5,
    ...
  },
  "issues": {
    "critical": 3,
    "high": 8,
    "medium": 12,
    "low": 5
  }
}
```

### Updated AGENTS.md
Discovered patterns and reusable knowledge:
- Architecture patterns that work
- Code patterns to follow
- Common gotchas
- File location map
- Configuration reference
- Troubleshooting guide

### Updated progress.txt
Iteration-by-iteration learnings:
- What each iteration accomplished
- Patterns discovered
- Gotchas encountered
- Insights for future work

---

## Interpreting Results

### Health Scores (0-10)

- **9-10**: Excellent, production ready
- **7-8**: Good, minor improvements needed
- **5-6**: Fair, some work needed
- **3-4**: Poor, significant improvements needed
- **0-2**: Critical, needs major overhaul

### Issue Severity

- **CRITICAL**: Must fix before production (security, data integrity, crashes)
- **HIGH**: Should fix before production (performance, reliability)
- **MEDIUM**: Should fix but not blocking (code quality, maintainability)
- **LOW**: Nice to have (documentation, minor optimizations)

---

## Next Steps After Audit

Once audit is complete:

### 1. Review Findings
```bash
cat AUDIT_REPORT.md    # Read detailed findings
cat AUDIT_SCORES.json  # Check metrics
```

### 2. Create Action Plan
Use GSD to create an updated ROADMAP based on audit findings:
```bash
/gsd:create-roadmap  # Will prioritize based on audit scores
```

### 3. Execute Fixes
```bash
/gsd:plan-phase 1.1  # Start with critical security fixes
./scripts/ralph/ralph.sh  # Use Ralph again to fix issues!
```

---

## Troubleshooting

### Ralph Hangs or Stops

**Symptom**: Ralph stops executing, appears frozen

**Solution**:
```bash
# Check if last iteration failed
tail -20 progress.txt

# Check git log for last commit
git log --oneline -1

# Check if AUDIT_PRD.md is malformed
cat AUDIT_PRD.md | grep "^###"
```

### Claude API Errors

**Symptom**: "Error calling Claude API"

**Solution**:
- Verify Claude CLI is installed: `which claude`
- Verify Claude is configured: `claude --help`
- Check Claude has access to project files

### Tasks Not Completing

**Symptom**: Task marked incomplete even after iteration

**Solution**:
- Review progress.txt learnings section
- Check if task has clear verification steps
- Ensure task can complete in single context window

### Merge Conflicts

**Symptom**: Git merge conflict on progress.txt

**Solution**:
```bash
# Accept latest version (current iteration)
git checkout --theirs progress.txt
git add progress.txt
git commit -m "Resolve progress.txt conflict"
./scripts/ralph/ralph.sh 20  # Resume Ralph
```

---

## Advanced: Customizing Audit

### Modify Task Scope

Edit `AUDIT_PRD.md`:
- Remove tasks you don't care about (mark `[x]` to skip)
- Add new audit tasks following the same format
- Update success criteria if needed

### Change Max Iterations

```bash
./scripts/ralph/ralph.sh 50  # Run up to 50 iterations
```

### Reset and Restart

```bash
# Revert PRD to uncompleted state
git checkout main AUDIT_PRD.md

# Clear progress (but keep learnings)
git rm progress.txt
echo "# Progress Log" > progress.txt

# Restart audit
./scripts/ralph/ralph.sh 20
```

---

## Real-World Example

```bash
$ cd /Users/cube/Documents/00-code/0xBot
$ ./scripts/ralph/ralph.sh 20

Starting Ralph - Max 20 iterations

===========================================
  Iteration 1 of 20
===========================================
[Claude processes Task 1: Architecture & Design...]
[Tests pass, marks [x], commits]

===========================================
  Iteration 2 of 20
===========================================
[Claude processes Task 2: Code Quality & Type Safety...]
[Tests pass, marks [x], commits]

...

===========================================
  Iteration 12 of 20
===========================================
[Claude completes Task 12: Creates AUDIT_REPORT.md]
[All tasks complete]
[Outputs: <promise>COMPLETE</promise>]

===========================================
  All tasks complete after 12 iterations!
===========================================

$ cat AUDIT_REPORT.md
# 0xBot Comprehensive Audit Report

## Executive Summary
- Overall Health Score: 7.2/10
- Critical Issues: 3
- High Priority Issues: 8
...
```

---

## Safety & Precautions

### Data Safety
- Ralph never deletes code, only modifies and tests
- All changes committed to git (revertible)
- Run on a feature branch if paranoid

### Resource Usage
- Each iteration calls Claude API (costs $)
- Set reasonable max iterations (10-20 is typical)
- Monitor API usage on Anthropic dashboard

### Network
- Ralph needs stable internet connection
- If interrupted, can resume by running again
- Previous iterations preserved in git history

---

## Summary

```
┌─ Create AUDIT_PRD.md ─────┐
│  (task definitions)         │
├─ Run ./scripts/ralph/ralph.sh──┐
│  Ralph Loop Iterations:      │  │
│  1. Architecture             │  │
│  2. Code Quality             │  │
│  3. Testing                  │  │
│  4. Performance              │  │
│  5. Security                 │  │
│  6. Reliability              │  │
│  7. Frontend                 │  │
│  8. Dependencies             │  │
│  9. Database                 │  │
│  10. DevOps                  │  │
│  11. Documentation           │  │
│  12. Report Generation       │  │
└────────────────────────────┘   │
       │                           │
       │ Generates                 │
       ├─ AUDIT_REPORT.md ◄───────┘
       ├─ AUDIT_SCORES.json
       ├─ Updated AGENTS.md
       └─ Updated progress.txt

Review audit findings → Create updated roadmap → Execute fixes
```

---

**Ready to start?**

```bash
cd /Users/cube/Documents/00-code/0xBot
./scripts/ralph/ralph.sh 20
```

Or use GSD to orchestrate:

```bash
# Coming next: /gsd:execute-plan (Ralph-based audit workflow)
```

---

**Created**: 2026-01-18
**Ralph Script**: scripts/ralph/ralph.sh
**Audit Config**: AUDIT_PRD.md
**Progress Tracking**: progress.txt, AGENTS.md
