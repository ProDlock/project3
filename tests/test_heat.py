"""Mapa de calor de posiciones desde el minuto 10."""
import copy
import unittest

from scouting import matches, playerstats, report
from tests.test_lanephase import _mi


class HeatPoints(unittest.TestCase):
    def setUp(self):
        self.mi = _mi()
        self.dec = matches.decode_positions(self.mi)
        self.p = self.dec["players"][0]

    def test_points_match_alive_samples_from_600(self):
        iv = self.dec.get("interval_s") or 1
        exp = [[x, y] for i, (x, y) in enumerate(zip(self.p["x"], self.p["y"]))
               if i * iv >= 600 and (i * iv) % 5 == 0 and x is not None]
        self.assertTrue(exp)
        self.assertEqual(playerstats.heat_points(self.mi, self.p["slot"]), exp)

    def test_rotate_negates(self):
        a = playerstats.heat_points(self.mi, self.p["slot"])
        b = playerstats.heat_points(self.mi, self.p["slot"], rotate=True)
        self.assertEqual(b, [[-x, -y] for x, y in a])

    def test_short_match_empty(self):
        mi = copy.deepcopy(self.mi)
        for q in mi["match_paths"]["paths"]:
            for k in ("x_pos", "y_pos", "health"):
                q[k] = (q.get(k) or [])[:300]
        self.assertEqual(playerstats.heat_points(mi, self.p["slot"]), [])

    def test_m08_one_heat_block_per_player(self):
        mi = self.mi
        roster = {p["account_id"] for p in mi["players"] if p["team"] == 1}
        out = report.run("T", [{"match_info": mi}], roster, None, None, None, hero_names={})
        sec = {s["id"]: s for s in out["sections"]}["jugadores"]
        heats = [b for b in sec["blocks"] if b.get("layers") and b["layers"][0]["kind"] == "heat"]
        self.assertEqual(len(heats), 6)
        for b in heats:
            self.assertEqual(b["n"], 1)
            self.assertTrue(b["normalized"])
            self.assertTrue(b["layers"][0]["points"])
            self.assertTrue(b["title"].startswith("Position heat after minute 10"))

    def test_m08_unavailable_when_no_positions(self):
        mi = copy.deepcopy(self.mi)
        for q in mi["match_paths"]["paths"]:
            for k in ("x_pos", "y_pos", "health"):
                q[k] = (q.get(k) or [])[:300]
        roster = {p["account_id"] for p in mi["players"] if p["team"] == 1}
        out = report.run("T", [{"match_info": mi}], roster, None, None, None, hero_names={})
        sec = {s["id"]: s for s in out["sections"]}["jugadores"]
        un = [b for b in sec["blocks"] if b.get("type") == "unavailable" and b["title"].startswith("Position heat")]
        self.assertEqual(len(un), 6)
        self.assertEqual(un[0]["reason"], "No positions after minute 10.")


if __name__ == "__main__":
    unittest.main()
