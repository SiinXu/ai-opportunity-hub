"""Generic, idempotent analytics/SEO/GEO/newsletter injector for static sites (blocks wrapped in <!--IA--> ... <!--/IA-->).

usage: python3 inject.py config.json [--dry-run OUTDIR]

  --dry-run OUTDIR  write every output (pages, sitemaps, robots, llms) under OUTDIR instead of in place.

Hard rule (enforced): non-Chinese pages (en/ja/ko/ms/vi/fr/es/de) must not contain Chinese in the
rendered page or the HTML source. Only "Incidental AI" is used there; the Chinese brand name and Chinese
intros are emitted only on pages whose own language is zh-CN / zh-TW. A site whose single HTML serves all
languages (front-end language switch, `hreflang: true` with ?lang=, or `single_page_i18n: true`) counts
as a non-Chinese page. Every output is scanned before anything is written; on a violation nothing is
written and the script exits 2.
"""
import json, os, re, sys, glob, html, datetime

HAN = re.compile(r'[\u4e00-\u9fff]')
ORG_ZH_ALT = '偶然 AI'  # allowed only on zh-CN / zh-TW pages


def is_zh(lang): return (lang or '').lower().startswith('zh')


def load_config(argv):
    args = list(argv[1:]); dry = None
    if '--dry-run' in args:
        i = args.index('--dry-run'); dry = args[i + 1]; del args[i:i + 2]
    if len(args) != 1: sys.exit(__doc__)
    return json.load(open(args[0], encoding='utf-8')), dry


C, DRY = load_config(sys.argv) if __name__ == '__main__' else ({}, None)


def setup(cfg):
    global C, ROOT, BASE, LC, ALIAS, SINGLE, SUBCSS
    C = cfg; ROOT = C['root']; BASE = C['base'].rstrip('/') + '/'
    LC = C.get('locales', ['zh-CN', 'zh-TW', 'en', 'ja', 'ko', 'ms', 'vi', 'fr', 'es', 'de'])
    ALIAS = C.get('lang_alias', {})
    # one HTML for all languages (language picked in the browser) -> the source must be Chinese-free
    SINGLE = bool(C.get('single_page_i18n', C.get('hreflang')))
    p = C.get('subcss_path', '/workspace/stats-worker/subscribe.css')
    SUBCSS = open(p).read().replace('\n', '') if os.path.exists(p) else ''


def org(lang):
    o = {'@type': 'Organization', '@id': 'https://incidental.site/#org', 'name': 'Incidental AI', 'url': 'https://incidental.site/'}
    if not SINGLE and is_zh(lang): o['alternateName'] = ORG_ZH_ALT
    return o


def page_lang(s, meta):
    """Language of this page's HTML: page config `lang` > <html lang> > config `lang` > en.
    Single-page multilingual sites are always treated as non-Chinese (default source is served to everyone)."""
    if SINGLE: return 'en'
    m = re.search(r'<html[^>]*\blang="([^"]+)"', s)
    return meta.get('lang') or (m and m.group(1)) or C.get('lang', 'en')


def intros_for(lang):
    """Which intro spans to embed. Per-locale page: only its own language (fallback to intro_fallback).
    Single-page site: never zh-*, and no intro containing Han characters (e.g. ja kanji) because the
    same source is served as the en / x-default page."""
    I = C.get('intro', {}) or {}
    if not SINGLE:
        k = lang if lang in I else next((c for c in I if lang in ALIAS.get(c, [])), None)
        if k is None:
            fb = C.get('intro_fallback', 'en')
            # never fall back to a Chinese intro on a non-Chinese page (or vice versa to nothing)
            k = fb if fb in I and (is_zh(lang) or not HAN.search(I[fb])) else None
        return {k: I[k]} if k else {}
    out = {k: v for k, v in I.items() if not is_zh(k) and not HAN.search(v)}
    dropped = [k for k in I if k not in out]
    if dropped: print(f'  note: single-page site, intro not embedded in default source for: {", ".join(dropped)} (put them on per-locale pages)')
    return out


