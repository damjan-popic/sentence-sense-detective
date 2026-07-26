(function exposeRoundState(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  } else {
    root.SentenceSenseRound = api;
  }
}(typeof globalThis !== 'undefined' ? globalThis : this, () => {
  'use strict';

  function answer(snapshot, selected, correctAnswer) {
    if (snapshot.finalized) return { ...snapshot, accepted: false };

    const attempts = snapshot.attempts + 1;
    const correct = selected === correctAnswer;
    const next = { ...snapshot, attempts, accepted: true, correct };

    if (correct && attempts === 1) {
      const streak = snapshot.streak + 1;
      return {
        ...next,
        score: snapshot.score + 1,
        streak,
        bestStreak: Math.max(snapshot.bestStreak, streak),
        finalized: true,
        firstTryCorrect: true,
        outcome: 'first-try-correct'
      };
    }

    if (correct) {
      return {
        ...next,
        finalized: true,
        firstTryCorrect: false,
        outcome: 'retry-correct'
      };
    }

    next.streak = 0;
    if (attempts === 1) {
      return {
        ...next,
        finalized: false,
        firstTryCorrect: false,
        outcome: 'retry-available'
      };
    }

    return {
      ...next,
      finalized: true,
      firstTryCorrect: false,
      outcome: 'second-try-wrong'
    };
  }

  function reveal(snapshot) {
    if (snapshot.finalized) return { ...snapshot, accepted: false };
    return {
      ...snapshot,
      accepted: true,
      streak: 0,
      finalized: true,
      firstTryCorrect: false,
      outcome: 'revealed'
    };
  }

  return { answer, reveal };
}));
