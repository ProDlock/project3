# Design: download the team report as a self-contained HTML file

Date: 2026-11-15 · Status: pending user approval · Size: small change

## Intent
Let the user download the team report exactly as it looks in the app, as one `.html` file that opens in any browser
without the app (to keep or share). Chosen by the user over a print-based PDF and a screenshot-based PDF.

## What
- Button **"Download HTML"** next to "Print / PDF" in the generated report.
- The file is a **static snapshot** of what is on screen: same dark style, fonts, colours, portraits, objective icons,
  cards, bars, and every map (zone maps, heat maps, kill/death maps) as images. No scripts in the file (so it is safe to
  open anywhere and never calls the app); tables keep the order they had when exported (sorting needs the app).
- Self-contained: the app's stylesheet inlined; images from the app (`/img/...` proxy, `/static/...`) embedded as
  `data:` URIs; the app's local fonts embedded as `data:` URIs; canvases converted with `toDataURL('image/png')`.
- Only the report is exported (not the form, sidebar, search or buttons; elements with `no-print` are dropped).
  Collapsed `<details>` sections are exported open. A header line says team, matches analysed and export date.
- File name: `deadlock-report-<team>-<YYYY-MM-DD>.html` (team slugified).
- All done in the browser (`static/js/views/report.js` + a small helper module); no server change, no new dependency.

## Rules
- Nothing removed from the report content; English UI; images that fail to load are left as their alt text, never
  invented; the exported file must not reference the app (no `http://127.0.0.1` URLs, no scripts).

## Approaches
- A: print stylesheet + "Save as PDF" (not chosen). B: html2canvas+jsPDF image PDF (not chosen). **C: self-contained HTML
  snapshot (chosen by the user).**

## Left to the builder
Helper structure (e.g. `static/js/export.js` with `exportReportHtml(rootEl, meta)`), how fonts are collected (from
`document.fonts`/the stylesheet's `@font-face` URLs), progress/toast while embedding, and a size note in the toast.
