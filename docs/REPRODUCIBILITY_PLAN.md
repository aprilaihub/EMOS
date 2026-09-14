# EMOS Reproducibility Plan

This document focuses only on reproducibility.

## Goal

Anyone should be able to clone EMOS and run it locally on their server with clear, repeatable steps.

## What "Done" Looks Like

- A fresh clone works without hidden steps.
- Setup commands are the same in docs and in CI.
- Backend, frontend, tests, and docs each have one standard command.
- New contributors can verify their environment quickly.

## Action List

## 1) Standardize Local Setup

- [x] Define one supported Python version range.
- [x] Keep one canonical setup flow (virtual environment + install).
- [x] Ensure setup scripts (`setup/setup.sh`, `setup/setup.bat`) match docs exactly.

## 2) Standardize Run Commands

- [x] Support and document this current local path first: build Docker image(s), run `python backend/app.py`, then open `index.html`.
- [x] Define one command for frontend local run.
- [x] Define one command for backend local run.
- [x] Confirm backend port in docs matches actual backend default.

## 3) Standardize Test Commands

- [x] Define minimal default test command for contributors.
- [x] Define full test command for maintainers.
- [x] Clearly separate network/slow tests from default local tests.

## 4) Dependency Reproducibility

- [x] Review `requirements.txt` for consistency (pin where needed).
- [ ] Split core vs optional/heavy dependencies if needed.
- [x] Add a quick dependency verification command.

## 5) Environment Verification

- [x] Add a simple environment verification step.
- [x] Validate Python version, key packages, and key files.
- [x] Print clear pass/fail messages with next steps.

## 6) CI Reproducibility Check

- [x] Add a workflow that runs on fresh environment.
- [x] Run setup, then a smoke test (import + backend health check + minimal tests).
- [x] Fail fast with clear logs when setup breaks.

## 7) Documentation Sync

- [x] Update `README.md` with exact setup/run/test commands.
- [x] Keep documentation pages consistent with `README.md`.
- [x] Add a short troubleshooting section for common setup failures.

## Immediate Next Steps (First Pass)

- [x] Write the current local run workflow clearly in README/docs as the baseline path.
- [x] Fix any current command mismatches between code and docs.
- [x] Finalize one minimal command set (`setup`, `run`, `test`, `docs`).
- [x] Implement CI smoke workflow for fresh-clone verification.

## Notes

- Keep this checklist practical.
- Update this file as tasks are completed.
- Avoid adding parallel setup paths unless absolutely needed.
