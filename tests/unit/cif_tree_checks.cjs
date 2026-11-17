// Run with node --test tests/unit/cif_tree_checks.cjs (Node 18+).
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const cif = require('../../cif-tree.js');
const plain = value => JSON.parse(JSON.stringify(value));
const block = text => cif.parse(text).blocks['1'];
const scalarPath = tag => ['blocks', '1', 'scalars', tag];
const columnPath = tag => ['blocks', '1', 'loop_columns', tag];
const field = (input, keys) => cif.adapt(input).entries.find(entry => entry.id === JSON.stringify(keys)).value;
const first = `data_first
_chemical_formula_sum 'Si O2'
_chemical_name_common quartz
_cell_length_a 4.913(2)
_space_group_name_H-M_alt 'P 32 2 1'
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_occupancy
Si1 Si .1 .2 .3 1
O1 O .4 .5 ? .
`;
const second = `data_second
_cell_length_b 9
loop_
_atom_site_label
_atom_site_fract_x
X1 0.12(3)
`;

test('scalars are strings, including uncertainty, formula, material and space group', () => {
    assert.deepEqual(plain(block(first).scalars), {
        _chemical_formula_sum: 'Si O2', _chemical_name_common: 'quartz', _cell_length_a: '4.913(2)',
        '_space_group_name_h-m_alt': 'P 32 2 1',
    });
});
test('loop labels/elements/xyz/occupancies retain row order and missing cells', () => {
    assert.deepEqual(plain(block(first).loop_columns), {
        _atom_site_label: ['Si1', 'O1'], _atom_site_type_symbol: ['Si', 'O'],
        _atom_site_fract_x: ['.1', '.4'], _atom_site_fract_y: ['.2', '.5'],
        _atom_site_fract_z: ['.3', null], _atom_site_occupancy: ['1', null],
    });
    assert.deepEqual(plain(block(first).loops._atom_site_fract_x), plain(block(first).loop_columns));
});
test('comments, quotes, embedded quotes/hash and next-line scalar values', () => {
    const result = block(`\uFEFF# comment\r\nDATA_test\r\n_A\r\n"a # b" # tail\r\n_b 'don't stop'\r\n_c abc#def\r\n_d 'loop_'\r\n_e '_tag'\r\n`);
    assert.deepEqual(plain(result.scalars), { _a: 'a # b', _b: "don't stop", _c: 'abc#def', _d: 'loop_', _e: '_tag' });
});
test('semicolon multiline scalar and loop cells preserve text and syntax-looking content', () => {
    const result = block('data_a\n_description\n;first\n# literal\n_data_ literal\nloop_\n;\nloop_\n_x\n_y\n;multi\nline\n;\n"two words"\n');
    assert.equal(result.scalars._description, 'first\n# literal\n_data_ literal\nloop_');
    assert.deepEqual(plain(result.loop_columns), { _x: ['multi\nline'], _y: ['two words'] });
});
test('bare missing markers become null but quoted markers remain strings', () => {
    assert.deepEqual(plain(block("data_a\n_a .\n_b ?\n_c '.'\n_d \"?\"\n").scalars), { _a: null, _b: null, _c: '.', _d: '?' });
});
test('loop rows can wrap lines, share lines and end with stop_', () => {
    assert.deepEqual(plain(block('data_a\nloop_ _a _b\n1\n2 3 4 stop_\n_c next\n').loop_columns), { _a: ['1', '3'], _b: ['2', '4'] });
});
test('single CIF fields are unwrapped; multiple CIFs keep order, duplicates and nulls', () => {
    assert.equal(field(first, scalarPath('_cell_length_a')), '4.913(2)');
    assert.deepEqual(field([second, first, null, first], scalarPath('_cell_length_a')), [null, '4.913(2)', null, '4.913(2)']);
    assert.deepEqual(field([second, first, null], columnPath('_atom_site_fract_x')), [['0.12(3)'], ['.1', '.4'], null]);
    assert.deepEqual(field([second, first], columnPath('_atom_site_occupancy')), [null, ['1', null]]);
});
test('loop column selection survives table/column reordering and changed schemas', () => {
    const reordered = 'data_a\nloop_ _z _a\nZ A\nloop_ _x _atom_site_fract_x\nX 0.7\n';
    assert.deepEqual(field([first, reordered, second], columnPath('_atom_site_fract_x')), [['.1', '.4'], ['0.7'], ['0.12(3)']]);
});
test('all blocks preserved and aligned by position, never concatenated or split to CIF text', () => {
    const a = 'data_one\n_a 1\ndata_two\n_a 2\n';
    const b = 'data_different_name\n_a 3\n';
    assert.deepEqual(field([a, b], ['blocks', '2', 'scalars', '_a']), ['2', null]);
    assert.deepEqual(field([a, b], ['blocks', '1', 'name']), ['one', 'different_name']);
    assert.equal(Object.keys(cif.parse(a).blocks).length, 2);
});
test('union fields appear under their parent and include fields only in later CIFs', () => {
    const entries = cif.adapt([first, second]).entries;
    const parent = entries.findIndex(e => e.id === JSON.stringify(['blocks', '1', 'scalars']));
    const child = entries.findIndex(e => e.id === JSON.stringify(scalarPath('_cell_length_b')));
    assert.ok(child > parent);
    assert.deepEqual(entries[child].value, [null, '9']);
    assert.equal(entries[child].depth, 3);
    assert.equal(new Set(entries.map(e => e.id)).size, entries.length);
});
test('normal JSON objects, arrays and strings do not activate CIF mode', () => {
    for (const input of [null, [], [null], [1, 2], ['ordinary', '_atom_site_label'], 'data_report', 'data_report is ready',
        'text\ndata_x\n_a 1', '_chemical_formula_sum Si', '{"text":"data_a\\n_x 1"}', { cif_strings: [first] }]) {
        assert.equal(cif.adapt(input), null, JSON.stringify(input));
    }
});
test('mixed CIF/non-CIF arrays report the input index instead of dropping rows', () => {
    for (const bad of ['', 'ordinary', {}, 5]) assert.throws(() => cif.adapt([first, bad]), /CIF input 2: expected/);
    assert.throws(() => cif.adapt([first, 'data_bad\n_a']), /CIF input 2: CIF line 2: missing value/);
});
test('malformed quoting and text blocks are rejected with line numbers', () => {
    for (const text of ["data_a\n_x 'unterminated", 'data_a\n_x "line\nbreak"', 'data_a\n_x\n;text', 'data_a\n_x\n;text\n;garbage']) {
        assert.throws(() => cif.parse(text), /CIF line \d+:/);
    }
});
test('incomplete/empty loops, duplicate tags, missing values and stray values fail', () => {
    for (const text of ['loop_\n_x _y\n1', 'loop_\n_x\n', 'loop_ 1', '_a 1\n_A 2', '_a 1\nloop_ _a\n2', '_x\n_y 2', '_x 1\nstray']) {
        assert.throws(() => cif.parse(`data_a\n${text}`), /CIF line/);
    }
});
test('unsupported STAR/CIF2 features fail explicitly', () => {
    for (const [text, pattern] of [
        ['#\\#CIF_2.0\ndata_a\n_x 1', /CIF 2.0/],
        ["data_a\n_x '''multi'''", /triple quotes/],
        ['data_a\n_x [1 2]', /containers/],
        ['data_a\nsave_frame\n_x 1\nsave_', /save frames/],
        ['global_\n_x 1', /global blocks/],
    ]) assert.throws(() => cif.parse(text), pattern);
});
test('block headers are required and duplicate names rejected case-insensitively', () => {
    for (const text of ['', '_x 1', 'data_\n_x 1', 'data_a\n_x 1\ndata_A\n_x 2']) assert.throws(() => cif.parse(text));
});
test('dictionary-like tokens cannot modify prototypes', () => {
    const result = block('data___proto__\n__proto__ safe\n_constructor ok\n');
    assert.equal(result.scalars.__proto__, 'safe');
    assert.equal({}.safe, undefined);
});

const fixtures = path.resolve(__dirname, '../cif_files');
function walk(directory) {
    return fs.readdirSync(directory, { withFileTypes: true }).flatMap(item => {
        const file = path.join(directory, item.name);
        return item.isDirectory() ? walk(file) : file.endsWith('.cif') ? [file] : [];
    });
}
for (const file of walk(fixtures)) {
    test(`repository CIF fixture: ${path.relative(fixtures, file)}`, () => {
        const text = fs.readFileSync(file, 'utf8');
        if (['empty.cif', 'invalid.cif'].includes(path.basename(file))) assert.throws(() => cif.parse(text));
        else {
            assert.ok(cif.looksLikeCif(text));
            assert.ok(cif.adapt(text).entries.length > 0);
        }
    });
}
