/* iteration-stepper.js — Prev/Next stepper that drives a linked gridworld component.
 *
 * Usage: <div data-component="iteration-stepper" data-config='{...}'></div>
 *
 * Config schema:
 *   steps           : [{ label, patch, note }]   patch = partial gridworld config
 *   linked-gridworld: CSS selector for target gridworld element
 */
(function (global) {
  'use strict';

  function _readConfig(el) {
    try { return JSON.parse(el.dataset.config); }
    catch (e) { console.error('stepper: bad data-config', e); return null; }
  }

  function mount(el) {
    const cfg = _readConfig(el);
    if (!cfg || !Array.isArray(cfg.steps) || cfg.steps.length === 0) return;

    let idx = 0;
    el.innerHTML = '';

    const wrap = document.createElement('div');
    wrap.style.display = 'flex';
    wrap.style.alignItems = 'center';
    wrap.style.gap = '0.75rem';
    wrap.style.flexWrap = 'wrap';

    const prevBtn = document.createElement('button');
    prevBtn.dataset.action = 'prev';
    prevBtn.textContent = '← 上一步';

    const nextBtn = document.createElement('button');
    nextBtn.dataset.action = 'next';
    nextBtn.textContent = '下一步 →';

    const label = document.createElement('span');
    label.style.fontWeight = 'bold';

    const note = document.createElement('div');
    note.style.flexBasis = '100%';
    note.style.color = '#555';
    note.style.fontStyle = 'italic';

    wrap.appendChild(prevBtn);
    wrap.appendChild(label);
    wrap.appendChild(nextBtn);
    wrap.appendChild(note);
    el.appendChild(wrap);

    function applyStep() {
      const step = cfg.steps[idx];
      label.textContent = `${step.label}  (${idx + 1} / ${cfg.steps.length})`;
      note.textContent = step.note || '';
      prevBtn.disabled = idx === 0;
      nextBtn.disabled = idx === cfg.steps.length - 1;

      const targetSel = cfg['linked-gridworld'];
      if (targetSel) {
        const tgt = document.querySelector(targetSel);
        if (tgt && global.RLComponents && global.RLComponents.gridworld) {
          global.RLComponents.gridworld.update(tgt, step.patch || {});
        }
      }
    }

    prevBtn.addEventListener('click', () => {
      if (idx > 0) { idx--; applyStep(); }
    });
    nextBtn.addEventListener('click', () => {
      if (idx < cfg.steps.length - 1) { idx++; applyStep(); }
    });

    applyStep();
  }

  global.RLComponents = global.RLComponents || {};
  global.RLComponents['iteration-stepper'] = { mount };
})(window);
