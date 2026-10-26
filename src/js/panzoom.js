/* ==========================================================================
   panzoom.js — Smooth Pan, Cursor-Centered Zoom, Pinch & 90° Rotation Engine
   ========================================================================== */
(function () {
  "use strict";

  class PanZoomController {
    constructor(viewportEl, worldEl, opts = {}) {
      this.viewport = viewportEl;
      this.world = worldEl;
      this.onChange = opts.onChange || (() => {});
      this.minScale = opts.minScale || 0.12;
      this.maxScale = opts.maxScale || 14;

      this.contentW = 800;
      this.contentH = 1100;
      this.scale = 1;
      this.tx = 0;
      this.ty = 0;
      this.rotation = 0; // degrees: 0, 90, 180, 270, -90

      this._dragging = false;
      this._startX = 0;
      this._startY = 0;
      this._moved = false;
      this._pointers = new Map();
      this._pinchDist = 0;
      this._suppressSync = false;

      this._bindEvents();
    }

    setContentSize(w, h, initialRotation = 0) {
      this.contentW = Math.max(1, w);
      this.contentH = Math.max(1, h);
      this.rotation = ((initialRotation % 360) + 360) % 360;
      this.fit();
    }

    getRotatedBounds() {
      const r = ((this.rotation % 360) + 360) % 360;
      if (r === 90 || r === 270) {
        return { w: this.contentH, h: this.contentW };
      }
      return { w: this.contentW, h: this.contentH };
    }

    apply(silent = false) {
      const r = ((this.rotation % 360) + 360) % 360;
      let rotShiftX = 0;
      let rotShiftY = 0;
      if (r === 90) {
        rotShiftX = this.contentH;
      } else if (r === 180) {
        rotShiftX = this.contentW;
        rotShiftY = this.contentH;
      } else if (r === 270) {
        rotShiftY = this.contentW;
      }

      this.world.style.width = `${this.contentW}px`;
      this.world.style.height = `${this.contentH}px`;
      this.world.style.transform =
        `translate(${this.tx.toFixed(2)}px, ${this.ty.toFixed(2)}px) ` +
        `scale(${this.scale.toFixed(5)}) ` +
        `translate(${rotShiftX}px, ${rotShiftY}px) ` +
        `rotate(${r}deg)`;

      if (!silent && !this._suppressSync) {
        this.onChange(this.getState());
      }
    }

    getState() {
      return {
        scale: this.scale,
        tx: this.tx,
        ty: this.ty,
        rotation: this.rotation,
        contentW: this.contentW,
        contentH: this.contentH,
      };
    }

    setState(st, silent = true) {
      this._suppressSync = silent;
      if (typeof st.rotation === "number") this.rotation = st.rotation;
      this.scale = Math.min(this.maxScale, Math.max(this.minScale, st.scale));
      this.tx = st.tx;
      this.ty = st.ty;
      this.apply(silent);
      this._suppressSync = false;
    }

    fit(padding = 24) {
      const rect = this.viewport.getBoundingClientRect();
      const vw = Math.max(120, rect.width - padding * 2);
      const vh = Math.max(120, rect.height - padding * 2);
      const { w, h } = this.getRotatedBounds();
      this.scale = Math.min(vw / w, vh / h);
      this.scale = Math.min(this.maxScale, Math.max(this.minScale, this.scale));
      this.tx = (rect.width - w * this.scale) / 2;
      this.ty = (rect.height - h * this.scale) / 2;
      this.apply();
    }

    reset() {
      this.rotation = 0;
      this.fit();
    }

    rotateBy(deltaDeg) {
      this.rotation = (((this.rotation + deltaDeg) % 360) + 360) % 360;
      this.fit();
    }

    setRotation(deg) {
      this.rotation = (((deg) % 360) + 360) % 360;
      this.fit();
    }

    zoomAt(factor, clientX, clientY) {
      const rect = this.viewport.getBoundingClientRect();
      const cx = clientX !== undefined ? clientX - rect.left : rect.width / 2;
      const cy = clientY !== undefined ? clientY - rect.top : rect.height / 2;

      const prev = this.scale;
      const next = Math.min(this.maxScale, Math.max(this.minScale, prev * factor));
      if (Math.abs(next - prev) < 1e-6) return;

      const wx = (cx - this.tx) / prev;
      const wy = (cy - this.ty) / prev;
      this.scale = next;
      this.tx = cx - wx * next;
      this.ty = cy - wy * next;
      this.apply();
    }

    panBy(dx, dy) {
      this.tx += dx;
      this.ty += dy;
      this.apply();
    }

    /**
     * Smoothly focuses on a rectangle [x, y, w, h] in unrotated content coordinates.
     */
    focusRect(x, y, w, h) {
      const rect = this.viewport.getBoundingClientRect();
      if (!rect.width || !rect.height) return;

      const r = ((this.rotation % 360) + 360) % 360;
      let rx = x, ry = y, rw = w, rh = h;
      if (r === 90) {
        rx = this.contentH - (y + h);
        ry = x;
        rw = h;
        rh = w;
      } else if (r === 180) {
        rx = this.contentW - (x + w);
        ry = this.contentH - (y + h);
      } else if (r === 270) {
        rx = y;
        ry = this.contentW - (x + w);
        rw = h;
        rh = w;
      }

      const targetScale = Math.min(
        this.maxScale,
        Math.max(this.scale, Math.min((rect.width * 0.45) / Math.max(24, rw), (rect.height * 0.45) / Math.max(24, rh), 3.6))
      );
      this.scale = targetScale;
      const cx = rx + rw / 2;
      const cy = ry + rh / 2;
      this.tx = rect.width / 2 - cx * targetScale;
      this.ty = rect.height / 2 - cy * targetScale;
      this.apply();
    }

    wasDragging() {
      return this._moved;
    }

    _bindEvents() {
      this.viewport.addEventListener("wheel", (e) => {
        e.preventDefault();
        const factor = e.deltaY < 0 ? 1.16 : 1 / 1.16;
        this.zoomAt(factor, e.clientX, e.clientY);
      }, { passive: false });

      this.viewport.addEventListener("pointerdown", (e) => {
        if (e.button !== 0 && e.pointerType === "mouse") return;
        this._pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
        if (this._pointers.size === 1) {
          this._dragging = true;
          this._moved = false;
          this._startX = e.clientX;
          this._startY = e.clientY;
        } else if (this._pointers.size === 2) {
          const pts = Array.from(this._pointers.values());
          this._pinchDist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
        }
      });

      window.addEventListener("pointermove", (e) => {
        if (!this._pointers.has(e.pointerId)) return;
        const prevPt = this._pointers.get(e.pointerId);
        this._pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });

        if (this._pointers.size === 2) {
          const pts = Array.from(this._pointers.values());
          const dist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
          const midX = (pts[0].x + pts[1].x) / 2;
          const midY = (pts[0].y + pts[1].y) / 2;
          if (this._pinchDist > 8) {
            this.zoomAt(dist / this._pinchDist, midX, midY);
          }
          this._pinchDist = dist;
          this._moved = true;
          return;
        }

        if (this._dragging && prevPt) {
          const dx = e.clientX - prevPt.x;
          const dy = e.clientY - prevPt.y;
          if (Math.hypot(e.clientX - this._startX, e.clientY - this._startY) > 4) {
            this._moved = true;
            this.viewport.classList.add("is-dragging");
          }
          if (this._moved) {
            this.panBy(dx, dy);
          }
        }
      });

      const endPtr = (e) => {
        this._pointers.delete(e.pointerId);
        if (this._pointers.size < 2) this._pinchDist = 0;
        if (this._pointers.size === 0) {
          this._dragging = false;
          this.viewport.classList.remove("is-dragging");
        }
      };
      window.addEventListener("pointerup", endPtr);
      window.addEventListener("pointercancel", endPtr);
    }
  }

  window.AtlasPanZoom = { PanZoomController };
})();
