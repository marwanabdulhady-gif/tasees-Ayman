/* ===== panzoom.js — smooth pan/zoom for large vector SVG =====
   During a gesture we only change a CSS transform (cheap, GPU-composited);
   ~140 ms after the gesture settles we commit the new viewBox so the vector
   map is re-rendered crisply at the new scale. */
"use strict";
class PanZoom {
  constructor(host, svg, opts) {
    this.host = host; this.svg = svg;
    this.o = Object.assign({ content: [0, 0, 100, 100], minWidth: 24, onChange: null, onCommit: null, onTap: null, onHover: null, readout: null }, opts);
    this.W = host.clientWidth || 800; this.H = host.clientHeight || 600;
    this.view = null; this.committed = null; this.pointers = new Map();
    this._commitTimer = null; this._anim = null; this.silent = false;
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    this._bind();
    this.fit(false);
    this.ro = new ResizeObserver(() => this._resize());
    this.ro.observe(host);
  }
  destroy() { this.ro.disconnect(); this._unbind(); cancelAnimationFrame(this._anim); clearTimeout(this._commitTimer); clearTimeout(this._animDeadline); }

  /* ---- geometry ---- */
  get fitWidth() {
    const [, , cw, ch] = this.o.content;
    return Math.max(cw, ch * (this.W / this.H)) * 1.02;
  }
  _clamp(v) {
    const [cx0, cy0, cw, ch] = this.o.content;
    const w = Math.min(Math.max(v.w, this.o.minWidth), this.fitWidth * 1.8);
    // keep the view centre over the map so it can never be "lost" off-screen
    const cx = Math.min(Math.max(v.cx, cx0), cx0 + cw);
    const cy = Math.min(Math.max(v.cy, cy0), cy0 + ch);
    return { cx, cy, w };
  }
  _box(v) { const h = v.w * this.H / this.W; return [v.cx - v.w / 2, v.cy - h / 2, v.w, h]; }
  screenToUser(px, py, v = this.view) { const [x, y, w] = this._box(v); const s = this.W / w; return [x + px / s, y + py / s]; }
  userToScreen(ux, uy, v = this.view) { const [x, y, w] = this._box(v); const s = this.W / w; return [(ux - x) * s, (uy - y) * s]; }
  get zoomPercent() { return Math.round(this.fitWidth / this.view.w * 100); }

