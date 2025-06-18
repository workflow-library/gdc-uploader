#!/bin/bash

# Multi-Agent Git Worktree Setup Script for GDC-Uploader Refactoring
# This script sets up multiple git worktrees for parallel agent development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MAIN_REPO_DIR=$(pwd)
WORKTREE_BASE_DIR="${MAIN_REPO_DIR}/../gdc-uploader-agents"
MAIN_BRANCH="main"

# Agent definitions
declare -A AGENTS=(
    ["1"]="core-architecture:Core Architecture Designer"
    ["2"]="common-utilities:Common Utilities Refactorer"
    ["3"]="upload-strategies:Upload Strategy Implementer"
    ["4"]="cli-modernizer:CLI Modernizer"
    ["5"]="testing-infrastructure:Testing Infrastructure Builder"
    ["6"]="api-client:API Client Developer"
    ["7"]="documentation:Documentation Updater"
)

# Phase assignments
PHASE_1_AGENTS=(1 2 4 6)
PHASE_2_AGENTS=(3)
PHASE_3_AGENTS=(5 7)

echo -e "${BLUE}=== Multi-Agent Git Worktree Setup ===${NC}"
echo "Main repository: $MAIN_REPO_DIR"
echo "Worktree base directory: $WORKTREE_BASE_DIR"
echo

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Error: Not in a git repository${NC}"
    exit 1
fi

# Create base directory for worktrees
echo -e "${YELLOW}Creating worktree base directory...${NC}"
mkdir -p "$WORKTREE_BASE_DIR"

# Ensure we're on main branch and up to date
echo -e "${YELLOW}Updating main branch...${NC}"
git checkout "$MAIN_BRANCH"
git pull origin "$MAIN_BRANCH" 2>/dev/null || echo "Could not pull from origin (may not exist yet)"

# Create integration branch if it doesn't exist
if ! git show-ref --verify --quiet refs/heads/integration; then
    echo -e "${YELLOW}Creating integration branch...${NC}"
    git checkout -b integration
    git checkout "$MAIN_BRANCH"
fi

# Function to create worktree for an agent
create_agent_worktree() {
    local agent_num=$1
    local agent_info=${AGENTS[$agent_num]}
    local agent_name=${agent_info%%:*}
    local agent_desc=${agent_info#*:}
    local branch_name="agent-${agent_num}-${agent_name}"
    local worktree_path="${WORKTREE_BASE_DIR}/agent-${agent_num}-${agent_name}"
    
    echo -e "${BLUE}Setting up Agent ${agent_num}: ${agent_desc}${NC}"
    
    # Create branch if it doesn't exist
    if ! git show-ref --verify --quiet "refs/heads/${branch_name}"; then
        echo "  Creating branch: ${branch_name}"
        git branch "${branch_name}" "$MAIN_BRANCH"
    fi
    
    # Remove existing worktree if it exists
    if [ -d "$worktree_path" ]; then
        echo "  Removing existing worktree..."
        git worktree remove --force "$worktree_path" 2>/dev/null || rm -rf "$worktree_path"
    fi
    
    # Create worktree
    echo "  Creating worktree at: ${worktree_path}"
    git worktree add "$worktree_path" "${branch_name}"
    
    # Create agent-specific directories and files
    echo "  Setting up agent workspace..."
    
    # Create progress tracking file
    mkdir -p "${worktree_path}/specs"
    cat > "${worktree_path}/specs/agent-${agent_num}-progress.md" << EOF
# Agent ${agent_num} Progress: ${agent_desc}

## Status
- [ ] Started
- [ ] In Progress
- [ ] Completed

## Tasks
$(get_agent_tasks $agent_num)

## Progress Log

### $(date +"%Y-%m-%d %H:%M")
- Workspace initialized
- Ready to begin implementation

## Notes

## Blockers

## Dependencies
$(get_agent_dependencies $agent_num)
EOF

    # Create .gitignore for agent-specific files
    cat > "${worktree_path}/.gitignore.agent" << EOF
# Agent-specific temporary files
*.tmp
*.bak
.agent-cache/
EOF

    echo -e "  ${GREEN}✓ Agent ${agent_num} workspace ready${NC}"
    echo
}

# Function to get agent tasks from the plan
get_agent_tasks() {
    local agent_num=$1
    case $agent_num in
        1)
            cat << EOF
- [ ] Create src/gdc_uploader/core/base_uploader.py with abstract base class
- [ ] Define common interfaces for file discovery, progress tracking, error handling, report generation
- [ ] Create src/gdc_uploader/core/exceptions.py for unified error handling
- [ ] Design plugin architecture for different upload strategies
EOF
            ;;
        2)
            cat << EOF
