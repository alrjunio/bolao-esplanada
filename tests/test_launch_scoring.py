"""V3.0 Launch: regression checks on approved scoring and public score floor."""
import json
import tempfile
import unittest
from pathlib import Path

from app import main as m
from app.scoring import score


def row(n="Educação", person="Ana", party="PT", status="Permanece", a="Manter", origin=""):
    return dict(n=n, person=person, party=party, status=status, a=a, origin=origin)


def confirmed(**updates):
    result = dict(row(), source="DOU", structureConfirmed=True)
    result.update(updates)
    return result


class LaunchScoring(unittest.TestCase):
    def test_full_ministerial_match(self):
        p = dict(rows=[row()], total=40, extras={})
        self.assertEqual(score(p, dict(published=[confirmed()]))["pts"], 20)

    def test_wrong_fields(self):
        p = dict(rows=[row(person="Bia", party="MDB", status="Novo titular")], extras={})
        self.assertEqual(score(p, dict(published=[confirmed()]))["pts"], -4)

    def test_name_correct_in_other_ministry(self):
        p = dict(rows=[row(person="Bia")], extras={})
        g = dict(published=[confirmed(), confirmed(n="Saúde", person="Bia")])
        self.assertEqual(score(p, g)["pts"], 10)  # +2 name, +5 party, +3 status

    def test_unconfirmed_fields_are_neutral(self):
        p = dict(rows=[row()], extras={})
        g = dict(published=[confirmed(person="", party="", status="")])
        self.assertEqual(score(p, g)["pts"], 0)

    def test_total_prediction_exact_and_one_off(self):
        g = dict(published=[], total=40, final=True)
        self.assertEqual(score(dict(rows=[], total=40, extras={}), g)["pts"], 50)
        self.assertEqual(score(dict(rows=[], total=39, extras={}), g)["pts"], 30)

    def test_exact_extras(self):
        p = dict(rows=[], extras={"0": 8, "1": 12})
        g = dict(published=[], publishedExtras={"0": 8, "1": 11})
        self.assertEqual(score(p, g)["pts"], 10)

    def test_public_floor_preserves_internal_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_db = m.DB
            m.DB = Path(tmp) / "launch.sqlite"
            try:
                with m.connect() as c:
                    bet = dict(rows=[row(person="Bia", party="MDB", status="Novo titular")], extras={})
                    c.execute("INSERT INTO users(nick,status,bet) VALUES(?,?,?)",
                              ("Teste", "active", json.dumps(bet)))
                    state = dict(published=[confirmed()], reference=["Educação"])
                    c.execute("INSERT INTO game(id,revision,state) VALUES(1,0,?)",
                              (json.dumps(state),))
                self.assertEqual(score(bet, state)["pts"], -4)
                self.assertEqual(m.ranking(1)["ranking"][0]["pts"], 0)
            finally:
                m.DB = old_db


if __name__ == "__main__":
    unittest.main()
