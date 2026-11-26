import os, sqlite3, json, secrets, hashlib, time, re
from contextlib import contextmanager
from fastapi import Request, Response
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .scoring import score, norm
PARTIES = ['AGIR', 'AVANTE', 'CIDADANIA', 'DC', 'DEMOCRATA', 'MDB', 'MISSÃO', 'MOBILIZA', 'NOVO', 'PCB', 'PCdoB', 'PCO', 'PDT', 'PL', 'PODE', 'PP', 'PRD', 'PRTB', 'PSB', 'PSD', 'PSDB', 'PSOL', 'PSTU', 'PT', 'PV', 'REDE', 'REPUBLICANOS', 'SOLIDARIEDADE', 'UNIÃO', 'UP', 'Sem filiação partidária']

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
security = HTTPBasic()
DB = Path(os.environ.get('DB_PATH', 'data/bolao.sqlite3'))

def auth(c: HTTPBasicCredentials = Depends(security)):
    password = os.environ.get('ADMIN_PASSWORD', '')
    if not password or not secrets.compare_digest(c.username.encode(), os.environ.get('ADMIN_USER','admin').encode()) or not secrets.compare_digest(c.password.encode(), password.encode()):
        raise HTTPException(401, 'Acesso restrito', headers={'WWW-Authenticate':'Basic'})

@contextmanager
def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=10)
    c.execute('CREATE TABLE IF NOT EXISTS game (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, state TEXT NOT NULL)')
    c.commit()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, nick TEXT UNIQUE COLLATE NOCASE, salt TEXT, password TEXT, revision INTEGER DEFAULT 0, draft TEXT, bet TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, uid INTEGER, expires INTEGER)")
    if 'status' not in {r[1] for r in c.execute('PRAGMA table_info(users)')}:
        c.execute("ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
    c.execute('CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, ts INTEGER, action TEXT, detail TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS attempts (key TEXT PRIMARY KEY, count INTEGER, since INTEGER)')
    c.commit()
    try:
        with c: yield c
    finally: c.close()

class Update(BaseModel):
    revision: int
    state: dict

def game(c):
    row=c.execute('SELECT revision,state FROM game WHERE id=1').fetchone()
    if not row: return 0,None
    g=json.loads(row[1]); g.setdefault('lockedPastas',[norm(r.get('n')) for r in g.get('published',[]) if norm(r.get('n'))]); g.setdefault('extrasLocked',bool(g.get('published') or g.get('publishedExtras'))); return row[0],g

def digest(password,salt):
    return hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()

def session(request: Request):
    token=request.cookies.get('bolao_session','')
    with connect() as c:
        row=c.execute('SELECT uid FROM sessions WHERE token=? AND expires>?',(hashlib.sha256(token.encode()).hexdigest(),int(time.time()))).fetchone()
        if row and row[0] and not c.execute("SELECT 1 FROM users WHERE id=? AND status='active'",(row[0],)).fetchone(): row=None
    if not row: raise HTTPException(401,'Entre na sua conta')
    return row[0]

def admin(uid=Depends(session)):
    if uid!=0: raise HTTPException(403,'Área administrativa')

class Login(BaseModel):
    nick:str
    password:str
    invite:str=''

def cookie(response,uid):
    token=secrets.token_urlsafe(32)
    with connect() as c:
        c.execute('DELETE FROM sessions WHERE expires<?',(int(time.time()),))
        c.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),uid,int(time.time())+43200))
    response.set_cookie('bolao_session',token,httponly=True,samesite='strict',secure=os.getenv('COOKIE_SECURE','0')=='1',max_age=43200)

@app.middleware('http')
async def protect(request,call_next):
    if request.method in ('POST','PUT','DELETE') and request.headers.get('content-type','').split(';')[0]!='application/json':
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail':'JSON obrigatório'},415)
    response=await call_next(request)
    response.headers['Cache-Control']='no-store'
    return response

@app.get('/')
def index():
    return FileResponse(Path(__file__).parent/'static/index.html')

