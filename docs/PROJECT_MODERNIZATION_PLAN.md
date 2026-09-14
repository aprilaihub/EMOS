# EMOS Plan (Simple Draft)

## 1) Reproducibility

People should be able to run this repository locally on their server.

**Best thing to do now:**
- Keep one simple setup path (`setup`, `run backend`, `run frontend`, `run tests`).
- Put these exact commands in `README.md` and keep them updated.
- Add one quick CI check that tests a fresh install from scratch.

## 2) Easy Contribution

Developers should be able to easily add their own Information Units (IUs) and Features.

**Best thing to do now:**
- Add clear templates for a new IU and a new Feature.
- Keep contribution steps short and consistent.
- Add a small scaffold tool/command so contributors do less manual work.

## 3) Proper Contribution Quality

Contributions should meet quality criteria. We need tests that pass properly for new IUs and Features. Current tests are too many; we should define the minimum tests needed. We also need documentation standards for newly added IUs and Features.

**Best thing to do now:**
- Define a **minimum required test set** for every new IU/Feature:
  - contract test (input/output shape)
  - registration/factory test
  - basic error-handling test
- Keep slow/network tests optional or nightly.
- Define a minimum documentation checklist for every new IU/Feature.

## 4) Documentation

Documentation has not been updated for a long while. It should reflect the current set of IUs and Features.

**Best thing to do now:**
- Audit docs against current code and remove outdated parts.
- Create one up-to-date IU catalog and one Feature catalog.
- Make docs checks run in CI so outdated docs are caught early.

## 5) Code Repository Cleanliness

There are many files in the repo. They should be better separated so the repository looks cleaner and stays easy to understand.

**Best thing to do now:**
- Group files by purpose (app code, docs, tests, scripts, configs).
- Reduce root-level clutter by moving related files into clear folders.
- Add a short repo structure guide so contributors know where things belong.

