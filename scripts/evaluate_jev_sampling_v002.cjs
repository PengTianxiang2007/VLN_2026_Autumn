#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const Base = require('../core/jev_online_sampler_v001.js');
const Trial = require('../core/jev_online_sampler_v002.js');
const root = path.resolve(__dirname, '..');
const run = 'run_20261124_01';
const record = path.join(root, 'experiments/crossing_checkpoint/online_sampling_v002', run);
const out = path.join(root, 'outputs/crossing_checkpoint/online_sampling_v002', run);
const scoresDir = path.join(root, 'outputs/crossing_checkpoint/online_sampling_v001/run_20261118_01/episodes');
const astra = path.join(root, 'outputs/codex_tasks/checkpoint_dedup/v006_1');
const merged = path.join(astra, 'run_20261124_04_astra_standard_all53');
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const save = (file, data) => fs.writeFileSync(file, JSON.stringify(data, null, 2) + '\n', {flag:'wx'});
const split = read(path.join(record, 'split.json'));
const modes = ['near', 'plateau', 'active'];
const radius = 3;
const inputs = [
  'core/jev_online_sampler_v001.js', 'core/jev_online_sampler_v002.js',
  'scripts/evaluate_jev_sampling_v002.cjs', path.relative(root, path.join(record,'split.json'))
];
const hashes = () => Object.fromEntries(inputs.map(file => [
  file, crypto.createHash('sha256').update(fs.readFileSync(path.join(root, file))).digest('hex')
]));

function loadCase(number) {
  const prefix = 'C' + String(number).padStart(2, '0') + '_';
  // Same precedence as the all53 aggregation. Read labels only for a requested case.
  for (const parent of [path.join(merged,'retry_01'), merged, path.join(astra,'run_20261124_01_astra_c01_c11')]) {
    const dir = path.join(parent, 'cases');
    const name = fs.readdirSync(dir).find(name => name.startsWith(prefix));
    if (!name) continue;
    const item = read(path.join(dir, name, 'result.json'));
    assert.equal(item.case_number, number);
    assert.deepEqual(item.effective_nodes.map(n => n.id), item.final_active_ids);
    return item;
  }
  throw new Error('Missing Astra case ' + number);
}

// Ordered maximum-cardinality one-to-one matching. Resolve equal cardinalities
// by the smallest total absolute offset to preserve meaningful frame diagnostics.
function match(pred, ref) {
  const states = Array.from({length:pred.length + 1}, () =>
    Array.from({length:ref.length + 1}, () => ({pairs:[], distance:0})));
  for (let i = 1; i <= pred.length; i++) {
    for (let j = 1; j <= ref.length; j++) {
      const options = [states[i-1][j], states[i][j-1]];
      const delta = Math.abs(pred[i-1] - ref[j-1]);
      if (delta <= radius) {
        const before = states[i-1][j-1];
        options.push({pairs:[...before.pairs, [pred[i-1], ref[j-1]]], distance:before.distance + delta});
      }
      states[i][j] = options.sort((a,b) => b.pairs.length - a.pairs.length || a.distance - b.distance)[0];
    }
  }
  return states[pred.length][ref.length].pairs;
}

function evaluate(number, variants) {
  const item = loadCase(number);
  const scores = read(path.join(scoresDir, item.episode_id, 'scores.json'));
  const reference = item.effective_nodes.map(n => n.index);
  const rows = {};
  for (const mode of variants) {
    const model = mode === 'baseline' ? new Base() : new Trial(mode);
    const frames = [];
    scores.forEach((score,t) => {
      const {node} = model.push(score, t);
      if (node) {
        assert.equal(node.index + 5, t);
        assert.equal(node.rawScore, scores[node.index]);
        frames.push(node.index);
      }
    });
    if (mode === 'baseline') assert.deepEqual(frames, item.nodes.map(n => n.index));
    rows[mode] = {frames, pairs:match(frames, reference)};
  }
  return {number, episode:item.episode_id, reference, rows};
}

function totals(cases, mode) {
  return cases.reduce((sum, c) => {
    sum.candidates += c.rows[mode].frames.length;
    sum.reference += c.reference.length;
    sum.matches += c.rows[mode].pairs.length;
    return sum;
  }, {candidates:0, reference:0, matches:0});
}

const phase = process.argv[2];
if (!['design','validation'].includes(phase)) throw new Error('Expected design or validation');
const lockPath = path.join(record, 'selection.json');
let lock;
if (phase === 'validation') {
  lock = read(lockPath);
  assert.deepEqual(hashes(), lock.sha256);
}
const variants = phase === 'design' ? ['baseline', ...modes] : [...new Set(['baseline', lock.selected])];
const cases = split[phase].map(number => evaluate(number, variants));
const summary = Object.fromEntries(variants.map(mode => [mode, totals(cases, mode)]));
if (phase === 'design') {
  const folds = Array.from({length:4}, (_,i) => cases.slice(5*i, 5*i+5));
  const eligible = modes.filter(mode => summary[mode].matches === summary[mode].reference
    && summary[mode].candidates < summary.baseline.candidates
    && folds.every(f => totals(f,mode).candidates <= totals(f,'baseline').candidates));
  const minimum = Math.min(...eligible.map(mode => summary[mode].candidates));
  const selected = eligible.find(mode => summary[mode].candidates <= minimum + .03*summary.baseline.candidates) || 'baseline';
  save(lockPath, {selected, radius, summary, folds:folds.map(f => Object.fromEntries(variants.map(m => [m, totals(f,m)]))),
    sha256:hashes(), frozenAt:new Date().toISOString()});
}
save(path.join(out, phase + '.json'), {phase, radius, summary, cases});
console.log(JSON.stringify({phase, summary, selected:read(lockPath).selected}));