@app.post('/api/register')
def register(body:Login,response:Response,request:Request):
    throttle(request, "register")
    nick=body.nick.strip(); invite=os.getenv('INVITE_CODE','')
    if not invite or not secrets.compare_digest(invite.encode(),body.invite.encode()): raise HTTPException(403,'Convite inválido')
    if not 2<=len(nick)<=60 or not 10<=len(body.password)<=128 or nick.casefold()==os.getenv('ADMIN_USER','admin').casefold(): raise HTTPException(422,'Apelido ou senha inválidos (mínimo 10 caracteres de senha)')
    salt=secrets.token_hex(16)
    with connect() as c:
        try: uid=c.execute('INSERT INTO users(nick,salt,password) VALUES(?,?,?)',(nick,salt,digest(body.password,salt))).lastrowid
        except sqlite3.IntegrityError: raise HTTPException(409,'Apelido em uso')
    cookie(response,uid); return {'role':'participant'}

@app.post('/api/login')
def login(body:Login,response:Response,request:Request):
    throttle(request, "login")
    if len(body.password)>128: raise HTTPException(401,'Credenciais inválidas')
    if body.nick==os.getenv('ADMIN_USER','admin') and os.getenv('ADMIN_PASSWORD') and secrets.compare_digest(body.password.encode(),os.environ['ADMIN_PASSWORD'].encode()): uid=0
    else:
        with connect() as c: row=c.execute("SELECT id,salt,password FROM users WHERE nick=? AND status='active'",(body.nick.strip(),)).fetchone()
        if not row or not secrets.compare_digest(digest(body.password,row[1]),row[2]): raise HTTPException(401,'Credenciais inválidas')
        uid=row[0]
    cookie(response,uid); return {'role':'admin' if uid==0 else 'participant'}

@app.post('/api/logout')
def logout(request:Request,response:Response):
    with connect() as c: c.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(request.cookies.get('bolao_session','').encode()).hexdigest(),))
    response.delete_cookie('bolao_session'); return {'ok':True}

@app.get('/api/me')
def me(uid=Depends(session)):
    return {'role':'admin' if uid==0 else 'participant'}

@app.get('/api/state',dependencies=[Depends(admin)])
def read():
    with connect() as c:
        rev,state=game(c)
        if state and state.get('locked'):
            state['players']=[json.loads(r[0]) for r in c.execute('SELECT bet FROM users WHERE bet IS NOT NULL AND status="active"')]+state.get('players',[])
    return {'revision':rev,'state':state}

@app.put('/api/state',dependencies=[Depends(admin)])
def write(update:Update):
    with connect() as c:
        c.execute('BEGIN IMMEDIATE'); rev,old=game(c)
        if rev!=update.revision: raise HTTPException(409,'Recarregue a página')
        state=update.state
        if old and old.get('final'):
            raise HTTPException(409,'Apuração finalizada')
        if old and old.get('locked') and not state.get('locked'): raise HTTPException(409,'Rodada encerrada não pode ser reaberta')
        for k in ('published','publishedExtras','lockedPastas','extrasLocked','radar'):
            state[k]=(old or {}).get(k, [] if k in ('published','lockedPastas','radar') else False if k=='extrasLocked' else {})
        if state.get('final') and not (old or {}).get('final'):
            validate_final(state); state['locked']=True; state['extrasLocked']=True
        # Participant bets are never overwritten by the administrative snapshot.
        state['players']=old.get('players',[]) if old else []
        raw=json.dumps(state,ensure_ascii=False,allow_nan=False)
        if len(raw.encode())>5_000_000: raise HTTPException(413,'Dados muito grandes')
        c.execute('INSERT INTO game VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,state=excluded.state',(rev+1,raw))
    return {'revision':rev+1}

@app.get('/api/own')
def own(uid=Depends(session)):
    if uid==0: raise HTTPException(403,'Use administração')
    with connect() as c:
        _,g=game(c); g=g or {}; nick,rev,draft,bet=c.execute('SELECT nick,revision,draft,bet FROM users WHERE id=?',(uid,)).fetchone()
        return {'revision':rev,'state':{'nick':nick,'reference':g.get('reference'), 'locked':g.get('locked',False),'lockedPastas':g.get('lockedPastas',[]),'extrasLocked':g.get('extrasLocked',False),'draft':json.loads(draft) if draft else None,'bet':json.loads(bet) if bet else None}}

