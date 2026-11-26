"""V3 Launch regression: lock scope and optimistic revision conflicts."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from app import main as m


def row(name, person):
    return dict(n=name, a="Manter", origin="", person=person, party="PT", status="Permanece")


class LaunchLocks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = m.DB
        m.DB = Path(self.tmp.name) / "lock-test.sqlite"
        m.write(m.Update(revision=0, state=dict(reference=["Educação", "Saúde"], official=[])))
        with m.connect() as c:
            self.uid = c.execute("INSERT INTO users(nick,status) VALUES('Teste','active')").lastrowid
        self.bet = dict(nick="Teste", total=2, rows=[row("Educação", "Ana"), row("Saúde", "Bia")], extras={"0": 1})
        m.save_own(m.Update(revision=0, state=dict(draft=copy.deepcopy(self.bet), bet=copy.deepcopy(self.bet))), self.uid)

    def tearDown(self):
        m.DB = self.old_db
        self.tmp.cleanup()

    def test_block_one_ministry_keeps_other_editable(self):
        m.lock_pasta(dict(revision=1, names=["Educação"]))
        changed = copy.deepcopy(self.bet)
        changed["rows"][1]["person"] = "Clara"
        result = m.save_own(m.Update(revision=1, state=dict(draft=changed, bet=changed)), self.uid)
        self.assertEqual(result["revision"], 2)

    def test_locked_ministry_cannot_be_changed(self):
        m.lock_pasta(dict(revision=1, names=["Educação"]))
        changed = copy.deepcopy(self.bet)
        changed["rows"][0]["person"] = "Clara"
        with self.assertRaises(HTTPException) as caught:
            m.save_own(m.Update(revision=1, state=dict(draft=changed, bet=changed)), self.uid)
        self.assertEqual(caught.exception.status_code, 409)

    def test_first_ministry_lock_freezes_total_and_extras(self):
        m.lock_pasta(dict(revision=1, names=["Educação"]))
        changed = copy.deepcopy(self.bet)
        changed["total"] = 3
        with self.assertRaises(HTTPException) as caught:
            m.save_own(m.Update(revision=1, state=dict(draft=changed, bet=changed)), self.uid)
        self.assertEqual(caught.exception.status_code, 409)

    def test_old_revision_is_rejected(self):
        changed = copy.deepcopy(self.bet)
        changed["rows"][1]["person"] = "Clara"
        with self.assertRaises(HTTPException) as caught:
            m.save_own(m.Update(revision=0, state=dict(draft=changed, bet=changed)), self.uid)
        self.assertEqual(caught.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
