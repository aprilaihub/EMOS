# MOSFET Channel Material Screening

This analysis documents an executed EMOS workflow for discovering and ranking candidate channel materials for MOSFET design. The workflow begins with broad database extraction, progressively narrows the pool using predictor-based criteria, and ends with device-level evaluation using the MOSFET Evaluation feature. This is a more natural use of the current MOSFET pipeline than gate-dielectric screening because the solver directly accepts channel-material parameters such as band gap, relative permittivity, and carrier mobilities. As a result, each shortlisted material can be evaluated through properties that directly influence channel transport and transistor switching behavior.

## Methodology and Results

### Stage 1: Broad Candidate Generation with Database Extractor

The first stage is designed to maximize recall rather than precision. Materials are queried from JARVIS-DFT and Alexandria in lenient mode using the filters band gap in the range $0.6 \leq E_g \leq 4.0$ eV, hull distance in the range $0.0 \leq E_{\mathrm{hull}} \leq 0.25$ eV/atom, and number of elements between 2 and 3, with a batch size of 120.

These criteria are well suited to channel-material discovery because they define a broad semiconductor search space while excluding obviously metallic or highly unstable systems. The lower band-gap bound of 0.6 eV is permissive enough to retain narrow-gap semiconductors for exploratory screening, while the upper bound of 4.0 eV avoids moving too far toward strongly insulating materials that are unlikely to act as effective channels. The hull-distance criterion is intentionally loose: it removes clearly unstable structures while preserving borderline candidates for later evaluation. Restricting the chemistry to binary and ternary systems keeps the search space physically broad but still plausible for synthesis and device integration.

This stage produced 120 unique CIF candidates corresponding to 71 unique reduced formulas.

### Stage 2: Descriptor Completion and Property Filtering with GBFS

The second stage uses the GBFS predictor IU to generate a consistent set of electronic descriptors across the candidate pool. For runtime control in the tutorial workflow, the first 36 Stage 1 candidates are evaluated. Only successful GBFS predictions are retained. The filtered criteria are then $0.9 \leq E_g \leq 4.0$ eV and dielectric constant $\kappa \geq 3.0$. Duplicate reduced formulas are removed by keeping one representative CIF per formula, chosen first by highest predicted electron mobility and then by lower band gap. The final selector keeps the top 16 candidates ranked by electron mobility in descending order and band gap in ascending order.

These criteria are particularly appropriate for channel screening. Band gap remains the key discriminator because it governs whether the channel can suppress off-state leakage while still allowing useful carrier transport under gate bias. Tightening the lower bound from 0.6 eV to 0.9 eV after descriptor completion is sensible because once predictions are available, the workflow can be more selective against candidates that may leak too strongly in the off state. The dielectric threshold of 3.0 is deliberately mild, but useful: for channel materials, a very low relative permittivity may correlate with less favorable electrostatics. Electron mobility is emphasized in the selector because high mobility is one of the clearest precursors to strong drive current in a transistor channel.

This stage reduced the pool from 36 evaluated structures representing 19 formulas to 16 retained candidates representing 16 unique formulas.

### Stage 3: Stability Proxy Filtering with MatterSim

Because the Stability Consensus feature is not yet ready, the third stage uses MatterSim as a practical stability proxy. Each Stage 2 candidate is relaxed with MatterSim, and only candidates with successful status and residual force norm satisfying $\max |F| \leq 0.10$ eV/\AA{} are retained. The final selector keeps the top 8 candidates with the lowest residual force.

This criterion is reasonable for channel-material screening because a useful channel material should not only exhibit attractive electronic properties, but should also relax to a mechanically coherent configuration. Residual force is not equivalent to a rigorous thermodynamic stability metric, but it is a defensible surrogate for whether the structure reaches a well-behaved relaxed state under the current surrogate model. For a tutorial workflow and early-stage discovery, this is a practical compromise.

This stage reduced the pool from 16 candidates to 8 retained candidates, all with distinct formulas.

### Stage 4: Synthesizability Filtering with SynthNN

The fourth stage uses SynthNN to estimate synthesis likelihood. Candidates are retained if the synthesizability score is at least 0.70, and the final selector keeps up to the top 5 by synthesizability score.

This step is especially important for channel materials because a candidate that is electronically promising and structurally plausible may still be experimentally inaccessible. Semiconductor device materials need not only to exist computationally, but also to be synthesizable in a form that can plausibly be integrated into a device stack. The threshold of 0.70 matches the default SynthNN decision boundary and is strong enough to prioritize experimentally actionable compounds without making the screen unrealistically strict.

This stage reduced the pool from 8 candidates to 3 retained candidates:

1. LiMgN with synthesizability score 0.9006
2. LiLuS2 with synthesizability score 0.8711
3. LiLuSe2 with synthesizability score 0.7295

### Stage 5: Device-Level Ranking with MOSFET Evaluation

