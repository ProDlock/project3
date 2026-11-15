# Design: gank detail (minute, heroes, origin lane) per lane

Date: 2026-11-16 · Status: pending user approval · Size: small change

## Intent
To prepare matches against a rival, see for each lane **when** ganks come (minute), **which heroes** gank and **from
which lane** they come, both in a single match and summed over the report. Today only the first gank per lane and a
count per player are shown.

## Definition (user's rule)
- Gank window: laning phase, 60–600 s (unchanged). Needs the demo (unchanged; without it → "not available").
- A hero counts as a ganker when, in one episode (same attacker, same victim lane, gaps < 30 s, as today), they deal
  **at least 200 damage** to heroes of a lane that is not their own, **or** get a kill there (builder's call: a kill
  always counts).
- Gankers of the same team on the same victim lane whose episodes overlap or are < 30 s apart form **one gank**
  (several heroes).
- The same definition feeds everything: first gank made/suffered, ganks made/suffered per player and the new detail,
  so no two numbers disagree. "Damage taken from ganks" stays the raw damage from other-lane heroes (a damage measure).

## What
- `lanephase.lane_phase` adds `ganks`: `[{t, t_end, lane, team, gankers:[{slot, hero_id, from_lane, dmg, kills}],
  victims:[slot], kills}]` (lane = victim lane; team = ganking team).
- **Match view, Laning phase tab:** a "Ganks" table, one row per gank: minute, ganking heroes (portraits), origin
  lane(s) → attacked lane (lane chips), victims, damage, kills.
- **Report (Laning phase):** for ganks they make and ganks they suffer, one table per attacked lane-row:
  counts from each origin lane (York / Broadway / Greenwich), by minute band (1–3, 3–5, 5–7, 7–10), kills, and the
  heroes who gank most (portraits + counts); n = matches with demo.

## Rules
Data only (no interpretation); missing → "–"/"not available"; English UI; lanes by name and colour.

## Approaches
- **A (chosen): extend `lane_phase`** with the threshold and the merged gank list, and derive first gank and counts from
  it — one definition everywhere.
- B: separate gank module — rejected, the first gank and counts would follow a different rule.
- C: compute in the browser — rejected, the report needs it server-side.

## Left to the builder
Exact table columns order, how origin lanes are shown when gankers come from two lanes, test fixtures.