@app.put('/api/own')
def save_own(update:Update,uid=Depends(session)):
    if uid==0: raise HTTPException(403,'Use administração')
    with connect() as c:
        c.execute('BEGIN IMMEDIATE'); _,g=game(c)
        if g and (g.get('locked') or g.get('final')): raise HTTPException(409,'Rodada encerrada')
        nick,rev,old_d,old_b=c.execute('SELECT nick,revision,draft,bet FROM users WHERE id=?',(uid,)).fetchone()
        if rev!=update.revision: raise HTTPException(409,'Recarregue a página')
        d=update.state.get('draft'); bet=update.state.get('bet')
        for value in (d,bet):
            if value is not None:
                if not isinstance(value,dict) or not isinstance(value.get('rows'),list) or len(value['rows'])>200: raise HTTPException(422,'Aposta inválida')
                validate_bet(value, strict=value is bet, check_party=value is bet and value != (json.loads(old_b) if old_b else None))
                value['nick']=nick
        g=g or {}
        for new, previous in ((d,old_d),(bet,old_b)):
            prior=json.loads(previous) if previous else {}
            new=new or {}
            frozen=set(g.get('lockedPastas',[]))
            def frozen_rows(x): return sorted([json.dumps(r,sort_keys=True) for r in x.get('rows',[]) if norm(r.get('n')) in frozen])
            if frozen_rows(new)!=frozen_rows(prior): raise HTTPException(409,'Pasta bloqueada: recarregue e preserve os palpites existentes')
            if g.get('extrasLocked') and (new.get('extras',{})!=prior.get('extras',{}) or str(new.get('total',40))!=str(prior.get('total',40))): raise HTTPException(409,'Palpites extras e total bloqueados')
        audit(c,'bet_update',{'uid':uid,'previous':json.loads(old_b) if old_b else None,'bet':bet})
        raw=json.dumps([d,bet],ensure_ascii=False,allow_nan=False)
        if len(raw.encode())>200000: raise HTTPException(413,'Aposta muito grande')
        if not c.execute("SELECT 1 FROM users WHERE id=? AND status='active'",(uid,)).fetchone(): raise HTTPException(403,'Conta indisponível')
        c.execute('UPDATE users SET revision=?,draft=?,bet=? WHERE id=?',(rev+1,json.dumps(d) if d else None,json.dumps(bet) if bet else None,uid))
    return {'revision':rev+1}

def throttle(request, kind):
    key=kind+':'+(request.client.host if request.client else 'unknown'); now=int(time.time())
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        r=c.execute('SELECT count,since FROM attempts WHERE key=?',(key,)).fetchone()
        if r and now-r[1]<300 and r[0]>=20: raise HTTPException(429,'Muitas tentativas. Tente em cinco minutos.')
        c.execute('INSERT OR REPLACE INTO attempts VALUES(?,?,?)',(key,r[0]+1 if r and now-r[1]<300 else 1,r[1] if r and now-r[1]<300 else now))

def integer(v,low=0):
    try: return not isinstance(v,bool) and float(v)==int(float(v)) and low<=int(float(v))<=10000
    except (TypeError,ValueError,OverflowError): return False

def validate_bet(b,strict=False,check_party=True):
    if strict and not integer(b.get('total'),1): raise HTTPException(422,'Total inválido')
    names=[]
    for r in b['rows']:
        if not isinstance(r,dict) or any(not isinstance(r.get(k,''),str) or len(r.get(k,''))>500 for k in ('n','a','origin','person','party','status')): raise HTTPException(422,'Registro inválido')
        if r.get('a') not in ('Manter','Criar','Extinguir','Fundir','Dividir','Renomear',''): raise HTTPException(422,'Ação inválida')
        if r.get('status','') not in ('','Permanece','Novo titular'): raise HTTPException(422,'Situação inválida')
        if check_party and r.get('party') and norm(r['party']) not in {norm(x) for x in PARTIES}: raise HTTPException(422,'Selecione um partido da lista')
        names.append(norm(r.get('n')))
    if strict and (not names or '' in names or len(set(names))!=len(names) or any(not r.get('a') for r in b['rows'])): raise HTTPException(422,'Pastas inválidas ou duplicadas')
    e=b.get('extras',{})
    if not isinstance(e,dict) or any(k not in ('0','1','2','3') or (v not in ('',None) and not integer(v)) for k,v in e.items()): raise HTTPException(422,'Extras inválidos')

