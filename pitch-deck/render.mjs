// Renders deck.html -> peer-prep-pitch-deck.pdf and reports any overflow/clipping.
import { chromium } from 'playwright';
import path from 'node:path';
const dir = path.dirname(new URL(import.meta.url).pathname);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
await page.goto('file://' + path.join(dir, 'deck.html'));
await page.evaluate(() => document.fonts.ready);
const problems = await page.evaluate(() => {
  const out = [];
  document.querySelectorAll('.slide').forEach((slide, i) => {
    const frame = slide.querySelector('.frame').getBoundingClientRect();
    slide.querySelectorAll('.frame *').forEach(el => {
      if (el.classList.contains('plus')) return;
      const r = el.getBoundingClientRect();
      if (!r.width) return;
      if (r.left < frame.left - 1 || r.right > frame.right + 1 || r.top < frame.top - 1 || r.bottom > frame.bottom + 1)
        out.push(`slide ${i}: ${el.className || el.tagName} outside frame`);
      if (el.scrollHeight > el.clientHeight + 1 && getComputedStyle(el).overflow !== 'visible')
        out.push(`slide ${i}: ${el.className || el.tagName} clipped`);
      // child sticking out of a bordered box
      const box = el.closest('.box, .body');
      if (box && box !== el) {
        const b = box.getBoundingClientRect();
        if (r.bottom > b.bottom + 1 || r.right > b.right + 1)
          if (!el.classList.contains('step-arrow')) out.push(`slide ${i}: ${el.className || el.tagName} overflows ${box.className} by ${Math.round(Math.max(r.bottom-b.bottom, r.right-b.right))}px`);
      }
    });
    // body content must stay above footer
    const body = slide.querySelector('.body');
    if (body) { const last = [...body.children].pop().getBoundingClientRect(); const foot = slide.querySelector('.foot').getBoundingClientRect();
      out.push(`slide ${i}: gap above footer = ${Math.round(foot.top - last.bottom)}px`); }
  });
  return out;
});
console.log(problems.join('\n'));
await page.pdf({ path: path.join(dir, 'peer-prep-pitch-deck.pdf'), width: '1600px', height: '900px', printBackground: true, preferCSSPageSize: true });
await browser.close();
