// Executed by pytest (or directly with node); no npm test dependencies.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const viewer = require(path.join(root, 'data-viewer.js'));
const { adapt, prepare, vectorFields, extent } = viewer;

assert.equal(prepare(adapt([3, 2, 1]), 'Auto').kind, 'Plot');
assert.equal(prepare(adapt([[3, 2], [1, 0]]), 'Auto').kind, 'Heatmap');
for (const data of [null, {}, [], [[]], [[1], [2, 3]], [NaN], [Infinity], ['1'], [[1, '2']], [true], [[null]], { results: [] }, [[1], , [2]], [1, , 3]]) {
    assert.throws(() => adapt(data));
}
const records = { results: [
    { index: 8, cif_input: 'data_Fe', properties: { vector: [1, 2], other: [3, 4] } },
    { index: 2, cif_input: 'data_O', properties: { vector: [5, 6], other: [7, 8] } },
] };
assert.equal(adapt(records).needsField, true);
assert.equal(vectorFields(records).length, 2);
const model = adapt(records, '["properties","vector"]', (row, index) => `${row.cif_input}:${index}`);
assert.deepEqual(model.matrix, [[1, 2], [5, 6]]);
assert.deepEqual(model.rows.map(row => [row.index, row.sourceIndex, row.label]), [[0, 8, 'data_Fe:0'], [1, 2, 'data_O:1']]);
assert.throws(() => adapt(records, '["missing"]'), /unavailable/);
assert.throws(() => adapt([{ a: [1] }, { b: [2] }], '["a"]'), /lengths/);
assert.throws(() => adapt([{ a: [1, NaN] }]), /finite/);
assert.equal(vectorFields([{ 'a.b': [1], a: { b: [2] } }]).length, 2);
assert.deepEqual(adapt([['data_Fe', [1, 2]], ['data_O', [3, 4]]], '', (cif, i) => `${cif}-${i}`).rows.map(row => row.label), ['data_Fe-0', 'data_O-1']);
assert.throws(() => adapt([['data_Fe', [1]], ['data_O', [3, 4]]]));
assert.throws(() => adapt([{ value: 1 }]), /no vector/);
for (const mode of ['Plot', 'Heatmap', 't-SNE']) {
    assert.throws(() => prepare(model, mode, ['one']), /exactly 2/);
    for (const labels of [null, [1, 'two'], [NaN, 2], [Infinity, 2], [{}, {}], [1, ,]]) assert.throws(() => prepare(model, mode, labels));
    assert.deepEqual(prepare(model, mode, ['same', 'same']).labels, ['same', 'same']);
    assert.deepEqual(prepare(model, mode, [2, 1]).labels, [2, 1]);
}
assert.throws(() => prepare(adapt([1, 2]), 'Heatmap'), /matrix/);
assert.throws(() => prepare(adapt([1, 2]), 't-SNE'), /matrix/);
assert.throws(() => prepare(adapt([[1]]), 't-SNE'), /2–1000/);
assert.throws(() => prepare(adapt(Array.from({ length: 1001 }, () => [1])), 't-SNE'), /1001/);
assert.throws(() => extent([-1e308, 1e308]), /range/);
assert.deepEqual(extent([0, 0]), [-1, 1]);

function workerRun(matrix) {
    const messages = [];
    const context = vm.createContext({ performance, console });
    context.self = context;
    context.postMessage = message => messages.push(JSON.parse(JSON.stringify(message)));
    context.importScripts = (...files) => files.forEach(file => vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), context));
    vm.runInContext(fs.readFileSync(path.join(root, 'data-viewer-worker.js'), 'utf8'), context);
    context.onmessage({ data: { id: 9, matrix } });
    return messages;
}
const fixture = Array.from({ length: 12 }, (_, i) => [Math.sin(i), i / 12, i % 3]);
const first = workerRun(fixture), second = workerRun(fixture);
assert.equal(first.length, 51);
assert.equal(first[0].type, 'progress');
assert.equal(first.at(-1).type, 'done');
assert.equal(first.at(-1).id, 9);
assert.deepEqual(first.at(-1).coordinates, second.at(-1).coordinates);
for (const n of [2, 3, 10, 91]) {
    const result = workerRun(Array.from({ length: n }, () => [0, 0])).at(-1);
    assert.equal(result.type, 'done');
    assert.ok(result.perplexity >= 1 && result.perplexity < n);
    assert.equal(result.coordinates.length, n);
    assert.ok(result.coordinates.flat().every(Number.isFinite));
}
for (const bad of [[], [[1]], [[NaN], [2]], [[1e308], [-1e308]], Array.from({ length: 1001 }, () => [0])]) {
    assert.equal(workerRun(bad).at(-1).type, 'error');
}
console.log('Data Viewer adapter and worker checks passed.');
