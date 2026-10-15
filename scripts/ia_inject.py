"""Generic, idempotent analytics/SEO/GEO/newsletter injector for static sites (blocks wrapped in <!--IA--> ... <!--/IA-->).
usage: python3 inject.py config.json"""
import json, os, re, sys, glob, html
C = json.load(open(sys.argv[1])) if not isinstance(sys.argv[1], dict) else sys.argv[1]
ROOT = C['root']; BASE = C['base'].rstrip('/') + '/'
LC = C.get('locales', ['zh-CN','zh-TW','en','ja','ko','ms','vi','fr','es','de'])
ORG = {'@type': 'Organization', '@id': 'https://incidental.site/#org', 'name': 'Incidental AI', 'alternateName': '偶然 AI', 'url': 'https://incidental.site/'}
ALIAS = C.get('lang_alias', {})
SUBCSS = open(C.get('subcss_path', '/workspace/stats-worker/subscribe.css')).read().replace('\n', '')
def css():
    show = ','.join(f'html[lang="{a}"] .geo-intro [data-gl="{c}"]' for c in C.get('intro', {}) for a in [c] + ALIAS.get(c, []))
    fb = C.get('intro_fallback', 'en')
    return ('<style id="ia-growth">.geo-intro{%s}.geo-intro [data-gl]{display:none}%s{display:inline}' % (C.get('intro_css', 'max-width:1120px;margin:10px auto 0;padding:0 20px;font-size:12.5px;line-height:1.55;opacity:.72'), show)
            + f'html:not([lang]) .geo-intro [data-gl="{fb}"]{{display:inline}}'
            + '.sub-band{%s}' % C.get('sub_css', 'max-width:1120px;margin:24px auto;padding:0 20px') + SUBCSS + C.get('extra_css', '') + '</style>')
def rel_of(p):
    r = os.path.relpath(p, ROOT).replace(os.sep, '/'); return re.sub(r'(^|/)index\.html$', r'\1', r)
def strip(s): return re.sub(r'<!--IA-->.*?<!--/IA-->', '', s, flags=re.S)
def text(s): return html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s))).strip()
def inject(p, meta):
    s = strip(open(p, encoding='utf-8').read()); rel = meta.get('rel', rel_of(p)); url = BASE + rel
    title = text((re.search(r'<title[^>]*>(.*?)</title>', s, re.S) or [None, ''])[1])
    if (not title or 'undefined' in title) and meta.get('title'): s = re.sub(r'<title[^>]*>.*?</title>', f'<title>{html.escape(meta["title"])}</title>', s, 1, re.S); title = meta['title']
    title = meta.get('title', title)
    desc = meta.get('desc') or C.get('desc', '')
    head = ['<!--IA-->']
    if C.get('seo', True):
        if 'name="description"' not in s and desc: head.append(f'<meta name="description" content="{html.escape(desc)}">')
        if 'rel="canonical"' not in s: head.append(f'<link rel="canonical" href="{url}">')
        if 'hreflang=' not in s and C.get('hreflang'): head.append(''.join(f'<link rel="alternate" hreflang="{l}" href="{url}?lang={l}">' for l in LC) + f'<link rel="alternate" hreflang="x-default" href="{url}">')
        if 'og:title' not in s:
            img = BASE + C['og_image']
            head.append(f'<meta property="og:type" content="{meta.get("og","website")}"><meta property="og:site_name" content="{html.escape(C["name"])}"><meta property="og:title" content="{html.escape(title)}"><meta property="og:description" content="{html.escape(desc)}"><meta property="og:url" content="{url}"><meta property="og:image" content="{img}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
                        f'<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{html.escape(title)}"><meta name="twitter:description" content="{html.escape(desc)}"><meta name="twitter:image" content="{img}">')
        g = [ORG]
        if rel == '': g.append({'@type': 'WebSite', '@id': BASE + '#site', 'name': C['name'], 'url': BASE, 'inLanguage': LC, 'publisher': {'@id': ORG['@id']}, 'description': desc})
        else:
            crumbs = [(C['name'], BASE)] + meta.get('crumbs', []) + [(title.split(' · ')[0], url)]
            g.append({'@type': 'BreadcrumbList', 'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': u} for i, (n, u) in enumerate(crumbs)]})
        g += meta.get('ld', [])
        head.append('<script type="application/ld+json">' + json.dumps({'@context': 'https://schema.org', '@graph': g}, ensure_ascii=False).replace('<', '\\u003c') + '</script>')
    head.append(css())
    head.append(f'<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon=\'{{"token":"{C["cf_token"]}"}}\'></script>'
                f'<script defer src="https://stats.incidental.site/events.js" data-site="{C["site"]}"{(" data-goal=%s" % json.dumps(C["goal"])) if C.get("goal") else ""}></script><script defer src="https://stats.incidental.site/subscribe.js"></script>')
    head.append('<!--/IA-->')
    s = s.replace('</head>', ''.join(head) + '</head>', 1)
    if C.get('intro') and not meta.get('no_intro'):
        intro = '<!--IA--><p class="geo-intro">' + ''.join(f'<span data-gl="{k}" lang="{k}">{html.escape(v)}</span>' for k, v in C['intro'].items()) + '</p><!--/IA-->'
        anchor = C.get('intro_after', '</header>')
        s = s.replace(anchor, anchor + intro, 1) if anchor in s else re.sub(r'(<body[^>]*>)', r'\1' + intro.replace('\\', '\\\\'), s, 1)
    if meta.get('ssr'):
        s = s.replace('</body>', '<!--IA--><noscript><section class="ssr-index">' + meta['ssr'] + '</section></noscript><!--/IA--></body>', 1)
    if not meta.get('no_sub'):
        sub = f'<!--IA--><aside class="sub-band" aria-label="Newsletter"><div data-ie-sub data-site="{C["site"]}" data-source="{html.escape(rel or "home")}"></div></aside><!--/IA-->'
        anchor = C.get('sub_before', '<footer')
        s = s.replace(anchor, sub + anchor, 1) if anchor in s else s.replace('</body>', sub + '</body>', 1)
    for a, b in C.get('replace', []): s = s.replace(a, b)
    open(p, 'w', encoding='utf-8').write(s)
    return url