def css(langs):
    show = ','.join(f'html[lang="{a}"] .geo-intro [data-gl="{c}"]' for c in langs for a in [c] + ALIAS.get(c, []))
    fb = C.get('intro_fallback', 'en')
    rule = ('.geo-intro{%s}.geo-intro{display:grid}.geo-intro [data-gl]{grid-area:1/1;visibility:hidden}' % C.get('intro_css', 'max-width:1120px;margin:10px auto 0;padding:0 20px;font-size:12.5px;line-height:1.55;opacity:.72')
            + (f'{show}{{visibility:visible}}' if show else ''))
    if len(langs) == 1:  # per-locale page: show its single intro regardless of the lang attribute spelling
        rule += f'.geo-intro [data-gl="{langs[0]}"]{{visibility:visible}}'
    elif fb in langs:
        rule += f'html:not([lang]) .geo-intro [data-gl="{fb}"]{{visibility:visible}}'
    return ('<style id="ia-growth">' + (rule if langs else '')
            + '.sub-band{%s}' % C.get('sub_css', 'max-width:1120px;margin:24px auto;padding:0 20px') + SUBCSS + C.get('extra_css', '') + '</style>')


def rel_of(p):
    r = os.path.relpath(p, ROOT).replace(os.sep, '/'); return re.sub(r'(^|/)index\.html$', r'\1', r)
def strip(s): return re.sub(r'<!--IA-->.*?<!--/IA-->', '', s, flags=re.S)
def text(s): return html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s))).strip()


def inject(p, meta):
    """Return (url, new_html, lang). Pure: does not write."""
    s = strip(open(p, encoding='utf-8').read()); rel = meta.get('rel', rel_of(p)); url = BASE + rel
    lang = page_lang(s, meta)
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
        o = org(lang); g = [o]
        if rel == '': g.append({'@type': 'WebSite', '@id': BASE + '#site', 'name': C['name'], 'url': BASE, 'inLanguage': LC if SINGLE else lang, 'publisher': {'@id': o['@id']}, 'description': desc})
        else:
            crumbs = [(C['name'], BASE)] + meta.get('crumbs', []) + [(title.split(' · ')[0], url)]
            g.append({'@type': 'BreadcrumbList', 'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': u} for i, (n, u) in enumerate(crumbs)]})
        g += meta.get('ld', [])
        head.append('<script type="application/ld+json">' + json.dumps({'@context': 'https://schema.org', '@graph': g}, ensure_ascii=False).replace('<', '\\u003c') + '</script>')
    intros = intros_for(lang) if C.get('intro') and not meta.get('no_intro') else {}
    head.append(css(list(intros)))
    head.append(f'<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon=\'{{"token":"{C["cf_token"]}"}}\'></script>'
                f'<script defer src="https://stats.incidental.site/events.js" data-site="{C["site"]}"{(" data-goal=%s" % json.dumps(C["goal"])) if C.get("goal") else ""}></script><script defer src="https://stats.incidental.site/subscribe.js"></script>')
    head.append('<!--/IA-->')
    s = s.replace('</head>', ''.join(head) + '</head>', 1)
    if intros:
        intro = '<!--IA--><p class="geo-intro">' + ''.join(f'<span data-gl="{k}" lang="{k}">{html.escape(v)}</span>' for k, v in intros.items()) + '</p><!--/IA-->'
        anchor = C.get('intro_after', '</header>')
        s = s.replace(anchor, anchor + intro, 1) if anchor in s else re.sub(r'(<body[^>]*>)', r'\1' + intro.replace('\\', '\\\\'), s, 1)
    if meta.get('ssr'):
        s = s.replace('</body>', '<!--IA--><noscript><section class="ssr-index">' + meta['ssr'] + '</section></noscript><!--/IA--></body>', 1)
    if not meta.get('no_sub'):
        sub = f'<!--IA--><aside class="sub-band" aria-label="Newsletter"><div data-ie-sub data-site="{C["site"]}" data-source="{html.escape(rel or "home")}"></div></aside><!--/IA-->'
        anchor = C.get('sub_before', '<footer')
        s = s.replace(anchor, sub + anchor, 1) if anchor in s else s.replace('</body>', sub + '</body>', 1)
    for a, b in C.get('replace', []): s = s.replace(a, b)
    return url, s, lang


