/* 图表悬停（exhibit-grammar HR46）：原样放进页面末尾的 <script>，不需要图表库。
   图上每个要能查数的元素写 data-tip="系列或类别｜时间或期间｜数值和单位｜口径"，用全角竖线隔开。
   鼠标移上、手指点按、键盘 Tab 到它都会显示；点空白处、按 Esc 或把图滚出屏幕时关闭。 */
(() => {
  const tip = document.createElement('div');
  tip.setAttribute('role', 'tooltip');
  tip.hidden = true;
  tip.style.cssText = 'position:fixed;z-index:1000;max-width:280px;padding:7px 10px;border-radius:4px;background:#0F1419;color:#FFFFFF;font:12.5px/1.55 system-ui,-apple-system,"PingFang SC","Noto Sans SC",sans-serif;font-variant-numeric:tabular-nums;box-shadow:0 2px 8px rgba(0,0,0,.18)';
  document.body.append(tip);
  const mark = t => t && t.closest && t.closest('[data-tip]');
  const show = (el, x, y) => {
    const [head, ...rest] = el.getAttribute('data-tip').split('｜');
    const b = document.createElement('b');
    b.textContent = head;
    tip.replaceChildren(b, ...rest.map(t => Object.assign(document.createElement('div'), { textContent: t })));
    tip.hidden = false;
    const w = tip.offsetWidth, h = tip.offsetHeight;
    tip.style.left = Math.max(8, Math.min(x + 14, innerWidth - w - 8)) + 'px';
    tip.style.top = (y - h - 14 >= 8 ? y - h - 14 : Math.min(y + 18, innerHeight - h - 8)) + 'px';
  };
  const hide = () => { tip.hidden = true; };
  const atTop = el => { const r = el.getBoundingClientRect(); show(el, r.left + r.width / 2, r.top); };
  document.querySelectorAll('[data-tip]').forEach(el => el.setAttribute('tabindex', '0'));
  document.addEventListener('pointermove', e => {
    if (e.pointerType !== 'mouse' || tip.contains(e.target)) return;
    const el = mark(e.target);
    el ? show(el, e.clientX, e.clientY) : hide();
  });
  document.addEventListener('pointerdown', e => {
    if (e.pointerType === 'mouse' || tip.contains(e.target)) return;
    const el = mark(e.target);
    el ? atTop(el) : hide();
  });
  document.addEventListener('focusin', e => { const el = mark(e.target); if (el) atTop(el); });
  document.addEventListener('focusout', hide);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') hide(); });
  addEventListener('scroll', () => {  // 键盘 Tab 到屏幕外的图会自动滚动：提示框开着、焦点图元还在屏幕里就跟着走，否则关掉
    const el = mark(document.activeElement), r = el && el.getBoundingClientRect();
    !tip.hidden && r && r.bottom > 0 && r.top < innerHeight ? atTop(el) : hide();
  }, { passive: true });
})();