In the final stage, the three shortlisted candidates are evaluated with the MOSFET Evaluation feature. The device geometry, oxide properties, contact assumptions, doping profile, and bias conditions are held fixed across all candidates. Only the candidate-dependent channel descriptors are varied, specifically band gap, relative permittivity, and carrier mobilities. The device-level screen requires $I_{\mathrm{off}} \leq 10^{-2}$ $\mu$A/$\mu$m and $0.15 \leq V_{\mathrm{th}} \leq 0.65$ V. Final ranking is performed by sorting first on passing the device screen, then by $I_{\mathrm{on}}/I_{\mathrm{off}}$ in descending order, then by $I_{\mathrm{on}}$ in descending order, and finally by the distance of $V_{\mathrm{th}}$ from 0.35 V in ascending order.

These criteria are particularly well matched to channel-material ranking. Unlike gate dielectrics, channel materials directly control the tradeoff between current drive and leakage. A good channel must provide large $I_{\mathrm{on}}$ while still suppressing $I_{\mathrm{off}}$, which makes $I_{\mathrm{on}}/I_{\mathrm{off}}$ a more meaningful primary selector than $I_{\mathrm{on}}$ alone. This avoids over-rewarding highly conductive but leaky materials. The threshold-voltage window is also important because a channel that produces high current is not practical if it pushes the device into an unusable operating regime. Using $V_{\mathrm{th}}$ as a secondary constraint rather than the primary ranking metric is appropriate because, within a fixed transistor architecture, the central question is whether the material supports strong and well-controlled switching.

All three candidates passed the device screen. The final ranking was:

1. **LiMgN**
   - $I_{\mathrm{on}} = 40.37$ $\mu$A/$\mu$m
   - $I_{\mathrm{off}} = 3.88 \times 10^{-4}$ $\mu$A/$\mu$m
   - $V_{\mathrm{th}} \approx 0.485$ V
   - $I_{\mathrm{on}}/I_{\mathrm{off}} \approx 1.04 \times 10^5$

2. **LiLuSe2**
   - $I_{\mathrm{on}} = 48.44$ $\mu$A/$\mu$m
   - $I_{\mathrm{off}} = 3.60 \times 10^{-3}$ $\mu$A/$\mu$m
   - $V_{\mathrm{th}} \approx 0.485$ V
   - $I_{\mathrm{on}}/I_{\mathrm{off}} \approx 1.35 \times 10^4$

3. **LiLuS2**
   - $I_{\mathrm{on}} = 60.88$ $\mu$A/$\mu$m
   - $I_{\mathrm{off}} = 6.08 \times 10^{-3}$ $\mu$A/$\mu$m
   - $V_{\mathrm{th}} \approx 0.485$ V
   - $I_{\mathrm{on}}/I_{\mathrm{off}} \approx 1.00 \times 10^4$

This result is physically informative. Although LiLuS2 delivered the highest on-current, LiMgN ranked first because it achieved the best balance between drive current and leakage by a large margin. This is exactly why the workflow uses $I_{\mathrm{on}}/I_{\mathrm{off}}$ as the primary selection metric for channel materials: transistor usefulness depends more on controllable switching than on raw conductivity alone.

## Candidate Funnel Summary

The executed workflow narrowed the candidate pool as follows:

1. Stage 1: 120 unique CIF candidates, 71 unique formulas
2. Stage 2: 16 retained candidates, 16 unique formulas
3. Stage 3: 8 retained candidates, 8 unique formulas
4. Stage 4: 3 retained candidates, 3 unique formulas
5. Stage 5: 3 ranked device candidates

## Why This Workflow Is Well Suited to MOSFET Channel Discovery

This workflow is especially appropriate for MOSFET channel-material discovery because every stage is aligned with a physical requirement of the channel layer:

1. The material must be semiconducting rather than metallic.
2. It should possess descriptors consistent with useful transport and electrostatics.
3. It should relax to a structurally credible configuration.
4. It should be plausibly synthesizable.
5. It must perform well as a transistor channel under fixed device conditions.

This structure also matches the current implementation state of EMOS. It preserves the advantages of an end-to-end integrated workflow, namely database retrieval, predictor-based descriptor completion, structural filtering, synthesizability assessment, and device-level ranking, while avoiding assumptions that the present implementation cannot yet support robustly. Most importantly, it uses the MOSFET solver in the way it is most naturally intended: comparing candidate channel materials through their direct effect on transistor characteristics under otherwise identical device conditions.

The workflow remains modular. As EMOS gains stronger stability tooling and richer device-output metrics, the same five-stage structure can be tightened without changing its logic. Stability consensus can replace the MatterSim-only proxy, and future MOSFET metrics such as subthreshold swing or DIBL can be incorporated as additional hard constraints or ranking terms. Until then, this workflow provides a sensible, reproducible baseline for channel-material discovery within the current EMOS environment.
