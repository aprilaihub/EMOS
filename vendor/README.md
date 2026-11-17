# Data Viewer browser dependencies

These files are served locally; the Data Viewer does not fetch CDN code or send
input data to a service. No npm/build step is required. Vendored files are
unmodified.

| Dependency | Pin / source | License | Runtime size |
| --- | --- | --- | --- |
| uPlot | `1.6.32`, https://registry.npmjs.org/uplot/-/uplot-1.6.32.tgz (`package/dist/uPlot.iife.min.js`, `package/dist/uPlot.min.css`) | MIT, original `LICENSE` included | 51,081 B JS + 1,857 B CSS |
| Andrej Karpathy's tSNEJS | commit `13ece5d7e751a5180a59ca396013e800e1059c20`, https://github.com/karpathy/tsnejs | MIT, declared in the included original `Readme.md` (upstream has no separate license file) | 11,292 B JS |

The small dependency-free uPlot build supplies scales, axes, canvas, resize and
cursor handling. The viewer's draw hook adds matrix cells and ordered line/scatter
points, avoiding a second chart library and avoiding any sorting/coalescing of
repeated x-values. The worker aliases `window` to its own global for tSNEJS's
unmodified browser export and installs its seeded RNG before initialization.
Neither shim affects the main page.

SHA-256 (verify after any dependency replacement):

```text
19c8d4c6ad88929a79f4ae49d6f7161566dfd0ba3d15cc495e974f787eb78f1f  uplot-1.6.32/uPlot.iife.min.js
df630c6a8d6f8eeaff264b50f73ce5b114f646ffd9a0bb74f049b0a00135fa04  uplot-1.6.32/uPlot.min.css
8f989229699b4fe2f1a0432d0e9edc338a8a911e250e2d1b01ecd770a5f5b1bd  uplot-1.6.32/LICENSE
70a7d6cd823fdc707c91b7cfa0036cd59a2199de6d5b7af9bb1f1081325a77f1  tsnejs-13ece5d/tsne.js
df8fddca95f5eb39494f596182280c07632f407633617ba9e3f1b3582562ba91  tsnejs-13ece5d/Readme.md
```
