(() => {
  'use strict';

  const roundEngine = window.SentenceSenseRound;
  const questionBank = window.SentenceSenseQuestionBank;
  if (!roundEngine || !questionBank) {
    document.body.innerHTML = '<p style="padding:2rem">The practice data could not be loaded.</p>';
    return;
  }

  const MANIFEST_URL = new URL('data/manifest.json', document.baseURI);
  const STORAGE_KEY = 'sentence-sense-detective:progress:v1';
  const RECENT_KEY_PREFIX = 'sentence-sense-detective:recent:v1:';
  const MAX_CACHED_SHARDS = 2;
  let manifest = null;
  let modes = [];
  let modeById = {};
  let roundSize = 10;
  let lastRequestedMode = null;
  let loadGeneration = 0;
  const shardCache = new Map();
  let goldCache = null;

  const $ = id => document.getElementById(id);
  const els = {
    home: $('home-view'),
    quiz: $('quiz-view'),
    summary: $('summary-view'),
    homeTitle: $('home-title'),
    brandHome: $('brand-home'),
    modeGrid: $('mode-grid'),
    homeLoadPanel: $('home-load-panel'),
    homeLoadTitle: $('home-load-title'),
    homeLoadMessage: $('home-load-message'),
    manifestRetry: $('manifest-retry'),
    progressCards: $('progress-cards'),
    resetProgress: $('reset-progress'),
    aboutButton: $('about-button'),
    aboutDialog: $('about-dialog'),
    exitRound: $('exit-round'),
    quizModeKicker: $('quiz-mode-kicker'),
    quizModeTitle: $('quiz-mode-title'),
    scoreValue: $('score-value'),
    streakValue: $('streak-value'),
    position: $('question-position'),
    subskill: $('subskill-label'),
    progressTrack: $('progress-track'),
    progressBar: $('progress-bar'),
    roundLoadPanel: $('round-load-panel'),
    roundLoadTitle: $('round-load-title'),
    roundLoadMessage: $('round-load-message'),
    roundRetry: $('round-retry'),
    roundLoadHome: $('round-load-home'),
    questionCard: $('question-card'),
    questionBadge: $('question-badge'),
    roundKind: $('round-kind'),
    sentence: $('sentence-text'),
    prompt: $('question-prompt'),
    options: $('answer-options'),
    showAnswer: $('show-answer'),
    next: $('next-question'),
    feedback: $('feedback-panel'),
    feedbackIcon: $('feedback-icon'),
    feedbackTitle: $('feedback-title'),
    feedbackMessage: $('feedback-message'),
    answerExplanation: $('answer-explanation'),
    correctAnswer: $('correct-answer'),
    explanation: $('explanation-text'),
    reportQuestion: $('report-question'),
    celebration: $('celebration'),
    summaryEmblem: $('summary-emblem'),
    summaryTitle: $('summary-title'),
    summaryCopy: $('summary-copy'),
    summaryScore: $('summary-score-value'),
    summaryPercent: $('summary-percent'),
    breakdown: $('breakdown-list'),
    mistakesSection: $('mistakes-section'),
    mistakesList: $('mistakes-list'),
    reviewMistakes: $('review-mistakes'),
    newRound: $('new-round'),
    summaryHome: $('summary-home'),
    aboutVersion: $('about-version')
  };

  const state = {
    modeId: null,
    roundQuestions: [],
    roundKind: 'new',
    index: 0,
    score: 0,
    streak: 0,
    roundBestStreak: 0,
    attempts: 0,
    finalized: false,
    results: [],
    optionOrder: []
  };

  function blankStats() {
    return Object.fromEntries(modes.map(mode => [mode.id, {
      attempted: 0,
      firstTryCorrect: 0,
      rounds: 0,
      bestStreak: 0
    }]));
  }

  function nonNegativeInteger(value) {
    const number = Number(value);
    return Number.isFinite(number) ? Math.max(0, Math.floor(number)) : 0;
  }

  function loadStats() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
      const base = blankStats();
      for (const mode of modes) {
        const saved = parsed[mode.id] || {};
        const attempted = nonNegativeInteger(saved.attempted);
        base[mode.id] = {
          attempted,
          firstTryCorrect: Math.min(attempted, nonNegativeInteger(saved.firstTryCorrect)),
          rounds: nonNegativeInteger(saved.rounds),
          bestStreak: nonNegativeInteger(saved.bestStreak)
        };
      }
      return base;
    } catch (_) {
      return blankStats();
    }
  }

  let stats = {};

  function saveStats() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(stats));
    } catch (_) {
      // The tool remains fully usable when browser storage is unavailable.
    }
  }

  function loadRecent(modeId) {
    try {
      const parsed = JSON.parse(localStorage.getItem(`${RECENT_KEY_PREFIX}${modeId}`) || '{}');
      return {
        questionIds: Array.isArray(parsed.questionIds)
          ? parsed.questionIds.filter(value => typeof value === 'string')
          : [],
        sentenceIds: Array.isArray(parsed.sentenceIds)
          ? parsed.sentenceIds.filter(value => typeof value === 'string')
          : []
      };
    } catch (_) {
      return { questionIds: [], sentenceIds: [] };
    }
  }

  function saveRecent(modeId, questions) {
    const existing = loadRecent(modeId);
    const policy = manifest?.sampling_policy || {};
    const recent = {
      questionIds: questionBank.appendRecent(
        existing.questionIds,
        questions.map(question => question.id),
        policy.recent_question_ids_per_mode ?? 250
      ),
      sentenceIds: questionBank.appendRecent(
        existing.sentenceIds,
        questions.map(question => question.sentence_id),
        policy.recent_sentence_ids_per_mode ?? 150
      )
    };
    try {
      localStorage.setItem(`${RECENT_KEY_PREFIX}${modeId}`, JSON.stringify(recent));
    } catch (_) {
      // Recent-item avoidance is best-effort when browser storage is unavailable.
    }
  }

  async function fetchJson(url) {
    const response = await fetch(url, { credentials: 'same-origin' });
    if (!response.ok) throw new Error(`Request failed with status ${response.status}.`);
    return response.json();
  }

  async function fetchShard(shard) {
    const key = shard.path;
    if (shardCache.has(key)) {
      const cached = shardCache.get(key);
      shardCache.delete(key);
      shardCache.set(key, cached);
      return cached;
    }
    const payload = await fetchJson(new URL(shard.path, MANIFEST_URL));
    if (
      payload?.mode !== shard.mode
      || !Array.isArray(payload?.questions)
      || payload.questions.length !== shard.count
    ) {
      throw new Error('A question set did not match its manifest entry.');
    }
    shardCache.set(key, payload);
    while (shardCache.size > MAX_CACHED_SHARDS) {
      shardCache.delete(shardCache.keys().next().value);
    }
    return payload;
  }

  async function fetchGold() {
    if (goldCache) return goldCache;
    const descriptor = manifest?.gold;
    if (!descriptor?.path) throw new Error('The reviewed question set is unavailable.');
    const payload = await fetchJson(new URL(descriptor.path, MANIFEST_URL));
    if (
      !Array.isArray(payload?.questions)
      || payload.questions.length !== descriptor.count
    ) {
      throw new Error('The reviewed question set did not match its manifest entry.');
    }
    goldCache = payload;
    return payload;
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function randomIndex(max) {
    if (max <= 1) return 0;
    if (window.crypto?.getRandomValues) {
      const bucket = new Uint32Array(1);
      window.crypto.getRandomValues(bucket);
      return bucket[0] % max;
    }
    return Math.floor(Math.random() * max);
  }

  function secureRandom() {
    if (!window.crypto?.getRandomValues) return Math.random();
    const bucket = new Uint32Array(1);
    window.crypto.getRandomValues(bucket);
    return bucket[0] / 0x100000000;
  }

  function shuffle(items) {
    const copy = [...items];
    for (let index = copy.length - 1; index > 0; index -= 1) {
      const swapIndex = randomIndex(index + 1);
      [copy[index], copy[swapIndex]] = [copy[swapIndex], copy[index]];
    }
    return copy;
  }

  function prefersReducedMotion() {
    return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true;
  }

  function scrollBehavior() {
    return prefersReducedMotion() ? 'auto' : 'smooth';
  }

  function focusWithoutScroll(element) {
    window.requestAnimationFrame(() => element?.focus({ preventScroll: true }));
  }

  function codePointBoundaries(value) {
    const boundaries = [0];
    let utf16Index = 0;
    for (const character of value) {
      utf16Index += character.length;
      boundaries.push(utf16Index);
    }
    return boundaries;
  }

  function highlightedSentence(sentence, targetSpans) {
    const boundaries = codePointBoundaries(sentence);
    const ranges = [];
    for (const span of targetSpans || []) {
      const start = Number(span.start);
      const end = Number(span.end);
      if (
        Number.isInteger(start)
        && Number.isInteger(end)
        && start >= 0
        && end > start
        && end < boundaries.length
      ) {
        ranges.push({ start: boundaries[start], end: boundaries[end] });
      }
    }
    ranges.sort((a, b) => a.start - b.start || b.end - a.end);

    const cleanRanges = [];
    for (const range of ranges) {
      if (!cleanRanges.length || range.start >= cleanRanges[cleanRanges.length - 1].end) {
        cleanRanges.push(range);
      }
    }

    if (!cleanRanges.length) return escapeHtml(sentence);
    let cursor = 0;
    let html = '';
    for (const range of cleanRanges) {
      html += escapeHtml(sentence.slice(cursor, range.start));
      html += `<mark class="target-mark">${escapeHtml(sentence.slice(range.start, range.end))}</mark>`;
      cursor = range.end;
    }
    html += escapeHtml(sentence.slice(cursor));
    return html;
  }

  function showView(name) {
    els.home.hidden = name !== 'home';
    els.quiz.hidden = name !== 'quiz';
    els.summary.hidden = name !== 'summary';
    window.scrollTo({ top: 0, behavior: scrollBehavior() });
  }

  function renderModeCards() {
    els.modeGrid.innerHTML = modes.map(mode => {
      const count = Number(manifest?.totals?.by_mode?.[mode.id] || 0);
      return `
        <article class="mode-card">
          <div class="mode-icon" aria-hidden="true">${escapeHtml(mode.icon)}</div>
          <h3>${escapeHtml(mode.title)}</h3>
          <p>${escapeHtml(mode.description)}</p>
          <div class="mode-card-footer">
            <span class="question-count">${count} questions available</span>
            <button class="start-button" type="button" data-mode="${escapeHtml(mode.id)}">Start</button>
          </div>
        </article>`;
    }).join('');

    els.modeGrid.querySelectorAll('[data-mode]').forEach(button => {
      button.addEventListener('click', () => loadModeRound(button.dataset.mode));
    });
  }

  function renderProgress() {
    els.progressCards.innerHTML = modes.map(mode => {
      const modeStats = stats[mode.id];
      const accuracy = modeStats.attempted
        ? Math.round((modeStats.firstTryCorrect / modeStats.attempted) * 100)
        : 0;
      const main = modeStats.attempted ? `${accuracy}%` : '—';
      const detail = modeStats.attempted
        ? `${modeStats.firstTryCorrect} of ${modeStats.attempted} correct first time`
        : 'No questions answered yet';
      return `
        <div class="progress-card">
          <span>${escapeHtml(mode.title)}</span>
          <strong>${main}</strong>
          <small>${escapeHtml(detail)} · ${modeStats.rounds} round${modeStats.rounds === 1 ? '' : 's'} · best streak ${modeStats.bestStreak}</small>
        </div>`;
    }).join('');
  }

  async function loadModeRound(modeId) {
    const mode = modeById[modeId];
    if (!mode) return;
    const generation = ++loadGeneration;
    lastRequestedMode = modeId;
    state.roundQuestions = [];
    els.quizModeKicker.textContent = 'Practice round';
    els.quizModeTitle.textContent = mode.title;
    els.roundLoadTitle.textContent = 'Loading your round…';
    els.roundLoadMessage.textContent = 'Selecting ten different sentences.';
    els.roundRetry.hidden = true;
    els.roundLoadPanel.hidden = false;
    els.questionCard.hidden = true;
    showView('quiz');
    focusWithoutScroll(els.roundLoadPanel);

    try {
      const selected = await questionBank.createRound({
        manifest,
        modeId,
        fetchShard,
        fetchGold,
        recent: loadRecent(modeId),
        random: secureRandom
      });
      if (generation !== loadGeneration) return;
      saveRecent(modeId, selected);
      beginRound(modeId, selected, 'new');
    } catch (error) {
      if (generation !== loadGeneration) return;
      els.roundLoadTitle.textContent = 'That round could not load.';
      els.roundLoadMessage.textContent = `${error.message || 'Please try again.'}`;
      els.roundRetry.hidden = false;
      focusWithoutScroll(els.roundRetry);
    }
  }

  function beginRound(modeId, suppliedQuestions, kind = 'new') {
    const mode = modeById[modeId];
    if (!mode || !Array.isArray(suppliedQuestions) || !suppliedQuestions.length) return;
    const bank = [...suppliedQuestions];

    state.modeId = modeId;
    state.roundKind = kind;
    state.roundQuestions = kind === 'review'
      ? shuffle(bank).slice(0, roundSize)
      : bank.slice(0, roundSize);
    state.index = 0;
    state.score = 0;
    state.streak = 0;
    state.roundBestStreak = 0;
    state.attempts = 0;
    state.finalized = false;
    state.results = [];
    state.optionOrder = [];

    els.quizModeKicker.textContent = kind === 'review' ? 'Review round' : 'Practice round';
    els.quizModeTitle.textContent = mode.title;
    els.roundKind.textContent = kind === 'review' ? 'Review mistakes' : 'New round';
    els.roundLoadPanel.hidden = true;
    els.questionCard.hidden = false;
    showView('quiz');
    renderQuestion();
  }

  function currentQuestion() {
    return state.roundQuestions[state.index] || null;
  }

  function renderQuestion() {
    const question = currentQuestion();
    if (!question) return;

    state.attempts = 0;
    state.finalized = false;
    state.optionOrder = shuffle(question.options);

    els.scoreValue.textContent = `${state.score}/${state.roundQuestions.length}`;
    els.streakValue.textContent = String(state.streak);
    els.position.textContent = `Question ${state.index + 1} of ${state.roundQuestions.length}`;
    els.subskill.textContent = question.subskill;
    const progress = state.index + 1;
    els.progressTrack.setAttribute('aria-valuemax', String(state.roundQuestions.length));
    els.progressTrack.setAttribute('aria-valuenow', String(progress));
    els.progressBar.style.width = `${(progress / state.roundQuestions.length) * 100}%`;
    els.questionBadge.textContent = question.subskill;
    els.sentence.innerHTML = highlightedSentence(question.sentence, question.target_spans);
    els.prompt.textContent = question.prompt;
    els.options.innerHTML = state.optionOrder.map((option, index) => `
      <button class="answer-option" type="button" data-answer="${escapeHtml(option)}" id="option-${index}">
        ${escapeHtml(option)}
      </button>`).join('');

    els.options.querySelectorAll('.answer-option').forEach(button => {
      button.addEventListener('click', () => answerQuestion(button.dataset.answer, button));
    });

    els.feedback.hidden = true;
    els.feedback.className = 'feedback-panel';
    els.answerExplanation.hidden = true;
    els.reportQuestion.hidden = true;
    els.showAnswer.hidden = false;
    els.showAnswer.disabled = false;
    els.next.hidden = true;
    els.next.textContent = state.index === state.roundQuestions.length - 1 ? 'See results' : 'Next question';
    focusWithoutScroll(els.questionCard);
  }

  function updateScoreStrip() {
    els.scoreValue.textContent = `${state.score}/${state.roundQuestions.length}`;
    els.streakValue.textContent = String(state.streak);
  }

  function optionButtons() {
    return [...els.options.querySelectorAll('.answer-option')];
  }

  function markCorrectAnswer(question) {
    for (const button of optionButtons()) {
      if (button.dataset.answer === question.answer) button.classList.add('is-correct');
    }
  }

  function disableAllOptions() {
    optionButtons().forEach(button => { button.disabled = true; });
  }

  function showFinalFeedback(question, type, title, message) {
    els.feedback.hidden = false;
    els.feedback.className = `feedback-panel ${type}`;
    els.feedbackIcon.textContent = type === 'correct' ? '✓' : '→';
    els.feedbackTitle.textContent = title;
    els.feedbackMessage.textContent = message;
    els.correctAnswer.textContent = question.answer;
    els.explanation.textContent = question.explanation;
    els.answerExplanation.hidden = false;
    configureReportLink(question);
    els.showAnswer.hidden = true;
    els.next.hidden = false;
    els.next.focus({ preventScroll: true });
  }

  function configureReportLink(question) {
    const configuredUrl = manifest?.report_issue_url;
    els.reportQuestion.hidden = true;
    if (!configuredUrl) return;
    try {
      const issueUrl = new URL(configuredUrl);
      const highlightedTarget = (question.target_spans || [])
        .map(span => [...question.sentence].slice(span.start, span.end).join(''))
        .join(' … ');
      issueUrl.searchParams.set('title', `Question correction: ${question.id}`);
      issueUrl.searchParams.set(
        'body',
        [
          `Question ID: ${question.id}`,
          `Mode: ${question.mode}`,
          `Sentence: ${question.sentence}`,
          `Highlighted target: ${highlightedTarget}`,
          `Displayed answer: ${question.answer}`,
          `App version: ${manifest?.version || 'unknown'}`,
          '',
          'Report:',
          ''
        ].join('\n')
      );
      els.reportQuestion.href = issueUrl.toString();
      els.reportQuestion.hidden = false;
    } catch (_) {
      // Invalid or absent issue URLs are deliberately ignored in local forks.
    }
  }

  function showRetryFeedback() {
    els.feedback.hidden = false;
    els.feedback.className = 'feedback-panel wrong';
    els.feedbackIcon.textContent = '↺';
    els.feedbackTitle.textContent = 'Not quite — one more try.';
    els.feedbackMessage.textContent = 'Take another look at the highlighted target. Your retry is for learning, so the point is no longer available.';
    els.answerExplanation.hidden = true;
  }

  function recordResult(question, firstTryCorrect, outcome, selectedAnswer) {
    if (!state.finalized || state.results.length > state.index) return;
    state.results.push({
      question,
      firstTryCorrect,
      outcome,
      selectedAnswer
    });

    const modeStats = stats[state.modeId];
    modeStats.attempted += 1;
    if (firstTryCorrect) modeStats.firstTryCorrect += 1;
    modeStats.bestStreak = Math.max(modeStats.bestStreak, state.roundBestStreak);
    saveStats();
  }

  function answerQuestion(selected, button) {
    const question = currentQuestion();
    if (!question || state.finalized || button.disabled) return;

    const transition = roundEngine.answer({
      attempts: state.attempts,
      finalized: state.finalized,
      score: state.score,
      streak: state.streak,
      bestStreak: state.roundBestStreak
    }, selected, question.answer);
    if (!transition.accepted) return;

    state.attempts = transition.attempts;
    state.finalized = transition.finalized;
    state.score = transition.score;
    state.streak = transition.streak;
    state.roundBestStreak = transition.bestStreak;

    if (transition.correct) {
      button.classList.add('is-correct');
      markCorrectAnswer(question);
      disableAllOptions();

      if (transition.firstTryCorrect) {
        recordResult(question, true, 'first-try-correct', selected);
        showFinalFeedback(question, 'correct', 'Correct!', 'One point — and your streak is still alive.');
        celebrate();
      } else {
        recordResult(question, false, 'retry-correct', selected);
        showFinalFeedback(question, 'correct', 'That’s it.', 'No point this time, but the second look did its job.');
      }
      updateScoreStrip();
      return;
    }

    button.classList.add('is-wrong');
    button.disabled = true;
    updateScoreStrip();

    if (transition.outcome === 'retry-available') {
      showRetryFeedback();
      focusWithoutScroll(optionButtons().find(option => !option.disabled));
      return;
    }

    markCorrectAnswer(question);
    disableAllOptions();
    recordResult(question, false, 'second-try-wrong', selected);
    showFinalFeedback(question, 'wrong', 'Here’s the answer.', 'This one will return in your review list.');
  }

  function revealAnswer() {
    const question = currentQuestion();
    if (!question || state.finalized) return;
    const transition = roundEngine.reveal({
      attempts: state.attempts,
      finalized: state.finalized,
      score: state.score,
      streak: state.streak,
      bestStreak: state.roundBestStreak
    });
    if (!transition.accepted) return;
    state.finalized = transition.finalized;
    state.streak = transition.streak;
    updateScoreStrip();
    markCorrectAnswer(question);
    disableAllOptions();
    recordResult(question, false, 'revealed', null);
    showFinalFeedback(question, 'wrong', 'Answer shown.', 'No point is awarded after revealing the answer.');
  }

  function celebrate() {
    if (prefersReducedMotion()) return;
    const symbols = ['✦', '•', '★', '✧', '●', '✦'];
    els.celebration.innerHTML = '';
    for (let index = 0; index < 10; index += 1) {
      const spark = document.createElement('span');
      spark.className = 'spark';
      spark.textContent = symbols[index % symbols.length];
      spark.style.left = `${12 + randomIndex(76)}%`;
      spark.style.top = `${42 + randomIndex(38)}%`;
      spark.style.animationDelay = `${index * 35}ms`;
      els.celebration.appendChild(spark);
    }
    window.setTimeout(() => { els.celebration.innerHTML = ''; }, 1100);
  }

  function nextQuestion() {
    if (!state.finalized) return;
    if (state.index < state.roundQuestions.length - 1) {
      state.index += 1;
      renderQuestion();
      els.questionCard.scrollIntoView({ behavior: scrollBehavior(), block: 'start' });
      return;
    }
    finishRound();
  }

  function finishRound() {
    stats[state.modeId].rounds += 1;
    stats[state.modeId].bestStreak = Math.max(stats[state.modeId].bestStreak, state.roundBestStreak);
    saveStats();
    renderProgress();
    renderSummary();
    showView('summary');
    focusWithoutScroll(els.summaryTitle);
  }

  function renderSummary() {
    const total = state.results.length;
    const percent = total ? Math.round((state.score / total) * 100) : 0;
    const mistakes = state.results.filter(result => !result.firstTryCorrect);

    if (state.score === total) {
      els.summaryTitle.textContent = 'Perfect round.';
      els.summaryCopy.textContent = 'Every answer was right on the first try. That is sentence sense doing its thing.';
      els.summaryEmblem.textContent = '✦';
    } else if (percent >= 80) {
      els.summaryTitle.textContent = 'Strong round.';
      els.summaryCopy.textContent = 'Most answers landed immediately, and the rest are ready for a quick review.';
      els.summaryEmblem.textContent = '★';
    } else if (percent >= 60) {
      els.summaryTitle.textContent = 'Good work.';
      els.summaryCopy.textContent = 'You have a solid base. Review the missed items while the examples are still fresh.';
      els.summaryEmblem.textContent = '✓';
    } else {
      els.summaryTitle.textContent = 'Useful practice.';
      els.summaryCopy.textContent = 'This round found exactly what deserves another look. That is what practice is for.';
      els.summaryEmblem.textContent = '↺';
    }

    els.summaryScore.textContent = `${state.score}/${total}`;
    els.summaryPercent.textContent = `${percent}% first-try accuracy`;

    const breakdown = {};
    for (const result of state.results) {
      const key = result.question.subskill;
      breakdown[key] ||= { correct: 0, total: 0 };
      breakdown[key].total += 1;
      if (result.firstTryCorrect) breakdown[key].correct += 1;
    }
    els.breakdown.innerHTML = Object.entries(breakdown).map(([label, values]) => `
      <div class="breakdown-row">
        <span>${escapeHtml(label)}</span>
        <strong>${values.correct}/${values.total}</strong>
      </div>`).join('');

    els.mistakesSection.hidden = mistakes.length === 0;
    els.reviewMistakes.hidden = mistakes.length === 0;
    els.mistakesList.innerHTML = mistakes.map(result => `
      <article class="mistake-item">
        <p class="mistake-sentence">${highlightedSentence(result.question.sentence, result.question.target_spans)}</p>
        <p><strong>${escapeHtml(result.question.answer)}</strong></p>
        <p>${escapeHtml(result.question.explanation)}</p>
      </article>`).join('');
  }

  function reviewMistakes() {
    const missedQuestions = state.results
      .filter(result => !result.firstTryCorrect)
      .map(result => result.question);
    if (missedQuestions.length) beginRound(state.modeId, missedQuestions, 'review');
  }

  function leaveRound() {
    const unfinished = state.roundQuestions.length && state.results.length < state.roundQuestions.length;
    if (unfinished && !window.confirm('Leave this round? Your completed questions are saved, but this round will not appear as finished.')) return;
    loadGeneration += 1;
    els.roundLoadPanel.hidden = true;
    els.questionCard.hidden = true;
    showView('home');
    renderProgress();
    focusWithoutScroll(els.homeTitle);
  }

  function resetProgress() {
    if (!window.confirm('Reset all saved Sentence Sense Detective progress on this device?')) return;
    stats = blankStats();
    try {
      localStorage.removeItem(STORAGE_KEY);
      for (const mode of modes) localStorage.removeItem(`${RECENT_KEY_PREFIX}${mode.id}`);
    } catch (_) {}
    renderProgress();
  }

  els.showAnswer.addEventListener('click', revealAnswer);
  els.next.addEventListener('click', nextQuestion);
  els.reviewMistakes.addEventListener('click', reviewMistakes);
  els.newRound.addEventListener('click', () => loadModeRound(state.modeId));
  els.summaryHome.addEventListener('click', () => {
    showView('home');
    renderProgress();
    focusWithoutScroll(els.homeTitle);
  });
  els.exitRound.addEventListener('click', leaveRound);
  els.brandHome.addEventListener('click', event => { event.preventDefault(); leaveRound(); });
  els.resetProgress.addEventListener('click', resetProgress);
  els.aboutButton.addEventListener('click', () => els.aboutDialog.showModal());
  els.roundRetry.addEventListener('click', () => loadModeRound(lastRequestedMode));
  els.roundLoadHome.addEventListener('click', leaveRound);
  els.manifestRetry.addEventListener('click', loadManifest);

  document.addEventListener('keydown', event => {
    if (
      els.quiz.hidden
      || state.finalized
      || els.aboutDialog.open
      || event.altKey
      || event.ctrlKey
      || event.metaKey
    ) return;
    const number = Number(event.key);
    if (number >= 1 && number <= 4) {
      const button = optionButtons()[number - 1];
      if (button && !button.disabled) button.click();
    }
  });

  showView('home');
  loadManifest();

  async function loadManifest() {
    els.manifestRetry.hidden = true;
    els.homeLoadPanel.hidden = false;
    els.homeLoadTitle.textContent = 'Loading practice…';
    els.homeLoadMessage.textContent = 'Checking which question sets are available.';
    try {
      const loaded = await fetchJson(MANIFEST_URL);
      if (
        !Array.isArray(loaded?.modes)
        || !Array.isArray(loaded?.shards)
        || !loaded?.totals?.by_mode
      ) {
        throw new Error('The question manifest is not valid.');
      }
      manifest = loaded;
      goldCache = null;
      modes = loaded.modes;
      modeById = Object.fromEntries(modes.map(mode => [mode.id, mode]));
      roundSize = Math.max(1, Number(loaded.round_size) || 10);
      stats = loadStats();
      els.aboutVersion.textContent = loaded.version || '';
      renderModeCards();
      renderProgress();
      els.homeLoadPanel.hidden = true;
    } catch (error) {
      els.modeGrid.innerHTML = '';
      els.progressCards.innerHTML = '';
      els.homeLoadTitle.textContent = 'Practice could not load.';
      els.homeLoadMessage.textContent = error.message || 'Please try again.';
      els.manifestRetry.hidden = false;
      focusWithoutScroll(els.manifestRetry);
    }
  }
})();
