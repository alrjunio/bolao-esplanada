"""DEV-007: ranking ties and manual editorial Radar on isolated SQLite."""
import json
import tempfile
import unittest
from pathlib import Path
from app import main as m


def record(person, party="", status=""):
    return dict(n="Educação", a="Manter", origin="", person=person,
                party=party, status=status)


class LaunchEditorialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = m.DB
        m.DB = Path(self.tmp.name) / "editorial.sqlite3"
        m.write(m.Update(revision=0, state=dict(reference=["Educação"],
                                                published=[dict(record("Ana"), source="DOU")])))

    def tearDown(self):
        m.DB = self.old_db
        self.tmp.cleanup()

    def test_zero_ties_not_decided_by_hits_or_parties(self):
        """Both participants display 0; presentation is alphabetical."""
        with m.connect() as c:
            for nick, person in [("Zeta", "Incorreto"), ("Alfa", "Outra")]:
                bet = dict(rows=[record(person)], total=40, extras={})
                c.execute("INSERT INTO users(nick,status,bet) VALUES(?,?,?)",
                          (nick, "active", json.dumps(bet)))
        ranked = m.ranking(1)["ranking"]
        self.assertEqual([(x["nick"], x["pts"]) for x in ranked],
                         [("Alfa", 0), ("Zeta", 0)])

    def test_manual_radar_persists_without_schema_change(self):
        out = m.edit_radar(dict(revision=1, action="add", ministry="Fazenda",
                                person="Nome hipotético", source="Nota editorial",
                                confidence=35))
        self.assertEqual(out["revision"], 2)
        self.assertEqual(m.get_radar()["entries"][0]["confidence"], 35)
        # Ordinary admin saves must not erase the versioned Radar.
        m.write(m.Update(revision=2, state=dict(reference=["Educação"], official=[])))
        self.assertEqual(len(m.get_radar()["entries"]), 1)
        m.edit_radar(dict(revision=3, action="remove", index=0))
        self.assertEqual(m.get_radar()["entries"], [])

    def test_radar_invalid_confidence_is_rejected(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as err:
            m.edit_radar(dict(revision=1, action="add", ministry="Fazenda",
                              person="X", source="Nota", confidence=101))
        self.assertEqual(err.exception.status_code, 422)

    def test_radar_revision_conflict(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as err:
            m.edit_radar(dict(revision=0, action="add", ministry="Fazenda",
                              person="X", source="Nota", confidence=40))
        self.assertEqual(err.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