def main():
    pages = json.load(open(C['pages'])) if isinstance(C.get('pages'), str) else C.get('pages', [])
    urls = []
    for m in pages:
        for p in glob.glob(os.path.join(ROOT, m['glob']), recursive=True) if 'glob' in m else [os.path.join(ROOT, m['file'])]:
            u = inject(p, {k: v for k, v in m.items() if k not in ('glob', 'file')})
            if not m.get('nomap'): urls.append(u)
    if C.get('seo', True):
        import datetime; today = datetime.date.today().isoformat()
        files = {'sitemap-default.xml': urls}
        for l in LC: files[f'sitemap-{l}.xml'] = [f'{u}?lang={l}' for u in urls] if C.get('hreflang') else None
        names = []
        for n, us in files.items():
            if us is None: continue
            names.append(n); open(os.path.join(ROOT, n), 'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(f'<url><loc>{html.escape(u)}</loc><lastmod>{today}</lastmod></url>' for u in us) + '\n</urlset>\n')
        open(os.path.join(ROOT, 'sitemap.xml'), 'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(f'<sitemap><loc>{BASE}{n}</loc><lastmod>{today}</lastmod></sitemap>' for n in names) + '\n</sitemapindex>\n')
        bots = ['GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot', 'Claude-Web', 'PerplexityBot', 'Google-Extended', 'Applebot-Extended']
        open(os.path.join(ROOT, 'robots.txt'), 'w').write('User-agent: *\nAllow: /\n\n# AI / generative search crawlers are welcome\n' + '\n'.join(f'User-agent: {b}\nAllow: /' for b in bots) + f'\n\nSitemap: {BASE}sitemap.xml\n')
        for n in ('llms.txt', 'llms-full.txt'):
            if C.get(n): open(os.path.join(ROOT, n), 'w', encoding='utf-8').write(C[n] if isinstance(C[n], str) else open(C[n]['file'], encoding='utf-8').read())
    print('injected', len(urls), 'pages')
main()
