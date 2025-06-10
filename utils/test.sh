#!/bin/bash
set -ex
repomix
rye run isort .
rye run black .
rye fmt
rye run mypy --strict src/ongoing_convo_with_bronn_2025_06_10/utils.py
rye run pytest tests/ --cov=bb_logic --cov-report=term-missing
rye run python bb_logic.py
