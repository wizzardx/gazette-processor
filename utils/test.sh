#!/bin/bash
set -ex
repomix
rye run isort .
rye run black .
rye fmt
rye run mypy --strict src/ongoing_convo_with_bronn_2025_06_10/*.py
rye run pytest tests/ --cov=bb_logic --cov-report=term-missing
rye run python bb_logic.py bulletin

# Everything built, so try to make a PDF:

rye run python bb_logic.py bulletin > output/output.md

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

# # Also try experimentally to make a bulletin that has ALL the Notice types.
#
# rye run python bb_logic.py bulletin2 > output/output2.md
#
# # Output to PDF:
# pandoc -o output/output2.pdf output/output2.md \
#   --pdf-engine=xelatex \
#   --variable fontsize=12pt \
#   --variable geometry:margin=1.25in \
#   --variable colorlinks=true \
#   --variable linkcolor=blue \
#   --highlight-style=tango
#
# # Output to DOCX:
# pandoc -o output/output2.docx output/output2.md \
#   --toc \
#   --toc-depth=2 \
#   --highlight-style=tango \
#   --metadata title="JUTA'S WEEKLY STATUTES BULLETIN" \
#   --metadata author="[Automatically Generated]" \
#   --metadata date="$(date +%Y-%m-%d)"

echo
echo -e "\e[32mTests completed succesfully.\e[0m"
echo
