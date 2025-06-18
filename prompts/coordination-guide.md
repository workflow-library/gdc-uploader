# Multi-Agent Coordination Guide

This guide explains how to effectively use the git worktree setup for multi-agent development on the gdc-uploader refactoring project.

## Overview

The multi-agent approach uses git worktrees to allow multiple AI agents (or developers) to work simultaneously on different aspects of the refactoring without conflicts.

## Setup

1. Run the setup script from the main repository:
   ```bash
   cd /path/to/gdc-uploader
   ./prompts/setup-multi-agent-worktrees.sh
   ```

2. This creates the following structure:
   ```
   gdc-uploader/              # Main repository
   ../gdc-uploader-agents/    # Worktree base directory
      ├── agent-1-core-architecture/
      ├── agent-2-common-utilities/
      ├── agent-3-upload-strategies/
      ├── agent-4-cli-modernizer/
      ├── agent-5-testing-infrastructure/
      ├── agent-6-api-client/
      └── agent-7-documentation/
   ```

## Working with Worktrees

### For Each Agent Session

1. **Navigate to Agent Worktree**:
   ```bash
   cd ../gdc-uploader-agents/agent-N-{name}
   ```

2. **Start Work with Agent Prompt**:
   - Open the corresponding prompt file: `prompts/agent-prompts/agent-N-{task}.md`
   - Use this as the initial prompt for the AI agent
   - The prompt contains all context, dependencies, and tasks

3. **Track Progress**:
   - Each worktree has `specs/agent-N-progress.md`
   - Update this file regularly with completed tasks and blockers

### Coordination Between Agents

1. **Shared Interfaces** (in main repo):
   ```bash
   # Agent 1 creates interface definitions
   main-repo/specs/interfaces/base_uploader_interface.py
   
   # Other agents reference these
   cd ../gdc-uploader-agents/agent-2-common-utilities
   cp ../../gdc-uploader/specs/interfaces/*.py ./reference/
   ```

2. **Check Status Across All Agents**:
   ```bash
   cd ../gdc-uploader-agents
   ./check-status.sh
   ```

3. **Sync with Main Branch**:
   ```bash
   # Run from agents directory to sync all
   ./sync-agents.sh
   
   # Or sync individual agent
   cd agent-N-{name}
   git fetch origin
   git merge origin/main
   ```

## Phase Management

### Phase 1 (Parallel Work)
Agents 1, 2, 4, and 6 can work simultaneously:
```bash
# Start all Phase 1 agents in separate sessions
cd ../gdc-uploader-agents/agent-1-core-architecture  # Terminal 1
cd ../gdc-uploader-agents/agent-2-common-utilities   # Terminal 2
cd ../gdc-uploader-agents/agent-4-cli-modernizer     # Terminal 3
cd ../gdc-uploader-agents/agent-6-api-client         # Terminal 4
```

### Phase 2 (Sequential Work)
Agent 3 waits for Phase 1 completion:
```bash
# After Phase 1 agents complete
cd ../gdc-uploader-agents
./test-integration.sh  # Test Phase 1 integration

# If successful, start Agent 3
cd agent-3-upload-strategies
```

### Phase 3 (Parallel Work)
Agents 5 and 7 work after Phase 2:
```bash
cd ../gdc-uploader-agents/agent-5-testing-infrastructure  # Terminal 1
cd ../gdc-uploader-agents/agent-7-documentation          # Terminal 2
```

## Communication Protocol

### 1. Interface Definitions
When creating shared interfaces:
```bash
# In Agent 1's worktree
cat > ../../gdc-uploader/specs/interfaces/base_uploader_interface.py << EOF
# Interface definition here
EOF

# Commit to agent branch
git add -A
git commit -m "Define base uploader interface"
git push origin agent-1-core-architecture
```

### 2. Progress Updates
Regular progress updates in the main repo:
```bash
# Update coordination status
cd ../../gdc-uploader
edit specs/coordination/status.md
git commit -m "Update Agent N progress"
```

### 3. Dependency Notification
When completing work that others depend on:
```bash
# Create a notification file
echo "Base interfaces complete - Agent 2 can proceed" > \
  ../../gdc-uploader/specs/coordination/agent-1-complete.flag
```

## Integration Testing

### Test Individual Agent Work
```bash
cd agent-N-{name}
# Run agent-specific tests
python -m pytest tests/
```

### Test Integration
```bash
cd ../gdc-uploader-agents
./test-integration.sh
```

This creates a temporary worktree that merges all agent branches to test compatibility.

## Merging Agent Work

### Individual Agent PR
```bash
cd agent-N-{name}
git push origin agent-N-{name}
# Create PR from agent branch to main
```

### Phase Integration
After all agents in a phase complete:
```bash
# From main repo
git checkout -b phase-1-integration
git merge origin/agent-1-core-architecture
git merge origin/agent-2-common-utilities
git merge origin/agent-4-cli-modernizer
git merge origin/agent-6-api-client

# Resolve any conflicts
# Run full test suite
pytest

# Create PR for phase integration
```

## Best Practices

1. **Frequent Commits**: Commit often to share progress
2. **Clear Commit Messages**: Include agent number in commits
3. **Update Progress Files**: Keep `agent-N-progress.md` current
4. **Test Before Pushing**: Run relevant tests before pushing
5. **Communicate Blockers**: Update status if blocked
6. **Use Interface Definitions**: Don't assume implementation details

## Troubleshooting

### Merge Conflicts
```bash
# If sync fails due to conflicts
git status  # See conflicted files
git merge --abort  # Abort if needed

# Or resolve manually
edit conflicted_file.py
git add conflicted_file.py
git merge --continue
```

### Worktree Issues
```bash
# List all worktrees
git worktree list

# Remove broken worktree
git worktree remove agent-N-{name} --force

# Re-add worktree
git worktree add ../gdc-uploader-agents/agent-N-{name} agent-N-{name}
```

### Finding Agent Work
```bash
# See all agent branches
git branch -a | grep agent-

# See commits by agent
git log --oneline --graph --branches='agent-*'
```

## Summary

The worktree approach enables true parallel development by giving each agent:
- Independent workspace
- Separate branch
- No switching overhead
- Easy integration testing
- Clear coordination points

Follow the phase dependencies and communication protocols for smooth collaboration!