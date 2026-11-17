/* One fresh worker per Run: seed and dependency Gaussian cache are isolated. */
'use strict';
// The unmodified upstream build exports to window; alias only inside this worker.
self.window = self;
importScripts('vendor/tsnejs-13ece5d/tsne.js', 'data-viewer.js');

self.onmessage = function (event) {
    const { id, matrix } = event.data;
    const send = message => self.postMessage({ id, ...message });
    const start = performance.now();
    try {
        const width = EMOSDataViewer.validateMatrix(matrix);
        const n = matrix.length;
        if (n < 2 || n > EMOSDataViewer.MAX_POINTS) throw new Error('t-SNE requires 2–1000 points; no sampling is performed.');
        // Reject overflow instead of silently rescaling the user's features.
        for (let i = 0; i < n; i++) {
            for (let j = i + 1; j < n; j++) {
                let distance = 0;
                for (let k = 0; k < width; k++) distance += (matrix[i][k] - matrix[j][k]) ** 2;
                if (!Number.isFinite(distance)) throw new Error('Squared distances overflow. Rescale features explicitly upstream.');
            }
        }
        let seed = 42;
        Math.random = function () {
            seed ^= seed << 13; seed ^= seed >>> 17; seed ^= seed << 5;
            return (seed >>> 0) / 4294967296;
        };
        const perplexity = Math.min(30, Math.max(1, (n - 1) / 3));
        const solver = new tsnejs.tSNE({ dim: 2, perplexity, epsilon: 10 });
        solver.initDataRaw(matrix);
        let mass = 0;
        for (const probability of solver.P) mass += probability;
        if (!Number.isFinite(mass) || Math.abs(mass - 1) > 0.01) {
            throw new Error('Affinities are numerically unstable at this scale. Rescale features explicitly upstream.');
        }
        for (let iteration = 1; iteration <= 500; iteration++) {
            const cost = solver.step();
            if (!Number.isFinite(cost)) throw new Error('t-SNE became numerically unstable. Check feature scales upstream.');
            if (iteration % 10 === 0) send({ type: 'progress', iteration, percent: iteration / 5 });
        }
        const coordinates = solver.getSolution();
        EMOSDataViewer.validateMatrix(coordinates);
        send({ type: 'done', coordinates, perplexity, elapsedMs: Math.round(performance.now() - start) });
    } catch (error) {
        send({ type: 'error', error: String(error.message || error) });
    }
};
