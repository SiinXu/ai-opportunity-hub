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
for q,tag in [('topic:llm','LLM'),('topic:ai-agents','Agent'),('topic:mcp','MCP'),('topic:saas','SaaS'),('topic:rag','RAG'),('topic:automation','Automation'),('topic:chrome-extension','Extension'),('topic:self-hosted','Self-hosted'),('topic:nextjs','Next.js'),('topic:ai','AI'),('topic:developer-tools','DevTools'),('topic:open-source-alternative','Alternative'),('topic:ecommerce','E-commerce'),('topic:design-system','Design'),('topic:indie-hacker','Indie'),('topic:no-code','No-code'),('topic:productivity','Productivity'),('topic:local-llm','Local LLM')]:
    r=get(f'https://api.github.com/search/repositories?q={q}+pushed:>{since}+stars:>1500&sort=stars&order=desc&per_page=14',gh)
    for x in (r or {}).get('items',[]):
        add(id='gh-'+str(x['id']),ch='repos',title=x['full_name'],summary=(x['description'] or '')[:220],url=x['html_url'],tags=[tag,x.get('language') or 'Repo'],meta=f"★ {x['stargazers_count']:,}",date=x['pushed_at'][:16].replace('T',' '),lang='en',source='GitHub')
new=(now-datetime.timedelta(days=10)).date().isoformat()
r=get(f'https://api.github.com/search/repositories?q=created:>{new}&sort=stars&order=desc&per_page=40',gh)
for x in (r or {}).get('items',[]):
    add(id='gh-'+str(x['id']),ch='repos',title=x['full_name'],summary=(x['description'] or '')[:220],url=x['html_url'],tags=['New',x.get('language') or 'Repo'],meta=f"★ {x['stargazers_count']:,}",date=x['created_at'][:16].replace('T',' '),lang='en',source='GitHub · new')
def hn(query,ch,n,tags='story',pts=60,days=14,tag=None):
    ts=int((now-datetime.timedelta(days=days)).timestamp())
    r=get(f'https://hn.algolia.com/api/v1/search?query={query}&tags={tags}&numericFilters=created_at_i>{ts},points>{pts}&hitsPerPage={n}')
    for x in (r or {}).get('hits',[]):
        u=x.get('url') or f"https://news.ycombinator.com/item?id={x['objectID']}"
        add(id='hn-'+x['objectID'],ch=ch,pts=x.get('points',0),cmt=x.get('num_comments',0),title=re.sub(r'^(Show|Launch) HN: ','',x['title']),summary='',url=u,discuss=f"https://news.ycombinator.com/item?id={x['objectID']}",tags=['HN']+([tag] if tag else []),meta=f"▲ {x['points']}",date=x['created_at'][:16].replace('T',' '),lang='en',source='Hacker News')
hn('AI','ai',20); hn('LLM','ai',12); hn('agent','ai',10); hn('OpenAI','ai',6); hn('','products',60,'show_hn',20); hn('Launch%20HN','products',8,'story',20,30)
hn('startup','news',16); hn('SaaS','ideas',12,'story',30,30); hn('indie','ideas',10,'story',20,30); hn('side%20project','ideas',10,'story',20,30); hn('Claude','ai',10); hn('open%20source','repos',12); hn('free','deals',10,'story',40,30); hn('Ask%20HN','ideas',12,'ask_hn',40,14); hn('apple','news',6); hn('google','news',6); hn('','news',20,'front_page',200,3)
r=get('https://huggingface.co/api/models?sort=trendingScore&limit=30')
for x in r or []:
    add(id='hf-'+x['id'].replace('/','-'),ch='ai',title=x['id'],summary=f"Trending model on Hugging Face · {x.get('pipeline_tag') or 'model'}",url='https://huggingface.co/'+x['id'],tags=['HF',x.get('pipeline_tag') or 'model'],meta=f"♥ {x.get('likes',0):,}",date=(x.get('createdAt') or now.isoformat())[:16].replace('T',' '),lang='en',source='Hugging Face')
for x in (get('https://lobste.rs/hottest.json') or [])[:25]:
    add(id='lb-'+x['short_id'],ch='news',title=x['title'],summary=', '.join(x.get('tags',[])),url=x['url'] or x['short_id_url'],discuss=x['comments_url'],tags=['Lobsters']+x.get('tags',[])[:2],meta=f"▲ {x['score']}",date=x['created_at'][:16].replace('T',' '),lang='en',source='Lobsters')
for x in (get('https://dev.to/api/articles?top=7&per_page=30') or []):
    add(id='dt-'+str(x['id']),ch='news',title=x['title'],summary=(x.get('description') or '')[:200],url=x['url'],tags=['DEV']+x.get('tag_list',[])[:2],meta=f"♥ {x.get('positive_reactions_count',0)}",date=x['published_at'][:16].replace('T',' '),lang='en',source='DEV')
r=get('https://huggingface.co/api/spaces?sort=trendingScore&limit=25')
for x in r or []:
    add(id='hfs-'+x['id'].replace('/','-'),ch='products',title=x['id'],summary=f"Trending AI app on Hugging Face Spaces · {x.get('sdk') or 'space'}",url='https://huggingface.co/spaces/'+x['id'],tags=['HF Space',x.get('sdk') or 'app'],meta=f"♥ {x.get('likes',0):,}",date=(x.get('createdAt') or now.isoformat())[:16].replace('T',' '),lang='en',source='HF Spaces')

