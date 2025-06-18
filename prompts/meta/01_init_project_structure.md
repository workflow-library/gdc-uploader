name: init_project_structure
tags: [bootstrap, structure, agent]

🧱 Initialize or Conform to Prompt-Based Scientific Workflow Project Structure

This is a prompt for the coding assistant.Its goal is to ensure the project follows the standard structure for a Python-based, prompt-first scientific workflow toolkit.

🎯 Objectives

Create or conform the current repository to match the structure below.

Do not delete existing files, but move/rename/reorganize as needed.

Use .md files in prompts/ as the source of truth for emitting:

.cwl files to artifacts/cwl/

Dockerfiles to artifacts/docker/

.qmd Quarto notebooks to artifacts/notebooks/

📂 Target Project Structure

prompts/                  # Human-written prompt definitions (.md)
src/
  your_project/
    __init__.py
    emit/
      cwl.py              # Generates CWL tool definitions from prompt
      docker.py           # Generates Dockerfiles
      notebook.py         # Generates .qmd notebooks
    parser.py             # Parses .md prompt to Python dict
    cli.py                # Optional command-line interface
artifacts/
  cwl/                    # Emitted CWL tools
  docker/                 # Emitted Dockerfiles
  notebooks/              # Emitted .qmd notebooks
notebooks/                # Optional hand-authored or demo notebooks
tests/                    # Unit tests
docs/                     # Quarto or Markdown documentation
README.md
pyproject.toml
LICENSE
plans/                    # Agent-generated plans (.plan.md) for review or execution

❌ Restrictions

Do not use Jinja2 or any templating engine.

Use plain Python string formatting (f-strings or .format() only).

All notebooks must use .qmd format, not .ipynb.

✅ Success Criteria

After running, the repo has the correct structure.

Sample emitters and parser files exist in src/your_project/.

At least one example prompt in prompts/ exists (e.g. example_tool.md).

Emitted .cwl, .Dockerfile, and .qmd files land in the right artifacts/ subfolders.

📓 Plan Emission Instructions

The agent must generate a detailed plan before making changes.

Plans must be written to the plans/ folder using the filename format {name}.plan.md.

Each plan should include:

A summary of goals

A list of steps to be taken

Any assumptions or constraints

Optional shell commands or code references

Plans should be idempotent and reviewable.

If a plan already exists, update it only if needed, and note the changes.

name: emit_all_artifacts
tags: [emission, prompt, agent]

🚀 Emit All Artifacts from Prompt Files

This prompt tells the coding assistant to locate all .md prompt files in the prompts/ directory, parse them, and emit:

.cwl files into artifacts/cwl/

Dockerfiles into artifacts/docker/

.qmd Quarto notebooks into artifacts/notebooks/

🔍 Steps

Loop through all .md files in prompts/.

Parse:

Metadata (tool name, docker image, inputs/outputs)

Command block (bash code)

Notebook sections (headers + content)

For each prompt:

Emit a .cwl tool definition

Emit a Dockerfile

Emit a .qmd notebook with demo and docs

❌ Constraints

Do not emit if an up-to-date artifact already exists unless instructed to overwrite.

Use only plain Python, not Jinja2 or other template engines.

Output paths:

artifacts/cwl/{tool}.cwl

artifacts/docker/{tool}.Dockerfile

artifacts/notebooks/{tool}.qmd

🧠 Assumptions

The prompt structure is consistent and parseable.

A parser.py module exists to convert .md to a structured Python dict.

Emitters exist in src/your_project/emit/.

