#!/bin/bash
set -ex
rye run mypy --strict src/ongoing_convo_with_bronn_2025_06_10/utils.py
rye run pytest tests/ --cov=bb_logic --cov-report=term-missing
rye run python bb_logic.py
