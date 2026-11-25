import tempfile, unittest
from pathlib import Path
from fastapi import HTTPException
from app import main as m
class Control(unittest.TestCase):
    def test_control(self):
        with tempfile.TemporaryDirectory() as tmp:
            original=m.DB; m.DB=Path(tmp)/'test.sqlite'
            try:
                m.write(m.Update(revision=0,state={'reference':['Educação','Saúde'],'official':[{'n':'Educação','a':'Manter','person':'Ana','source':'DOU'}]}))
                with m.connect() as c: c.execute("INSERT INTO users(nick,status,bet) VALUES('Teste','active','{}')")
                m.lock_pasta({'revision':1,'names':['Educação','Saúde']})
                out=m.competition_control({'revision':2,'action':'unlock','name':'Saúde'})
                self.assertEqual(out['state']['lockedPastas'],['educacao'])
                m.publish({'revision':3,'index':0})
                with self.assertRaises(HTTPException): m.competition_control({'revision':4,'action':'unlock','name':'Educação'})
                out=m.competition_control({'revision':4,'action':'annul','name':'Educação','confirm':'REINICIAR'})
                self.assertEqual(out['state']['published'],[])
                out=m.competition_control({'revision':5,'action':'reset','confirm':'REINICIAR','clearBets':True})
                self.assertFalse(out['state']['extrasLocked']); self.assertEqual(out['state']['lockedPastas'],[]); self.assertEqual(out['state']['reference'],['Educação','Saúde'])
                with m.connect() as c: self.assertEqual(c.execute('SELECT nick,bet FROM users').fetchone(),('Teste',None))
                self.assertEqual(len(list((Path(tmp)/'backups').glob('*.sqlite3'))),2)
            finally: m.DB=original
