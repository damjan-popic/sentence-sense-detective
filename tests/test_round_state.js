'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const round = require('../docs/assets/round-state.js');

function fresh(overrides = {}) {
  return {
    attempts: 0,
    finalized: false,
    score: 0,
    streak: 0,
    bestStreak: 0,
    ...overrides
  };
}

test('a first-try correct answer earns one point and extends the streak', () => {
  const result = round.answer(fresh({ score: 3, streak: 2, bestStreak: 2 }), 'S', 'S');
  assert.equal(result.score, 4);
  assert.equal(result.streak, 3);
  assert.equal(result.bestStreak, 3);
  assert.equal(result.outcome, 'first-try-correct');
  assert.equal(result.firstTryCorrect, true);
  assert.equal(result.finalized, true);
});

test('a wrong answer opens one retry, resets the streak, and awards no point', () => {
  const result = round.answer(fresh({ score: 3, streak: 2, bestStreak: 4 }), 'DO', 'S');
  assert.equal(result.score, 3);
  assert.equal(result.streak, 0);
  assert.equal(result.bestStreak, 4);
  assert.equal(result.outcome, 'retry-available');
  assert.equal(result.finalized, false);
});

test('a correct retry finalizes the question without awarding a point', () => {
  const first = round.answer(fresh({ score: 3, streak: 2 }), 'DO', 'S');
  const result = round.answer(first, 'S', 'S');
  assert.equal(result.score, 3);
  assert.equal(result.streak, 0);
  assert.equal(result.outcome, 'retry-correct');
  assert.equal(result.firstTryCorrect, false);
  assert.equal(result.finalized, true);
});

test('a second wrong answer finalizes the question without a negative point', () => {
  const first = round.answer(fresh({ score: 3, streak: 2 }), 'DO', 'S');
  const result = round.answer(first, 'A', 'S');
  assert.equal(result.score, 3);
  assert.equal(result.streak, 0);
  assert.equal(result.outcome, 'second-try-wrong');
  assert.equal(result.finalized, true);
});

test('revealing an answer awards no point and resets the streak', () => {
  const result = round.reveal(fresh({ score: 3, streak: 2, bestStreak: 4 }));
  assert.equal(result.score, 3);
  assert.equal(result.streak, 0);
  assert.equal(result.bestStreak, 4);
  assert.equal(result.outcome, 'revealed');
  assert.equal(result.finalized, true);
});

test('a finalized question rejects additional answers and reveals', () => {
  const finalized = round.answer(fresh(), 'S', 'S');
  assert.equal(round.answer(finalized, 'S', 'S').accepted, false);
  assert.equal(round.reveal(finalized).accepted, false);
});
