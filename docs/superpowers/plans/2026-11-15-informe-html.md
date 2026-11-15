# Report HTML download — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A "Download HTML" button that saves the generated team report as one self-contained, script-free `.html` file that looks exactly like the app.

**Architecture:** A browser-side helper clones the report DOM, swaps canvases for PNG images, inlines the stylesheet with fonts and images embedded as `data:` URIs, strips scripts/interactive chrome, and downloads the result.

**Tech Stack:** vanilla JS (ES modules), existing `downloadBlob` in `static/js/util.js`.

**Spec:** `docs/superpowers/specs/2026-11-15-informe-html-design.md`

## Global Constraints
- File name `deadlock-report-<team-slug>-<YYYY-MM-DD>.html`.
- No `<script>`, no event-handler attributes, no URL pointing at the app (no `/static/`, `/img/`, `/api/`, `127.0.0.1`, `localhost`) left in the output; `<details>` exported open; `.no-print` elements removed; header line with team, matches analysed, export date.
- Images that fail to embed keep their `alt` text (image element removed or left without src) — never a broken link to the app.
- English UI; nothing removed from the report content; no new dependency; no server change.

## Review Focus
- Report with many portraits (≈100 images): embedding must not hang the page — fetch each distinct URL once (cache) and show progress in a toast.
- Canvas maps drawn after the export starts (lazy MapView): wait for `map.ready` or for canvases to have content before snapshotting.
- Fonts: the `@font-face` URLs in app.css must be embedded, otherwise the file falls back to system fonts.

---

### Task 1: Export helper + button
**Files:** Create `static/js/export.js`; Modify `static/js/views/report.js` (button "Download HTML" next to "Print / PDF", class `no-print`), `README.md`/`HANDOFF.md` (Spanish, one line each).
**Produces:** `export async function exportReportHtml(rootEl, { team, n, title }) -> Promise<{ bytes: number }>` that builds the document and triggers the download via `downloadBlob`.
- [ ] Implement: clone `rootEl`; replace every `canvas` (read from the LIVE element, same order) with `<img src=canvas.toDataURL('image/png')>` keeping size/class/aria-label as alt; remove `.no-print`, `script`, `button`, inputs/selects, `on*` attributes; open all `details`; collect the text of all same-origin stylesheets (`document.styleSheets` → `cssRules`), rewrite every `url(...)` inside (fonts, images) to `data:` URIs fetched once; rewrite `img[src]` and inline `style` background URLs to `data:` URIs (fetch → blob → FileReader); wrap in a full `<!doctype html>` with `<meta charset>`, `<title>`, the `<html>` classes/data-theme and `body` classes copied so the theme matches, a header line, and the cloned report.
- [ ] Verification (no node): the controller exports a real report in the browser and checks, by reading the produced string before download (expose the HTML via a returned value or a debug flag), that it contains no `<script`, no `/static/`, `/img/`, `/api/`, `127.0.0.1`, `localhost`, and that `data:image/png` and `data:font` appear; then opens the file.
- [ ] Commit `feat(informe): descargar el informe como HTML autocontenido`.
