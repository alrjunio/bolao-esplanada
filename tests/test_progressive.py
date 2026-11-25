import tempfile, unittest
from pathlib import Path
from fastapi import HTTPException
from app import main as m
class Progressive(unittest.TestCase):
    def test_round(self):
        with tempfile.TemporaryDirectory() as tmp:
            original=m.DB; m.DB=Path(tmp)/'test.sqlite'
            try:
                row=lambda n,p: dict(n=n,a='Manter',person=p,party='',origin='',status='')
                g=dict(locked=False,official=[dict(row('Educação','Ana'),source='DOU')],reference=['Educação','Saúde'])
                m.write(m.Update(revision=0,state=g))
                with m.connect() as c: uid=c.execute("INSERT INTO users(nick,status) VALUES('Teste','active')").lastrowid
                b=dict(total=40,rows=[row('Educação','Ana'),row('Saúde','Bia')],extras={})
                m.save_own(m.Update(revision=0,state={'draft':b,'bet':b}),uid)
                out=m.publish({'revision':1,'index':0}); self.assertFalse(out['state']['locked']);self.assertEqual(m.ranking(uid)['ranking'][0]['pts'],10)
                b['rows'][1]['person']='Clara';m.save_own(m.Update(revision=1,state={'draft':b,'bet':b}),uid)
                b['rows'][0]['person']='Outra'
                with self.assertRaises(HTTPException): m.save_own(m.Update(revision=2,state={'draft':b,'bet':b}),uid)
                self.assertEqual(m.ranking(uid)['ranking'][0]['pts'],10)
            finally: m.DB=original
if __name__=='__main__': unittest.main()
