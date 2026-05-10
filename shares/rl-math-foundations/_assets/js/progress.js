/* RL Math Foundations — progress tracking via localStorage. */

(function (global) {
  'use strict';

  const KEY = 'rl-math-foundations:progress:v1';

  function read() {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return defaultState();
      const parsed = JSON.parse(raw);
      if (parsed.version !== 1) return defaultState();
      return parsed;
    } catch (_) {
      return defaultState();
    }
  }

  function defaultState() {
    return {
      completed: [],
      lastVisited: null,
      lastVisitedAt: null,
      estimatedMinutes: {},
      version: 1,
    };
  }

  function write(state) {
    try {
      localStorage.setItem(KEY, JSON.stringify(state));
    } catch (e) {
      console.warn('progress: localStorage write failed', e);
    }
  }

  function markComplete(lessonId, estMinutes) {
    const s = read();
    if (!s.completed.includes(lessonId)) s.completed.push(lessonId);
    s.estimatedMinutes[lessonId] = estMinutes;
    s.lastVisited = lessonId;
    s.lastVisitedAt = new Date().toISOString();
    write(s);
  }

  function isComplete(lessonId) {
    return read().completed.includes(lessonId);
  }

  function stats() {
    const s = read();
    const totalMinutes = Object.values(s.estimatedMinutes).reduce((a, b) => a + b, 0);
    return {
      totalCompleted: s.completed.length,
      totalMinutes,
      lastVisited: s.lastVisited,
      lastVisitedAt: s.lastVisitedAt,
    };
  }

  function nextLessonId(orderedIds) {
    for (const id of orderedIds) {
      if (!isComplete(id)) return id;
    }
    return null;
  }

  function reset() {
    try {
      localStorage.removeItem(KEY);
    } catch (_) {}
  }

  global.Progress = { read, markComplete, isComplete, stats, nextLessonId, reset };
})(window);