# ---- v7: more hot news / AI trends / deals / security ----
for q in ['GPT','Gemini','Anthropic','DeepSeek','Qwen','Llama','MCP','AI%20agents','coding%20agent','Cursor','vibe%20coding','reasoning%20model','open%20weights','diffusion','video%20generation','RAG','inference','GPU','Nvidia','fine-tuning','benchmark','multimodal','voice%20AI','robotics']:
    hn(q,'ai',8,'story',80,10,'Trend')
for q in ['','AI']: hn(q,'news',30,'front_page',100,2)
for q in ['vulnerability','CVE','security%20breach','zero-day','data%20leak','exploit','malware','supply%20chain%20attack']:
    hn(q,'news',6,'story',80,14,'Security')
for q in ['Microsoft','Amazon','Meta','Tesla','regulation','layoffs','acquisition','funding','EU','China','chip','privacy','Linux','Rust','browser']:
    hn(q,'news',5,'story',150,7)
for q in ['free%20tier','credits','discount','coupon','Black%20Friday','pricing%20change','open%20source%20alternative','free%20for%20students','price%20drop','lifetime%20deal']:
    hn(q,'deals',6,'story',25,60,'Deal')
for q in ['make%20money','revenue','MRR','bootstrapped','solo%20founder','niche','marketplace','acquired']:
    hn(q,'ideas',6,'story',40,45)
tsince=(now-datetime.timedelta(days=21)).date().isoformat()
for q in ['topic:llm','topic:ai-agents','topic:mcp','topic:agent','topic:rag','topic:claude','topic:llm-inference','topic:generative-ai','topic:computer-use','topic:vibe-coding']:
    r=get(f'https://api.github.com/search/repositories?q={q}+created:>{tsince}&sort=stars&order=desc&per_page=8',gh)
    for x in (r or {}).get('items',[]):
        add(id='gh-'+str(x['id']),ch='ai',title=x['full_name'],summary=(x['description'] or '')[:220],url=x['html_url'],tags=['Trend',q.split(':')[1]],meta=f"★ {x['stargazers_count']:,}",stars=x['stargazers_count'],date=x['created_at'][:16].replace('T',' '),lang='en',source='GitHub')
r=get('https://huggingface.co/api/datasets?sort=trendingScore&limit=15')
for x in r or []:
    add(id='hfd-'+x['id'].replace('/','-'),ch='ai',title=x['id'],summary="Trending dataset on Hugging Face",url='https://huggingface.co/datasets/'+x['id'],tags=['HF','dataset'],meta=f"♥ {x.get('likes',0):,}",date=(x.get('createdAt') or now.isoformat())[:16].replace('T',' '),lang='en',source='Hugging Face')
r=get('https://huggingface.co/api/daily_papers?limit=30')
for x in r or []:
    p=x.get('paper',{})
    add(id='hfp-'+p.get('id',''),ch='ai',title=p.get('title',''),summary=(p.get('summary') or '')[:220].replace('\n',' '),url='https://huggingface.co/papers/'+p.get('id',''),tags=['Paper','Trend'],meta=f"▲ {p.get('upvotes',0)}",pts=p.get('upvotes',0),date=(x.get('publishedAt') or now.isoformat())[:16].replace('T',' '),lang='en',source='HF Papers')
for x in (get('https://dev.to/api/articles?tag=ai&top=7&per_page=20') or [])+(get('https://dev.to/api/articles?tag=security&top=30&per_page=10') or []):
    add(id='dt-'+str(x['id']),ch='news',title=x['title'],summary=(x.get('description') or '')[:200],url=x['url'],tags=['DEV']+x.get('tag_list',[])[:2],meta=f"♥ {x.get('positive_reactions_count',0)}",date=x['published_at'][:16].replace('T',' '),lang='en',source='DEV')
# ---- hotness: flag top trend items + why-hot facts ----
def age_h(i):
    try: return max(1,(now-datetime.datetime.fromisoformat(i['date'].replace(' ','T')).replace(tzinfo=datetime.timezone.utc)).total_seconds()/3600)
    except Exception: return 999
for i in items:
    sc=i.get('pts',0)+i.get('cmt',0)*0.5+i.get('stars',0)*0.3
    i['heat']=round(sc/(age_h(i)+2)**0.8,2)
    if i.get('pts') or i.get('stars'): i['hot']=dict(p=i.get('pts',0),c=i.get('cmt',0),s=i.get('stars',0),h=int(age_h(i)))
    for k in ('pts','cmt','stars'): i.pop(k,None)
for ch,n in [('ai',40),('news',40),('products',15),('repos',15),('ideas',10),('deals',10)]:
    for i in sorted([x for x in items if x['ch']==ch and x.get('hot')],key=lambda x:-x['heat'])[:n]:
        i['trend']=True
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

# analytics/SEO/GEO/newsletter blocks + sitemaps/llms (scripts/growth.py)
import subprocess as _sp; _sp.run(['python3', os.path.join(D, 'growth.py')], check=True)
