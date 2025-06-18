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

