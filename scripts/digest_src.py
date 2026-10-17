#!/usr/bin/env python3
"""Real source text for digest items (stdlib only). Never invents anything: every string returned was taken
from the item's own source (page meta description / article paragraphs, GitHub description + README,
HN self-post text, the feed's own summary). Returns '' when nothing usable could be fetched.

source_text(item) -> {'desc': short description (<= ~200 chars), 'excerpt': longer excerpt (<= ~1000 chars),
                      'kind': where it came from}"""
import json, os, re, html, gzip, urllib.request
from html.parser import HTMLParser
from urllib.parse import urlparse

UA = {'User-Agent': 'Mozilla/5.0 (compatible; OPCRadarDigest/1.0; +https://radar.incidental.site/)',
      'Accept': 'text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8', 'Accept-Encoding': 'gzip'}
HAN = re.compile(r'[\u3400-\u9fff\uf900-\ufaff]')

BROWSER = dict(UA, **{'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36'})

def _get(u, h=None, limit=2_500_000, timeout=20):
    r = _get1(u, h, limit, timeout)
    if not r and h is None: r = _get1(u, BROWSER, limit, timeout)   # some sites reject bot user agents
    return r

def _get1(u, h, limit, timeout):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=h or UA), timeout=timeout)
        b = r.read(limit)
        if r.headers.get('Content-Encoding') == 'gzip':
            try: b = gzip.decompress(b)
            except Exception: pass
        cs = r.headers.get_content_charset() or 'utf-8'
        return b.decode(cs, 'replace')
    except Exception as ex:
        print('  src skip', u[:90], type(ex).__name__, str(ex)[:60]); return ''

def clean(s):
    s = html.unescape(s or ''); s = re.sub(r'<[^>]+>', ' ', s); s = s.replace('\u200b', '')
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def trim(s, n):
    """Cut at a sentence end before n chars if possible, else at a word boundary, add an ellipsis."""
    s = clean(s)
    if len(s) <= n: return s
    cut = s[:n]
    m = max(cut.rfind('. '), cut.rfind('! '), cut.rfind('? '), cut.rfind('。'))
    if m > n * 0.55: return cut[:m + 1].strip()
    sp = cut.rfind(' ')
    return (cut[:sp] if sp > n * 0.6 else cut).rstrip(' ,;:-—') + '…'

class _P(HTMLParser):
    SKIP = {'script', 'style', 'nav', 'header', 'footer', 'aside', 'noscript', 'form', 'svg', 'button', 'figcaption'}
    def __init__(s):
        super().__init__(convert_charrefs=True); s.meta = {}; s.paras = []; s.skip = 0; s.inp = 0; s.buf = []; s.title = ''; s.int = False
    def handle_starttag(s, t, a):
        a = dict(a)
        if t == 'meta':
            k = (a.get('property') or a.get('name') or '').lower()
            if k in ('description', 'og:description', 'twitter:description') and a.get('content'): s.meta.setdefault(k, a['content'])
        elif t == 'title': s.int = True
        elif t in s.SKIP: s.skip += 1
        elif t in ('p', 'li') and not s.skip: s.inp += 1; s.buf = [] if s.inp == 1 else s.buf
    def handle_endtag(s, t):
        if t == 'title': s.int = False
        elif t in s.SKIP: s.skip = max(0, s.skip - 1)
        elif t in ('p', 'li') and s.inp:
            s.inp -= 1
            if not s.inp:
                txt = clean(''.join(s.buf))
                if len(txt) >= 60 and t == 'p': s.paras.append(txt)
    def handle_data(s, d):
        if s.int: s.title += d
        if s.inp and not s.skip: s.buf.append(d)

GENERIC = re.compile(r'(^update\b|^note:|cookie|javascript|sign in|log in|subscribe|newsletter|all rights reserved|enable js|privacy policy|^posted on|^by [A-Z])', re.I)

