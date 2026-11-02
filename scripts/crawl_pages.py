"""Crawlable, static English pages for OPC Radar (AI-search / GEO). Run from growth.py after ia_inject (idempotent).

Writes (all real data from site/data/items.json and site/data/digests.json, nothing invented):
  site/channel/<channel>/index.html   one page per channel: every item (title, source, date, link to the original)
  site/item/<slug>/index.html         one page per item that has a real English summary (title, summary, source numbers,
                                      link to the original + discussion, related items in the same channel)
  site/sitemap-pages.xml              channel + item URLs; appended to site/sitemap.xml (the index robots.txt points to)
It also gives every daily digest page a clear English <title>/og:title ("OPC Radar Daily Digest · <date> · <issue title>")
and Article/ItemList JSON-LD in <head> (no visible change: the in-page h1 and the language boxes are untouched).
Non-Chinese rule: every generated page is English and must contain zero Han characters; the script refuses to write otherwise.
Reuses the existing styles.css (same classes as the digest pages); no new visual components."""
import json, os, re, html, collections, shutil, datetime

D = os.path.dirname(os.path.abspath(__file__)); S = os.path.normpath(os.path.join(D, '../site'))
BASE = 'https://siinxu.github.io/ai-opportunity-hub/'
HAN = re.compile(r'[\u3400-\u9fff\uf900-\ufaff]')
e = html.escape
CH = {'ai': 'AI', 'repos': 'GitHub repos', 'products': 'New products', 'news': 'News', 'deals': 'Deals', 'ideas': 'Ideas'}
CH_DESC = {'ai': 'AI tools, models, papers and news', 'repos': 'Trending and new open-source GitHub repositories', 'products': 'New products and launches',
           'news': 'Technology news', 'deals': 'Deals, free tiers and programs for builders', 'ideas': 'Ideas and opportunities for one-person companies'}
SRC = {'精选': 'Curated'}
CF_TOKEN = '41d8abdb6f1247c08f2412afcd5f2143'
ANALYTICS = ('<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon=\'{"token":"%s"}\'></script>'
             '<script defer src="https://stats.incidental.site/events.js" data-site="opc" data-goal="outbound"></script>' % CF_TOKEN)

def en(i, k): return ((i.get(k + '_i18n') or {}).get('en') or (i.get(k) if i.get('lang') == 'en' or k == 'title' else '') or '').strip()
def clean(s): return '' if (not s or HAN.search(s)) else re.sub(r'\s+', ' ', s).strip()
def slug(i): return re.sub(r'[^A-Za-z0-9._-]+', '-', i['id']).strip('-')
def src(i): return SRC.get(i.get('source', ''), i.get('source', ''))
def cut(s, n):
    return s if len(s) <= n else s[:n].rsplit(' ', 1)[0].rstrip(',.;:') + '…'

STYLE = ('<style>.dig{padding:36px 0 56px;max-width:760px}@media (max-width:760px){.dig{padding-left:18px;padding-right:18px}}'
         '.dig .crumb{font-size:13px;color:var(--ink2);margin-bottom:18px;display:flex;gap:8px;flex-wrap:wrap}.dig .crumb a{color:var(--ink2)}'
         '.dig h1{font-size:clamp(26px,4vw,36px);letter-spacing:-.035em;line-height:1.15;margin:0 0 10px;font-weight:700}'
         '.dig .lede{color:var(--ink2);font-size:15px;margin-bottom:24px}.dig h2{font-size:17px;margin:28px 0 12px;letter-spacing:-.02em}'
         '.dig .meta{font:12px "Geist Mono",monospace;color:var(--ink3);display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}'
         '.dig ul.ops{padding-left:1.1em;margin:0;color:var(--ink2);font-size:14px}.dig ul.ops li{margin:9px 0}'
         '.dig ul.ops a{color:var(--ink);font-weight:600}.dig .sum{font-size:15px;color:var(--ink2);margin:0 0 20px}'
         '.dig .go{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin:18px 0}</style>')

