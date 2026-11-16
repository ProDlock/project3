"""Resumen de la fase de líneas (0-600 s, ambos extremos incluidos) de una partida: dúos por línea, daño, Guardians y gankeos."""
from . import demo, lanes as lanes_mod, matches

T_FIN = 600
T_GANK = 60
GAP_EPISODIO = 30
GANK_MIN_DMG = 200   # daño mínimo de un episodio para contar como gankeo (una kill también lo hace contar)


def _slot_of(mi):
    return {p["account_id"]: p["player_slot"] for p in mi.get("players") or []}


def _stats_dmg(mi, t=T_FIN):
    """({slot: hecho}, {slot: recibido}) a `t` s desde las muestras player_damage / player_damage_taken (interpoladas).
    Un jugador sin muestras da None (dato ausente, no 0)."""
    done, taken = {}, {}
    for p in mi.get("players") or []:
        d = matches.stat_at(p, "player_damage", t)
        k = matches.stat_at(p, "player_damage_taken", t)
        done[p["player_slot"]] = None if d is None else int(round(d))
        taken[p["player_slot"]] = None if k is None else int(round(k))
    return done, taken


def _episodes(events):
    """Agrupa eventos cruzados en episodios de gankeo.

    Eventos consecutivos (daño o kill) del mismo atacante hacia la misma línea de víctima con huecos
    < GAP_EPISODIO s forman un solo episodio. Devuelve [{"att", "victims": set, "vlane", "t_start", "t_end",
    "dmg", "kills", "events"}]; "dmg" suma el daño de los eventos (clave "dmg", 0 si falta)."""
    eps, last = [], {}
    for e in sorted(events, key=lambda e: e["t"]):
        key = (e["attacker_slot"], e["vlane"])
        ep = last.get(key)
        if ep is None or e["t"] - ep["t_last"] >= GAP_EPISODIO:
            ep = {"att": e["attacker_slot"], "vlane": e["vlane"], "victims": set(), "t_last": e["t"],
                  "t_start": e["t"], "t_end": e["t"], "dmg": 0, "kills": 0, "events": []}
            eps.append(ep)
            last[key] = ep
        ep["victims"].add(e["victim_slot"])
        ep["t_last"] = ep["t_end"] = e["t"]
        ep["dmg"] += e.get("dmg", 0)
        ep["kills"] += e["kind"] == "kill"
        ep["events"].append(e)
    return eps


def _gank_ok(ep):
    """Un episodio cuenta como gankeo con daño suficiente o con alguna kill."""
    return ep["dmg"] >= GANK_MIN_DMG or ep["kills"] > 0


def _merge_ganks(eps, team, lane_of, ps):
    """Une los episodios del mismo equipo atacante sobre la misma línea víctima cuyos rangos se solapan o
    distan < GAP_EPISODIO s. Devuelve la lista de gankeos ordenada por t."""
    groups = {}
    for ep in sorted(eps, key=lambda e: e["t_start"]):
        groups.setdefault((team[ep["att"]], ep["vlane"]), []).append(ep)
    out = []
    for (tm, vl), lst in groups.items():
        cur = None
        for ep in lst:
            if cur is None or ep["t_start"] - cur["t_end"] >= GAP_EPISODIO:
                cur = {"t": ep["t_start"], "t_end": ep["t_end"], "lane": vl, "team": tm, "eps": []}
                out.append(cur)
            cur["t_end"] = max(cur["t_end"], ep["t_end"])
            cur["eps"].append(ep)
    res = []
    for g in out:
        gk, victims = {}, set()
        for ep in g["eps"]:
            x = gk.setdefault(ep["att"], {"slot": ep["att"], "hero_id": ps[ep["att"]].get("hero_id"),
                                          "from_lane": lane_of[ep["att"]], "dmg": 0, "kills": 0})
            x["dmg"] += ep["dmg"]
            x["kills"] += ep["kills"]
            victims |= ep["victims"]
        gl = sorted(gk.values(), key=lambda x: x["slot"])
        res.append({"t": g["t"], "t_end": g["t_end"], "lane": g["lane"], "team": g["team"], "gankers": gl,
                    "victims": sorted(victims), "dmg": sum(x["dmg"] for x in gl), "kills": sum(x["kills"] for x in gl)})
    res.sort(key=lambda g: (g["t"], g["lane"], g["team"]))
    return res


