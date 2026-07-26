(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.SentenceSenseQuestionBank = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, () => {
  'use strict';

  function shuffled(items, random = Math.random) {
    const copy = [...items];
    for (let index = copy.length - 1; index > 0; index -= 1) {
      const swapIndex = Math.floor(random() * (index + 1));
      [copy[index], copy[swapIndex]] = [copy[swapIndex], copy[index]];
    }
    return copy;
  }

  function weightedIndex(items, random = Math.random) {
    const total = items.reduce((sum, item) => sum + Math.max(0, Number(item.count) || 0), 0);
    if (!items.length) return -1;
    if (total <= 0) return Math.floor(random() * items.length);
    let cursor = random() * total;
    for (let index = 0; index < items.length; index += 1) {
      cursor -= Math.max(0, Number(items[index].count) || 0);
      if (cursor < 0) return index;
    }
    return items.length - 1;
  }

  function addCandidates(pool, selectedIds, selectedSentences, recent, target, random) {
    if (target <= 0) return [];
    const chosen = [];
    const ordered = shuffled(pool, random);
    const passes = [
      question => !recent.has(question.id),
      () => true
    ];
    for (const accept of passes) {
      for (const question of ordered) {
        if (chosen.length >= target) return chosen;
        if (
          !question
          || !question.id
          || !question.sentence_id
          || selectedIds.has(question.id)
          || selectedSentences.has(question.sentence_id)
          || !accept(question)
        ) continue;
        selectedIds.add(question.id);
        selectedSentences.add(question.sentence_id);
        chosen.push(question);
      }
    }
    return chosen;
  }

  async function collectFromTier({
    shards,
    target,
    fetchShard,
    recent,
    selectedIds,
    selectedSentences,
    random
  }) {
    const remaining = [...shards];
    const collected = [];
    while (remaining.length && collected.length < target) {
      const index = weightedIndex(remaining, random);
      const [shard] = remaining.splice(index, 1);
      const payload = await fetchShard(shard);
      const questions = Array.isArray(payload?.questions) ? payload.questions : [];
      collected.push(...addCandidates(
        questions,
        selectedIds,
        selectedSentences,
        recent,
        target - collected.length,
        random
      ));
    }
    return collected;
  }

  async function createRound({
    manifest,
    modeId,
    fetchShard,
    recentIds = [],
    random = Math.random
  }) {
    if (!manifest || !Array.isArray(manifest.shards)) {
      throw new Error('The question manifest is unavailable.');
    }
    if (typeof fetchShard !== 'function') {
      throw new Error('A shard loader is required.');
    }
    const roundSize = Math.max(1, Number(manifest.round_size) || 10);
    const modeShards = manifest.shards.filter(shard => shard.mode === modeId);
    if (!modeShards.length) throw new Error('No questions are available for this mode.');

    const reviewedShards = modeShards.filter(shard => shard.tier === 'reviewed-core');
    const provisionalShards = modeShards.filter(shard => shard.tier !== 'reviewed-core');
    const share = Math.min(
      1,
      Math.max(0, Number(manifest.sampling_policy?.reviewed_core_share) || 0)
    );
    let reviewedTarget = 0;
    if (reviewedShards.length && provisionalShards.length) {
      reviewedTarget = Math.round(roundSize * share);
    } else if (reviewedShards.length) {
      reviewedTarget = roundSize;
    }
    const provisionalTarget = roundSize - reviewedTarget;
    const recent = new Set(recentIds);
    const selectedIds = new Set();
    const selectedSentences = new Set();
    const selected = [];

    selected.push(...await collectFromTier({
      shards: reviewedShards,
      target: reviewedTarget,
      fetchShard,
      recent,
      selectedIds,
      selectedSentences,
      random
    }));
    selected.push(...await collectFromTier({
      shards: provisionalShards,
      target: provisionalTarget,
      fetchShard,
      recent,
      selectedIds,
      selectedSentences,
      random
    }));

    if (selected.length < roundSize) {
      selected.push(...await collectFromTier({
        shards: modeShards,
        target: roundSize - selected.length,
        fetchShard,
        recent,
        selectedIds,
        selectedSentences,
        random
      }));
    }
    if (selected.length < roundSize) {
      throw new Error(
        `Only ${selected.length} unique sentence questions are available; ${roundSize} are required.`
      );
    }
    return shuffled(selected, random).slice(0, roundSize);
  }

  function appendRecent(existing, questionIds, limit = 500) {
    const maximum = Math.min(500, Math.max(0, Number(limit) || 0));
    if (!maximum) return [];
    const ordered = [];
    const seen = new Set();
    for (const id of [...existing, ...questionIds]) {
      if (!id || seen.has(id)) continue;
      seen.add(id);
      ordered.push(id);
    }
    return ordered.slice(-maximum);
  }

  return {
    appendRecent,
    createRound,
    shuffled,
    weightedIndex
  };
}));
