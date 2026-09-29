/*
 * Study-time tracking.
 *
 * The database stores mastery but no timestamps, so study time is measured
 * here: while a learner is on a diagnostic or practice page, the tab is
 * visible, and they have interacted in the last 90 seconds, each second
 * counts. Totals are kept per learner and per ISO week in localStorage, which
 * means the figure is for this device (the dashboard says so).
 */
import { useEffect } from 'react';

const IDLE_MS = 90_000;
const TICK_MS = 5_000;
const key = (userId) => `atlas-study-time:${userId}`;

/** ISO-8601 week key, e.g. "2026-W40". */
export function isoWeekKey(date = new Date()) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const day = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const week = Math.ceil(((d - yearStart) / 86_400_000 + 1) / 7);
  return `${d.getUTCFullYear()}-W${String(week).padStart(2, '0')}`;
}

function read(userId) {
  try {
    return JSON.parse(localStorage.getItem(key(userId)) || '{}');
  } catch {
    return {};
  }
}

function add(userId, seconds) {
  const data = read(userId);
  const wk = isoWeekKey();
  data[wk] = (data[wk] || 0) + seconds;
  // keep the last 12 weeks only
  const keep = Object.keys(data).sort().slice(-12);
  const trimmed = Object.fromEntries(keep.map((k) => [k, data[k]]));
  try {
    localStorage.setItem(key(userId), JSON.stringify(trimmed));
  } catch {
    /* storage full or blocked: tracking is best-effort */
  }
}

/** Seconds studied this week on this device. */
export function getWeeklyStudySeconds(userId) {
  if (!userId) return 0;
  return read(userId)[isoWeekKey()] || 0;
}

/** Human form: "45 min", "1 h 20 min", or in Bangla digits when lang is bn. */
export function formatStudyTime(seconds, lang = 'en') {
  const mins = Math.round(seconds / 60);
  const fmt = (n) => n.toLocaleString(lang === 'bn' ? 'bn-BD' : 'en-US');
  const [h, m, min] = lang === 'bn' ? ['ঘ', 'মি', 'মিনিট'] : ['h', 'min', 'min'];
  if (mins < 60) return `${fmt(mins)} ${min}`;
  const hours = Math.floor(mins / 60);
  const rest = mins % 60;
  return rest ? `${fmt(hours)} ${h} ${fmt(rest)} ${m}` : `${fmt(hours)} ${h}`;
}

/** Count active time while the calling page is mounted. */
export function useStudyTimer(userId) {
  useEffect(() => {
    if (!userId) return undefined;
    let lastInput = Date.now();
    let lastTick = Date.now();
    const onInput = () => {
      lastInput = Date.now();
    };
    const events = ['pointerdown', 'keydown', 'wheel', 'touchstart', 'pointermove'];
    events.forEach((e) => window.addEventListener(e, onInput, { passive: true }));

    // Visibility during the interval that just ended, not at the moment of flushing:
    // the flush fired by the tab becoming hidden still counts the visible time before it.
    let visible = !document.hidden;
    const flush = () => {
      const now = Date.now();
      const active = visible && now - lastInput < IDLE_MS;
      const elapsed = Math.min(now - lastTick, TICK_MS * 2);
      lastTick = now;
      if (active && elapsed > 0) add(userId, elapsed / 1000);
    };
    const id = window.setInterval(flush, TICK_MS);
    const onHide = () => {
      flush();
      visible = !document.hidden;
    };
    document.addEventListener('visibilitychange', onHide);

    return () => {
      flush();
      window.clearInterval(id);
      document.removeEventListener('visibilitychange', onHide);
      events.forEach((e) => window.removeEventListener(e, onInput));
    };
  }, [userId]);
}