- [ ] Create src/gdc_uploader/core/file_operations.py (file discovery, validation, filtering)
- [ ] Create src/gdc_uploader/core/progress.py (unified progress tracking and reporting)
- [ ] Create src/gdc_uploader/core/retry.py (retry decorator with exponential backoff)
- [ ] Enhance utils.py with additional shared utilities
EOF
            ;;
        3)
            cat << EOF
- [ ] Refactor upload.py to inherit from base uploader
- [ ] Refactor parallel_api_upload.py to use shared components
- [ ] Refactor spot_upload.py with proper resilience patterns
- [ ] Refactor upload_single.py as a simple strategy
- [ ] Create src/gdc_uploader/strategies/ directory for organization
EOF
            ;;
        4)
            cat << EOF
- [ ] Create src/gdc_uploader/cli/options.py with shared option definitions
- [ ] Refactor cli.py to use Click command groups, option inheritance, proper context
- [ ] Implement command aliases for backward compatibility
- [ ] Add rich terminal output support
- [ ] Create src/gdc_uploader/cli/validators.py for input validation
EOF
            ;;
        5)
            cat << EOF
- [ ] Set up pytest framework with proper fixtures
- [ ] Create unit tests for core modules
- [ ] Add integration tests for upload workflows
- [ ] Create mock GDC API for testing
- [ ] Add test coverage reporting
- [ ] Update GitHub Actions for automated testing
EOF
            ;;
        6)
            cat << EOF
- [ ] Create src/gdc_uploader/api/client.py (GDC API wrapper, session management, rate limiting)
- [ ] Create src/gdc_uploader/api/models.py for API data models
- [ ] Add authentication token management
- [ ] Implement connection pooling for performance
EOF
            ;;
        7)
            cat << EOF
- [ ] Update README.md with new structure
- [ ] Create architecture diagrams
- [ ] Write migration guide from old to new structure
- [ ] Update CWL workflow documentation
- [ ] Create API reference documentation
- [ ] Add inline code documentation (docstrings)
EOF
            ;;
    esac
}

# Function to get agent dependencies
get_agent_dependencies() {
    local agent_num=$1
    case $agent_num in
        1) echo "None (starts first)" ;;
        2) echo "Agent 1 (base interfaces)" ;;
        3) echo "Agents 1 and 2 (base classes and utilities)" ;;
        4) echo "None (can start immediately)" ;;
        5) echo "Agents 1-3 (needs established structure)" ;;
        6) echo "None (can start immediately)" ;;
        7) echo "All other agents (final documentation)" ;;
    esac
}

# Create shared coordination directory in main repo
echo -e "${YELLOW}Setting up coordination structure in main repository...${NC}"
mkdir -p "${MAIN_REPO_DIR}/specs/interfaces"
mkdir -p "${MAIN_REPO_DIR}/specs/coordination"

# Create interface definition template
cat > "${MAIN_REPO_DIR}/specs/interfaces/README.md" << EOF
# Shared Interface Definitions

This directory contains interface definitions that multiple agents need to coordinate on.

## Files
- base_uploader_interface.py - Abstract base class for all uploaders (Agent 1)
- file_operations_interface.py - File discovery and validation interfaces (Agent 2)
- progress_interface.py - Progress tracking interfaces (Agent 2)
- api_client_interface.py - GDC API client interfaces (Agent 6)

## Guidelines
1. Define interfaces before implementation
2. Use type hints for clarity
3. Document expected behavior
4. Version interfaces if breaking changes needed
EOF

# Create coordination status file
cat > "${MAIN_REPO_DIR}/specs/coordination/status.md" << EOF
# Multi-Agent Coordination Status

Updated: $(date +"%Y-%m-%d %H:%M")

## Phase 1 Status (Parallel Work)
- [ ] Agent 1 (Core Architecture) - Branch: agent-1-core-architecture
- [ ] Agent 2 (Common Utilities) - Branch: agent-2-common-utilities
- [ ] Agent 4 (CLI Modernizer) - Branch: agent-4-cli-modernizer
- [ ] Agent 6 (API Client) - Branch: agent-6-api-client

## Phase 2 Status (Sequential Work)
- [ ] Agent 3 (Upload Strategies) - Branch: agent-3-upload-strategies

## Phase 3 Status (Parallel Work)
- [ ] Agent 5 (Testing Infrastructure) - Branch: agent-5-testing-infrastructure
- [ ] Agent 7 (Documentation) - Branch: agent-7-documentation

