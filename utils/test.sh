#!/bin/bash
set -ex
repomix
rye run isort .
rye run black .
rye fmt
rye run mypy --strict src/ongoing_convo_with_bronn_2025_06_10/utils.py
rye run pytest tests/ --cov=bb_logic --cov-report=term-missing
rye run python bb_logic.py

# Everything built, so try to make a PDF and view it:

rye run python bb_logic.py > output/output.md

# Output to PDF:
pandoc -o output/output.pdf output/output.md \
  --pdf-engine=xelatex \
  --variable fontsize=12pt \
  --variable geometry:margin=1.25in \
  --variable colorlinks=true \
  --variable linkcolor=blue \
  --highlight-style=tango

# Output to DOCX:
pandoc -o output/output.docx output/output.md \
  --toc \
  --toc-depth=2 \
  --highlight-style=tango \
  --metadata title="JUTA'S WEEKLY STATUTES BULLETIN" \
  --metadata author="[Automatically Generated]" \
  --metadata date="$(date +%Y-%m-%d)"
