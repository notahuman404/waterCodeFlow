# Quick Start: Recursive Branching in CodeVovle

Get up and running with CodeVovle's new hierarchical branching system in 5 minutes.

## Installation & Setup

```bash
cd CodeVovle
python -m codevovle --help  # Should show updated commands
```

## 30-Second Overview

CodeVovle now uses path-like branch names:
- `main` - your root branch (always exists)
- `main/feature-login` - a feature branch
- `main/feature-login/jwt` - a sub-feature of feature-login
- `main/feature-login/jwt/refresh` - even deeper nesting

**Key point**: Every branch has its own timeline of recorded changes!

## Basic Workflow (5 minutes)

### 1. Start Recording
```bash
# Terminal 1: Start recording your file
codevovle record --file src/app.py --interval 5 &

# Make some edits to src/app.py
# After a few changes, stop recording: Ctrl+C
```

### 2. Create Branches
```bash
# Create a feature branch
codevovle branch create --file src/app.py main/features/dark-mode

# Create a sub-branch for a specific part of the feature
codevovle branch create --file src/app.py main/features/dark-mode/colors
```

### 3. Switch to a Branch
```bash
# Jump to the dark-mode branch
codevovle branch jump --file src/app.py main/features/dark-mode

# Your file is now at the state of that branch's head
```

### 4. Record on Your Branch
```bash
# Terminal 1: Start recording (now on dark-mode branch)
codevovle record --file src/app.py --interval 5 &

# Make more edits
# These are recorded on main/features/dark-mode, not main
```

### 5. View Your Branches
```bash
# See all branches in hierarchy
codevovle branch list --file src/app.py

# See children of a parent
codevovle branch list --file src/app.py --parent main/features
```

### 6. Get AI Insights
```bash
# Analyze what changed in your feature
codevovle insights --file src/app.py \
  --from main/features/dark-mode@1 \
  --to main/features/dark-mode@10 \
  --model gemini
```

## Common Commands

### Create & Manage Branches
```bash
# Create a branch tree
codevovle branch create --file src/app.py main/v2
codevovle branch create --file src/app.py main/v2/ui
codevovle branch create --file src/app.py main/v2/ui/buttons

# Rename the short name (preserves parent)
codevovle branch rename --file src/app.py main/v2/ui button-components
# Result: main/v2/button-components

# Delete a branch and all children
codevovle branch delete --file src/app.py main/v2/ui
```

### Navigate Your Timeline
```bash
# List all branches
codevovle branch list --file src/app.py

# Switch to a branch
codevovle branch jump --file src/app.py main/v2/feature-x

# Check current status
codevovle status --file src/app.py

# Revert to earlier change on current branch
codevovle revert --file src/app.py --at 5
```

### Record & Analyze
```bash
# Start recording changes
codevovle record --file src/app.py --interval 5

# Stop with Ctrl+C when done

# Analyze what you did
codevovle insights --file src/app.py \
  --from main@5 \
  --to main@10 \
  --model claude
```

## Branch Path Syntax

Always use `/` to separate: `main/section/subsection`

### Valid paths:
```
main                          ✓ Root
main/features                 ✓ First level
main/features/auth            ✓ Nested
main/features/auth/jwt        ✓ Very nested
main/features/auth/jwt/v2     ✓ Many levels ok
```

### Invalid paths:
```
main//features                ✗ Double slash
main/                         ✗ Trailing slash
/main                         ✗ Leading slash
feature                       ✗ Doesn't start with main
```

## Tips & Tricks

### Organize by Domain
```bash
# Organize by feature area
codevovle branch create --file app.py main/auth/login
codevovle branch create --file app.py main/auth/signup
codevovle branch create --file app.py main/db/migrations
codevovle branch create --file app.py main/db/schema
```

### Organize by Status
```bash
# Organize by project status
codevovle branch create --file app.py main/active/wip-dark-mode
codevovle branch create --file app.py main/review/pr-123
codevovle branch create --file app.py main/done/v1-release
```

### Track Experiments
```bash
# Each experiment in its own branch tree
codevovle branch create --file app.py main/experiments/react-rewrite
codevovle branch create --file app.py main/experiments/performance-opt
codevovle branch create --file app.py main/experiments/new-api

# Jump between experiments
codevovle branch jump --file app.py main/experiments/react-rewrite
# ... work and record ...

codevovle branch jump --file app.py main/experiments/performance-opt
# ... work and record ...
```

### Deep Feature Work
```bash
# Create a feature stack
codevovle branch create --file app.py main/features/auth-v2
codevovle branch create --file app.py main/features/auth-v2/mfa
codevovle branch create --file app.py main/features/auth-v2/mfa/totp
codevovle branch create --file app.py main/features/auth-v2/mfa/sms
codevovle branch create --file app.py main/features/auth-v2/mfa/sms/provider-twilio

# Work on each specialized branch
codevovle branch jump --file app.py main/features/auth-v2/mfa/sms/provider-twilio
codevovle record --file app.py --interval 5 &
```

## Troubleshooting

### "Parent branch does not exist"
When creating `main/features/auth`, the parent `main/features` must exist first:
```bash
codevovle branch create --file app.py main/features      # Create parent first
codevovle branch create --file app.py main/features/auth # Then child
```

### "Branch does not exist" during jump
Double-check the path with `branch list`:
```bash
codevovle branch list --file app.py
codevovle branch jump --file app.py main/features  # Use exact path
```

### Current branch not what you expected
Check status before recording:
```bash
codevovle status --file app.py  # Shows active branch
codevovle branch list --file app.py  # Shows all branches
codevovle branch jump --file app.py main/correct/path  # Switch first
```

### Accidental delete
Use `branch list` before delete:
```bash
codevovle branch list --file app.py --parent main/features
codevovle branch delete --file app.py main/features/old-thing  # Confirm first!
```

## Next Steps

1. **Read the full guide**: [RECURSIVE_BRANCHING.md](RECURSIVE_BRANCHING.md)
2. **Check implementation details**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
3. **Start organizing**: Design your branch structure before recording large projects
4. **Share feedback**: These features are production-ready!

## Summary

You now have:
- ✅ Unlimited branch nesting depth
- ✅ Clear hierarchical naming (`main/section/subsection`)
- ✅ Full management (create, rename, delete, list)
- ✅ Per-branch recording and analysis
- ✅ Insights on any branch path
- ✅ Complete time travel within branches

Go forth and organize! 🚀

