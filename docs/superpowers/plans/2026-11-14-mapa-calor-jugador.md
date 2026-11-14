# Per-player position heatmap (after min 10) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A heatmap of each player's alive positions from minute 10 to the end, next to their kill/death maps, in the report and the match view.

**Architecture:** A pure helper builds downsampled, normalized position points per player; report m08 adds a heat map block per player; the match view draws a third map from the positions it already loads.

**Tech Stack:** Python 3.15 stdlib, vanilla JS, `python -m unittest`.

**Spec:** `docs/superpowers/specs/2026-11-14-mapa-calor-jugador-design.md`

## Global Constraints
- Window: t ≥ 600 s (game seconds) to match end; alive positions only (`decode_positions` gives None when dead).
- Report: one point every 5 s; team 1 rotated 180° (`-x, -y`) so own base is at the bottom; n = matches with ≥ 1 point after 600 s.
- Match view: step 2 s (same positions request as the Minimap); same orientation as the player's kill/death maps.
- Rendering with the existing `MapView` `heat` layer. English UI. Nothing removed, nothing invented.

## Review Focus
- Match shorter than 10 min → no points, excluded from n; the map says "not available" when n = 0.
- Player dead for long stretches → fewer points, no crash.
- Report with many matches → payload stays small (5 s sampling).

---

### Task 1: Heat points helper + report block
**Files:** `scouting/playerstats.py` (or a small new function in it), `scouting/report/metricas/m08_jugadores.py`, `scouting/report/__init__.py` if a lazy cache of decoded positions per match is useful (positions are already decoded for lanes — reuse `MatchCtx` cache if present), `tests/test_lanephase.py` (or new `tests/test_heat.py`).
**Produces:** `heat_points(mi, slot, t_from=600, step_s=5, rotate=False) -> list[[x, y]]` (rounded ints); m08 per player: a `map` block titled "Position heat after minute 10 — <player>" with `layers: [{"kind": "heat", "points": [...]}]`, `n`, `normalized: true`, placed with the player's kill/death zone maps.
- [ ] Tests (fixture `tests/fixtures/match_135801973.json.gz`): every point comes from a time ≥ 600 s (check by recomputing from `decode_positions` for one slot: count = number of alive samples at t ≥ 600 with t % 5 == 0 … or equivalent step logic); `rotate=True` negates coordinates; a synthetic `mi` with duration < 600 → `[]`; m08 has one heat block per roster player with n = 1 for the fixture.
- [ ] RED → implement → GREEN → full suite → commit `feat(jugadores): mapa de calor de posiciones desde el minuto 10`.

### Task 2: Match view third map + docs
**Files:** `static/js/views/matches.js` (Players tab: when a player is selected, a third map "Position heat (after min 10)" beside the kill/death maps, using the positions from `/api/matches/<id>/positions?step=2` — reuse the Minimap's fetch/cache if present, filter by slot and t ≥ 600, same rotation handling as the player's other maps), `static/app.css` if needed, `README.md`/`HANDOFF.md` (Spanish) one line each.
- [ ] Implement; re-read JS; full suite; commit `feat(partidas): mapa de calor de cada jugador desde el minuto 10`. Controller checks in the browser.