def _event(t, att, vic, kind, dmg=0):
    """Evento de gankeo; `dmg` y `vlane` son internos y se quitan antes de exponerlo (ver _public)."""
    return {"t": int(round(t)), "attacker_slot": att, "victim_slot": vic, "kind": kind, "dmg": dmg}


def _public(e):
    return {k: e[k] for k in ("t", "attacker_slot", "victim_slot", "kind")}


def _better(cur, new):
    """El evento más temprano; a igual t gana la kill."""
    if cur is None:
        return new
    if (new["t"], new["kind"] != "kill") < (cur["t"], cur["kind"] != "kill"):
        return new
    return cur


def _demo_usable(mi, lane_rows):
    """Hay filas y al menos una enlaza dos jugadores de la partida (si no, serían ceros falsos)."""
    by_acc = _slot_of(mi)
    return any(by_acc.get(r.get("att")) is not None and by_acc.get(r.get("vic")) is not None for r in lane_rows or [])


def lane_phase(mi, lane_rows=None, rules=None, paths=None, tick_limit=None):
    """Resumen por partida. ganks_made/ganks_suffered por jugador cuentan GANKEOS de la lista `ganks` (ya fusionados, ver _merge_ganks):
    los gankeos en los que el jugador es ganker / víctima; coinciden siempre con esa lista.
    Con las líneas no válidas: lanes {}, source None, lane/ganks None; el daño por jugador se mantiene.

    `tick_limit` = límite de tick con el que se consultaron `lane_rows` (por defecto el antiguo, 48000). Si con las
    pausas de la partida no alcanza 600 s de juego, el daño del demo está incompleto: se usa la aproximación
    (source "aprox") y demo_incompleto = True. Filas vacías o sin jugadores de la partida → aproximación.
    Sin demo los gankeos no están disponibles (None)."""
    ps = matches.players(mi)
    team = {s: p.get("team") for s, p in ps.items()}
    lane_of = lanes_mod.assign_lanes(mi, paths if paths is not None else lanes_mod.load_paths())
    duo = lanes_mod.duos(mi, lane_of)
    valid = bool(duo)
    use_demo = lane_rows is not None and rules is not None and _demo_usable(mi, lane_rows)
    incompleto = False
    if use_demo:
        limit = tick_limit if tick_limit is not None else demo.LANE_TICK_LIMIT_LEGACY
        if demo.game_seconds_from_tick(limit, rules) < T_FIN:
            use_demo, incompleto = False, True

    d_done = {s: 0 for s in ps}
    d_taken = {s: 0 for s in ps}
    d_done_l = {s: 0 for s in ps}
    d_taken_l = {s: 0 for s in ps}
    d_taken_g = {s: 0 for s in ps}
    gank_ev = []   # (t, att, vic, kind) cruzados
    if use_demo:
        by_acc = _slot_of(mi)
        for r in lane_rows:
            a, v = by_acc.get(r["att"]), by_acc.get(r["vic"])
            if a is None or v is None or team[a] == team[v] or not r.get("dmg"):
                continue
            t = demo.game_seconds_from_tick(r["b"] * 320, rules)
            if t < 0 or t > T_FIN:
                continue
            d_done[a] += r["dmg"]
            d_taken[v] += r["dmg"]
            if valid:
                if lane_of[a] == lane_of[v]:
                    d_done_l[a] += r["dmg"]
                    d_taken_l[v] += r["dmg"]
                else:
                    d_taken_g[v] += r["dmg"]
                    if t >= T_GANK and r["dmg"] > 0:
                        gank_ev.append(_event(t, a, v, "dano", r["dmg"]))
    else:
        d_done, d_taken = _stats_dmg(mi)
        for s in ps:
            d_done.setdefault(s, 0)
            d_taken.setdefault(s, 0)

    deaths, kills = {s: 0 for s in ps}, {s: 0 for s in ps}
    for d in matches.deaths(mi):
        t = d["t"]
        if t is None or t > T_FIN:
            continue
        deaths[d["victim_slot"]] += 1
        k = d["killer_slot"]
        if k is not None and d["killer_team"] != d["victim_team"]:
            kills[k] += 1
            if use_demo and valid and t >= T_GANK and lane_of[k] != lane_of[d["victim_slot"]]:
                gank_ev.append(_event(t, k, d["victim_slot"], "kill"))

    # Guardians
    guard = {}
    for o in matches.objectives(mi):
        if o["type"] == "Guardian" and o["destroyed_s"]:
            guard[(o["lane"], o["owner_team"])] = o["destroyed_s"]

    made, suffered = {}, {}
    ganks_made = {s: 0 for s in ps}
    ganks_suffered = {s: 0 for s in ps}
    ganks = None
    if use_demo and valid:
        for e in gank_ev:
            e["vlane"] = lane_of[e["victim_slot"]]
        eps = [ep for ep in _episodes(gank_ev) if _gank_ok(ep)]
        for ep in eps:
            for e in ep["events"]:
                pe = _public(e)
                a, v = e["attacker_slot"], e["victim_slot"]
                k = (lane_of[v], team[a])          # gankea el equipo de a en la línea de v
                made[k] = _better(made.get(k), pe)
                k = (lane_of[v], team[v])
                suffered[k] = _better(suffered.get(k), pe)
        ganks = _merge_ganks(eps, team, lane_of, ps)
        # los contadores por jugador salen de la lista fusionada: así coinciden con las filas que se muestran
        for g in ganks:
            for k in g["gankers"]:
                ganks_made[k["slot"]] += 1
            for v in g["victims"]:
                ganks_suffered[v] += 1

    def tot(d, slots, on):
        if not on or any(d[s] is None for s in slots):
            return None
        return sum(d[s] for s in slots)

    out_lanes = {}
    for tm, per_lane in duo.items():
        for ln, slots in per_lane.items():
            enemy = 1 - tm
            out_lanes.setdefault(str(ln), {})[str(tm)] = {
                "slots": slots,
                "heroes": [ps[s].get("hero_id") for s in slots],
                "dmg_done": tot(d_done, slots, True), "dmg_taken": tot(d_taken, slots, True),
                "dmg_done_lane": tot(d_done_l, slots, use_demo),
                "dmg_taken_lane": tot(d_taken_l, slots, use_demo),
                "dmg_taken_gank": tot(d_taken_g, slots, use_demo),
                "guardian_taken_t": guard.get((ln, enemy)), "guardian_lost_t": guard.get((ln, tm)),
                "deaths": sum(deaths[s] for s in slots), "kills": sum(kills[s] for s in slots),
                "first_gank_suffered": suffered.get((ln, tm)) if use_demo else None,
                "first_gank_made": made.get((ln, tm)) if use_demo else None,
            }
    players = {str(s): {"lane": lane_of.get(s) if valid else None,
                        "dmg_done": d_done[s], "dmg_taken": d_taken[s],
                        "ganks_made": ganks_made[s] if valid and use_demo else None,
                        "ganks_suffered": ganks_suffered[s] if valid and use_demo else None,
                        "deaths": deaths[s], "kills": kills[s]} for s in sorted(ps)}
    return {"valid": valid, "source": ("demo" if use_demo else "aprox") if valid else None, "demo_incompleto": incompleto,
            "lanes": out_lanes, "players": players, "ganks": ganks}
