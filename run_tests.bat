@echo off
call .venv\Scripts\activate
python -m pytest tests/test_phase1_*.py -v
python -m pytest tests/test_phase2_*.py -v
pause
