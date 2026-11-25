import tempfile, unittest, json
from pathlib import Path
from fastapi import HTTPException
from app import main as m

class Persistence(unittest.TestCase):
    def test_legacy_party_and_new_ministry(self):
        with tempfile.TemporaryDirectory() as tmp:
            old=m.DB; m.DB=Path(tmp)/'test.sqlite'
            try:
                m.write(m.Update(revision=0,state={'reference':['Educação'],'official':[]}))
                row=dict(n='Educação',a='Manter',person='Teste',party='pmdf',status='Novo titular')
                bet=dict(nick='Teste',total=40,rows=[row],extras={})
                with m.connect() as c:
                    uid=c.execute('INSERT INTO users(nick,status,bet,draft) VALUES(?,?,?,?)',('Teste','active',json.dumps(bet),json.dumps(bet))).lastrowid
                new=dict(n='Ministério Digital',a='Criar',person='Pessoa teste',party='PT',status='Novo titular')
                draft=dict(bet,rows=[row,new])
                self.assertEqual(m.save_own(m.Update(revision=0,state={'draft':draft,'bet':bet}),uid)['revision'],1)
                self.assertEqual(len(m.own(uid)['state']['draft']['rows']),2)
                self.assertEqual(m.custom_ministries(),[])
                with self.assertRaises(HTTPException): m.save_own(m.Update(revision=1,state={'draft':draft,'bet':draft}),uid)
                fixed=dict(draft,rows=[dict(row,party='MDB'),new])
                self.assertEqual(m.save_own(m.Update(revision=1,state={'draft':fixed,'bet':fixed}),uid)['revision'],2)
                self.assertEqual(m.own(uid)['state']['bet']['rows'][1]['n'],'Ministério Digital')
                self.assertEqual(m.custom_ministries()[0]['name'],'Ministério Digital')
            finally: m.DB=old
