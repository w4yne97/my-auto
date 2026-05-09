/* convergence-plot.js — Pure-SVG line chart for convergence/learning curves.
 *
 * Config schema:
 *   x-label, y-label : string
 *   log-y           : bool
 *   series          : [{ name, color, points: [[x,y],...] }]
 */
(function (global) {
  'use strict';

  const NS = 'http://www.w3.org/2000/svg';
  const W = 560, H = 320;
  const M = { l: 60, r: 20, t: 20, b: 50 };

  function _readConfig(el) {
    try { return JSON.parse(el.dataset.config); }
    catch (e) { console.error('plot: bad data-config', e); return null; }
  }

  function _bounds(series, logY) {
    let xmin = Infinity, xmax = -Infinity, ymin = Infinity, ymax = -Infinity;
    for (const s of series) {
      for (const [x, y] of s.points) {
        if (x < xmin) xmin = x; if (x > xmax) xmax = x;
        const yv = logY ? Math.log10(Math.max(y, 1e-12)) : y;
        if (yv < ymin) ymin = yv; if (yv > ymax) ymax = yv;
      }
    }
    if (xmin === xmax) xmax = xmin + 1;
    if (ymin === ymax) ymax = ymin + 1;
    return { xmin, xmax, ymin, ymax };
  }

  function _scale(b, logY) {
    const plotW = W - M.l - M.r;
    const plotH = H - M.t - M.b;
    return {
      x: (x) => M.l + plotW * (x - b.xmin) / (b.xmax - b.xmin),
      y: (y) => {
        const yv = logY ? Math.log10(Math.max(y, 1e-12)) : y;
        return M.t + plotH * (1 - (yv - b.ymin) / (b.ymax - b.ymin));
      },
    };
  }

  function _axes(svg, b, scale, cfg) {
    const ax = document.createElementNS(NS, 'g');
    ax.setAttribute('stroke', '#666');
    ax.setAttribute('fill', 'none');

    function mkline(x1, y1, x2, y2) {
      const l = document.createElementNS(NS, 'line');
      l.setAttribute('x1', x1); l.setAttribute('y1', y1);
      l.setAttribute('x2', x2); l.setAttribute('y2', y2);
      return l;
    }
    ax.appendChild(mkline(M.l, M.t, M.l, H - M.b));
    ax.appendChild(mkline(M.l, H - M.b, W - M.r, H - M.b));

    function mktext(x, y, text, anchor) {
      const t = document.createElementNS(NS, 'text');
      t.setAttribute('x', x); t.setAttribute('y', y);
      t.setAttribute('text-anchor', anchor || 'middle');
      t.setAttribute('font-size', '11');
      t.setAttribute('fill', '#333');
      t.textContent = text;
      return t;
    }
    for (let i = 0; i <= 3; i++) {
      const xv = b.xmin + (b.xmax - b.xmin) * i / 3;
      const sx = scale.x(xv);
      ax.appendChild(mktext(sx, H - M.b + 14, xv.toFixed(0)));
      const sy = scale.y(b.ymin + (b.ymax - b.ymin) * (1 - i / 3));
      const labelV = cfg['log-y'] ? Math.pow(10, b.ymax - (b.ymax - b.ymin) * i / 3).toExponential(1)
                                  : (b.ymax - (b.ymax - b.ymin) * i / 3).toFixed(2);
      ax.appendChild(mktext(M.l - 6, sy + 3, labelV, 'end'));
    }
    ax.appendChild(mktext((M.l + W - M.r) / 2, H - 8, cfg['x-label'] || ''));
    const yLab = mktext(14, (M.t + H - M.b) / 2, cfg['y-label'] || '');
    yLab.setAttribute('transform', `rotate(-90 14,${(M.t + H - M.b) / 2})`);
    ax.appendChild(yLab);

    svg.appendChild(ax);
  }

  function mount(el) {
    const cfg = _readConfig(el);
    if (!cfg) return;
    el.innerHTML = '';

    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.setAttribute('width', W);
    svg.setAttribute('height', H);
    svg.style.maxWidth = '100%'; svg.style.height = 'auto';

    const b = _bounds(cfg.series, !!cfg['log-y']);
    const scale = _scale(b, !!cfg['log-y']);

    _axes(svg, b, scale, cfg);

    cfg.series.forEach(s => {
      const points = s.points.map(([x, y]) => `${scale.x(x)},${scale.y(y)}`).join(' ');
      const poly = document.createElementNS(NS, 'polyline');
      poly.setAttribute('points', points);
      poly.setAttribute('fill', 'none');
      poly.setAttribute('stroke', s.color);
      poly.setAttribute('stroke-width', '2');
      svg.appendChild(poly);
    });

    el.appendChild(svg);

    const legend = document.createElement('div');
    legend.className = 'cp-legend';
    cfg.series.forEach(s => {
      const span = document.createElement('span');
      span.innerHTML = `<i style="background:${s.color}"></i>${s.name}`;
      legend.appendChild(span);
    });
    el.appendChild(legend);
  }

  global.RLComponents = global.RLComponents || {};
  global.RLComponents['convergence-plot'] = { mount };
})(window);
