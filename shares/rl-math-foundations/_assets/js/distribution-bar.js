/* distribution-bar.js — bar chart for action probability distributions.
 *
 * Config:
 *   actions       : ["↑","→",...]
 *   distributions : [{ label, values: [p0,p1,...] }]
 *
 * Rendering: HTML/CSS based (no SVG); each row is a flex container of bars.
 */
(function (global) {
  'use strict';

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

  function _readConfig(el) {
    try { return JSON.parse(el.dataset.config); }
    catch (e) { console.error('distbar: bad data-config', e); return null; }
  }

  function mount(el) {
    const cfg = _readConfig(el);
    if (!cfg) return;
    el.innerHTML = '';

    cfg.distributions.forEach(dist => {
      const row = document.createElement('div');
      row.className = 'dist-row';

      const lbl = document.createElement('div');
      lbl.className = 'dist-label';
      lbl.textContent = dist.label;
      row.appendChild(lbl);

      const bars = document.createElement('div');
      bars.className = 'dist-bars';
      dist.values.forEach((v, i) => {
        const action = cfg.actions[i] || `a${i}`;
        const cell = document.createElement('div');
        cell.className = 'dist-cell';

        const bar = document.createElement('div');
        bar.className = 'dist-bar';
        bar.style.height = `${Math.max(2, v * 100)}px`;
        bar.style.background = COLORS[i % COLORS.length];
        bar.title = `${action}: ${v.toFixed(3)}`;
        cell.appendChild(bar);

        const tag = document.createElement('div');
        tag.className = 'dist-tag';
        tag.textContent = action;
        cell.appendChild(tag);

        bars.appendChild(cell);
      });
      row.appendChild(bars);

      el.appendChild(row);
    });
  }

  global.RLComponents = global.RLComponents || {};
  global.RLComponents['distribution-bar'] = { mount };
})(window);
