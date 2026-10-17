#!/usr/bin/env python3
"""OPC Radar · automatic daily digest (每日简报).

Builds one issue for a Shanghai calendar date from real items in site/data/items.json, then updates
site/data/digests.json, site/digest/<date>/index.html, the archive page site/digest/index.html and the
digest sitemaps. Stdlib only.

usage: python3 scripts/digest.py [--date YYYY-MM-DD] [--now ISO8601]

Rules
- Issue date = Asia/Shanghai date. Publish time 07:30 Asia/Shanghai; the issue's cutoff is that moment.
  --date may backfill a missed day up to 7 days back (marked catch-up).
  Without --date, a run before 07:30 Shanghai exits 0 without doing anything (too early).
- Idempotent: if site/digest/<date>/ or a digests.json entry for <date> already exists -> exit 0, no change.
- "New item" = an item from items.json whose source timestamp (`date`, UTC) is inside the look-back window
  (cutoff-48h, cutoff], whose URL was never part of an earlier issue (scripts/digest_seen.json + URLs in
  digests.json), and whose timestamp really marks first appearance (curated entries and GitHub repos dated by
  last push are excluded). Fewer than MIN_NEW (8) new items -> no issue, exit 0 with a log line.
- Ranking: item heat (from refresh.py) x channel weight (AI/repos/products/ideas favoured over general news),
  at most PER_CH per channel in the top list.
- Never fabricates: every entry is a real item with its own source URL; summaries are the item's own
  (translated) summary or its real HN/GitHub numbers.
- i18n: zh-Hans / zh-Hant boxes + one English box served to all non-Chinese locales (same as the hand-made
  issues). The English box, <head>, and the digests.json `en` fields must contain no Han characters;
  scripts/digest_guard.py enforces this in CI before anything is committed.
GitHub Actions outputs: changed=0|1, date=<date> (written to $GITHUB_OUTPUT when set).
"""
import json, os, re, sys, html, datetime as dt
from zoneinfo import ZoneInfo
from urllib.parse import urlparse

D = os.path.dirname(os.path.abspath(__file__)); S = os.path.normpath(os.path.join(D, '../site'))
SH = ZoneInfo('Asia/Shanghai'); PUBLISH = dt.time(7, 30)
LOOKBACK_H = 48; MIN_NEW = 8; MAX_BACKFILL_D = 7; TOP_N = 8; MORE_N = 10; FOLLOW_N = 3; PER_CH = 4
BASE = 'https://siinxu.github.io/ai-opportunity-hub/'
TECH = re.compile(r'\b(AI|A\.I\.|LLMs?|GPT\w*|models?|agents?|agentic|open[- ]?source|open[- ]weights?|GitHub|code|coding|coder|developers?|API|SDK|MCP|Claude|Anthropic|OpenAI|Gemini|DeepSeek|Qwen|Llama|Mistral|Nvidia|GPU|CUDA|inference|neural|machine learning|ML|Rust|Python|JavaScript|TypeScript|Linux|kernel|compiler|database|SQL|startup|SaaS|founder|indie|app|apps|tool|tools|framework|library|browser|security|spyware|vulnerability|CVE|exploit|privacy|data|cloud|chip|robot\w*|automation|programming|software|git)\b', re.I)
HAN = re.compile(r'[\u3400-\u9fff\uf900-\ufaff]')
SEEN_P = os.path.join(D, 'digest_seen.json'); DIG_P = os.path.join(S, 'data/digests.json')
e = lambda s: html.escape(str(s or ''), quote=True)

def out(**kv):
    p = os.environ.get('GITHUB_OUTPUT')
    if p:
        with open(p, 'a') as f:
            for k, v in kv.items(): f.write(f'{k}={v}\n')

def done(msg, **kv):
    print(msg); out(**kv); sys.exit(0)

def parse_args(a):
    r = {}
    for k in ('--date', '--now'):
        if k in a: r[k[2:]] = a[a.index(k) + 1]
    return r

def item_ts(i):
    try: return dt.datetime.fromisoformat(i['date'].strip().replace(' ', 'T')[:16]).replace(tzinfo=dt.timezone.utc)
    except Exception: return None