def cjk_violations(content, lang, where):
    """Self-check. zh-* pages: anything goes. ja pages: kanji are legitimate Japanese, so only Chinese
    strings we know (brand alias, zh intros) are banned. Every other page / generated file: no Han at all."""
    if is_zh(lang): return []
    if lang.lower().startswith('ja'):
        banned = [ORG_ZH_ALT] + [v for k, v in (C.get('intro') or {}).items() if is_zh(k)]
        return [f'{where} [{lang}]: Chinese string {b[:24]!r}' for b in banned if b and b in content]
    out = []
    for m in list(HAN.finditer(content))[:5]:
        a = max(0, m.start() - 40); ctx = content[a:m.start() + 20].replace('\n', ' ')
        out.append(f'{where} [{lang}]: CJK U+{ord(m.group()):04X} near …{ctx}…')
    n = len(HAN.findall(content))
    if n > 5: out.append(f'{where} [{lang}]: … {n} Han chars in total')
    return out


def build():
    """Render everything into {path: (content, lang)} without touching disk."""
    pages = json.load(open(C['pages'])) if isinstance(C.get('pages'), str) else C.get('pages', [])
    out, urls = {}, []
    for m in pages:
        for p in glob.glob(os.path.join(ROOT, m['glob']), recursive=True) if 'glob' in m else [os.path.join(ROOT, m['file'])]:
            u, s, lang = inject(p, {k: v for k, v in m.items() if k not in ('glob', 'file')})
            out[p] = (s, lang)
            if not m.get('nomap'): urls.append(u)
    if C.get('seo', True):
        today = datetime.date.today().isoformat()
        files = {'sitemap-default.xml': urls}
        for l in LC: files[f'sitemap-{l}.xml'] = [f'{u}?lang={l}' for u in urls] if C.get('hreflang') else None
        names = []
        for n, us in files.items():
            if us is None: continue
            names.append(n)
            out[os.path.join(ROOT, n)] = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(f'<url><loc>{html.escape(u)}</loc><lastmod>{today}</lastmod></url>' for u in us) + '\n</urlset>\n', 'xml')
        out[os.path.join(ROOT, 'sitemap.xml')] = ('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(f'<sitemap><loc>{BASE}{n}</loc><lastmod>{today}</lastmod></sitemap>' for n in names) + '\n</sitemapindex>\n', 'xml')
        bots = ['GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot', 'Claude-Web', 'PerplexityBot', 'Google-Extended', 'Applebot-Extended']
        out[os.path.join(ROOT, 'robots.txt')] = ('User-agent: *\nAllow: /\n\n# AI / generative search crawlers are welcome\n' + '\n'.join(f'User-agent: {b}\nAllow: /' for b in bots) + f'\n\nSitemap: {BASE}sitemap.xml\n', 'txt')
        for n in ('llms.txt', 'llms-full.txt'):  # language-neutral files served to every crawler -> Chinese-free
            if C.get(n): out[os.path.join(ROOT, n)] = (C[n] if isinstance(C[n], str) else open(C[n]['file'], encoding='utf-8').read(), 'txt')
    return out, urls


def check(out):
    errs = []
    for p, (s, lang) in out.items(): errs += cjk_violations(s, 'en' if lang in ('xml', 'txt') else lang, os.path.relpath(p, ROOT))
    return errs


def write(out, dry):
    for p, (s, _) in out.items():
        dst = p if not dry else os.path.join(dry, os.path.relpath(p, ROOT).replace('..', '__up__'))
        os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
        open(dst, 'w', encoding='utf-8').write(s)


def main(cfg, dry=None):
    setup(cfg)
    out, urls = build()
    errs = check(out)
    if errs:
        print('CJK self-check FAILED (non-Chinese output contains Chinese) — nothing written:', file=sys.stderr)
        for e in errs: print('  ' + e, file=sys.stderr)
        return 2
    write(out, dry)
    pl = [p for p, (_, l) in out.items() if l not in ('xml', 'txt')]
    print(f'{"dry-run → " + dry if dry else "injected"}: {len(urls)} pages in sitemap, {len(pl)} html files; CJK self-check OK '
          f'({sum(1 for p in pl if not is_zh(out[p][1]))} non-Chinese pages scanned)')
    return 0


if __name__ == '__main__':
    sys.exit(main(C, DRY))
