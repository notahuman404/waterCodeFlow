# Recursive Branching in CodeVovle

CodeVovle now supports **hierarchical (recursive) branching**, allowing you to create branches at any level of nesting with full functionality for managing complex development workflows.

## Overview

### Branch Naming Convention

Branches use a **path-like naming structure** similar to file paths:

- **Root branch**: `main` (automatically created)
- **First-level branches**: `main/feature`, `main/bugfix`, `main/experiment`
- **Nested branches**: `main/feature/auth`, `main/feature/auth/jwt`, `main/feature/auth/jwt/refresh`

This creates a clear hierarchy where:
- Every branch has an optional parent
- A branch can have multiple children
- Full path represents the complete ancestry

### Key Concepts

1. **Hierarchical Path**: The complete path from root to leaf (e.g., `main/feature/auth`)
2. **Short Name**: The final component of the path (e.g., `auth`)
3. **Diff Chain**: Each branch maintains its own sequence of recorded ticks
4. **Independent Timelines**: Each branch can diverge from its parent and record independent changes

## Creating Branches

### Basic Usage

```bash
# Create a first-level branch
codevovle branch create --file src/app.py main/feature-login

# Create a nested branch (parent must exist)
codevovle branch create --file src/app.py main/feature-login/jwt-auth

# Create multiple levels at once (all parent paths created automatically)
codevovle branch create --file src/app.py main/ui/components/buttons
```

### Branch Validation

- **Parent must exist**: When creating `main/feature/sub`, the parent `main/feature` must already exist
- **Unique paths**: Each branch path must be unique (but short names can repeat at different levels)
- **Main is protected**: The `main` branch cannot be deleted

## Full Branching Operations

### List Branches

```bash
# List all branches (hierarchical view)
codevovle branch list --file src/app.py

# List only children of a specific parent
codevovle branch list --file src/app.py --parent main
codevovle branch list --file src/app.py --parent main/feature-login

# Output includes:
# - Full branch path
# - Head tick (last recorded change)
# - Number of child branches
# - Active status indicator
```

### Switch Branches (Jump)

```bash
# Switch to a specific branch and reconstruct file to that branch's head
codevovle branch jump --file src/app.py main/feature-login

# File is automatically reconstructed to the last tick on that branch
# Recording now happens on the new branch
```

### Rename Branches

```bash
# Rename a branch (only the short name changes)
codevovle branch rename --file src/app.py main/feature-old features/new-name

# Results in path: main/features/new-name
# All children are automatically updated
```

### Delete Branches

```bash
# Delete a branch and all its children recursively
codevovle branch delete --file src/app.py main/feature-login

# If the branch has children, they are also deleted
# Cannot delete the main branch
```

## Recording with Hierarchical Branches

### Recording Behavior

1. Each branch maintains its own **diff chain** (sequence of ticks)
2. When recording on a branch, new ticks are appended to that branch's diff chain
3. Reverting to a previous tick and editing creates a new divergence point
4. The **base snapshot** remains global (all branches share the same original state)

```bash
# Record changes on the current active branch
codevovle record --file src/app.py --interval 5

# Changes are recorded to the active branch's diff chain
# Status shows which branch is active
codevovle status --file src/app.py
```

### Creating Branch Divisions

The typical workflow for creating a new branch with diverging changes:

```bash
# Record 3 changes on main
codevovle record --file src/app.py --interval 2
# Ctrl+C after recording tick 1, 2, 3

# Create a feature branch
codevovle branch create --file src/app.py main/experimental

# Switch to experimental branch
codevovle branch jump --file src/app.py main/experimental
# File is reconstructed to head of main (tick 3)

# Edit file and record different changes
# Tick 4+ will be on the main/experimental branch
```

## Reverting and Branching

### Revert Within a Branch

```bash
# Revert to an earlier tick on the current branch
codevovle revert --file src/app.py --at 2

# Only works if tick 2 exists on the current branch
# Fails with clear error if tick is not on current branch
```

### Important: Revert Behavior

⚠️ **Note**: When you revert to a non-head tick and continue recording:
- The base snapshot is updated to match your reverted state
- New recordings create new ticks on the current branch
- This may create non-linear history in the diff chain

**Best Practice**: Use `branch jump` to switch contexts rather than reverting within a branch.

## AI Insights with Hierarchical Branches

### Insights Syntax

```bash
# Analyze changes on a specific branch
codevovle insights --file src/app.py --from main@1 --to main@5 --model gemini

# Analyze changes on nested branches
codevovle insights --file src/app.py \
  --from main/feature@1 \
  --to main/feature@10 \
  --model claude

# Mix branches in analysis
codevovle insights --file src/app.py \
  --from main@3 \
  --to main/experimental@7
```

The format is: `branch/path@tick` or just `tick` (uses current branch)

## Status and Inspection

### View Current State

```bash
# Show recording status including active branch
codevovle status --file src/app.py

# Output includes:
# - Active branch (hierarchical path)
# - Cursor tick (current position on branch)
# - Branch head tick (last tick on active branch)
# - Recording interval
```

### Understand Branch Structure

```bash
# List all branches with ancestry info
codevovle branch list --file src/app.py

# Shows:
# main
# ├── main/feature-login
# │   ├── main/feature-login/jwt
# │   └── main/feature-login/oauth
# ├── main/feature-export
# └── main/experimental
```

