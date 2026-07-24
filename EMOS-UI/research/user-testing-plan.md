# EMOS UI — Usability Testing Plan

A plan for moderated usability testing of the redesigned EMOS interface. Run this once the UI is
feature-complete and stable, to validate the heuristic findings against real user behaviour.

## 1. Objectives

1. Can a materials researcher assemble and run a discovery workflow **without help**?
2. Is the **IU / Feature** distinction understood, and does multi-select read as "queried together"?
3. Can users move between the **guided form** and the **node editor** without getting lost?
4. Are **outputs** (summary, table, 3D structure, uncertainty) understood and trusted?
5. Where does friction remain, and how does it compare to the previous version?

## 2. Method

- **Type:** moderated, think-aloud usability test (in person or screen-share).
- **Sessions:** 45 minutes each, one participant at a time.
- **Sample size:** 5–8 participants (Nielsen: ~5 users surface ~85% of issues). Test in two rounds of 4 if fixing between rounds.
- **Design:** within-subjects task list; observer records success, time, errors and verbatim quotes.
- **Environment:** the live app; if the compute backend is not yet connected, brief participants that data is representative.

## 3. Participants

| Segment | Why | Target |
|---------|-----|--------|
| Materials scientists / computational chemists | Primary users; judge scientific validity | 3–4 |
| Adjacent researchers / engineers (no EMOS experience) | Test learnability cold | 2–3 |
| Office / lab staff (non-domain) | Stress-test navigation and copy | 1 |

Recruit through the APRIL AI Hub, the Centre for Electronics Frontiers, and departmental mailing lists.
Screener: research field, familiarity with materials databases (COD, Materials Project), frequency of computational screening.

## 4. Task scenarios (moderator script)

Give tasks one at a time; do not read out UI labels. Capture success (unaided / aided / failed), time, and errors.

1. **Orientation (no clicking).** "Looking at this screen, what does this tool do, and where would you start?"
2. **Run a database extraction.** "Find candidate structures from at least two databases with a band gap between 1 and 3 eV, and tell me how many you got." *(Tests unit selection, multi-select meaning, feature config, reading the output summary.)*
3. **Recover / switch.** "You opened the wrong unit. Get back and open a different one." *(Tests the Back / breadcrumb fix — the previous version's lock.)*
4. **Inspect a result.** "Pick a promising candidate and show me its crystal structure. How confident is the prediction?" *(Tests the 3D viewer and uncertainty.)*
5. **Build a pipeline.** "Using the node editor, connect a database to a predictor and run it." *(Tests the node editor and same-page switch.)*
6. **Find help.** "You are not sure what a predictor does. Find out without leaving the app." *(Tests clickable help + Documentation.)*
7. **Wrap-up (SEQ + SUS).** Single Ease Question per task; System Usability Scale at the end.

## 5. Metrics

- **Task success rate** (unaided / aided / fail).
- **Time on task** and **error count** per task.
- **SEQ** (1–7) per task; **SUS** overall (target ≥ 70).
- **Qualitative:** points of confusion, misused controls, quotes, feature requests.

## 6. Analysis & reporting

- Rank issues by frequency × severity; map each to the Nielsen heuristic it touches.
- Compare success rate and SUS against the pre-redesign build where data exists.
- Produce a findings deck: top 5 issues, evidence (clips/quotes), and prioritised fixes.

## 7. Logistics checklist

- [ ] Consent form + recording permission.
- [ ] Stable build URL; backend status confirmed (live vs representative data).
- [ ] Moderator guide + observer scoring sheet.
- [ ] SEQ / SUS forms.
- [ ] 2 pilot sessions to debug the script before real participants.

> Do not begin recruitment until the UI is signed off as complete. Ask Atish to help reach materials
> scientists and office staff for the sample.
