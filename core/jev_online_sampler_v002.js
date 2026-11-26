// Keep the v001 detector and its timing intact. Consolidate its proposals
// using only information already available at the current push().
'use strict';
const JevBaseSampler = typeof module === 'object'
  ? require('./jev_online_sampler_v001.js') : globalThis.JevOnlineSampler;

class JevOnlineSamplerV002 extends JevBaseSampler {
  constructor(mode) {
    super();
    if (!['near', 'plateau', 'active'].includes(mode)) throw new Error('Unknown consolidation rule');
    this.mode = mode;
    this.pending = null;
    this.lastEmitted = -Infinity;
    this.emittedCount = 0;
  }

  decide(index, emittedAt) {
    const proposal = super.decide(index, emittedAt);
    // Detector proposals are at least three steps apart, so a projection of
    // two steps is resolved before another proposal can arrive.
    if (proposal && index - this.lastEmitted > this.config.minGap) {
      const project = this.mode === 'plateau' && proposal.kind === 'plateau'
        || this.mode === 'active' && this.active;
      const later = this.filtered.get(index + this.confirmation);
      this.pending = {
        proposal,
        target: project && later.value !== null ? later.index : index
      };
    }
    if (!this.pending || this.pending.target !== index) return null;

    const {proposal: origin} = this.pending;
    this.pending = null;
    this.lastEmitted = index;
    this.emittedCount += 1;
    const point = this.filtered.get(index);
    return Object.freeze({...origin, id: 'S' + String(this.emittedCount).padStart(2, '0'),
      index, value: point.value, rawScore: point.raw, emittedAt, delay: emittedAt - index,
      sourceIndex: origin.index, sourceKind: origin.kind});
  }

  state() {
    return Object.freeze({...super.state(), samples: this.emittedCount});
  }
}
if (typeof module === 'object') module.exports = JevOnlineSamplerV002;
else globalThis.JevOnlineSamplerV002 = JevOnlineSamplerV002;
