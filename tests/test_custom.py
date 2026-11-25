import tempfile, unittest, json
from pathlib import Path
from fastapi import HTTPException
from app import main as m
class Custom(unittest.TestCase):
    def test_custom(self):
        with tempfile.TemporaryDirectory() as tmp:
            old=m.DB; m.DB=Path(tmp)/'test.sqlite'
            try:
                m.write(m.Update(revision=0,state={'reference':['Educação'],'official':[]}))
                row=lambda n: dict(n=n,a='Criar',person='Pessoa teste',party='PT',status='Novo titular')
                b=dict(total=40,rows=[row('Educação'),row('Ministério Digital')],extras={})
                with m.connect() as c:
                    for nick,st,bet in [('A','active',b),('B','active',dict(b,rows=[row('MINISTERIO DIGITAL')])),('C','deleted',dict(b,rows=[row('Excluído')])),('D','active',None)]:
                        c.execute('INSERT INTO users(nick,status,bet,draft) VALUES(?,?,?,?)',(nick,st,json.dumps(bet) if bet else None,json.dumps(dict(b,rows=[row('Rascunho')]))))
                self.assertEqual(m.custom_ministries(),[dict(name='Ministério Digital',inOfficial=False,locked=False)])
                m.write(m.Update(revision=1,state={'reference':['Educação'],'official':[dict(row('Ministério Digital'),source='Teste',structureConfirmed=True)]}))
                self.assertTrue(m.custom_ministries()[0]['inOfficial'])
                m.publish({'revision':2,'index':0})
                self.assertTrue(m.custom_ministries()[0]['locked'])
                self.assertEqual(m.ranking(0)['ranking'][0]['pts'],35)
                with self.assertRaises(HTTPException): m.admin(1)
            finally: m.DB=old