## Integration Status
- [ ] Phase 1 integration test
- [ ] Phase 2 integration test
- [ ] Phase 3 integration test
- [ ] Final integration

## Next Sync: TBD
EOF

# Create all agent worktrees
echo -e "${YELLOW}Creating agent worktrees...${NC}"
echo

# Phase 1 agents
echo -e "${BLUE}=== Phase 1 Agents (can start immediately) ===${NC}"
for agent in "${PHASE_1_AGENTS[@]}"; do
    create_agent_worktree $agent
done

# Phase 2 agents
echo -e "${BLUE}=== Phase 2 Agents (wait for Phase 1) ===${NC}"
for agent in "${PHASE_2_AGENTS[@]}"; do
    create_agent_worktree $agent
done

# Phase 3 agents
echo -e "${BLUE}=== Phase 3 Agents (wait for Phase 2) ===${NC}"
for agent in "${PHASE_3_AGENTS[@]}"; do
    create_agent_worktree $agent
done

# Create helper scripts
echo -e "${YELLOW}Creating helper scripts...${NC}"

# Status check script
cat > "${WORKTREE_BASE_DIR}/check-status.sh" << 'EOF'
#!/bin/bash
echo "=== Multi-Agent Status Check ==="
echo
for dir in agent-*; do
    if [ -d "$dir" ]; then
        echo "## $dir"
        cd "$dir"
        echo "Branch: $(git branch --show-current)"
        echo "Status: $(git status --porcelain | wc -l) uncommitted changes"
        echo "Commits ahead: $(git rev-list --count origin/main..HEAD 2>/dev/null || echo 'N/A')"
        echo
        cd ..
    fi
done
EOF
chmod +x "${WORKTREE_BASE_DIR}/check-status.sh"

# Sync script
cat > "${WORKTREE_BASE_DIR}/sync-agents.sh" << 'EOF'
#!/bin/bash
echo "=== Syncing all agents with main ==="
for dir in agent-*; do
    if [ -d "$dir" ]; then
        echo "Syncing $dir..."
        cd "$dir"
        git fetch origin
        git merge origin/main --no-edit || echo "Merge conflicts in $dir - manual resolution needed"
        cd ..
    fi
done
EOF
chmod +x "${WORKTREE_BASE_DIR}/sync-agents.sh"

# Integration test script
cat > "${WORKTREE_BASE_DIR}/test-integration.sh" << 'EOF'
#!/bin/bash
INTEGRATION_DIR="integration-test"
echo "=== Testing integration of all agent branches ==="

# Create temporary integration worktree
rm -rf "$INTEGRATION_DIR"
git worktree add "$INTEGRATION_DIR" integration

cd "$INTEGRATION_DIR"

# Merge all agent branches
for i in 1 2 3 4 5 6 7; do
    branch=$(git branch -r | grep "agent-$i-" | head -1 | sed 's/origin\///')
    if [ -n "$branch" ]; then
        echo "Merging $branch..."
        git merge "origin/$branch" --no-edit || {
            echo "Conflict merging $branch"
            exit 1
        }
    fi
done

echo "Integration successful! Running tests..."
# Add test commands here

cd ..
EOF
chmod +x "${WORKTREE_BASE_DIR}/test-integration.sh"

# Summary
echo
echo -e "${GREEN}=== Setup Complete! ===${NC}"
echo
echo "Worktree Structure:"
echo "  $WORKTREE_BASE_DIR/"
find "$WORKTREE_BASE_DIR" -maxdepth 1 -type d -name "agent-*" | sort | while read dir; do
    echo "    $(basename $dir)/"
done
echo
echo "Helper Scripts:"
echo "  - ${WORKTREE_BASE_DIR}/check-status.sh    # Check status of all agents"
echo "  - ${WORKTREE_BASE_DIR}/sync-agents.sh     # Sync all agents with main"
echo "  - ${WORKTREE_BASE_DIR}/test-integration.sh # Test integration of all branches"
echo
echo "Coordination Files:"
echo "  - ${MAIN_REPO_DIR}/specs/coordination/status.md"
echo "  - ${MAIN_REPO_DIR}/specs/interfaces/README.md"
echo
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Navigate to each agent worktree"
echo "2. Use the agent prompt files in ./prompts/agent-prompts/"
echo "3. Begin implementation according to the phase schedule"
echo "4. Update progress in specs/agent-N-progress.md"
echo "5. Coordinate on shared interfaces in specs/interfaces/"
echo
echo -e "${BLUE}Happy coding!${NC}"