  /* ---- rendering ---- */
  _apply() {
    if (!this.committed) { this._commit(); return; }
    const [x0, y0, w0] = this._box(this.committed);
    const [x1, y1, w1] = this._box(this.view);
    const s0 = this.W / w0, s1 = this.W / w1, k = s1 / s0;
    this.svg.style.transform = `translate(${(x0 - x1) * s1}px, ${(y0 - y1) * s1}px) scale(${k})`;
    clearTimeout(this._commitTimer);
    this._commitTimer = setTimeout(() => this._commit(), 140);
    this._emit();
  }
  _commit() {
    clearTimeout(this._commitTimer);
    const b = this._box(this.view);
    this.svg.setAttribute("viewBox", b.map((n) => n.toFixed(3)).join(" "));
    this.svg.style.transform = "";
    this.committed = Object.assign({}, this.view);
    this._emit();
    if (this.o.onCommit) this.o.onCommit(this.view);
  }
  _emit() {
    if (this.o.readout) this.o.readout.textContent = `تكبير ${toArabicDigits(this.zoomPercent)}٪`;
    if (this.o.onChange && !this.silent) this.o.onChange(this.view, this);
  }
  setView(v, { animate = false, silent = false, commit = false } = {}) {
    const target = this._clamp(v);
    cancelAnimationFrame(this._anim); this._anim = null; clearTimeout(this._animDeadline);
    if (!animate || prefersReducedMotion() || !this.view) {
      this.silent = silent; this.view = target; commit ? this._commit() : this._apply(); this.silent = false; return;
    }
    const from = Object.assign({}, this.view), t0 = performance.now(), D = 360;
    const ease = (t) => 1 - Math.pow(1 - t, 3);
    const finish = () => {
      cancelAnimationFrame(this._anim); this._anim = null; clearTimeout(this._animDeadline);
      this.silent = silent; this.view = target; this._commit(); this.silent = false;
    };
    const step = () => {
      // use performance.now() (not the rAF timestamp, which can precede t0)
      const t = Math.min(1, Math.max(0, (performance.now() - t0) / D)), e = ease(t);
      if (t >= 1) { finish(); return; }
      // interpolate width in log-space so the zoom feels uniform
      const w = Math.exp(Math.log(from.w) + (Math.log(target.w) - Math.log(from.w)) * e);
      this.silent = silent;
      this.view = { cx: from.cx + (target.cx - from.cx) * e, cy: from.cy + (target.cy - from.cy) * e, w };
      this._apply(); this.silent = false;
      this._anim = requestAnimationFrame(step);
    };
    // Deadline guard: browsers may throttle requestAnimationFrame (background tabs,
    // headless, power saving).  The animation must still land exactly on target.
    this._animDeadline = setTimeout(finish, D + 80);
    this._anim = requestAnimationFrame(step);
  }
  fit(animate = true) {
    const [x, y, w, h] = this.o.content;
    this.setView({ cx: x + w / 2, cy: y + h / 2, w: this.fitWidth }, { animate, commit: !animate });
  }
  zoomBy(f, px = this.W / 2, py = this.H / 2, animate = false) {
    const [ux, uy] = this.screenToUser(px, py);
    const w = this.view.w / f;
    const cw = this._clamp({ cx: 0, cy: 0, w }).w; const ff = this.view.w / cw;
    const cx = ux - (ux - this.view.cx) / ff, cy = uy - (uy - this.view.cy) / ff;
    this.setView({ cx, cy, w: cw }, { animate });
  }
  panBy(dx, dy) { const s = this.W / this.view.w; this.setView({ cx: this.view.cx - dx / s, cy: this.view.cy - dy / s, w: this.view.w }); }
  zoomToRect(r, { pad = 0.35, minW = 60, animate = true } = {}) {
    const [x0, y0, x1, y1] = r;
    const rw = Math.max(x1 - x0, 1), rh = Math.max(y1 - y0, 1);
    let w = Math.max(rw * (1 + pad * 2), rh * (1 + pad * 2) * this.W / this.H, minW);
    this.setView({ cx: (x0 + x1) / 2, cy: (y0 + y1) / 2, w }, { animate });
  }
  setContent(box) { this.o.content = box; }
  _resize() {
    const W = this.host.clientWidth, H = this.host.clientHeight;
    if (!W || !H || (W === this.W && H === this.H)) return;
    const keep = this.view && this.committed;
    this.W = W; this.H = H;
    if (keep) this.setView(this.view, { commit: true }); else this.fit(false);
  }