def audit(c,action,detail): c.execute('INSERT INTO audit(ts,action,detail) VALUES(?,?,?)',(int(time.time()),action,json.dumps(detail,ensure_ascii=False)))

@app.get('/api/users',dependencies=[Depends(admin)])
def users():
    with connect() as c:
        return [dict(id=i,nick=n,status=s,registered=bool(b)) for i,n,s,b in c.execute('SELECT id,nick,status,bet FROM users ORDER BY nick')]

@app.post('/api/users/{uid}',dependencies=[Depends(admin)])
def manage(uid:int,body:dict):
    action=body.get('action'); mapping={'delete':'deleted','suspend':'suspended','activate':'active'}
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        if not c.execute('SELECT 1 FROM users WHERE id=?',(uid,)).fetchone(): raise HTTPException(404,'Conta inexistente')
        if action in mapping: c.execute('UPDATE users SET status=? WHERE id=?',(mapping[action],uid))
        elif action=='purge':
            if body.get('confirm')!='EXCLUIR' or not c.execute("SELECT 1 FROM users WHERE id=? AND status='deleted'",(uid,)).fetchone(): raise HTTPException(409,'Exclua logicamente primeiro e confirme')
            c.execute('DELETE FROM users WHERE id=?',(uid,))
        elif action=='password':
            pw=body.get('password','')
            if not isinstance(pw,str) or not 10<=len(pw)<=128: raise HTTPException(422,'Senha de 10 a 128 caracteres')
            salt=secrets.token_hex(16);c.execute('UPDATE users SET salt=?,password=? WHERE id=?',(salt,digest(pw,salt),uid))
        else: raise HTTPException(422,'Ação inválida')
        c.execute('DELETE FROM sessions WHERE uid=?',(uid,));audit(c,'participant_'+action,{'id':uid})
    return {'ok':True}

@app.post('/api/publish',dependencies=[Depends(admin)])
def publish(body:dict):
    with connect() as c:
        c.execute('BEGIN IMMEDIATE');rev,g=game(c)
        if not g or g.get('final'): raise HTTPException(409,'Apuração indisponível')
        if body.get('revision')!=rev: raise HTTPException(409,'Recarregue a página')
        if body.get('extras'):
            g['extrasLocked']=True
            e=g.get('extras',{});validate_bet({'rows':[],'extras':e});g['publishedExtras']=e.copy()
        else:
            idx=body.get('index');rows=g.get('official',[])
            if not isinstance(idx,int) or not 0<=idx<len(rows): raise HTTPException(422,'Registro inválido')
            r=rows[idx].copy();validate_bet({'rows':[r]})
            if not norm(r.get('n')) or not r.get('source','').strip() or not (r.get('structureConfirmed') or any(r.get(k) for k in ('person','party','status'))): raise HTTPException(422,'Informe fonte e pelo menos um campo confirmado')
            g['lockedPastas']=sorted(set(g.get('lockedPastas',[]))|{norm(r['n'])}|{norm(x) for x in body.get('related',[]) if isinstance(x,str) and x.strip()});g['extrasLocked']=True
            published=g.get('published',[]); r['nameAliases']=next((x.get('nameAliases',[]) for x in published if norm(x.get('n'))==norm(r['n']) and norm(x.get('person'))==norm(r.get('person'))),[]);oldkey=r.get('publishedKey',norm(r['n']));published=[x for x in published if norm(x['n'])!=oldkey and norm(x['n'])!=norm(r['n'])];published.append(r);g['published']=published;rows[idx]['publishedKey']=norm(r['n'])
        audit(c,'publish',{'index':body.get('index'),'extras':bool(body.get('extras'))});c.execute('UPDATE game SET revision=?,state=? WHERE id=1',(rev+1,json.dumps(g,ensure_ascii=False)))
    return {'revision':rev+1,'state':g}

