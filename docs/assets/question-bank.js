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

  function requestedDifficultyCounts(manifest, roundSize, random) {
    const shares = manifest.sampling_policy?.difficulty || {};
    const difficulties = ['basic', 'intermediate', 'advanced'];
    const rows = difficulties.map(name => {
      const exact = Math.max(0, Number(shares[name]) || 0) * roundSize;
      return { name, count: Math.floor(exact), remainder: exact % 1 };
    });
    let remaining = roundSize - rows.reduce((sum, row) => sum + row.count, 0);
    const order = shuffled(rows, random).sort((a, b) => b.remainder - a.remainder);
    for (const row of order) {
      if (remaining <= 0) break;
      row.count += 1;
      remaining -= 1;
    }
    return Object.fromEntries(rows.map(row => [row.name, row.count]));
  }

  function goldTarget(manifest, roundSize, random) {
    const exact = Math.max(
      0,
      Math.min(1, Number(manifest.sampling_policy?.reviewed_item_weight) || 0)
    ) * roundSize;
    return Math.floor(exact) + (random() < exact % 1 ? 1 : 0);
  }

  function chooseQuestions(pool, {
    target,
    difficultyCounts,
    selectedIds,
    selectedSentences,
    recentQuestionIds,
    recentSentenceIds,
    random,
    relaxDifficulty = true
  }) {
    const chosen = [];
    const wanted = { ...difficultyCounts };
    const passes = [
      question => (
        !recentQuestionIds.has(question.id)
        && !recentSentenceIds.has(question.sentence_id)
      ),
      () => true
    ];
    for (const acceptRecent of passes) {
      for (const question of shuffled(pool, random)) {
        if (chosen.length >= target) break;
        if (
          !question?.id
          || !question?.sentence_id
          || selectedIds.has(question.id)
          || selectedSentences.has(question.sentence_id)
          || !acceptRecent(question)
          || (wanted[question.difficulty] ?? 0) <= 0
        ) continue;
        selectedIds.add(question.id);
        selectedSentences.add(question.sentence_id);
        wanted[question.difficulty] -= 1;
        chosen.push(question);
      }
    }
    if (relaxDifficulty && chosen.length < target) {
      for (const question of shuffled(pool, random)) {
        if (chosen.length >= target) break;
        if (
          !question?.id
          || !question?.sentence_id
          || selectedIds.has(question.id)
          || selectedSentences.has(question.sentence_id)
        ) continue;
        selectedIds.add(question.id);
        selectedSentences.add(question.sentence_id);
        chosen.push(question);
      }
    }
    return chosen;
  }

  function takeDifficultyBudget(totalBudget, target) {
    const total = Object.values(totalBudget).reduce((sum, count) => sum + count, 0);
    if (!total || target <= 0) {
      return Object.fromEntries(Object.keys(totalBudget).map(key => [key, 0]));
    }
    const rows = Object.entries(totalBudget).map(([name, count]) => ({
      name,
      count: Math.floor((count / total) * target),
      remainder: ((count / total) * target) % 1
    }));
    let remaining = target - rows.reduce((sum, row) => sum + row.count, 0);
    rows.sort((a, b) => b.remainder - a.remainder || a.name.localeCompare(b.name));
    for (const row of rows) {
      if (remaining <= 0) break;
      row.count += 1;
      remaining -= 1;
    }
    return Object.fromEntries(rows.map(row => [row.name, row.count]));
  }

  async function createRound({
    manifest,
    modeId,
    fetchShard,
    fetchGold,
    recent = { questionIds: [], sentenceIds: [] },
    random = Math.random
  }) {
    if (!manifest || !Array.isArray(manifest.shards)) {
      throw new Error('The question manifest is unavailable.');
    }
    if (typeof fetchShard !== 'function' || typeof fetchGold !== 'function') {
      throw new Error('Question loaders are required.');
    }
    const roundSize = Math.max(1, Number(manifest.round_size) || 10);
    const modeShards = shuffled(
      manifest.shards.filter(shard => shard.mode === modeId),
      random
    );
    const difficultyBudget = requestedDifficultyCounts(manifest, roundSize, random);
    const selectedIds = new Set();
    const selectedSentences = new Set();
    const recentQuestionIds = new Set(recent.questionIds || []);
    const recentSentenceIds = new Set(recent.sentenceIds || []);
    const selected = [];

    let goldQuestions = [];
    try {
      const gold = await fetchGold();
      goldQuestions = (gold.questions || []).filter(question => question.mode === modeId);
    } catch (_) {
      goldQuestions = [];
    }
    const requestedGold = Math.min(goldTarget(manifest, roundSize, random), goldQuestions.length);
    const goldBudget = takeDifficultyBudget(difficultyBudget, requestedGold);
    const selectedGold = chooseQuestions(goldQuestions, {
      target: requestedGold,
      difficultyCounts: goldBudget,
      selectedIds,
      selectedSentences,
      recentQuestionIds,
      recentSentenceIds,
      random,
      relaxDifficulty: true
    });
    selected.push(...selectedGold);
    for (const question of selectedGold) {
      difficultyBudget[question.difficulty] = Math.max(
        0,
        (difficultyBudget[question.difficulty] || 0) - 1
      );
    }

    const shardPool = [];
    const failures = [];
    for (const shard of modeShards) {
      if (selected.length >= roundSize) break;
      try {
        const payload = await fetchShard(shard);
        shardPool.push(...(payload.questions || []));
      } catch (error) {
        failures.push(error);
        continue;
      }
      const chosen = chooseQuestions(shardPool, {
        target: roundSize - selected.length,
        difficultyCounts: difficultyBudget,
        selectedIds,
        selectedSentences,
        recentQuestionIds,
        recentSentenceIds,
        random,
        relaxDifficulty: false
      });
      selected.push(...chosen);
      for (const question of chosen) {
        difficultyBudget[question.difficulty] = Math.max(
          0,
          (difficultyBudget[question.difficulty] || 0) - 1
        );
      }
    }

    if (selected.length < roundSize) {
      selected.push(...chooseQuestions([...shardPool, ...goldQuestions], {
        target: roundSize - selected.length,
        difficultyCounts: {
          basic: roundSize,
          intermediate: roundSize,
          advanced: roundSize
        },
        selectedIds,
        selectedSentences,
        recentQuestionIds,
        recentSentenceIds,
        random,
        relaxDifficulty: true
      }));
    }
    if (selected.length < roundSize) {
      const detail = failures.length ? ' Some question files could not be loaded.' : '';
      throw new Error(
        `Only ${selected.length} unique sentence questions are available; `
        + `${roundSize} are required.${detail}`
      );
    }
    return shuffled(selected, random).slice(0, roundSize);
  }

  function appendRecent(existing, ids, limit) {
    const maximum = Math.max(0, Math.floor(Number(limit) || 0));
    if (!maximum) return [];
    const ordered = [];
    const seen = new Set();
    for (const id of [...existing, ...ids]) {
      if (!id || seen.has(id)) continue;
      seen.add(id);
      ordered.push(id);
    }
    return ordered.slice(-maximum);
  }

  return {
    appendRecent,
    createRound,
    goldTarget,
    requestedDifficultyCounts,
    shuffled
  };
}));
