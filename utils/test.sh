#!/bin/bash
set -ex
rye run pytest tests/ --cov=bb_logic --cov-report=term-missing
rye run python bb_logic.py
rye run python utils/smoke_test_all_gg_files.py
