'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const bank = require('../docs/assets/question-bank.js');

const root = path.resolve(__dirname, '..');
const publicRoot = path.join(root, 'docs', 'data', 'en');
const manifest = JSON.parse(fs.readFileSync(path.join(publicRoot, 'manifest.json'), 'utf8'));
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

test('every mode yields ten unique questions and ten unique sentence IDs', async () => {
  for (const mode of manifest.modes) {
    const round = await bank.createRound({
      manifest,
      modeId: mode.id,
      fetchShard: loadRealShard,
      random: seededRandom(17)
    });
    assert.equal(round.length, 10);
    assert.equal(new Set(round.map(question => question.id)).size, 10);
    assert.equal(new Set(round.map(question => question.sentence_id)).size, 10);
    assert.ok(round.every(question => question.mode === mode.id));
  }
});

test('recent-question avoidance is best effort and never blocks a round', async () => {
  const modeId = 'parts-of-speech';
  const recentIds = shardPayloads.get(
    manifest.shards.find(shard => shard.mode === modeId).id
  ).questions.map(question => question.id);
  const round = await bank.createRound({
    manifest,
    modeId,
    fetchShard: loadRealShard,
    recentIds,
    random: seededRandom(3)
  });
  assert.equal(round.length, 10);
});

test('recent history stays bounded at 500 IDs', () => {
  const ids = Array.from({ length: 650 }, (_, index) => `question-${index}`);
  const history = bank.appendRecent([], ids, 500);
  assert.equal(history.length, 500);
  assert.equal(history[0], 'question-150');
  assert.equal(history.at(-1), 'question-649');
});

test('weighted shard choice follows counts within statistical tolerance', () => {
  const items = [{ count: 1 }, { count: 9 }];
  const random = seededRandom(29);
  let second = 0;
  const trials = 10000;
  for (let index = 0; index < trials; index += 1) {
    if (bank.weightedIndex(items, random) === 1) second += 1;
  }
  const share = second / trials;
  assert.ok(share > 0.88 && share < 0.92, `observed weighted share ${share}`);
});

test('mixed banks retain the configured reviewed-core share', async () => {
  const reviewedSource = shardPayloads.get(
    manifest.shards.find(shard => shard.tier === 'reviewed-core').id
  ).questions;
  const reviewedSentenceIds = new Set();
  const reviewed = reviewedSource.filter(question => {
    if (reviewedSentenceIds.has(question.sentence_id)) return false;
    reviewedSentenceIds.add(question.sentence_id);
    return true;
  }).slice(0, 20);
  const provisionalSource = shardPayloads.get(
    manifest.shards.find(shard => shard.tier === 'provisional').id
  ).questions;
  const provisionalSentenceIds = new Set(reviewed.map(question => question.sentence_id));
  const provisional = provisionalSource.filter(question => {
    if (provisionalSentenceIds.has(question.sentence_id)) return false;
    provisionalSentenceIds.add(question.sentence_id);
    return true;
  }).slice(0, 20);
  const mixedManifest = {
    round_size: 10,
    sampling_policy: { reviewed_core_share: 0.2 },
    shards: [
      { id: 'reviewed', mode: 'mixed', tier: 'reviewed-core', count: reviewed.length },
      { id: 'provisional', mode: 'mixed', tier: 'provisional', count: provisional.length }
    ]
  };
  const payloads = {
    reviewed: { questions: reviewed },
    provisional: { questions: provisional }
  };
  const reviewedIds = new Set(reviewed.map(question => question.id));
  let reviewedTotal = 0;
  const trials = 200;
  for (let index = 0; index < trials; index += 1) {
    const round = await bank.createRound({
      manifest: mixedManifest,
      modeId: 'mixed',
      fetchShard: async shard => payloads[shard.id],
      random: seededRandom(index + 1)
    });
    reviewedTotal += round.filter(question => reviewedIds.has(question.id)).length;
  }
  assert.ok(Math.abs(reviewedTotal / trials - 2) < 0.05);
});

test('a failed fetch is recoverable by retrying', async () => {
  const modeId = 'clauses';
  await assert.rejects(
    bank.createRound({
      manifest,
      modeId,
      fetchShard: async () => { throw new Error('offline'); },
      random: seededRandom(4)
    }),
    /offline/
  );
  const round = await bank.createRound({
    manifest,
    modeId,
    fetchShard: loadRealShard,
    random: seededRandom(4)
  });
  assert.equal(round.length, 10);
});