def validate_final(g):
    rows=g.get('published',[])
    if not integer(g.get('total'),1) or not rows or any(not r.get('structureConfirmed') or (r.get('a')!='Extinguir' and not all(r.get(k) for k in ('person','party','status'))) for r in rows): raise HTTPException(422,'Publique e confirme todos os resultados antes de finalizar')
    if len([r for r in rows if r.get('a')!='Extinguir'])!=int(g['total']): raise HTTPException(422,'Total oficial deve coincidir com as pastas publicadas não extintas')

@app.get('/api/ranking')
def ranking(uid=Depends(session)):
    with connect() as c:
        _,g=game(c);g=g or {};a=[]
        for nick,bet in c.execute("SELECT nick,bet FROM users WHERE status='active' AND bet IS NOT NULL"):
            try: a.append(dict(nick=nick,**score(json.loads(bet),g)))
            except (ValueError,TypeError,KeyError): continue
        # Competitively tied displayed scores remain tied: no unapproved tiebreakers.
        for entry in a:
            entry['pts'] = max(0, entry['pts'])
        # Alphabetical ordering is presentation-only and does not resolve ties.
        a.sort(key=lambda p:(-p['pts'],p['nick'].casefold()))
        # Public ranking contains only nickname and displayed points.
        public_ranking=[{'nick':entry['nick'],'pts':entry['pts']} for entry in a]
        return {'ranking':public_ranking,'participantCount':len(a),'published':g.get('published',[]),'locked':bool(g.get('locked') or g.get('published') or g.get('publishedExtras')),'final':g.get('final',False)}

@app.get('/api/audit',dependencies=[Depends(admin)])
def history():
    with connect() as c: return [dict(ts=t,action=a,detail=json.loads(d)) for t,a,d in c.execute("SELECT ts,action,detail FROM audit WHERE action!='bet_update' ORDER BY id DESC LIMIT 100")]

@app.post('/api/lock-pasta',dependencies=[Depends(admin)])
def lock_pasta(body:dict):
    with connect() as c:
        c.execute('BEGIN IMMEDIATE'); rev,g=game(c)
        if not g or g.get('final') or body.get('revision')!=rev: raise HTTPException(409,'Recarregue a página')
        names=body.get('names',[])
        if not isinstance(names,list) or any(not isinstance(n,str) for n in names): raise HTTPException(422,'Pastas inválidas')
        g['lockedPastas']=sorted(set(g.get('lockedPastas',[]))|{norm(n) for n in names if norm(n)})
        g['extrasLocked']=True
        audit(c,'lock_pasta',{'names':names});c.execute('UPDATE game SET revision=?,state=? WHERE id=1',(rev+1,json.dumps(g,ensure_ascii=False)))
    return {'revision':rev+1,'state':g}

def backup_game():
    folder=DB.parent/'backups'; folder.mkdir(mode=0o700,exist_ok=True)
    dest=folder/f'pre-controle-{int(time.time())}-{secrets.token_hex(4)}.sqlite3'
    with sqlite3.connect(DB) as src, sqlite3.connect(dest) as dst:
        src.backup(dst)
        if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise HTTPException(500,'Backup inválido')
    dest.chmod(0o600)
    return dest.name

