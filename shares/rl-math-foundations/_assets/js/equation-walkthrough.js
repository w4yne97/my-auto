/* equation-walkthrough.js — Renders a KaTeX equation with a list of annotation chips.
 * Click a chip to show the description. Avoids fighting KaTeX's DOM by NOT trying
 * to highlight inline subexpressions — instead, the chip itself is the affordance.
 *
 * Config schema:
 *   equation     : LaTeX string
 *   annotations  : [{ key, label, description }]
 */
(function (global) {
  'use strict';

  function _readConfig(el) {
    try { return JSON.parse(el.dataset.config); }
    catch (e) { console.error('equation: bad data-config', e); return null; }
  }

  function mount(el) {
    const cfg = _readConfig(el);
    if (!cfg) return;

    el.innerHTML = '';

    const eqDiv = document.createElement('div');
    eqDiv.className = 'eq-display';
    if (global.katex) {
      try {
        global.katex.render(cfg.equation, eqDiv, { displayMode: true, throwOnError: false });
      } catch (e) {
        console.error('katex render failed', e);
        eqDiv.textContent = cfg.equation;
      }
    } else {
      eqDiv.textContent = cfg.equation;
    }
    el.appendChild(eqDiv);

    const chipsDiv = document.createElement('div');
    chipsDiv.className = 'eq-chips';
    cfg.annotations.forEach((a, i) => {
      const chip = document.createElement('button');
      chip.className = 'ann-chip';
      chip.dataset.idx = i;
      chip.textContent = a.label;
      chip.addEventListener('click', () => _select(el, i));
      chipsDiv.appendChild(chip);
    });
    el.appendChild(chipsDiv);

    const descDiv = document.createElement('div');
    descDiv.className = 'eq-desc';
    descDiv.textContent = '点击任意一项 chip 查看含义';
    el.appendChild(descDiv);

    el._cfg = cfg;
  }

  function _select(el, idx) {
    const cfg = el._cfg;
    el.querySelectorAll('.ann-chip').forEach(c => c.classList.remove('active'));
    const target = el.querySelector(`.ann-chip[data-idx="${idx}"]`);
    if (target) target.classList.add('active');
    const desc = el.querySelector('.eq-desc');
    if (desc) desc.textContent = cfg.annotations[idx].description;
  }

  global.RLComponents = global.RLComponents || {};
  global.RLComponents['equation-walkthrough'] = { mount };
})(window);
