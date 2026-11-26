// A candidate at q proposes a representative at q+2. Both the features and
// the decision for that position are available at q+7 (position + 5).
'use strict';
const RankBase = typeof module === 'object' ? require('./jev_online_sampler_v001.js') : globalThis.JevOnlineSampler;
class JevOnlineSamplerV003 extends RankBase {
  constructor(profile, observe) {
    super();
    this.profile = profile;
    this.observe = observe;
    this.pending = null;
    this.lastOutput = -Infinity;
    this.outputCount = 0;
    this.previousProposal = -Infinity;
  }

  decide(index, at) {
    const proposal = super.decide(index, at);
    if (proposal) {
      this.pending = {proposal, gap:index - this.previousProposal,
        before:this.filtered.get(Math.max(0,index - 2))?.value,
        active:this.active};
      this.previousProposal = index;
    }
    const pending = this.pending;
    if (!pending || index !== pending.proposal.index + 2) return null;
    this.pending = null;
    const q = pending.proposal;
    const point = this.filtered.get(index);
    const right = this.filtered.get(index + 2);
    if ([point.value, right.value, pending.before].some(v => v == null)) return null;
    const early = q.index === 0;
    const features = [
      q.value, point.value, right.value, pending.before,
      Math.max(pending.before, q.value, point.value) - right.value,
      Math.abs(q.rawScore - q.value), Math.min(pending.gap, 14) / 14,
      Number(early), Number(early) * (q.value - 0.65),
      Number(pending.active), Number(q.kind === 'peak')
    ];
    if (this.observe) this.observe(index, features);
    if (!this.profile || index - this.lastOutput < this.profile.spacing) return null;
    const {weights, intercept, threshold} = this.profile;
    const logit = features.reduce((v,x,i) => v + weights[i] * x, intercept);
    const probability = 1 / (1 + Math.exp(-logit));
    if (probability < threshold) return null;
    this.lastOutput = index;
    this.outputCount++;
    return Object.freeze({...q, id:'S'+String(this.outputCount).padStart(2,'0'),
      index, value:point.value, rawScore:point.raw, emittedAt:at, delay:at-index,
      sourceIndex:q.index, estimatedMatch:probability});
  }

  state() { return Object.freeze({...super.state(), samples:this.outputCount}); }
}
if (typeof module === 'object') module.exports = JevOnlineSamplerV003;
else globalThis.JevOnlineSamplerV003 = JevOnlineSamplerV003;