def from_html(u):
    h = _get(u)
    if not h: return '', ''
    p = _P()
    try: p.feed(h)
    except Exception: pass
    paras = [x for x in p.paras if not GENERIC.search(x[:80])]
    title = clean(p.title).lower()
    desc = ''
    for k in ('og:description', 'description', 'twitter:description'):
        v = clean(p.meta.get(k, ''))
        if len(v) >= 40 and v.lower() != title and not GENERIC.search(v[:80]): desc = v; break
    if re.search(r'(\[\.\.\.\]|\.\.\.|…)$', desc) and paras: desc = paras[0]   # truncated meta -> first paragraph
    if sum(len(x) for x in paras) < 400:   # list-style articles: fall back to the <article>/<main> text
        t = re.sub(r'<(script|style|nav|header|footer|aside)[^>]*>.*?</\1>', ' ', h, flags=re.S | re.I)
        m = re.search(r'<(article|main)[^>]*>(.*?)</\1>', t, re.S | re.I)
        if m:
            body = clean(m.group(2))
            if len(body) > sum(len(x) for x in paras) + 200: paras = [body]
    ex = ''
    for x in paras:
        if len(ex) > 6000: break
        ex = (ex + ' ' + x).strip()
    if not desc and paras: desc = paras[0]
    return desc, ex

def _md_paras(md):
    md = re.sub(r'```.*?```', ' ', md, flags=re.S); md = re.sub(r'<!--.*?-->', ' ', md, flags=re.S)
    out = []
    for blk in re.split(r'\n\s*\n', md):
        b = blk.strip()
        if not b or b.startswith(('#', '|', '>', '[![', '![', '<p align', '<img', '<div', '<a ', '---', '===')): continue
        if re.match(r'^(\s*[-*+]\s|\s*\d+\.\s)', b) and len(out) == 0: continue
        b = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', b); b = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', b)
        b = re.sub(r'[*_`]{1,3}', '', b); b = clean(b)
        if len(b) >= 50 and len(re.findall(r'[A-Za-z]{2,}', b)) >= 6: out.append(b)
    return out

def from_github(u):
    m = re.match(r'https?://github\.com/([^/]+)/([^/#?]+)', u)
    if not m: return '', ''
    o, r = m.group(1), m.group(2)
    h = {'User-Agent': 'opc-radar', 'Accept': 'application/vnd.github+json'}
    if os.environ.get('GITHUB_TOKEN'): h['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    desc = ''
    try: desc = clean(json.loads(_get(f'https://api.github.com/repos/{o}/{r}', h) or '{}').get('description') or '')
    except Exception: pass
    h2 = dict(h, Accept='application/vnd.github.raw')
    md = _get(f'https://api.github.com/repos/{o}/{r}/readme', h2) or ''
    paras = _md_paras(md)
    ex = ''
    for x in paras:
        if len(ex) > 6000: break
        ex = (ex + ' ' + x).strip()
    return desc or (paras[0] if paras else ''), ex

def from_hn_self(discuss):
    m = re.search(r'id=(\d+)', discuss or '')
    if not m: return ''
    try: return clean(json.loads(_get(f'https://hn.algolia.com/api/v1/items/{m.group(1)}') or '{}').get('text') or '')
    except Exception: return ''

def source_text(i):
    u = i.get('url') or ''; own = clean(i.get('summary') or '') if not HAN.search(i.get('summary') or '') else ''
    desc = ex = ''; kind = ''
    if host(u) == 'github.com':
        desc, ex = from_github(u); kind = 'github'
    elif 'news.ycombinator.com/item' in u:
        desc = ex = from_hn_self(u); kind = 'hn'
    elif u:
        desc, ex = from_html(u); kind = 'page'
    if not desc and own: desc, kind = own, 'feed'
    if not ex and own: ex = own
    if len(ex) < 500 and i.get('discuss') and 'news.ycombinator.com' in i['discuss']:   # author's own Show HN text
        t = from_hn_self(i['discuss'])
        if t: ex = (ex + ' ' + t).strip(); desc = desc or t; kind = kind or 'hn'
    if not ex: ex = desc
    return {'desc': trim(desc, 200), 'excerpt': trim(ex, 1000), 'full': trim(ex, 6000), 'kind': kind if desc else ''}

def host(u):
    try: return (urlparse(u).hostname or '').removeprefix('www.')
    except Exception: return ''

