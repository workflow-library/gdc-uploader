# refactor_01.md

## Meta

* **Task Name**: refactor_01
* **Purpose**: Refactor codebase to align with OWL (Optimized Workflow Library) structure
* **Target Agent**: @coder.agent
* **Dependencies**: Python ≥ 3.9, CWLTool, Git
* **Created**: 2025-06-20

---

## Task: Refactor to OWL Structure

Hi @coder.agent — Please refactor this repository to follow the OWL structure and best practices.

### 🎯 Refactoring Goals

1. **Consolidate and simplify the codebase**
2. **Establish clear modular boundaries**
3. **Ensure all components are easily composable**
4. **Maintain backwards compatibility where critical**

### 📁 Target Structure

```
gdc-uploader/
├── cwl/                    # Single-purpose CWL workflows
│   ├── upload.cwl         # Core upload workflow
│   ├── validate.cwl       # Metadata validation
│   └── transform.cwl      # Data transformation
├── docs/                   # Minimal, clear documentation
│   ├── README.md          # Quick start guide
│   ├── API.md             # API reference
│   └── EXAMPLES.md        # Usage examples
├── notebooks/              # Simple demonstration notebooks
│   ├── quick_start.ipynb  # Basic usage
│   └── advanced.ipynb     # Advanced features
├── prompts/               # AI agent prompts (ONLY agents and tasks)
│   ├── agents/            # Agent definitions
│   └── tasks/             # Task specifications
├── src/gdc_uploader/      # Source code
│   ├── __init__.py
│   ├── upload.py          # Core upload logic
│   ├── validate.py        # Validation functions
│   └── utils.py           # Shared utilities
├── tests/                 # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── fixtures/          # Test data
├── Dockerfile             # Container definition
├── README.md              # Project overview
├── pyproject.toml         # Python project config
└── requirements.txt       # Dependencies
```

### 🔧 Refactoring Steps

1. **Analyze Current Structure**
   - Map existing functionality to new structure
   - Identify core vs auxiliary components
   - Document dependencies between modules

2. **Consolidate Core Functionality**
   - Move all upload logic to `src/gdc_uploader/upload.py`
   - Extract validation to `src/gdc_uploader/validate.py`
   - Centralize utilities in `src/gdc_uploader/utils.py`

3. **Simplify CWL Workflows**
   - Create single-purpose CWL files
   - Remove complex nested workflows
   - Ensure each CWL is independently runnable

4. **Clean Up Documentation**
   - Keep only essential docs
   - Focus on quick start and examples
   - Remove redundant or outdated content

5. **Organize Prompts**
   - Keep ONLY agents/ and tasks/ in prompts/
   - Move specs elsewhere or remove
   - Ensure clear agent/task separation

6. **Streamline Tests**
   - Organize by type (unit/integration)
   - Ensure all core functions have tests
   - Add simple smoke tests for CWL workflows

### ✅ Success Criteria

- [ ] All core functionality preserved
- [ ] Each module has single responsibility
- [ ] CWL workflows run with `cwltool`
- [ ] Tests pass without modification
- [ ] Documentation is concise and accurate
- [ ] No circular dependencies
- [ ] Clean separation of concerns
- [ ] Prompts folder contains only agents/ and tasks/

### 🚫 What NOT to Do

- Don't break existing APIs without migration path
- Don't over-engineer or add unnecessary abstraction
- Don't create deep folder hierarchies
- Don't duplicate functionality across modules
- Don't remove features without documenting alternatives
- Don't put specs, meta, or other content in prompts/

### 📝 Implementation Notes

- Start with moving files, then refactor internals
- Use git mv to preserve history
- Create a migration guide for breaking changes
- Test each step incrementally
- Keep commits atomic and well-described

---

## 📊 Implementation Status

### Phase 1: Structure Setup (Completed ✓)
- [x] Create target directory structure
- [x] Move prompts/specs/ out of prompts (removed)
- [x] Move prompts/meta/ out of prompts (removed)
- [x] Verify prompts/ only has agents/ and tasks/

### Phase 2: Core Consolidation (Completed ✓)
- [x] Consolidate upload functionality
- [x] Extract validation logic to validate.py
- [x] Centralize utilities in utils.py
- [x] Remove duplicate code

### Phase 3: CWL Simplification (Completed ✓)
- [x] Identify core CWL workflows
- [x] Create single-purpose CWL files (upload.cwl, validate.cwl, transform.cwl)
- [x] Ready for testing with cwltool
- [x] Legacy CWL files already removed

### Phase 4: Documentation Cleanup (Completed ✓)
- [x] Audit existing docs (most were already removed)
- [x] Create minimal essential docs (README.md, API.md, EXAMPLES.md)
- [x] Update Dockerfile (removed ENTRYPOINT for CWL compatibility)
- [x] Archive old documentation (already done)

### Phase 5: Testing & Validation (Completed ✓)
- [x] Create unit test structure
- [x] Add test_validate.py for validation functions
- [x] Add test_utils.py for utility functions
- [x] Create test fixtures (manifest.json, token.txt)
- [x] Create quick_start.ipynb notebook

### Current Blockers
- None

### Next Steps
1. Run pytest to verify tests pass
2. Test CWL workflows with cwltool
3. Build and test Docker image
4. Update coder.agent.md with CWL Docker requirements ✓

---

## Example Command Sequence

```bash
# 1. Create new structure
mkdir -p src/gdc_uploader notebooks

# 2. Clean prompts folder
git mv prompts/specs ../specs
git mv prompts/meta ../meta

# 3. Consolidate core modules
git mv src/gdc_uploader/uploaders/api.py src/gdc_uploader/upload.py
git mv src/gdc_uploader/parser.py src/gdc_uploader/validate.py

# 4. Simplify CWL
git mv artifacts/cwl/gdc_upload.cwl cwl/upload.cwl

# 5. Clean documentation
git mv docs/API.md docs/
git rm docs/*_ANALYSIS.md docs/*_OPTIMIZATION.md

# 6. Run tests
python -m pytest tests/
```

---

## Version

v0.1 — Created 2025-06-20 for OWL structure refactoring