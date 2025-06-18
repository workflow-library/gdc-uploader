# Worktree Direct Merge Workflow

This document describes the practical workflow for using git worktrees with multiple AI agents, then merging directly without pull requests.

## Overview

This workflow enables parallel development using multiple AI agents while keeping the process simple and direct. No pull requests needed - just develop and merge.

## Setup

1. **Run the setup script** (one time only):
   ```bash
   cd /workspaces/gdc-uploader
   ./prompts/setup-multi-agent-worktrees.sh
   ```

   This creates:
   - 7 worktrees in `../gdc-uploader-agents/`
   - Each agent gets their own branch and directory
   - Helper scripts for coordination

2. **Verify setup**:
   ```bash
   git worktree list
   cd ../gdc-uploader-agents && ls -la
   ```

## Phase-Based Execution

### Phase 1: Parallel Foundation Work

Start these agents simultaneously (they have no dependencies):

```bash
# Terminal 1 - Agent 1: Core Architecture
cd ../gdc-uploader-agents/agent-1-core-architecture
cat agent-prompt.md  # Use this as the AI prompt
# Let Agent 1 work...

# Terminal 2 - Agent 2: Common Utilities  
cd ../gdc-uploader-agents/agent-2-common-utilities
cat agent-prompt.md  # Use this as the AI prompt
# Let Agent 2 work...

# Terminal 3 - Agent 4: CLI Modernizer
cd ../gdc-uploader-agents/agent-4-cli-modernizer
cat agent-prompt.md  # Use this as the AI prompt
# Let Agent 4 work...

# Terminal 4 - Agent 6: API Client
cd ../gdc-uploader-agents/agent-6-api-client
cat agent-prompt.md  # Use this as the AI prompt
# Let Agent 6 work...
```

### Monitor Progress

From any terminal:
```bash
# Check status of all agents
cd ../gdc-uploader-agents
./check-status.sh

# See commit history
cd /workspaces/gdc-uploader
git log --oneline --graph --all -n 20

# Check specific agent's work
git log agent-1-core-architecture --oneline --not main
```

### Merge Phase 1

When Phase 1 agents complete their work:

```bash
cd /workspaces/gdc-uploader

# Merge in order (respecting any soft dependencies)
git merge agent-1-core-architecture -m "Merge Agent 1: Core architecture"
git merge agent-2-common-utilities -m "Merge Agent 2: Common utilities"
git merge agent-4-cli-modernizer -m "Merge Agent 4: CLI modernization"
git merge agent-6-api-client -m "Merge Agent 6: API client"

# Test the integration
./tests/test-cwl.sh  # or your test command
python -m pytest     # if Python tests exist
```

### Phase 2: Dependent Work

Only after Phase 1 is merged and tested:

```bash
# Terminal 1 - Agent 3: Upload Strategies
cd ../gdc-uploader-agents/agent-3-upload-strategies
cat agent-prompt.md  # Use this as the AI prompt
# Agent 3 can now see all Phase 1 work in main branch
```

When complete:
```bash
cd /workspaces/gdc-uploader
git merge agent-3-upload-strategies -m "Merge Agent 3: Upload strategies"
```

### Phase 3: Final Work

After Phase 2 is merged:

```bash
# Terminal 1 - Agent 5: Testing Infrastructure
cd ../gdc-uploader-agents/agent-5-testing-infrastructure
cat agent-prompt.md

# Terminal 2 - Agent 7: Documentation
cd ../gdc-uploader-agents/agent-7-documentation
cat agent-prompt.md
```

Final merges:
```bash
cd /workspaces/gdc-uploader
git merge agent-5-testing-infrastructure -m "Merge Agent 5: Testing"
git merge agent-7-documentation -m "Merge Agent 7: Documentation"
```

## Handling Common Scenarios

### Merge Conflicts

If you encounter conflicts:
```bash
git status                    # See conflicted files
# Edit files to resolve conflicts
git add <resolved-files>
git merge --continue
```

### Testing Before Merging

To test agent work before merging to main:
```bash
cd ../gdc-uploader-agents
./test-integration.sh  # Creates temporary integration branch
```

### Checking Agent Changes

Before merging, review what each agent did:
```bash
# Summary of changes
git diff main..agent-1-core-architecture --stat

# Detailed diff
git diff main..agent-1-core-architecture

# Just the commits
git log agent-1-core-architecture --oneline --not main
```

### Rolling Back a Merge

If something goes wrong:
```bash
# Undo last merge
git reset --hard HEAD~1

# Or reset to specific commit
git log --oneline -n 10  # Find the commit
git reset --hard <commit-hash>
```

## Best Practices

1. **Respect Dependencies**: Don't start Phase 2 agents until Phase 1 is merged
2. **Test After Each Phase**: Run tests after merging each phase
3. **Commit Messages**: Agents should use clear commit messages
4. **Small Commits**: Encourage agents to make focused commits
5. **Sync If Needed**: If an agent takes too long, sync with main:
   ```bash
   cd ../gdc-uploader-agents/agent-X-name
   git pull origin main
   ```

## Quick Reference

```bash
# Start agents
cd ../gdc-uploader-agents/agent-N-name
cat agent-prompt.md

# Check progress
cd ../gdc-uploader-agents && ./check-status.sh

# Merge work
cd /workspaces/gdc-uploader
git merge agent-N-name -m "Merge Agent N: Description"

# Test integration
./test-cwl.sh
```

## Advantages of This Workflow

- ✅ **Parallel Development**: Multiple agents work simultaneously
- ✅ **No PR Overhead**: Direct merging when ready
- ✅ **Clear Phases**: Dependencies are respected
- ✅ **Easy Rollback**: Git history preserved
- ✅ **Flexible**: Can adapt based on progress

## Summary

1. Setup worktrees (once)
2. Start Phase 1 agents in parallel
3. Merge Phase 1 when complete
4. Start Phase 2 agents
5. Continue through phases
6. Test after each merge
7. No pull requests needed!

This workflow maximizes parallel development while keeping the process simple and direct.