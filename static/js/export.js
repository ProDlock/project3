// Descarga del informe como un único HTML autocontenido (imágenes, fuentes y CSS incrustados).
import { downloadBlob, toast } from './util.js';

const URL_RE = /url\(\s*(['"]?)(.*?)\1\s*\)/g;

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const fr = new FileReader();
    fr.onload = () => resolve(fr.result);
    fr.onerror = () => reject(fr.error);
    fr.readAsDataURL(blob);
  });
}

function canvasHasContent(c) {
  try {
    if (!c.width || !c.height) return false;
    const w = Math.min(c.width, 64), h = Math.min(c.height, 64);
    const t = document.createElement('canvas'); t.width = w; t.height = h;
    const g = t.getContext('2d'); g.drawImage(c, 0, 0, w, h);
    const d = g.getImageData(0, 0, w, h).data;
    for (let i = 3; i < d.length; i += 4) if (d[i] !== 0) return true;
    return false;
  } catch (e) { return true; } // canvas contaminado: no se puede comprobar, se exporta tal cual
}

// los mapas se dibujan cuando carga su imagen: esperar a que ningún canvas esté en blanco
async function waitCanvases(canvases, maxMs = 5000) {
  const t0 = Date.now();
  while (Date.now() - t0 < maxMs && !canvases.every(canvasHasContent)) await new Promise(r => setTimeout(r, 150));
}

export async function exportReportHtml(rootEl, { team = '', n = 0, title = '' } = {}) {
  const cache = new Map(); // URL absoluta -> Promise<data: URL | null>
  let done = 0;
  const fetchData = (abs) => {
    if (!cache.has(abs)) {
      cache.set(abs, fetch(abs).then(r => { if (!r.ok) throw new Error(r.status); return r.blob(); }).then(blobToDataUrl).catch(() => null)
        .then(v => { done++; toast(`Embedding images… ${done}/${cache.size}`); return v; }));
    }
    return cache.get(abs);
  };
  const absOf = (u, base) => { try { return new URL(u, base || location.href).href; } catch (e) { return null; } };
  const inlineCssUrls = async (css, base) => {
    const found = new Map();
    for (const m of css.matchAll(URL_RE)) {
      const u = m[2].trim();
      if (!u || u.startsWith('data:') || u.startsWith('#')) continue;
      found.set(m[0], absOf(u, base));
    }
    const repl = new Map();
    await Promise.all([...found].map(async ([whole, abs]) => { repl.set(whole, abs ? await fetchData(abs) : null); }));
    return css.replace(URL_RE, whole => (repl.has(whole) ? (repl.get(whole) ? `url("${repl.get(whole)}")` : 'none') : whole));
  };

  toast('Preparing report…');
  const live = [...rootEl.querySelectorAll('canvas')];
  await waitCanvases(live);
  const clone = rootEl.cloneNode(true);
  clone.querySelectorAll('canvas').forEach((cv, i) => {
    const src = live[i];
    let data = '';
    try { data = src.toDataURL('image/png'); } catch (e) { /* canvas contaminado */ }
    const img = document.createElement('img');
    if (data) img.src = data;
    img.alt = src.getAttribute('aria-label') || '';
    if (src.className) img.className = src.className;
    img.style.cssText = cv.style.cssText;
    img.width = src.width; img.height = src.height;
    if (!img.style.width) img.style.width = '100%';
    img.style.height = 'auto';
    cv.replaceWith(img);
  });
  clone.querySelectorAll('.no-print, script, button, input, select, textarea').forEach(x => x.remove());
  clone.querySelectorAll('details').forEach(d => d.setAttribute('open', ''));
  clone.querySelectorAll('*').forEach(x => {
    for (const a of [...x.attributes]) if (/^on/i.test(a.name)) x.removeAttribute(a.name);
    if (x.tagName === 'A') {
      const h = x.getAttribute('href') || '';
      if (h.startsWith('/') || /^https?:\/\/(localhost|127\.0\.0\.1)/.test(h)) x.removeAttribute('href');
    }
  });

  // imágenes <img src> y fondos en línea
  const imgs = [...clone.querySelectorAll('img[src]')].filter(i => !i.getAttribute('src').startsWith('data:'));
  await Promise.all(imgs.map(async i => {
    const abs = absOf(i.getAttribute('src'));
    const d = abs ? await fetchData(abs) : null;
    if (d) i.setAttribute('src', d); else i.removeAttribute('src');
  }));
  for (const x of clone.querySelectorAll('[style*="url("]')) x.setAttribute('style', await inlineCssUrls(x.getAttribute('style'), location.href));

  // hojas de estilo
  let css = '';
  for (const sheet of document.styleSheets) {
    let rules;
    try { rules = sheet.cssRules; } catch (e) { continue; }
    const txt = [...rules].map(r => r.cssText).join('\n');
    css += await inlineCssUrls(txt, sheet.href || location.href) + '\n';
  }

  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const de = document.documentElement;
  const attr = (k) => (de.getAttribute(k) ? ` ${k}="${esc(de.getAttribute(k))}"` : '');
  const docTitle = title || `Report ${team}`.trim();
  const html = `<!doctype html>\n<html${attr('lang')}${attr('class')}${attr('data-theme')}>\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>${esc(docTitle)}</title>\n<style>\n${css}\n</style>\n</head>\n<body${document.body.className ? ` class="${esc(document.body.className)}"` : ''}>\n<p class="muted small">${esc(docTitle)} · ${esc(n)} matches · exported ${esc(new Date().toISOString().slice(0, 10))}</p>\n<div${rootEl.id ? ` id="${esc(rootEl.id)}"` : ''}${rootEl.className ? ` class="${esc(rootEl.className)}"` : ''}>${clone.innerHTML}</div>\n</body>\n</html>\n`;

  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  const slug = (team || 'report').replace(/[^\w-]+/g, '_');
  downloadBlob(`report_${slug}_${new Date().toISOString().slice(0, 10)}.html`, blob);
  toast(`HTML downloaded (${(blob.size / 1048576).toFixed(1)} MB)`);
  return { bytes: blob.size, html };
}
