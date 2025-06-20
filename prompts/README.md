# Prompt-Driven Development System

This directory implements a hierarchical prompt system for feature development using AI agents.

## Architecture: Meta → Specs → Agents

### 1. `/meta` - Foundational Guidelines
How agents should work and behave:
- `agent_creator.md` - Template for creating task-specific agents
- `spec_creator.md` - Template for writing feature specifications
- `spec_to_agents.md` - Breaking specs into executable tasks
- `spec_tracker.md` - Tracking feature implementation progress

### 2. `/specs` - Feature Specifications
What to build - concrete feature definitions:
- Feature requirements and user stories
- Acceptance criteria and success metrics
- Technical requirements and API contracts
- Task breakdown for implementation

Example: `gdc_http_upload.md` - Complete spec for HTTP upload feature

### 3. `/agents` - Task Implementations
How to build it - specific executable tasks:
- Each agent implements one atomic task from a spec
- References specific spec and task number
- Has clear inputs, outputs, and success criteria
- Can be executed independently

Examples:
- `implement_manifest_parser.md` - Parse GDC JSON manifests
- `implement_http_uploader.md` - HTTP PUT with chunks
- `implement_progress_display.md` - Progress bar with tqdm

## Development Flow

```
1. Write Spec (using spec_creator)
   ↓
2. Break into Tasks (using spec_to_agents)
   ↓
3. Create Agents (using agent_creator)
   ↓
4. Execute Agents (following meta guidelines)
   ↓
5. Track Progress (using spec_tracker)
   ↓
6. Feature Complete (all tasks integrated)
```

## Key Principles

### Clear Hierarchy
- **Meta**: Behavioral rules (how to work)
- **Specs**: Feature definitions (what to build)  
- **Agents**: Task execution (implementation details)

### Atomic Tasks
- Each agent does ONE thing
- Tasks are independently testable
- Clear dependencies between tasks
- No task larger than 8 hours

### Traceability
- Every agent references its spec
- Every task maps to acceptance criteria
- Progress tracked at task and spec level

## Usage Example

1. **Create a Spec**:
   ```
   prompts/specs/user_auth.md
   - User stories for authentication
   - Technical requirements
   - Task breakdown
   ```

2. **Generate Agents**:
   ```
   prompts/agents/create_user_schema.md (Task #1)
   prompts/agents/implement_password_hash.md (Task #2)
   prompts/agents/build_login_endpoint.md (Task #3)
   ```

3. **Execute Tasks**:
   - Run agents in dependency order
   - Each produces testable output
   - Track completion in spec

## Benefits

- **Clarity**: Clear what, why, and how for every feature
- **Trackability**: Know exactly what's done and what's left
- **Modularity**: Tasks can be distributed across agents/developers
- **Quality**: Each task has clear acceptance criteria
- **Reusability**: Specs and patterns can be reused across projects

## Project Management

- **Specs** = Feature backlog
- **Agents** = Sprint tasks
- **Meta** = Team working agreements
- **Progress** = Burndown tracking

This creates a complete system for AI-assisted feature development with clear boundaries and excellent progress visibility.