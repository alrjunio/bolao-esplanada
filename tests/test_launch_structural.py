"""Extended approved structural scoring regression suite."""
import unittest
from app.scoring import score

def row(a='Criar', n='Pasta A', origin='', person='', party='', status=''):
    return dict(a=a,n=n,origin=origin,person=person,party=party,status=status)
def official(a='Criar',n='Pasta A',origin='',structureConfirmed=True):
    return dict(row(a=a,n=n,origin=origin),source='DOU',structureConfirmed=structureConfirmed)

class StructuralRules(unittest.TestCase):
    def test_create_reward(self):
        self.assertEqual(score({'rows':[row()]},{'published':[official()]})['pts'],15)
    def test_create_penalty(self):
        self.assertEqual(score({'rows':[row()]},{'published':[official(a='Manter')]})['pts'],-5)
    def test_rename_reward(self):
        self.assertEqual(score({'rows':[row(a='Renomear',origin='Antiga')]},{'published':[official(a='Renomear',origin='Antiga')]})['pts'],10)
    def test_rename_penalty(self):
        self.assertEqual(score({'rows':[row(a='Renomear',origin='Antiga')]},{'published':[official(a='Manter')]})['pts'],-3)
    def test_fusion_reward(self):
        self.assertEqual(score({'rows':[row(a='Fundir',origin='A+B')]},{'published':[official(a='Fundir',origin='A+B')]})['pts'],20)
    def test_division_reward(self):
        self.assertEqual(score({'rows':[row(a='Dividir',origin='A')]},{'published':[official(a='Dividir',origin='A')]})['pts'],20)
    def test_extinction_reward(self):
        self.assertEqual(score({'rows':[row(a='Extinguir')]},{'published':[official(a='Extinguir')]})['pts'],15)
    def test_unconfirmed_structure_neutral(self):
        self.assertEqual(score({'rows':[row()]},{'published':[official(structureConfirmed=False)]})['pts'],0)
    def test_unpublished_neutral(self):
        self.assertEqual(score({'rows':[row()]},{'published':[]})['pts'],0)

if __name__ == '__main__':
    unittest.main()
