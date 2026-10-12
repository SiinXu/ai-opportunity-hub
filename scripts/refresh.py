#!/usr/bin/env python3
"""Refresh feed data: GitHub repos (search API), HN AI/tech news + Show HN products.
Curated ideas/deals live in scripts/curated.json and are merged in. Output: site/data/items.json"""
import json, urllib.request, datetime, os, subprocess
H={'User-Agent':'ai-opportunity-hub'}
def get(u,h=H):
    return json.load(urllib.request.urlopen(urllib.request.Request(u,headers=h),timeout=30))
tok=os.environ.get('GITHUB_TOKEN')
gh=dict(H); 
if tok: gh['Authorization']='Bearer '+tok
since=(datetime.date.today()-datetime.timedelta(days=30)).isoformat()
items=[]
for q,tag in [('topic:llm','LLM'),('topic:ai-agents','Agent'),('topic:mcp','MCP'),('topic:saas','SaaS')]:
    r=get(f'https://api.github.com/search/repositories?q={q}+pushed:>{since}+stars:>2000&sort=stars&order=desc&per_page=5',gh)
    for x in r['items']:
        if any(i['url']==x['html_url'] for i in items): continue
        items.append(dict(id='gh-'+str(x['id']),ch='repos',title=x['full_name'],summary=(x['description'] or '')[:220],url=x['html_url'],tags=[tag,x.get('language') or 'Repo'],meta=f"★ {x['stargazers_count']:,}",date=x['pushed_at'][:10],lang='en',source='GitHub'))
def hn(query,ch,n,tags='story'):
    ts=int((datetime.datetime.now()-datetime.timedelta(days=14)).timestamp())
    r=get(f'https://hn.algolia.com/api/v1/search?query={query}&tags={tags}&numericFilters=created_at_i>{ts},points>80&hitsPerPage={n}')
    for x in r['hits']:
        u=x.get('url') or f"https://news.ycombinator.com/item?id={x['objectID']}"
        if any(i['url']==u for i in items): continue
        items.append(dict(id='hn-'+x['objectID'],ch=ch,title=x['title'].replace('Show HN: ',''),summary='',url=u,discuss=f"https://news.ycombinator.com/item?id={x['objectID']}",tags=['HN'],meta=f"▲ {x['points']}",date=x['created_at'][:10],lang='en',source='Hacker News'))
hn('AI','ai',12); hn('LLM','ai',6); hn('','products',12,'show_hn'); hn('startup','news',6); hn('apple','news',4)
cur=json.load(open(os.path.join(os.path.dirname(__file__),'curated.json')))
items=cur+items
json.dump(dict(updated=datetime.datetime.utcnow().isoformat()+'Z',items=items),open(os.path.join(os.path.dirname(__file__),'../site/data/items.json'),'w'),ensure_ascii=False,indent=1)
print(len(items),{c:sum(1 for i in items if i['ch']==c) for c in set(i['ch'] for i in items)})
