#!/usr/bin/env python3
"""OPC Radar live refresh.
Sources (all free, no key needed; GITHUB_TOKEN optional for higher rate limit):
  GitHub search API (repos), Hacker News Algolia (AI / tech news / Show HN products),
  Hugging Face trending models (AI), Lobsters hottest (news), dev.to top (news), curated.json (deals/ideas).
Then translates title+summary into 10 locales with offline Argos Translate (cached in scripts/i18n_cache.json).
Run:  pip install argostranslate opencc-python-reimplemented && python3 scripts/refresh.py   (--no-translate to skip)
Output: site/data/items.json"""
import json, urllib.request, datetime, os, sys, re
D=os.path.dirname(os.path.abspath(__file__)); H={'User-Agent':'opc-radar'}
def get(u,h=H):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(u,headers=h),timeout=30))
    except Exception as e: print('skip',u[:80],e,file=sys.stderr); return None
gh=dict(H)
if os.environ.get('GITHUB_TOKEN'): gh['Authorization']='Bearer '+os.environ['GITHUB_TOKEN']
now=datetime.datetime.now(datetime.timezone.utc); items=[]; seen=set()
def add(**k):
    if k['url'] in seen: return
    seen.add(k['url']); items.append(k)
since=(now-datetime.timedelta(days=30)).date().isoformat()
for q,tag in [('topic:llm','LLM'),('topic:ai-agents','Agent'),('topic:mcp','MCP'),('topic:saas','SaaS'),('topic:rag','RAG'),('topic:automation','Automation'),('topic:chrome-extension','Extension'),('topic:self-hosted','Self-hosted'),('topic:nextjs','Next.js'),('topic:ai','AI')]:
    r=get(f'https://api.github.com/search/repositories?q={q}+pushed:>{since}+stars:>1500&sort=stars&order=desc&per_page=8',gh)
    for x in (r or {}).get('items',[]):
        add(id='gh-'+str(x['id']),ch='repos',title=x['full_name'],summary=(x['description'] or '')[:220],url=x['html_url'],tags=[tag,x.get('language') or 'Repo'],meta=f"★ {x['stargazers_count']:,}",date=x['pushed_at'][:16].replace('T',' '),lang='en',source='GitHub')
new=(now-datetime.timedelta(days=10)).date().isoformat()
r=get(f'https://api.github.com/search/repositories?q=created:>{new}&sort=stars&order=desc&per_page=20',gh)
for x in (r or {}).get('items',[]):
    add(id='gh-'+str(x['id']),ch='repos',title=x['full_name'],summary=(x['description'] or '')[:220],url=x['html_url'],tags=['New',x.get('language') or 'Repo'],meta=f"★ {x['stargazers_count']:,}",date=x['created_at'][:16].replace('T',' '),lang='en',source='GitHub · new')
def hn(query,ch,n,tags='story',pts=60,days=14):
    ts=int((now-datetime.timedelta(days=days)).timestamp())
    r=get(f'https://hn.algolia.com/api/v1/search?query={query}&tags={tags}&numericFilters=created_at_i>{ts},points>{pts}&hitsPerPage={n}')
    for x in (r or {}).get('hits',[]):
        u=x.get('url') or f"https://news.ycombinator.com/item?id={x['objectID']}"
        add(id='hn-'+x['objectID'],ch=ch,title=re.sub(r'^(Show|Launch) HN: ','',x['title']),summary='',url=u,discuss=f"https://news.ycombinator.com/item?id={x['objectID']}",tags=['HN'],meta=f"▲ {x['points']}",date=x['created_at'][:16].replace('T',' '),lang='en',source='Hacker News')
hn('AI','ai',20); hn('LLM','ai',12); hn('agent','ai',10); hn('OpenAI','ai',6); hn('','products',30,'show_hn',30); hn('Launch%20HN','products',8,'story',20,30)
hn('startup','news',10); hn('apple','news',6); hn('google','news',6); hn('','news',20,'front_page',200,3)
r=get('https://huggingface.co/api/models?sort=trendingScore&limit=20')
for x in r or []:
    add(id='hf-'+x['id'].replace('/','-'),ch='ai',title=x['id'],summary=f"Trending model on Hugging Face · {x.get('pipeline_tag') or 'model'}",url='https://huggingface.co/'+x['id'],tags=['HF',x.get('pipeline_tag') or 'model'],meta=f"♥ {x.get('likes',0):,}",date=(x.get('createdAt') or now.isoformat())[:16].replace('T',' '),lang='en',source='Hugging Face')
for x in (get('https://lobste.rs/hottest.json') or [])[:20]:
    add(id='lb-'+x['short_id'],ch='news',title=x['title'],summary=', '.join(x.get('tags',[])),url=x['url'] or x['short_id_url'],discuss=x['comments_url'],tags=['Lobsters']+x.get('tags',[])[:2],meta=f"▲ {x['score']}",date=x['created_at'][:16].replace('T',' '),lang='en',source='Lobsters')
for x in (get('https://dev.to/api/articles?top=7&per_page=15') or []):
    add(id='dt-'+str(x['id']),ch='news',title=x['title'],summary=(x.get('description') or '')[:200],url=x['url'],tags=['DEV']+x.get('tag_list',[])[:2],meta=f"♥ {x.get('positive_reactions_count',0)}",date=x['published_at'][:16].replace('T',' '),lang='en',source='DEV')
items=json.load(open(os.path.join(D,'curated.json')))+items
# ---- i18n ----
LOC=['zh-Hans','zh-Hant','en','ja','ko','ms','vi','fr','es','de']
if '--no-translate' not in sys.argv:
    import argostranslate.translate as T, opencc
    s2t=opencc.OpenCC('s2twp'); t2s=opencc.OpenCC('t2s')
    cp=os.path.join(D,'i18n_cache.json'); C=json.load(open(cp)) if os.path.exists(cp) else {}
    AC={'zh-Hans':'zh','ja':'ja','ko':'ko','ms':'ms','vi':'vi','fr':'fr','es':'es','de':'de'}
    _TR={}
    def X(t,a,b):
        k=(a,b)
        if k not in _TR: _TR[k]=T.get_translation_from_codes(a,b)
        return _TR[k].translate(t)
    def tr(text,src):
        if not text: return {}
        if text in C: return C[text]
        out={}
        en=text if src=='en' else X(text,'zh','en')
        out['en']=en
        for l,a in AC.items():
            if src=='zh' and l=='zh-Hans': out[l]=text
            else: out[l]=X(en,'en',a)
        out['zh-Hant']=s2t.convert(out['zh-Hans'])
        C[text]=out; return out
    for n,i in enumerate(items):
        keep_title = i['source'] in ('GitHub','GitHub · new','Hugging Face')  # repo/model slugs stay as-is
        if not keep_title: i['title_i18n']=tr(i['title'],i['lang'])
        i['summary_i18n']=tr(i['summary'],i['lang'])
        if n%20==0: print('translated',n,'/',len(items),flush=True); json.dump(C,open(cp,'w'),ensure_ascii=False)
    json.dump(C,open(cp,'w'),ensure_ascii=False)
json.dump(dict(updated=now.strftime('%Y-%m-%dT%H:%M:%SZ'),items=items),open(os.path.join(D,'../site/data/items.json'),'w'),ensure_ascii=False,indent=1)
print(len(items),{c:sum(1 for i in items if i['ch']==c) for c in sorted(set(i['ch'] for i in items))})