@app.post('/api/competition-control',dependencies=[Depends(admin)])
def competition_control(body:dict):
    action=body.get('action')
    if body.get('confirm')!='REINICIAR' and action in ('reset','annul'): raise HTTPException(422,'Confirmação necessária')
    with connect() as c:
        c.execute('BEGIN IMMEDIATE'); rev,g=game(c)
        if not g or body.get('revision')!=rev: raise HTTPException(409,'Recarregue a página')
        if action=='backup': return {'backup':backup_game()}
        published=g.get('published',[])
        if action in ('unlock','unlock_all','unlock_extras'):
            if g.get('locked') or g.get('final'): raise HTTPException(409,'Rodada encerrada; use reinicialização se for teste')
            if action=='unlock_extras':
                if published or g.get('publishedExtras'): raise HTTPException(409,'Há resultados publicados; extras permanecem bloqueados')
                g['extrasLocked']=False
            else:
                frozen=set(g.get('lockedPastas',[])); protected={norm(r.get('n')) for r in published}
                if any(r.get('a') in ('Fundir','Dividir','Renomear') for r in published): protected=frozen.copy()
                names={norm(body.get('name'))} if action=='unlock' else frozen-protected
                if names & protected: raise HTTPException(409,'Resultado publicado ou mudança estrutural relacionada')
                g['lockedPastas']=sorted(frozen-names)
        elif action=='annul':
            if g.get('final'): raise HTTPException(409,'Apuração finalizada; use reinicialização apenas para testes')
            name=norm(body.get('name'))
            if not any(norm(r.get('n'))==name for r in published): raise HTTPException(404,'Resultado não encontrado')
            backup_game()
            g['published']=[r for r in published if norm(r.get('n'))!=name]
            for r in g.get('official',[]):
                if norm(r.get('publishedKey'))==name or norm(r.get('n'))==name: r.pop('publishedKey',None)
            # Anulação não reabre palpites automaticamente.
        elif action=='reset':
            backup_game()
            for k,v in dict(official=[],published=[],publishedExtras={},lockedPastas=[],extrasLocked=False,locked=False,final=False,extras={},players=[]).items(): g[k]=v
            g['total']=40
            if body.get('clearBets') is True: c.execute('UPDATE users SET draft=NULL,bet=NULL,revision=revision+1')
            else: c.execute('UPDATE users SET revision=revision+1')
        else: raise HTTPException(422,'Ação inválida')
        if action!='reset': c.execute('UPDATE users SET revision=revision+1')
        audit(c,'competition_'+action,{'name':body.get('name'),'clearBets':body.get('clearBets') is True})
        c.execute('UPDATE game SET revision=?,state=? WHERE id=1',(rev+1,json.dumps(g,ensure_ascii=False)))
    return {'revision':rev+1,'state':g}

@app.post('/api/reset-test',dependencies=[Depends(admin)])
def reset_test(body:dict):
    if body.get('confirm')!='LIMPAR TESTES': raise HTTPException(422,'Confirmação necessária')
    with connect() as c:
        c.execute('BEGIN IMMEDIATE'); rev,g=game(c)
        if c.execute("SELECT 1 FROM users WHERE status!='deleted'").fetchone(): raise HTTPException(409,'Exclua as contas de teste primeiro. Não use com participantes reais.')
        if not g: return {'ok':True}
        for k,v in dict(official=[],published=[],publishedExtras={},lockedPastas=[],extrasLocked=False,locked=False,final=False,extras={},players=[]).items(): g[k]=v
        g['total']=40
        c.execute('UPDATE users SET draft=NULL,bet=NULL,revision=revision+1')
        c.execute('UPDATE game SET revision=?,state=? WHERE id=1',(rev+1,json.dumps(g,ensure_ascii=False)))
        audit(c,'reset_test',{})
    return {'ok':True}


@app.get('/api/name-review',dependencies=[Depends(admin)])
def name_review():
    from difflib import SequenceMatcher
    with connect() as c:
        _,g=game(c);g=g or {}; out=[]
        for o in g.get('published',[]):
            target=norm(o.get('person')); pasta=norm(o.get('n'))
            if not target: continue
            counts={}
            for (raw,) in c.execute("SELECT bet FROM users WHERE status='active' AND bet IS NOT NULL"):
                for r in json.loads(raw).get('rows',[]):
                    name=r.get('person',''); n=norm(name)
                    if norm(r.get('n'))!=pasta or not n or n==target: continue
                    counts[name]=counts.get(name,0)+1
            for name,count in counts.items():
                ratio=SequenceMatcher(None,norm(name),target).ratio()
                out.append(dict(pasta=o['n'],official=o['person'],name=name,count=count,similarity=round(ratio*100),approved=norm(name) in o.get('nameAliases',[])))
        return sorted(out,key=lambda x:-x['similarity'])