def eligible(i):
    """True when the item's timestamp marks when it first appeared (not curated, not 'last pushed')."""
    src = i.get('source') or ''
    if src in ('精选', '') or i.get('lang') == 'zh' and src == '精选': return False
    if src == 'GitHub' and not ({'New', 'Trend'} & set(i.get('tags') or [])): return False   # pushed_at
    return bool(i.get('url'))

def loc(i, f, L):
    m = i.get(f + '_i18n') or {}
    v = (m.get(L) or '').strip()
    if v: return v
    base = (i.get(f) or '').strip()
    return base if (L.startswith('zh') or not HAN.search(base)) else ''

def host(u):
    try: return urlparse(u).hostname or ''
    except Exception: return ''

FACT = {
 'zh-Hans': {'hn': 'Hacker News {p} 分 · {c} 条评论', 'gh': 'GitHub {s} 星', 'src': '来源：{x}'},
 'zh-Hant': {'hn': 'Hacker News {p} 分 · {c} 則留言', 'gh': 'GitHub {s} 星', 'src': '來源：{x}'},
 'en': {'hn': '{p} points · {c} comments on Hacker News', 'gh': '{s} stars on GitHub', 'src': 'Source: {x}'},
}
def fact(i, L):
    h = i.get('hot') or {}; F = FACT[L]
    if h.get('s'): return F['gh'].format(s=f"{h['s']:,}")
    if h.get('p') and i.get('source') == 'Hacker News': return F['hn'].format(p=h['p'], c=h.get('c', 0))
    src = i.get('source') or ''
    src = src.replace(' · new', '')
    return F['src'].format(x=src) if src and not HAN.search(src) else ''

ORIG = {'zh-Hans': '原标题：', 'zh-Hant': '原標題：'}
def summary(i, L):
    s = loc(i, 'summary', L); f = fact(i, L)
    if L.startswith('zh') and not s and i.get('lang') != 'zh' and title(i, L) != i.get('title'):
        s = ORIG[L] + (i.get('title') or '')   # machine-translated title -> show the original next to it
    if L == 'en' and HAN.search(s): s = ''
    s = s[:220] + ('…' if len(s) > 220 else '')
    sep = '。' if L.startswith('zh') else '. '
    if s and f: return s.rstrip('。.') + sep + f
    return s or f

def title(i, L):
    t = loc(i, 'title', L) or (i.get('title') or '')
    if L == 'en' and HAN.search(t): return ''
    return t

T = {
 'zh-Hans': dict(home='首页', arch='每日简报', h1='早间技术热点 · {d}', h1b='早间技术热点 · {d}（补发）',
   lede='上海时间 {d} 07:30 自动生成：从上一期以来 OPC Radar 新收录的 {n} 条信号里，按热度挑出最值得看的内容。',
   ledeb='补发：按上海时间 {d} 07:30 的截止点事后自动生成，收录当时新出现的 {n} 条信号。',
   top='① 今日热点（Top {k}）', more='② 更多新信号', follow='③ 值得跟进',
   note='全部条目来自公开来源（Hacker News、GitHub、Hugging Face 等），附原文链接；自动生成，未编造数据。',
   label='早间技术热点', labelb='早间技术热点（补发）', disc='讨论'),
 'zh-Hant': dict(home='首頁', arch='每日簡報', h1='早間技術熱點 · {d}', h1b='早間技術熱點 · {d}（補發）',
   lede='上海時間 {d} 07:30 自動生成：從上一期以來 OPC Radar 新收錄的 {n} 條信號裡，按熱度挑出最值得看的內容。',
   ledeb='補發：按上海時間 {d} 07:30 的截止點事後自動生成，收錄當時新出現的 {n} 條信號。',
   top='① 今日熱點（Top {k}）', more='② 更多新信號', follow='③ 值得跟進',
   note='全部條目來自公開來源（Hacker News、GitHub、Hugging Face 等），附原文連結；自動生成，未編造數據。',
   label='早間技術熱點', labelb='早間技術熱點（補發）', disc='討論'),
 'en': dict(home='Home', arch='Daily digests', h1='Morning tech digest · {d}', h1b='Morning tech digest · {d} (catch-up)',
   lede='Generated automatically at 07:30 Asia/Shanghai on {d}: the hottest of the {n} signals OPC Radar picked up since the previous issue.',
   ledeb='Catch-up issue: generated afterwards for the 07:30 Asia/Shanghai cutoff on {d}, from the {n} signals that were new at that time.',
   top="① Today's top {k}", more='② More new signals', follow='③ Worth following',
   note='Every entry comes from a public source (Hacker News, GitHub, Hugging Face, …) with its original link; generated automatically, no invented metrics.',
   label='Morning tech digest', labelb='Morning tech digest (catch-up)', disc='discussion'),
}
BOXES = ['zh-Hans', 'zh-Hant', 'en']
BEACON = ('<!--IA--><script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon=\'{"token":"41d8abdb6f1247c08f2412afcd5f2143"}\'></script>'
          '<script defer src="https://stats.incidental.site/events.js" data-site="opc" data-goal="outbound"></script><!--/IA-->')

