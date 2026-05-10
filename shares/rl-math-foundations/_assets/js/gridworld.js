/* gridworld.js — Renders a 2D grid-world with cells, target, forbidden, agent,
 * heatmap, policy arrows, and an optional trajectory polyline.
 *
 * Usage:  <div data-component="gridworld" data-config='{...}'></div>
 *
 * Config schema:
 *   rows, cols      : int
 *   target          : [row, col]
 *   forbidden       : [[row, col], ...]
 *   agent           : [row, col]               (optional)
 *   heatmap         : [[v00, v01, ...], ...]   (optional, same shape as grid)
 *   policy          : [["→","↓",...], ...]     (optional, same shape)
 *   trajectory      : [[r,c], [r,c], ...]      (optional)
 *
 * Public API exposed as window.RLComponents.gridworld:
 *   mount(el)
 *   update(el, partialConfig)
 */
(function (global) {
  'use strict';

  const NS = 'http://www.w3.org/2000/svg';
  const CELL = 60;          // px per cell
  const PADDING = 12;       // px around the grid
  const ARROW_FONT = 22;    // px

  function _readConfig(el) {
    try { return JSON.parse(el.dataset.config); }
    catch (e) { console.error('gridworld: bad data-config JSON', e); return null; }
  }

  function _heatColor(v, vmin, vmax) {
    if (vmax === vmin) return '#f0f0f0';
    const t = Math.max(0, Math.min(1, (v - vmin) / (vmax - vmin)));
    const r = Math.round(240 + (37 - 240) * t);
    const g = Math.round(240 + (99 - 240) * t);
    const b = Math.round(240 + (235 - 240) * t);
    return `rgb(${r},${g},${b})`;
  }

  function _draw(el, cfg) {
    while (el.firstChild) el.removeChild(el.firstChild);

    const { rows, cols } = cfg;
    const w = cols * CELL + PADDING * 2;
    const h = rows * CELL + PADDING * 2;

    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
    svg.setAttribute('width', w);
    svg.setAttribute('height', h);
    svg.style.maxWidth = '100%';
    svg.style.height = 'auto';

    let vmin = Infinity, vmax = -Infinity;
    if (cfg.heatmap) {
      for (const row of cfg.heatmap)
        for (const v of row) { if (v < vmin) vmin = v; if (v > vmax) vmax = v; }
    }

    const isForbidden = new Set(
      (cfg.forbidden || []).map(([r, c]) => `${r},${c}`)
    );
    const targetKey = cfg.target ? `${cfg.target[0]},${cfg.target[1]}` : null;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const x = PADDING + c * CELL;
        const y = PADDING + r * CELL;
        const rect = document.createElementNS(NS, 'rect');
        rect.setAttribute('class', 'cell');
        rect.setAttribute('x', x);
        rect.setAttribute('y', y);
        rect.setAttribute('width', CELL);
        rect.setAttribute('height', CELL);
        rect.setAttribute('stroke', '#999');
        rect.setAttribute('stroke-width', '1');

        const key = `${r},${c}`;
        let fill = '#fff';
        if (key === targetKey) fill = '#bbf7d0';
        else if (isForbidden.has(key)) fill = '#fecaca';
        else if (cfg.heatmap) fill = _heatColor(cfg.heatmap[r][c], vmin, vmax);
        rect.setAttribute('fill', fill);
        svg.appendChild(rect);

        if (cfg.heatmap) {
          const t = document.createElementNS(NS, 'text');
          t.setAttribute('x', x + CELL / 2);
          t.setAttribute('y', y + CELL / 2 - 6);
          t.setAttribute('text-anchor', 'middle');
          t.setAttribute('font-size', '11');
          t.setAttribute('fill', '#333');
          t.textContent = cfg.heatmap[r][c].toFixed(2);
          svg.appendChild(t);
        }

        if (cfg.policy && cfg.policy[r] && cfg.policy[r][c]) {
          const t = document.createElementNS(NS, 'text');
          t.setAttribute('x', x + CELL / 2);
          t.setAttribute('y', y + CELL / 2 + ARROW_FONT / 3);
          t.setAttribute('text-anchor', 'middle');
          t.setAttribute('font-size', ARROW_FONT);
          t.setAttribute('fill', '#1d4ed8');
          t.textContent = cfg.policy[r][c];
          svg.appendChild(t);
        }
      }
    }

    if (cfg.trajectory && cfg.trajectory.length > 1) {
      const points = cfg.trajectory.map(([r, c]) => {
        const x = PADDING + c * CELL + CELL / 2;
        const y = PADDING + r * CELL + CELL / 2;
        return `${x},${y}`;
      }).join(' ');
      const poly = document.createElementNS(NS, 'polyline');
      poly.setAttribute('points', points);
      poly.setAttribute('fill', 'none');
      poly.setAttribute('stroke', '#f59e0b');
      poly.setAttribute('stroke-width', '3');
      poly.setAttribute('stroke-linejoin', 'round');
      svg.appendChild(poly);
    }

    if (cfg.agent) {
      const [ar, ac] = cfg.agent;
      const cx = PADDING + ac * CELL + CELL / 2;
      const cy = PADDING + ar * CELL + CELL / 2;
      const dot = document.createElementNS(NS, 'circle');
      dot.setAttribute('cx', cx);
      dot.setAttribute('cy', cy);
      dot.setAttribute('r', 10);
      dot.setAttribute('fill', '#1f2937');
      svg.appendChild(dot);
    }

    el.appendChild(svg);
    el._cfg = cfg;
  }

  function mount(el) {
    const cfg = _readConfig(el);
    if (!cfg) return;
    _draw(el, cfg);
  }

  function update(el, patch) {
    const cfg = Object.assign({}, el._cfg || _readConfig(el), patch);
    _draw(el, cfg);
  }

  global.RLComponents = global.RLComponents || {};
  global.RLComponents.gridworld = { mount, update };
})(window);
