import unicodedata

def norm(v):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFD',str(v or '')) if not unicodedata.combining(c)).lower().split())
REWARDS={'Criar':15,'Extinguir':15,'Fundir':20,'Dividir':20,'Renomear':10}
def key(r):
    return (norm(r.get('n')),r.get('a'),norm(r.get('origin')) if r.get('a') in ('Fundir','Dividir','Renomear') else '')
def score(p,g):
    official=[r for r in g.get('published',[]) if r.get('source','').strip()]; final=g.get('final',False)
    pts=hits=parties=struct=0
    for r in p.get('rows',[]):
        o=next((x for x in official if norm(x.get('n'))==norm(r.get('n'))),None)
        a=r.get('a'); n=norm(r.get('person')); party=norm(r.get('party')); status=r.get('status')
        if a in REWARDS:
            if any(key(x)==key(r) and x.get('structureConfirmed') for x in official): pts+=REWARDS[a];struct+=1
            elif final or (o and o.get('structureConfirmed')): pts-=3 if a=='Renomear' else 5
        if a=='Extinguir': continue
        if not o or (o.get('a')=='Extinguir' and o.get('structureConfirmed')):
            if final or o:
                pts-=2 if n else 0;pts-=1 if party else 0
                pts-=1 if status else 0
            continue
        on=norm(o.get('person')); op=norm(o.get('party')); os=o.get('status')
        nh=bool(n and on and (n==on or n in o.get('nameAliases',[]))); ph=bool(party and op and party==op); sh=bool(status and os and status==os)
        if nh: pts+=10;hits+=1
        elif n and on: pts+=2 if any(norm(x.get('person'))==n for x in official) else -2
        if ph: pts+=5;parties+=1
        elif party and op: pts-=1
        if sh: pts+=3
        elif status and os: pts-=1
        if nh and ph and sh: pts+=2
    if final:
        d=abs(int(p.get('total',0))-int(g.get('total',0)));pts+= [50,30,20,10,5][d] if d<5 else 0
    for k,v in p.get('extras',{}).items():
        actual=g.get('publishedExtras',{}).get(k)
        if v not in ('',None) and actual not in ('',None) and int(v)==int(actual): pts+=10
    return dict(pts=pts,hits=hits,parties=parties,struct=struct)