def links(it):
    a = [it['url']] + it.get('extra', [])
    return ' · '.join(f'<a href="{e(u)}" rel="noopener" target="_blank">{e(host(u))}</a>' for u in a)

def box(dg, L):
    t = T[L]; d = dg['date']; cb = dg.get('kind') == 'catch-up'
    top = ''.join(f'<li><div><b>{e(x["title"][L])}</b><p>{e(x["summary"][L])}</p><div class="ln">{links(x)}</div></div></li>' for x in dg['top'])
    h = [f'<div class="langbox" data-lang="{L}">',
         f'<p class="crumb"><a href="../../">{t["home"]}</a><span>/</span><a href="../">{t["arch"]}</a><span>/</span><span>{d}</span></p>',
         f'<h1>{e(dg["title"][L])}</h1>', f'<p class="lede">{e(dg["lede"][L])}</p>',
         f'<h2>{t["top"].format(k=len(dg["top"]))}</h2>', f'<ol class="top box" style="padding:4px 18px 8px">{top}</ol>']
    if dg.get('more'):
        h += [f'<h2>{t["more"]}</h2>', '<ul class="ops">' + ''.join(
            f'<li><a href="{e(x["url"])}" rel="noopener" target="_blank">{e(x["title"][L])}</a> — {e(x["summary"][L] or host(x["url"]))}</li>' for x in dg['more']) + '</ul>']
    if dg.get('follow'):
        h += [f'<h2>{t["follow"]}</h2>', '<ul class="ops">' + ''.join(
            f'<li class="follow"><a href="{e(x["url"])}" rel="noopener" target="_blank">{e(x["title"][L])}</a> — {e(x["summary"][L])}</li>' for x in dg['follow']) + '</ul>']
    h += [f'<p class="note">{t["note"]}</p>', '</div>']
    return '\n'.join(h)

def page(dg):
    d = dg['date']; ti = e(dg['title']['en']); de = e(dg['lede']['en']); url = f'{BASE}digest/{d}/'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{ti} · OPC Radar</title>
