#!/usr/bin/env python3
"""CI guard for digest output: non-Chinese surfaces must contain zero Chinese (Han) characters.
Checks
- every site/digest/**/index.html: everything outside the zh-Hans / zh-Hant langboxes (<head>, chrome, scripts, the en /
  ko / ms / vi / fr / es / de boxes) must have zero Han; the ja box may contain kanji only inside text that is real Japanese
  (contains kana) - the nocjk.py rule - ONLY when DIGEST_JA_KANJI=1; by default ja is held to zero Han too;
- every non-zh field in site/data/digests.json (same ja rule);
- every per-locale reader file site/digest/<date>/<locale>.json for the 8 non-Chinese locales (same ja rule).
Only the language-switcher autonyms 简体中文 / 繁體中文 / 日本語 are allowed anywhere. Exit 1 on any violation."""
import re, os, sys, json, glob
D = os.path.dirname(os.path.abspath(__file__)); S = os.path.normpath(os.path.join(D, '../site'))
HAN = re.compile(r'[\u3400-\u9fff\uf900-\ufaff]'); KANA = re.compile(r'[\u3040-\u30ff]')
ALLOW = ('简体中文', '繁體中文', '日本語')  # language-switcher autonyms only
NONZH = ['en', 'ja', 'ko', 'ms', 'vi', 'fr', 'es', 'de']
JA_KANJI = os.environ.get('DIGEST_JA_KANJI') == '1'   # default strict: ja must have zero Han like every non-zh locale
bad = []; counts = {}
def strip(s):
    for a in ALLOW: s = s.replace(a, '')
    return s
def chk(where, s, ja=False):
    s = strip(s)
    if ja and JA_KANJI:   # judge each text node / string on its own: Han only allowed together with kana
        parts = re.split(r'<[^>]+>', s) if '<' in s else [s]
        for p in parts:
            if HAN.search(p) and not KANA.search(p):
                bad.append(f'{where} [ja without kana]: …{p.strip()[:80]}…'); return
        return
    m = HAN.search(s)
    if m: bad.append(f'{where}: …{s[max(0, m.start()-30):m.end()+30]}…')

BOX = re.compile(r'<div class="langbox" data-lang="([^"]+)"[^>]*>')
for p in sorted(glob.glob(os.path.join(S, 'digest/**/index.html'), recursive=True)):
    s = open(p, encoding='utf-8').read(); rel = os.path.relpath(p, S)
    ms = list(BOX.finditer(s)); rest = s; ja_parts = []
    if ms:
        end = s.find('</main>', ms[-1].end()); end = end if end > 0 else len(s)
        segs = [(m.group(1), m.start(), (ms[n + 1].start() if n + 1 < len(ms) else end)) for n, m in enumerate(ms)]
        rest = s[:segs[0][1]] + s[end:]
        for L, a, b in segs:
            seg = s[a:b]
            if L.startswith('zh'): continue
            if L == 'ja': chk(rel + '#ja', seg, ja=True)
            else: rest += seg
    chk(rel, rest)

G = json.load(open(os.path.join(S, 'data/digests.json'), encoding='utf-8'))
def walk(o, path, ja=False):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ('zh-Hans', 'zh-Hant'): continue
            walk(v, f'{path}.{k}', ja or k == 'ja')
    elif isinstance(o, list):
        for n, v in enumerate(o): walk(v, f'{path}[{n}]', ja)
    elif isinstance(o, str): chk(path, o, ja)
walk(G, 'digests.json')

for L in NONZH:
    for p in sorted(glob.glob(os.path.join(S, f'digest/*/{L}.json'))):
        def w2(o, path):
            if isinstance(o, dict):
                for k, v in o.items(): w2(v, f'{path}.{k}')
            elif isinstance(o, list):
                for n, v in enumerate(o): w2(v, f'{path}[{n}]')
            elif isinstance(o, str): chk(path, o, L == 'ja')
        w2(json.load(open(p, encoding='utf-8')), os.path.relpath(p, S)); counts[L] = counts.get(L, 0) + 1

if bad:
    print('i18n guard FAILED — Han characters on non-Chinese surfaces:'); print('\n'.join(bad[:40])); sys.exit(1)
print(f'i18n guard OK — no Han on non-Chinese digest surfaces ({len(G["digests"])} issues, reader files per locale: {counts})')