## Example Workflow

### Feature Development Workflow

```bash
# Initialize recording on main
cd CodeVovle
codevovle record --file parser.py --interval 10 &
# Make some changes, Ctrl+C after tick 1-5

# Create feature branch
codevovle branch create --file parser.py main/feature-json

# Switch to feature branch
codevovle branch jump --file parser.py main/feature-json

# Resume recording on feature branch
codevovle record --file parser.py --interval 10 &
# Record feature changes on ticks 6-10

# Create sub-feature for error handling
codevovle branch create --file parser.py main/feature-json/error-handling
codevovle branch jump --file parser.py main/feature-json/error-handling

# Record more specific changes
codevovle record --file parser.py --interval 10 &
# Record ticks 11-15 for error handling

# Go back to main branch to see original state
codevovle branch jump --file parser.py main

# Or jump to initial feature state
codevovle branch jump --file parser.py main/feature-json

# Generate insights on feature development
codevovle insights --file parser.py \
  --from main/feature-json@1 \
  --to main/feature-json@10 \
  --model gemini
```

## Advanced Usage

### Listing Branch Hierarchy

```bash
# List direct children of a branch
codevovle branch list --file src/app.py --parent main

# List all branches (shows full paths with hierarchy)
codevovle branch list --file src/app.py

# All descendants of a branch
codevovle branch list --file src/app.py --parent main/feature-auth
# Shows: feature-auth/jwt, feature-auth/oauth, feature-auth/mfa, etc.
```

### Renaming Branch Hierarchies

```bash
# Rename just the short name (final component)
codevovle branch rename --file src/app.py main/old-name new-name
# Result: main/new-name

# Children keep their parent reference updated automatically
# If main/old-name/child existed, it becomes main/new-name/child
```

### Clean Up Experimental Branches

```bash
# Delete entire branch tree
codevovle branch delete --file src/app.py main/experimental

# Or delete a specific feature branch and all related work
codevovle branch delete --file src/app.py main/feature-old-ui
# Removes main/feature-old-ui and all children like
# main/feature-old-ui/buttons, main/feature-old-ui/theme, etc.
```

## Storage Structure

Branch metadata is stored hierarchically:

```
.codevovle/
├── branches/
│   ├── main/
│   │   ├── meta.json
│   │   ├── feature-login/
│   │   │   ├── meta.json
│   │   │   ├── jwt/
│   │   │   │   └── meta.json
│   │   │   └── oauth/
│   │   │       └── meta.json
│   │   └── experimental/
│   │       └── meta.json
│   ├── diffs/
│   └── snapshots/
└── config.json
```

Each `meta.json` contains:
- `id`: Full branch path
- `label`: Short name (final component)
- `parent`: Parent branch path (or null for root)
- `forked_at_tick`: Tick where this branch diverged from parent (optional)
- `diff_chain`: Array of tick IDs in this branch's timeline
- `head_tick`: Latest tick on this branch

## Limitations and Notes

1. **Main branch is protected**: Cannot be deleted or moved
2. **Parent must exist**: Cannot create `main/a/b` if `main/a` doesn't exist
3. **Global snapshots**: All branches share the same base snapshot
4. **Unique paths**: Each full path must be unique (e.g., can't have two `auth` branches at the same parent level)
5. **Recording continues on active branch**: Always be aware of which branch you're on before recording

## Migration from Flat Branching

If you have existing projects with flat branching (single-level branches), you can manually reorganize:

```bash
# Current structure: "main", "develop", "feature1"

# Create new hierarchy:
codevovle branch create --file src/app.py main/v2/develop
codevovle branch create --file src/app.py main/v2/feature1

# Switch to old branches, export if needed, then delete:
codevovle branch jump --file src/app.py develop
# [Export important changes if needed]
codevovle branch delete --file src/app.py develop
```

## Performance Considerations

- **Diff chains**: Each branch maintains its own diff chain; storage grows with number of branches and ticks
- **Reconstruction**: Jumping to a branch with deep nesting reconstructs the file by applying all diffs from base to head
- **List operations**: Listing branches with many children is O(n) where n is total number of branches
- **Directory structure**: Deep nesting (10+ levels) may impact file system performance on some systems

## Best Practices

1. **Keep branch depth reasonable**: 2-4 levels typically sufficient for most workflows
2. **Use descriptive names**: `main/features/auth/jwt` is clearer than `main/a/b/c`
3. **Switch before recording**: Always verify active branch before starting `record`
4. **Clean up experimental branches**: Delete branches once their purpose is fulfilled
5. **Use insights regularly**: Track changes at each level to understand development flow
6. **Atomic changes per branch**: Each branch should represent a cohesive unit of work

## Troubleshooting

### "Parent branch does not exist"
Ensure parent path exists: `codevovle branch create --file app.py main/a` before creating `main/a/b`

### "Branch does not exist" during jump
Check branch list: `codevovle branch list --file app.py`, use exact path with slashes

### Unexpected file state after jump
File is reconstructed to the branch's head tick. If this isn't what you expected, check status and use `branch list` to verify tick positions

### Can't delete main branch
Main branch is protected. Delete children instead or create new root branches if needed

