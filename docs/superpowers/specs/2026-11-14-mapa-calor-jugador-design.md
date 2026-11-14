# Design: per-player position heatmap (after the laning phase)

Date: 2026-11-14 · Status: pending user approval · Size: small change

## Intent
Next to each player's kill and death maps, show a heatmap of where that player spends time **after the laning
phase** (from 600 s / minute 10 to the end of the match), to see how each player moves in mid/late game.

## What
- **Match view, Players tab:** when a player is selected, a third map "Position heat (after min 10)" next to the kill and
  death maps. Data: the match positions already served to the Minimap (`/api/matches/<id>/positions`, step 2 s), filtered
  to that player, alive positions only, t ≥ 600 s. Same orientation as the player's other maps (own base at the bottom).
- **Team report, Players section (m08):** per roster player, one heatmap aggregating all analysed matches: alive
  positions with t ≥ 600 s, sampled every 5 s, team 1 rotated 180° so the own base is at the bottom (same convention as
  the zone maps). The block states n = matches with positions after minute 10.
- Rendering: existing `MapView` `heat` layer.

## Rules
- Nothing invented: matches without positions (or ending before 600 s) are left out and counted in n.
- Nothing removed; English UI.

## Approaches
- Client-side heat in the match view from the existing positions endpoint (chosen: no new endpoint, data already loaded
  for the Minimap) vs a server-side per-player endpoint (rejected: duplicates data).
- Report: server-side downsampled points per player (chosen; keeps the report payload small) vs sending all positions
  (rejected: too heavy).

## Left to the builder
Exact layout of the third map, heat radius, payload shape of the report block (e.g. map block with a `heat` layer of
`[[x,y],...]` points), tests (point counts, t ≥ 600 filter, rotation for team 1).
