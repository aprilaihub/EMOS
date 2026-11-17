/* CIF 1.x field adapter for Tree Splitter. No numeric coercion or structure expansion.
 * Browser global + CommonJS export, following data-viewer.js's local-module boundary.
 */
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    else root.EMOSCifTree = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';

    function looksLikeCif(value) {
        if (typeof value !== 'string') return false;
        // Only a document header, never a tag mentioned inside ordinary text/JSON.
        const text = value.replace(/^\uFEFF/, '').replace(/^(?:\s|#[^\r\n]*(?:\r?\n|$))*/, '');
        return /^data_[^\s]+(?:[ \t]*(?:#[^\r\n]*)?\r?\n|\s+(?=_|loop_|data_))/i.test(text);
    }

    function tokenize(source) {
        const text = source.replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n');
        if (/^#\\#CIF_2\.0/.test(text)) throw new Error('CIF 2.0 is not supported; use CIF 1.x.');
        const tokens = [];
        let i = 0, line = 1;
        const fail = message => { throw new Error(`CIF line ${line}: ${message}`); };
        const advance = () => { if (text[i++] === '\n') line++; };
        while (i < text.length) {
            if (/\s/.test(text[i])) { advance(); continue; }
            if (text[i] === '#') {
                while (i < text.length && text[i] !== '\n') advance();
                continue;
            }
            const startLine = line;
            if (text[i] === ';' && (i === 0 || text[i - 1] === '\n')) {
                advance();
                const start = i;
                while (i < text.length && !(text[i] === ';' && text[i - 1] === '\n')) advance();
                if (i === text.length) fail('unterminated semicolon text field');
                const value = text.slice(start, i).replace(/\n$/, '');
                advance();
                if (i < text.length && !/\s|#/.test(text[i])) fail('text after semicolon terminator');
                tokens.push({ value, quoted: true, line: startLine });
            } else if (text[i] === "'" || text[i] === '"') {
                const quote = text[i];
                if (text.slice(i, i + 3) === quote.repeat(3)) fail('CIF 2.0 triple quotes are not supported');
                advance();
                const start = i;
                while (i < text.length && !(text[i] === quote && (i + 1 === text.length || /\s|#/.test(text[i + 1])))) {
                    if (text[i] === '\n') fail('newline in quoted value (use a semicolon text field)');
                    advance();
                }
                if (i === text.length) fail('unterminated quoted value');
                tokens.push({ value: text.slice(start, i), quoted: true, line: startLine });
                advance();
            } else {
                const start = i;
                while (i < text.length && !/\s/.test(text[i])) advance();
                const value = text.slice(start, i);
                if (/^[\[\]{}]/.test(value)) fail('CIF 2.0 containers are not supported');
                tokens.push({ value, quoted: false, line: startLine });
            }
        }
        return tokens;
    }

    const keyword = token => token && !token.quoted ? token.value.toLowerCase() : '';
    const structural = token => /^(?:_|data_|save_|loop_$|stop_$|global_$)/.test(keyword(token));
    const valueOf = token => !token.quoted && ['.', '?'].includes(token.value) ? null : token.value;

    function parse(source) {
        const tokens = tokenize(source);
        const blocks = Object.create(null), names = new Set();
        let i = 0, block = null, tags = new Set(), count = 0;
        const fail = (message, token = tokens[i]) => {
            throw new Error(`CIF line ${token?.line || tokens.at(-1)?.line || 1}: ${message}`);
        };
        const register = token => {
            const tag = keyword(token);
            if (tag.length < 2) fail('empty data tag', token);
            if (tags.has(tag)) fail(`duplicate tag ${tag}`, token);
            tags.add(tag);
            return tag;
        };
        while (i < tokens.length) {
            const token = tokens[i], key = keyword(token);
            if (key.startsWith('data_')) {
                const name = token.value.slice(5);
                if (!name) fail('data block needs a name');
                if (names.has(name.toLowerCase())) fail(`duplicate block name ${name}`);
                names.add(name.toLowerCase());
                block = { name, scalars: Object.create(null), loop_columns: Object.create(null), loops: Object.create(null) };
                blocks[String(++count)] = block;
                tags = new Set();
                i++;
            } else if (key.startsWith('save_') || key === 'global_') {
                fail('save frames and global blocks are not supported');
            } else if (!block) {
                fail('expected a data_ block header');
            } else if (key === 'loop_') {
                i++;
                const columns = [];
                while (keyword(tokens[i]).startsWith('_')) columns.push(register(tokens[i++]));
                if (!columns.length) fail('loop has no column tags');
                const table = Object.create(null);
                columns.forEach(tag => { table[tag] = []; block.loop_columns[tag] = table[tag]; });
                let cells = 0;
                while (i < tokens.length && !structural(tokens[i])) {
                    table[columns[cells++ % columns.length]].push(valueOf(tokens[i++]));
                }
                if (!cells || cells % columns.length) fail(`loop needs complete rows of ${columns.length} values`);
                // Stable across column reordering; each tag is unique within its block.
                block.loops[[...columns].sort()[0]] = table;
                if (keyword(tokens[i]) === 'stop_') i++;
            } else if (key.startsWith('_')) {
                const tag = register(token);
                i++;
                if (!tokens[i] || structural(tokens[i])) fail(`missing value for ${tag}`);
                block.scalars[tag] = valueOf(tokens[i++]);
            } else {
                fail(`unexpected token ${token.value.slice(0, 60)}`);
            }
        }
        if (!count) fail('expected a data_ block header');
        return { blocks };
    }

    function atPath(value, path) {
        for (const key of path) {
            if (value == null || !Object.hasOwn(value, key)) return null;
            value = value[key];
        }
        return value ?? null;
    }

    function adapt(input) {
        const many = Array.isArray(input);
        const items = many ? input : [input];
        if (!items.some(looksLikeCif)) return null; // Preserve the generic JSON tree unchanged.
        const parsed = items.map((item, index) => {
            if (item == null && many) return null;
            try {
                if (!looksLikeCif(item)) throw new Error('expected a CIF 1.x document or null');
                return parse(item);
            } catch (error) {
                throw new Error(`CIF input ${index + 1}: ${error.message}`);
            }
        });
        const paths = new Map();
        function visit(value, path) {
            if (!value || typeof value !== 'object' || Array.isArray(value)) return;
            Object.keys(value).sort().forEach(key => {
                const child = [...path, key];
                paths.set(JSON.stringify(child), child);
                visit(value[key], child);
            });
        }
        parsed.forEach(value => visit(value, []));
        // Traverse the union so fields seen only in later CIFs stay under their parent.
        const tree = Object.create(null);
        paths.forEach(path => {
            let branch = tree;
            path.forEach(key => { branch = branch[key] ||= Object.create(null); });
        });
        const entries = [];
        function emit(branch, path) {
            Object.keys(branch).sort().forEach(key => {
                const child = [...path, key];
                entries.push({ id: JSON.stringify(child), path: child, depth: path.length,
                    label: key, value: many ? parsed.map(value => atPath(value, child)) : atPath(parsed[0], child) });
                emit(branch[key], child);
            });
        }
        emit(tree, []);
        return { entries };
    }

    return { looksLikeCif, tokenize, parse, adapt };
});
