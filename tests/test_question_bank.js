'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const bank = require('../docs/assets/question-bank.js');

const root = path.resolve(__dirname, '..');
const publicRoot = path.join(root, 'docs', 'data');
const manifest = JSON.parse(fs.readFileSync(path.join(publicRoot, 'manifest.json'), 'utf8'));
const gold = JSON.parse(fs.readFileSync(path.join(publicRoot, manifest.gold.path), 'utf8'));
const shardPayloads = new Map(
  manifest.shards.map(shard => [
    shard.id,
    JSON.parse(fs.readFileSync(path.join(publicRoot, shard.path), 'utf8'))
  ])
);

function seededRandom(seed = 1) {
  let value = seed >>> 0;
  return () => {
    value = (1664525 * value + 1013904223) >>> 0;
    return value / 0x100000000;
  };
}

async function loadRealShard(shard) {
  return shardPayloads.get(shard.id);
}

async function loadGold() {
  return gold;
}

test('every mode yields ten unique questions and ten unique sentence IDs', async () => {
  for (const mode of manifest.modes) {
    const round = await bank.createRound({
      manifest,
      modeId: mode.id,
      fetchShard: loadRealShard,
      fetchGold: loadGold,
      random: seededRandom(17)
    });
    assert.equal(round.length, 10);
    assert.equal(new Set(round.map(question => question.id)).size, 10);
    assert.equal(new Set(round.map(question => question.sentence_id)).size, 10);
    assert.ok(round.every(question => question.mode === mode.id));
  }
});

test('recent question and sentence avoidance is best effort', async () => {
  const modeId = 'parts-of-speech';
  const recentQuestions = manifest.shards
    .filter(shard => shard.mode === modeId)
    .flatMap(shard => shardPayloads.get(shard.id).questions)
    .slice(0, 500);
  const round = await bank.createRound({
    manifest,
    modeId,
    fetchShard: loadRealShard,
    fetchGold: loadGold,
    recent: {
      questionIds: recentQuestions.map(question => question.id),
      sentenceIds: recentQuestions.map(question => question.sentence_id)
    },
    random: seededRandom(3)
  });
  assert.equal(round.length, 10);
});

test('recent histories remain independently bounded', () => {
  const ids = Array.from({ length: 650 }, (_, index) => `item-${index}`);
  const questionHistory = bank.appendRecent([], ids, 250);
  const sentenceHistory = bank.appendRecent([], ids, 150);
  assert.equal(questionHistory.length, 250);
  assert.equal(questionHistory[0], 'item-400');
  assert.equal(sentenceHistory.length, 150);
  assert.equal(sentenceHistory[0], 'item-500');
});

test('difficulty budgets allocate the whole ten-question round', () => {
  const counts = bank.requestedDifficultyCounts(manifest, 10, seededRandom(7));
  assert.equal(Object.values(counts).reduce((sum, count) => sum + count, 0), 10);
  assert.equal(counts.advanced, 2);
  assert.ok([3, 4].includes(counts.basic));
  assert.ok([4, 5].includes(counts.intermediate));
});

test('reviewed sampling averages the configured 15 percent', () => {
  const random = seededRandom(29);
  const trials = 10000;
  let total = 0;
  for (let index = 0; index < trials; index += 1) {
    total += bank.goldTarget(manifest, 10, random);
  }
  assert.ok(Math.abs(total / trials - 1.5) < 0.03);
});

test('a failed shard fetch is skipped when another shard can complete the round', async () => {
  const modeId = 'parts-of-speech';
  let failed = false;
  const round = await bank.createRound({
    manifest,
    modeId,
    fetchGold: loadGold,
    fetchShard: async shard => {
      if (!failed) {
        failed = true;
        throw new Error('temporary offline failure');
      }
      return loadRealShard(shard);
    },
    random: seededRandom(4)
  });
  assert.equal(round.length, 10);
  assert.equal(failed, true);
});

test('loaded shard payloads are sufficient without further network access', async () => {
  const modeId = 'clauses';
  const cache = new Map();
  await bank.createRound({
    manifest,
    modeId,
    fetchGold: loadGold,
    fetchShard: async shard => {
      const payload = await loadRealShard(shard);
      cache.set(shard.id, payload);
      return payload;
    },
    random: seededRandom(9)
  });
  const round = await bank.createRound({
    manifest,
    modeId,
    fetchGold: loadGold,
    fetchShard: async shard => {
      if (!cache.has(shard.id)) throw new Error('network disabled');
      return cache.get(shard.id);
    },
    random: seededRandom(9)
  });
  assert.equal(round.length, 10);
});
