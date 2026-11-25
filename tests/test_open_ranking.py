import unittest, tempfile, json
from pathlib import Path
from app import main as m
class OpenRanking(unittest.TestCase):
    def test_open(self):
        old=m.DB
        with tempfile.TemporaryDirectory() as tmp:
            m.DB=Path(tmp)/'test.sqlite'
            try:
                m.write(m.Update(revision=0,state={'reference':['Educação'],'official':[]}))
                b=dict(total=40,rows=[dict(n='Digital',a='Criar',person='Teste',party='PT',status='Novo titular')],extras={})
                with m.connect() as c:
                    for nick,st,bet in [('Junior','active',b),('Rascunho','active',None),('Excluido','deleted',b)]:
                        c.execute('INSERT INTO users(nick,status,bet) VALUES(?,?,?)',(nick,st,json.dumps(bet) if bet else None))
                r=m.ranking(0)
                self.assertFalse(r['locked']);self.assertEqual(r['participantCount'],1)
                self.assertEqual(r['ranking'][0]['nick'],'Junior');self.assertEqual(r['ranking'][0]['pts'],0)
                self.assertEqual(m.custom_ministries(),[dict(name='Digital',inOfficial=False,locked=False)])
            finally: m.DB=old
