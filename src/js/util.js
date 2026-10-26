/* ===== util.js — DOM helpers, Arabic normalisation, storage ===== */
"use strict";
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const SVGNS = "http://www.w3.org/2000/svg";

function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "html") el.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
    else if (k === "dataset") Object.assign(el.dataset, v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return el;
}
/** Null-safe append (native Element.append turns null into the text "null"). */
function appendKids(parent, ...kids) { for (const k of kids.flat()) if (k !== null && k !== undefined && k !== false) parent.append(k); return parent; }
function s(tag, attrs = {}) {
  const el = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v !== null && v !== undefined) el.setAttribute(k, v);
  return el;
}
const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
function debounce(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }
const AR_DIGITS = "٠١٢٣٤٥٦٧٨٩";
const toArabicDigits = (n) => String(n).replace(/[0-9]/g, (d) => AR_DIGITS[d]);
const prefersReducedMotion = () => window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- Arabic search normalisation ----------
   Mirrors tools/build_content.py:normalize().  Display text is never altered;
   normalisation only feeds the search index.  normalizeMap() also returns, for
   every normalised character, the index of the original character so matches
   can be highlighted in the original spelling. */
const TASHKEEL_RE = /[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]/;
const PUNCT_RE = /[\-–—_/\\.,:؛،()«»"'…]/;
function normChar(c) {
  if (TASHKEEL_RE.test(c) || c === "\u0640") return "";
  if ("أإآٱ".includes(c)) return "ا";
  if (c === "ى") return "ي";
  if (c === "ة") return "ه";
  if (c === "ؤ") return "و";
  if (c === "ئ") return "ي";
  let i = AR_DIGITS.indexOf(c); if (i >= 0) return String(i);
  i = "۰۱۲۳۴۵۶۷۸۹".indexOf(c); if (i >= 0) return String(i);
  if (PUNCT_RE.test(c) || /\s/.test(c)) return " ";
  return c.toLowerCase();
}
function normalizeMap(str) {
  let out = ""; const map = [];
  for (let i = 0; i < str.length; i++) {
    const n = normChar(str[i]);
    if (!n) continue;
    if (n === " " && (out.length === 0 || out.endsWith(" "))) continue;
    out += n; map.push(i);
  }
  if (out.endsWith(" ")) { out = out.slice(0, -1); map.pop(); }
  return { norm: out, map };
}
const normalize = (str) => normalizeMap(String(str || "")).norm;

/** Highlight occurrences of normalised query q inside original text. */
function highlight(text, q) {
  if (!q) return esc(text);
  const { norm, map } = normalizeMap(text);
  const idx = norm.indexOf(q);
  if (idx < 0) return esc(text);
  const start = map[idx];
  const endNorm = idx + q.length - 1;
  let end = map[endNorm] + 1;
  // extend over trailing combining marks (tashkeel) belonging to the last letter
  while (end < text.length && (TASHKEEL_RE.test(text[end]) || text[end] === "\u0640")) end++;
  return esc(text.slice(0, start)) + "<mark>" + esc(text.slice(start, end)) + "</mark>" + esc(text.slice(end));
}

/* ---------- storage (fails gracefully) ---------- */
const Store = {
  prefix: "islamic-atlas.v1.",
  ok: (() => { try { const k = "__t"; localStorage.setItem(k, "1"); localStorage.removeItem(k); return true; } catch (e) { return false; } })(),
  get(key, fallback) {
    if (!this.ok) return fallback;
    try { const v = localStorage.getItem(this.prefix + key); return v === null ? fallback : JSON.parse(v); } catch (e) { return fallback; }
  },
  set(key, value) {
    if (!this.ok) return false;
    try { localStorage.setItem(this.prefix + key, JSON.stringify(value)); return true; } catch (e) { return false; }
  },
  clearAll() {
    if (!this.ok) return 0;
    let n = 0;
    for (const k of Object.keys(localStorage)) if (k.startsWith(this.prefix)) { localStorage.removeItem(k); n++; }
    return n;
  },
};

let toastTimer;
function toast(msg, ms = 2400) {
  const t = $("#toast"); if (!t) return;
  t.textContent = msg; t.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, ms);
}