def shell(rel_depth, title, desc, url, ld, body, og='website'):
    up = '../' * rel_depth
    g = {'@context': 'https://schema.org', '@graph': [{'@type': 'Organization', '@id': 'https://incidental.site/#org', 'name': 'Incidental AI', 'url': 'https://incidental.site/'}] + ld}
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<script>try{{var th=localStorage.getItem('theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');document.documentElement.dataset.theme=th}}catch(e){{}}</script>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Geist+Mono:wght@400;500&family=Geist:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="{up}styles.css?v=8">
<link rel="canonical" href="{url}">
<meta property="og:type" content="{og}"><meta property="og:site_name" content="OPC Radar"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}og.png"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(title)}"><meta name="twitter:description" content="{e(desc)}"><meta name="twitter:image" content="{BASE}og.png">
{STYLE}
<!--IA--><script type="application/ld+json">{json.dumps(g, ensure_ascii=False).replace('<', '\\u003c')}</script>{ANALYTICS}<!--/IA-->
</head><body>
<header class="nav"><div class="wrap navin">
<a class="brand" href="{up}"><span class="logo"></span>OPC Radar</a>
<nav id="navlinks"><a href="{up}">Home</a><a href="{up}digest/">Digests</a></nav>
<div class="tools"><button class="icon" id="themeBtn" aria-label="theme">◐</button></div></div></header>
<main class="wrap dig">
{body}
</main>
<footer class="wrap foot"><span>OPC Radar · opportunity radar for one-person companies</span><span>Incidental AI</span></footer>
<script>document.getElementById('themeBtn').onclick=function(){{var n=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=n;try{{localStorage.setItem('theme',n)}}catch(e){{}}}}</script>
</body></html>
'''

def build():
    data = json.load(open(os.path.join(S, 'data/items.json'), encoding='utf-8')); items = data['items']
    upd = (data.get('updated') or '')[:10] or datetime.date.today().isoformat()
    # item pages: only items with a real English title and summary
    pages = {}
    for i in items:
        t = clean(en(i, 'title'))
        if not t: continue
        i['_t'] = t; i['_s'] = clean(en(i, 'summary'))
        if i['_s'] and i.get('lang') == 'en' and (i.get('summary') or '').strip() == i['_s']: pages[i['id']] = i   # only the source's own English summary, never machine-translated text
    by_ch = collections.defaultdict(list)
    for i in sorted(items, key=lambda x: x.get('date', ''), reverse=True):
        if i.get('_t'): by_ch[i['ch']].append(i)
    out = {}; urls = []
    # ---- item pages
    for i in pages.values():
        sl = slug(i); rel = f'item/{sl}/'; url = BASE + rel; ch = i['ch']; label = CH.get(ch, ch)
        rel_items = [x for x in by_ch[ch] if x['id'] != i['id'] and x['id'] in pages][:6]
        tags = [t for t in (i.get('tags') or []) if t.isascii() and t.strip()]
        meta = [e(src(i)), e(i.get('date', ''))] + ([e(i['meta'])] if i.get('meta') and i['meta'].isascii() else []) + [e(t) for t in tags[:4]]
        body = (f'<p class="crumb"><a href="../../">OPC Radar</a><span>/</span><a href="../../channel/{ch}/">{e(label)}</a><span>/</span><span>{e(cut(i["_t"], 60))}</span></p>'
                f'<h1>{e(i["_t"])}</h1><div class="meta">{"".join(f"<span>{m}</span>" for m in meta if m)}</div>'
                f'<p class="sum">{e(i["_s"])}</p>'
                f'<div class="go"><a class="btn pri" href="{e(i["url"])}" rel="noopener" target="_blank">Read the original ↗</a>'
                + (f'<a class="btn" href="{e(i["discuss"])}" rel="noopener" target="_blank">Discussion ↗</a>' if i.get('discuss') else '') + '</div>'
                f'<p class="lede">Listed in the {e(label)} channel of OPC Radar. Source: {e(src(i))}. Title and summary come from the source;</p>'
                + ('<h2>More in ' + e(label) + '</h2><ul class="ops">' + ''.join(f'<li><a href="../{slug(x)}/">{e(x["_t"])}</a> — {e(src(x))}, {e(x.get("date", "")[:10])}</li>' for x in rel_items) + '</ul>' if rel_items else ''))
        ld = [{'@type': 'BreadcrumbList', 'itemListElement': [{'@type': 'ListItem', 'position': n + 1, 'name': nm, 'item': u} for n, (nm, u) in enumerate([('OPC Radar', BASE), (label, f'{BASE}channel/{ch}/'), (cut(i['_t'], 60), url)])]},
              {'@type': 'WebPage', '@id': url, 'url': url, 'name': i['_t'], 'inLanguage': 'en', 'description': cut(i['_s'], 300), 'isPartOf': {'@type': 'WebSite', 'name': 'OPC Radar', 'url': BASE},
               'about': {'@type': 'CreativeWork', 'name': i['_t'], 'url': i['url']}, 'publisher': {'@id': 'https://incidental.site/#org'}, 'dateModified': (i.get('date') or upd)[:10]}]
        out[os.path.join(S, rel, 'index.html')] = shell(2, f'{cut(i["_t"], 90)} — {label} | OPC Radar', cut(i['_s'], 155), url, ld, body, 'article')
        urls.append((url, (i.get('date') or upd)[:10]))
    # ---- channel pages
    for ch, lst in by_ch.items():
        rel = f'channel/{ch}/'; url = BASE + rel; label = CH.get(ch, ch)
        srcs = collections.Counter(src(x) for x in lst)
        desc = f'{len(lst)} {label} items on OPC Radar: {CH_DESC.get(ch, label)}. Sources: ' + ', '.join(f'{k} ({v})' for k, v in srcs.most_common(5)) + '.'
        lis = ''.join(f'<li><a href="{("../../item/%s/" % slug(x)) if x["id"] in pages else e(x["url"])}"{"" if x["id"] in pages else " rel=\"noopener\" target=\"_blank\""}>{e(x["_t"])}</a> — {e(src(x))}, {e(x.get("date", "")[:10])}'
                      + (f' · <a href="{e(x["url"])}" rel="noopener" target="_blank">original ↗</a>' if x['id'] in pages else '')
                      + (f'<br><span class="meta">{e(cut(x["_s"], 160))}</span>' if x['id'] in pages else '') + '</li>' for x in lst)
        nav = ' · '.join(f'<a href="../{k}/">{e(v)}</a>' if k != ch else f'<b>{e(v)}</b>' for k, v in CH.items() if k in by_ch)
        body = (f'<p class="crumb"><a href="../../">OPC Radar</a><span>/</span><span>{e(label)}</span></p><h1>{e(label)} — OPC Radar</h1>'
                f'<p class="lede">{e(desc)} Updated {e(upd)}. Channels: {nav}</p><ul class="ops">{lis}</ul>')
        ld = [{'@type': 'CollectionPage', '@id': url, 'url': url, 'name': f'{label} — OPC Radar', 'inLanguage': 'en', 'description': desc, 'dateModified': upd, 'numberOfItems': len(lst),
               'isPartOf': {'@type': 'WebSite', 'name': 'OPC Radar', 'url': BASE}, 'publisher': {'@id': 'https://incidental.site/#org'},
               'mainEntity': {'@type': 'ItemList', 'itemListElement': [{'@type': 'ListItem', 'position': n + 1, 'url': (f'{BASE}item/{slug(x)}/' if x['id'] in pages else x['url']), 'name': x['_t']} for n, x in enumerate(lst[:50])]}},
              {'@type': 'BreadcrumbList', 'itemListElement': [{'@type': 'ListItem', 'position': 1, 'name': 'OPC Radar', 'item': BASE}, {'@type': 'ListItem', 'position': 2, 'name': label, 'item': url}]}]
        out[os.path.join(S, rel, 'index.html')] = shell(2, f'{label} — latest items | OPC Radar', desc, url, ld, body)
        urls.insert(0, (url, upd))
    return out, urls

def write(out, urls):
    bad = [(p, HAN.search(s).group()) for p, s in out.items() if HAN.search(s)]
    if bad: raise SystemExit(f'crawl_pages: Han characters in English pages, nothing written: {bad[:3]}')
    for sub in ('channel', 'item'): shutil.rmtree(os.path.join(S, sub), ignore_errors=True)
    for p, s in out.items():
        os.makedirs(os.path.dirname(p), exist_ok=True); open(p, 'w', encoding='utf-8').write(s)
    sm = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + '\n'.join(f'<url><loc>{e(u)}</loc><lastmod>{m}</lastmod></url>' for u, m in urls) + '\n</urlset>\n')
    open(os.path.join(S, 'sitemap-pages.xml'), 'w', encoding='utf-8').write(sm)
    p = os.path.join(S, 'sitemap.xml'); s = open(p, encoding='utf-8').read()
    if 'sitemap-pages.xml' not in s:
        today = datetime.date.today().isoformat()
        s = s.replace('</sitemapindex>', f'<sitemap><loc>{BASE}sitemap-pages.xml</loc><lastmod>{today}</lastmod></sitemap>\n</sitemapindex>'); open(p, 'w', encoding='utf-8').write(s)

# ---------------- daily digest pages: clear English <title>, JSON-LD ----------------
def digest_title(dg):
    d = dg['date']; issue = dg['title']['en']
    issue_nodate = re.sub(r'\s*[·\-–—]\s*' + re.escape(d), '', issue).strip() or issue
    return f'OPC Radar Daily Digest · {d} · {issue_nodate}'

def digest_head(G):
    n = 0
    for dg in G['digests']:
        p = os.path.join(S, 'digest', dg['date'], 'index.html')
        if not os.path.exists(p): continue
        s = open(p, encoding='utf-8').read(); d = dg['date']; url = f'{BASE}digest/{d}/'
        title = digest_title(dg)
        desc = dg['lede']['en']
        top = dg.get('top') or []
        ld = {'@context': 'https://schema.org', '@type': 'CollectionPage', '@id': url, 'url': url, 'name': title, 'headline': title, 'inLanguage': 'en', 'description': desc,
              'datePublished': dg.get('generated') or d, 'dateModified': dg.get('generated') or d, 'isPartOf': {'@type': 'WebSite', 'name': 'OPC Radar', 'url': BASE},
              'publisher': {'@type': 'Organization', '@id': 'https://incidental.site/#org', 'name': 'Incidental AI', 'url': 'https://incidental.site/'},
              'mainEntity': {'@type': 'ItemList', 'name': f'Top items, {d}', 'itemListElement': [{'@type': 'ListItem', 'position': k + 1, 'url': x['url'], 'name': (x.get('title') or {}).get('en') if isinstance(x.get('title'), dict) else x.get('title')} for k, x in enumerate(top) if x.get('url')]}}
        for x in ld['mainEntity']['itemListElement']:
            if not x['name']: x.pop('name')
        if HAN.search(json.dumps(ld, ensure_ascii=False)): ld['mainEntity']['itemListElement'] = [{'@type': 'ListItem', 'position': k + 1, 'url': x['url']} for k, x in enumerate(top) if x.get('url')]
        block = '<!--DG--><script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace('<', '\\u003c') + '</script><!--/DG-->'
        t = e(title)
        new = re.sub(r'<title>.*?</title>', lambda m: f'<title>{t}</title>', s, count=1, flags=re.S)
        new = re.sub(r'(<meta property="og:title" content=")[^"]*(")', lambda m: m.group(1) + t + m.group(2), new, count=1)
        new = re.sub(r'<!--DG-->.*?<!--/DG-->', '', new, flags=re.S)
        new = new.replace('</head>', block + '</head>', 1)
        if new != s: open(p, 'w', encoding='utf-8').write(new); n += 1
    p = os.path.join(S, 'digest', 'index.html')   # archive page
    if os.path.exists(p):
        s = open(p, encoding='utf-8').read(); t = 'OPC Radar Daily Digest archive · every morning tech digest'
        new = re.sub(r'<title>.*?</title>', f'<title>{t}</title>', s, count=1, flags=re.S)
        if new != s: open(p, 'w', encoding='utf-8').write(new); n += 1
    return n

def main():
    out, urls = build(); write(out, urls)
    G = json.load(open(os.path.join(S, 'data/digests.json'), encoding='utf-8'))
    nd = digest_head(G)
    print(f'crawl_pages ok: {sum(1 for p in out if "/item/" in p)} item pages, {sum(1 for p in out if "/channel/" in p)} channel pages, {nd} digest heads updated')

if __name__ == '__main__': main()