  /* ---- input ---- */
  _bind() {
    const host = this.host;
    this._h = {
      wheel: (e) => {
        e.preventDefault();
        const r = host.getBoundingClientRect();
        let dy = e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 400 : 1);
        const f = Math.exp(-dy * (e.ctrlKey ? 0.012 : 0.0022));
        this.zoomBy(f, e.clientX - r.left, e.clientY - r.top);
      },
      down: (e) => {
        if (e.button !== undefined && e.button > 0) return;
        host.setPointerCapture && host.setPointerCapture(e.pointerId);
        const r = host.getBoundingClientRect();
        this.pointers.set(e.pointerId, { x: e.clientX - r.left, y: e.clientY - r.top });
        if (this.pointers.size === 1) {
          this._down = { x: e.clientX, y: e.clientY, t: performance.now(), target: e.target, moved: false };
          this._last = { x: e.clientX, y: e.clientY };
        } else if (this.pointers.size === 2) {
          const [a, b] = [...this.pointers.values()];
          this._pinch = { d: Math.hypot(a.x - b.x, a.y - b.y), mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2 };
          if (this._down) this._down.moved = true;
        }
      },
      move: (e) => {
        const r = host.getBoundingClientRect();
        if (!this.pointers.has(e.pointerId)) { if (this.o.onHover) this.o.onHover(e); return; }
        this.pointers.set(e.pointerId, { x: e.clientX - r.left, y: e.clientY - r.top });
        if (this.pointers.size === 1 && this._last) {
          const dx = e.clientX - this._last.x, dy = e.clientY - this._last.y;
          if (this._down && Math.hypot(e.clientX - this._down.x, e.clientY - this._down.y) > 5) { this._down.moved = true; host.classList.add("dragging"); }
          if (this._down && this._down.moved) this.panBy(dx, dy);
          this._last = { x: e.clientX, y: e.clientY };
        } else if (this.pointers.size === 2 && this._pinch) {
          const [a, b] = [...this.pointers.values()];
          const d = Math.hypot(a.x - b.x, a.y - b.y), mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
          this.panBy(mx - this._pinch.mx, my - this._pinch.my);
          this.zoomBy(d / this._pinch.d, mx, my);
          this._pinch = { d, mx, my };
        }
      },
      up: (e) => {
        const wasDown = this._down;
        this.pointers.delete(e.pointerId);
        if (this.pointers.size < 2) this._pinch = null;
        if (this.pointers.size === 0) {
          host.classList.remove("dragging");
          if (wasDown && !wasDown.moved && e.type === "pointerup" && performance.now() - wasDown.t < 700 && this.o.onTap) {
            const r = host.getBoundingClientRect();
            const [ux, uy] = this.screenToUser(e.clientX - r.left, e.clientY - r.top);
            this.o.onTap(wasDown.target, ux, uy, e);
          }
          this._down = null; this._last = null;
        } else if (this.pointers.size === 1) {
          const p = [...this.pointers.values()][0]; const r = host.getBoundingClientRect();
          this._last = { x: p.x + r.left, y: p.y + r.top };
        }
      },
      dbl: (e) => { const r = host.getBoundingClientRect(); this.zoomBy(e.shiftKey ? 0.5 : 2, e.clientX - r.left, e.clientY - r.top, true); },
      key: (e) => {
        if (e.target !== host) return;
        const k = e.key; let handled = true;
        if (k === "+" || k === "=") this.zoomBy(1.4, undefined, undefined, true);
        else if (k === "-" || k === "_") this.zoomBy(1 / 1.4, undefined, undefined, true);
        else if (k === "0") this.fit();
        else if (k === "ArrowLeft") this.panBy(70, 0);
        else if (k === "ArrowRight") this.panBy(-70, 0);
        else if (k === "ArrowUp") this.panBy(0, 70);
        else if (k === "ArrowDown") this.panBy(0, -70);
        else handled = false;
        if (handled) e.preventDefault();
      },
      leave: (e) => { if (this.o.onHover) this.o.onHover(null); },
    };
    host.addEventListener("wheel", this._h.wheel, { passive: false });
    host.addEventListener("pointerdown", this._h.down);
    host.addEventListener("pointermove", this._h.move);
    host.addEventListener("pointerup", this._h.up);
    host.addEventListener("pointercancel", this._h.up);
    host.addEventListener("pointerleave", this._h.leave);
    host.addEventListener("dblclick", this._h.dbl);
    host.addEventListener("keydown", this._h.key);
  }
  _unbind() {
    const host = this.host, H = this._h;
    host.removeEventListener("wheel", H.wheel); host.removeEventListener("pointerdown", H.down);
    host.removeEventListener("pointermove", H.move); host.removeEventListener("pointerup", H.up);
    host.removeEventListener("pointercancel", H.up); host.removeEventListener("pointerleave", H.leave);
    host.removeEventListener("dblclick", H.dbl); host.removeEventListener("keydown", H.key);
  }
}