@app.post('/api/name-review',dependencies=[Depends(admin)])
def review_name(body:dict):
    with connect() as c:
        c.execute('BEGIN IMMEDIATE');rev,g=game(c)
        if not g or g.get('final'): raise HTTPException(409,'Apuração finalizada ou indisponível')
        o=next((r for r in g.get('published',[]) if norm(r.get('n'))==norm(body.get('pasta'))),None)
        name=norm(body.get('name'))
        if not o or not name or norm(o.get('person'))!=norm(body.get('official')): raise HTTPException(409,'Resultado mudou. Recarregue')
        if not any(norm(r.get('n'))==norm(o['n']) and norm(r.get('person'))==name for (raw,) in c.execute("SELECT bet FROM users WHERE status='active' AND bet IS NOT NULL") for r in json.loads(raw).get('rows',[])): raise HTTPException(422,'Nome não encontrado nas apostas')
        aliases=set(o.get('nameAliases',[]))
        if body.get('approve') is True: aliases.add(name)
        else: aliases.discard(name)
        o['nameAliases']=sorted(aliases)
        audit(c,'name_review',{'pasta':o['n'],'name':name,'approve':body.get('approve') is True})
        c.execute('UPDATE game SET revision=?,state=? WHERE id=1',(rev+1,json.dumps(g,ensure_ascii=False)))
    return {'ok':True}


@app.get('/api/custom-ministries',dependencies=[Depends(admin)])
def custom_ministries():
    with connect() as c:
        _,g=game(c); g=g or {}
        known={norm(n) for n in g.get('reference',[])}
        official={norm(r.get('n')) for r in g.get('official',[])+g.get('published',[])}
        locked=set(g.get('lockedPastas',[]))
        names={}
        for (raw,) in c.execute("SELECT bet FROM users WHERE status='active' AND bet IS NOT NULL"):
            for r in json.loads(raw).get('rows',[]):
                n=r.get('n','').strip(); k=norm(n)
                if k and k not in known:
                    names.setdefault(k,n)
        return [dict(name=names[k],inOfficial=k in official,locked=k in locked) for k in sorted(names)]

@app.get('/api/radar')
def get_radar():
    """Only editorial entries; never includes individual participant guesses."""
    with connect() as c:
        revision,g=game(c)
        return {'revision':revision,'entries':(g or {}).get('radar',[])}

@app.post('/api/radar',dependencies=[Depends(admin)])
def edit_radar(body:dict):
    """Manual editorial radar, versioned with the existing game state."""
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        revision,g=game(c)
        if g is None or body.get('revision')!=revision:
            raise HTTPException(409,'Recarregue o Radar antes de alterar')
        entries=list(g.get('radar',[]))
        if body.get('action')=='add':
            name=body.get('ministry'); person=body.get('person'); source=body.get('source')
            confidence=body.get('confidence')
            if (not all(isinstance(v,str) and 1<=len(v.strip())<=300 for v in (name,person,source))
                    or type(confidence) is not int or not 0<=confidence<=100
                    or len(entries)>=100):
                raise HTTPException(422,'Informe pasta, nome, fonte e índice entre 0 e 100')
            entries.append(dict(ministry=name.strip(),person=person.strip(),
                                source=source.strip(),confidence=confidence,
                                updatedAt=int(time.time())))
        elif body.get('action')=='remove':
            index=body.get('index')
            if type(index) is not int or not 0<=index<len(entries):
                raise HTTPException(422,'Registro inválido')
            entries.pop(index)
        else:
            raise HTTPException(422,'Ação inválida')
        g['radar']=entries
        audit(c,'radar_'+body['action'],{'count':len(entries)})
        c.execute('UPDATE game SET revision=?,state=? WHERE id=1',
                  (revision+1,json.dumps(g,ensure_ascii=False)))
    return {'revision':revision+1,'entries':entries}
