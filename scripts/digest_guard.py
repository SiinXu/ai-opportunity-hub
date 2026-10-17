#!/usr/bin/env python3
"""CI guard for digest output: non-Chinese surfaces must contain zero Han characters.
Checks every site/digest/**/index.html (everything outside the zh-Hans / zh-Hant langboxes, i.e. <head>, chrome,
the English box that all non-Chinese locales see, scripts) and every non-zh field in site/data/digests.json.
Only the language-switcher autonyms 简体中文 / 繁體中文 / 日本語 are allowed. Exit 1 on any violation."""
import re, os, sys, json, glob
D = os.path.dirname(os.path.abspath(__file__)); S = os.path.normpath(os.path.join(D, '../site'))
HAN = re.compile(r'[\u3400-\u9fff\uf900-\ufaff]'); ALLOW = ('简体中文', '繁體中文', '日本語')  # language-switcher autonyms only
bad = []
def chk(where, s):
    for a in ALLOW: s = s.replace(a, '')
    for m in HAN.finditer(s):
        bad.append(f'{where}: …{s[max(0, m.start()-30):m.end()+30]}…'); break
for p in sorted(glob.glob(os.path.join(S, 'digest/**/index.html'), recursive=True)):
    s = open(p, encoding='utf-8').read()
    s = re.sub(r'<div class="langbox" data-lang="zh-Han[st]">.*?</div>(?=<div class="langbox"|\s*</main>|\n<div class="langbox")', '', s, flags=re.S)
    if 'data-lang="zh-Hans"' in s or 'data-lang="zh-Hant"' in s: bad.append(f'{p}: could not isolate zh langboxes')
    chk(os.path.relpath(p, S), s)
G = json.load(open(os.path.join(S, 'data/digests.json'), encoding='utf-8'))
def walk(o, path):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ('zh-Hans', 'zh-Hant'): continue
            walk(v, f'{path}.{k}')
    elif isinstance(o, list):
        for n, v in enumerate(o): walk(v, f'{path}[{n}]')
    elif isinstance(o, str): chk(path, o)
walk(G, 'digests.json')
if bad:
    print('i18n guard FAILED — Han characters on non-Chinese surfaces:'); print('\n'.join(bad)); sys.exit(1)
print(f'i18n guard OK — no Han on non-Chinese digest surfaces ({len(G["digests"])} issues checked)')