<meta name="description" content="{de}">
<script>try{{var th=localStorage.getItem('theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');document.documentElement.dataset.theme=th}}catch(e){{}}</script>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Geist+Mono:wght@400;500&family=Geist:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="../../styles.css?v=8">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article"><meta property="og:site_name" content="OPC Radar">
<meta property="og:title" content="{ti} · OPC Radar">
<meta property="og:description" content="{de}">
<meta property="og:url" content="{url}">
<style>
.dig{{padding:36px 0 56px;max-width:720px}}
.dig .crumb{{font-size:13px;color:var(--ink2);margin-bottom:18px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}}
.dig .crumb a{{color:var(--ink2)}}.dig .crumb a:hover{{color:var(--ink)}}
.dig h1{{font-size:clamp(26px,4vw,36px);letter-spacing:-.035em;line-height:1.15;margin:0 0 10px;font-weight:700}}
.dig .lede{{color:var(--ink2);font-size:15px;margin-bottom:28px}}
.dig h2{{font-size:17px;margin:28px 0 12px;letter-spacing:-.02em}}
.dig ol.top{{list-style:none;padding:0;margin:0;counter-reset:n}}
.dig ol.top li{{counter-increment:n;padding:14px 0;border-top:1px solid var(--line2);display:grid;grid-template-columns:28px 1fr;gap:10px}}
.dig ol.top li::before{{content:counter(n,decimal-leading-zero);font:500 12px "Geist Mono",monospace;color:var(--ink3);padding-top:3px}}
.dig ol.top b{{display:block;font-size:15px;font-weight:600;letter-spacing:-.01em;margin-bottom:4px}}
.dig ol.top p{{color:var(--ink2);font-size:13.5px;margin:0 0 6px}}
.dig ol.top .ln{{font:12px "Geist Mono",monospace;color:var(--ink3);display:flex;gap:10px;flex-wrap:wrap}}
.dig ol.top .ln a{{color:var(--ink2);text-decoration:underline;text-underline-offset:2px}}
.dig ul.ops{{padding-left:1.1em;margin:0;color:var(--ink2);font-size:14px}}
.dig ul.ops li{{margin:8px 0}}
.dig .follow a{{font-weight:600}}
.dig .note{{margin-top:32px;font-size:12px;color:var(--ink3)}}
.dig .langbox[hidden]{{display:none!important}}
.dig-tools{{display:flex;gap:8px;align-items:center;margin-left:auto}}
</style>
{BEACON}
</head><body>
<header class="nav"><div class="wrap navin">
<a class="brand" href="../../"><span class="logo"></span>OPC Radar</a>
<nav id="navlinks"><a href="../../">Home</a><a href="../">Digests</a></nav>
<div class="tools"><select id="langSel" aria-label="language"></select>
<button class="icon" id="themeBtn" aria-label="theme">◐</button></div></div></header>
<main class="wrap dig">
{''.join(box(dg, L) for L in BOXES)}
</main>
<footer class="wrap foot"><span>OPC Radar · daily digest</span><span>{d}</span></footer>
<script src="../../i18n.js?v=8"></script>
<script>
const LANGS_D={{"zh-Hans":"简体中文","zh-Hant":"繁體中文",en:"English",ja:"日本語",ko:"한국어",ms:"Bahasa Melayu",vi:"Tiếng Việt",fr:"Français",es:"Español",de:"Deutsch"}};
function pickLang(){{try{{const q=new URLSearchParams(location.search).get('lang');if(q&&LANGS_D[q])return q}}catch(e){{}}const s=localStorage.getItem('lang');if(s&&LANGS_D[s])return s;const n=(navigator.language||'en').toLowerCase();if(n.startsWith('zh'))return/(tw|hk|mo|hant)/.test(n)?'zh-Hant':'zh-Hans';return'en'}}
let L=pickLang();document.documentElement.lang=/^zh/.test(L)?L:'en';
const sel=document.getElementById('langSel');
sel.innerHTML=Object.entries(LANGS_D).map(([k,v])=>`<option value="${{k}}">${{v}}</option>`).join('');
sel.value=L;
function apply(){{
  const zh=/^zh/.test(L);document.documentElement.lang=zh?L:'en';
  document.querySelectorAll('.langbox').forEach(el=>{{
    const want=el.dataset.lang;
    if(want==='zh-Hans')el.hidden=!(L==='zh-Hans');
    else if(want==='zh-Hant')el.hidden=!(L==='zh-Hant');
    else el.hidden=zh; // en box for all non-zh
  }});
  document.title=(zh?(L==='zh-Hant'?document.querySelector('[data-lang=zh-Hant] h1')?.textContent:document.querySelector('[data-lang=zh-Hans] h1')?.textContent):document.querySelector('[data-lang=en] h1')?.textContent)+' · OPC Radar';
}}
sel.onchange=()=>{{L=sel.value;localStorage.setItem('lang',L);apply()}};
document.getElementById('themeBtn').onclick=()=>{{const n=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=n;localStorage.setItem('theme',n)}};
apply();
</script>
</body></html>
'''

LEGACY_LABEL = {  # hand-made issues (e56cd18) keep their original archive labels
 '2026-10-17': {'zh-Hans': '早间技术热点', 'zh-Hant': '早間技術熱點', 'en': 'Morning tech digest'},
 '2026-10-13': {'zh-Hans': '技术热点简报（补发）', 'zh-Hant': '技術熱點簡報（補發）', 'en': 'Tech digest (catch-up)'},
}
def label(dg, L):
    if dg.get('label'): return dg['label'].get(L) or dg['label'].get('en', '')
    return LEGACY_LABEL.get(dg['date'], {}).get(L) or T[L]['label']

def write_archive(digs):
    p = os.path.join(S, 'digest/index.html'); s = open(p, encoding='utf-8').read()
    for L in BOXES:
        lis = '\n'.join(f'<li><a href="{d["date"]}/"><b>{d["date"]}</b></a> — {e(label(d, L))}</li>' for d in digs)
        s, n = re.subn(r'(<div class="langbox" data-lang="%s">.*?<ul class="ops">\n?).*?(\n?</ul>)' % re.escape(L),
                       lambda m: m.group(1) + lis + m.group(2), s, count=1, flags=re.S)
        if n != 1: sys.exit(f'archive: langbox {L} not found')
    open(p, 'w', encoding='utf-8').write(s)

def add_beacon(path):
    s = open(path, encoding='utf-8').read()
    if 'stats.incidental.site/events.js' in s: return False
    s = s.replace('</head>', BEACON + '\n</head>', 1); open(path, 'w', encoding='utf-8').write(s); return True

def sitemaps(date):
    loc_ = f'{BASE}digest/{date}/'
    for f in ('sitemap-default.xml', 'sitemap-en.xml', 'sitemap-zh-Hans.xml', 'sitemap-zh-Hant.xml'):
        p = os.path.join(S, f)
        if not os.path.exists(p): continue
        s = open(p, encoding='utf-8').read()
        if loc_ in s: continue
        blk = f'  <url>\n    <loc>{loc_}</loc>\n    <lastmod>{date}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>0.7</priority>\n  </url>\n'
        anchor = f'    <loc>{BASE}digest/</loc>'
        if anchor in s:  # insert right after the archive entry so the newest issue comes first
            i = s.index('</url>', s.index(anchor)) + len('</url>\n'); s = s[:i] + blk + s[i:]
        else: s = s.replace('</urlset>', blk + '</urlset>')
        open(p, 'w', encoding='utf-8').write(s)

def entry(i, with_extra=True):
    r = {'id': i.get('id'), 'title': {L: title(i, L) for L in BOXES}, 'summary': {L: summary(i, L) for L in BOXES}, 'url': i['url']}
    if with_extra and i.get('discuss') and i['discuss'] != i['url']: r['extra'] = [i['discuss']]
    return r

def main():
    a = parse_args(sys.argv[1:])
    now = dt.datetime.fromisoformat(a['now']) if a.get('now') else dt.datetime.now(dt.timezone.utc)
    if a.get('date'):
        date = dt.date.fromisoformat(a['date'])
    else:
        date = now.astimezone(SH).date()
    cutoff = dt.datetime.combine(date, PUBLISH, SH).astimezone(dt.timezone.utc)
    ds = date.isoformat(); kind = 'daily'
    if now < cutoff:
        if a.get('date'): done(f'digest {ds}: cutoff {cutoff:%F %H:%M} UTC is in the future; refusing to publish early', changed=0, date=ds)
        done(f'digest {ds}: before 07:30 Asia/Shanghai publish time; nothing to do', changed=0, date=ds)
    if (now - cutoff) > dt.timedelta(days=MAX_BACKFILL_D):
        done(f'digest {ds}: older than {MAX_BACKFILL_D} days; items.json is a rolling snapshot, refusing to backfill', changed=0, date=ds)
    if (now - cutoff) > dt.timedelta(hours=20): kind = 'catch-up'   # generated well after the morning cutoff

    G = json.load(open(DIG_P, encoding='utf-8')) if os.path.exists(DIG_P) else {'latest': None, 'digests': []}
    if any(x['date'] == ds for x in G['digests']) or os.path.exists(os.path.join(S, 'digest', ds, 'index.html')):
        done(f'digest {ds}: already published; nothing to do (idempotent)', changed=0, date=ds)

    data = json.load(open(os.path.join(S, 'data/items.json'), encoding='utf-8'))
    seen = json.load(open(SEEN_P)) if os.path.exists(SEEN_P) else {}
    used = set()
    for x in G['digests']:
        for k in ('top', 'more', 'follow'):
            for it in x.get(k) or []: used.add(it.get('url')); used.update(it.get('extra') or [])
    for urls in seen.values(): used.update(urls)
    lo = cutoff - dt.timedelta(hours=LOOKBACK_H)
    cand, dedup = [], set()
    for i in data['items']:
        ts = item_ts(i)
        if not ts or not (lo < ts <= cutoff) or not eligible(i): continue
        if i['url'] in used or i['url'] in dedup: continue
        if not title(i, 'en'): continue   # cannot show it on non-Chinese pages without leaking Han
        dedup.add(i['url']); cand.append(i)
    print(f'digest {ds}: window ({lo:%F %H:%M}, {cutoff:%F %H:%M}] UTC · {len(cand)} new items (min {MIN_NEW})')
    if len(cand) < MIN_NEW:
        done(f'digest {ds}: only {len(cand)} new items since the previous issue (< {MIN_NEW}); not publishing an empty issue', changed=0, date=ds)

    # OPC focus: AI / repos / products / ideas first; general front-page news is down-weighted
    W = {'ai': 1.5, 'repos': 1.3, 'products': 1.3, 'ideas': 1.2, 'deals': 1.0, 'news': 0.6}
    def rel(i):  # topical relevance: HN search matches are loose, so check the item's own text
        if not (i.get('source') or '').startswith('Hacker News'): return 1.0
        txt = ' '.join([i.get('title') or '', loc(i, 'summary', 'en'), i.get('url') or ''])
        return 1.6 if TECH.search(txt) else 0.15
    cand.sort(key=lambda i: (-(i.get('heat') or 0) * W.get(i['ch'], 1.0) * rel(i), i['url']))
    top, perch = [], {}
    for i in cand:
        if len(top) >= TOP_N: break
        if perch.get(i['ch'], 0) >= PER_CH: continue
        perch[i['ch']] = perch.get(i['ch'], 0) + 1; top.append(i)
    rest = [i for i in cand if i not in top]
    def stars(i): return (i.get('hot') or {}).get('s') or int(re.sub(r'\D', '', i.get('meta') or '') or 0) if '★' in (i.get('meta') or '') else 0
    follow = sorted([i for i in rest if i.get('source', '').startswith('GitHub') and stars(i)], key=lambda i: -stars(i))[:FOLLOW_N]
    more = [i for i in rest if i not in follow][:MORE_N]

    n = len(cand); tk = 'h1b' if kind == 'catch-up' else 'h1'; lk = 'ledeb' if kind == 'catch-up' else 'lede'
    dg = {'date': ds, 'path': f'digest/{ds}/', 'kind': kind, 'auto': True,
          'cutoff': cutoff.strftime('%Y-%m-%dT%H:%M:%SZ'), 'generated': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'new_count': n,
          'title': {L: T[L][tk].format(d=ds) for L in BOXES}, 'lede': {L: T[L][lk].format(d=ds, n=n) for L in BOXES},
          'label': {L: T[L]['labelb' if kind == 'catch-up' else 'label'] for L in BOXES},
          'top': [entry(i) for i in top], 'more': [entry(i, False) for i in more], 'follow': [entry(i, False) for i in follow]}
    # provenance: every URL must be a real item from items.json
    real = {i['url'] for i in data['items']}
    for k in ('top', 'more', 'follow'):
        for it in dg[k]:
            assert it['url'] in real, it['url']
    G['digests'] = sorted([x for x in G['digests'] if x['date'] != ds] + [dg], key=lambda x: x['date'], reverse=True)
    G['latest'] = G['digests'][0]['date']
    json.dump(G, open(DIG_P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    os.makedirs(os.path.join(S, 'digest', ds), exist_ok=True)
    open(os.path.join(S, 'digest', ds, 'index.html'), 'w', encoding='utf-8').write(page(dg))
    write_archive(G['digests'])
    for f in ['digest/index.html'] + [f'digest/{x["date"]}/index.html' for x in G['digests']]:
        p = os.path.join(S, f)
        if os.path.exists(p): add_beacon(p)
    sitemaps(ds)
    seen[ds] = sorted(dedup)
    keep = sorted(seen)[-45:]; seen = {k: seen[k] for k in keep}
    json.dump(seen, open(SEEN_P, 'w'), ensure_ascii=False, indent=0)
    done(f'digest {ds}: published {kind} issue · top {len(top)}, more {len(more)}, follow {len(follow)} from {n} new items', changed=1, date=ds)

if __name__ == '__main__': main()
