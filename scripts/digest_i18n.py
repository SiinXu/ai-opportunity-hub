#!/usr/bin/env python3
"""Translation for the digest: the same offline path as refresh.py (Argos Translate en->xx, OpenCC zh-Hans->zh-Hant),
cached in scripts/digest_i18n_cache.json. Han guard built in: a non-Chinese value that contains Han characters falls
back to English (ja is kept only when it is real Japanese, i.e. contains kana - same rule as nocjk.py).
If Argos is not installed, non-English locales fall back to English (never to invented text)."""
import json, os, re
D = os.path.dirname(os.path.abspath(__file__)); CP = os.path.join(D, 'digest_i18n_cache.json')
LOCS = ['zh-Hans', 'zh-Hant', 'en', 'ja', 'ko', 'ms', 'vi', 'fr', 'es', 'de']
NONZH = ['en', 'ja', 'ko', 'ms', 'vi', 'fr', 'es', 'de']
HAN = re.compile(r'[\u3400-\u9fff\uf900-\ufaff]'); KANA = re.compile(r'[\u3040-\u30ff]')
AC = {'zh-Hans': 'zh', 'ja': 'ja', 'ko': 'ko', 'ms': 'ms', 'vi': 'vi', 'fr': 'fr', 'es': 'es', 'de': 'de'}

# Japanese policy. Default (strict, the site rule "non-zh pages contain zero Han"): Japanese machine translation almost
# always contains kanji, so the ja locale shows the English text. DIGEST_JA_KANJI=1 switches to real Japanese
# (kanji allowed only together with kana, the rule nocjk.py uses for the main site); the guard follows the same switch.
JA_KANJI = os.environ.get('DIGEST_JA_KANJI') == '1'

def ok(L, v):
    if not v or not HAN.search(v): return True
    if L.startswith('zh'): return True
    return L == 'ja' and JA_KANJI and bool(KANA.search(v))

class Tr:
    def __init__(s):
        s.C = json.load(open(CP, encoding='utf-8')) if os.path.exists(CP) else {}
        s._tr = {}; s.ok = True; s.n = 0
        try:
            if os.environ.get('DIGEST_NO_TRANSLATE') == '1': raise RuntimeError('DIGEST_NO_TRANSLATE=1')
            import argostranslate.translate as T, opencc
            s.T = T; s.s2t = opencc.OpenCC('s2twp')
        except Exception as ex:
            print('digest_i18n: translator unavailable, non-English locales fall back to English:', ex); s.ok = False
    def x(s, text, a, b):
        k = (a, b)
        if k not in s._tr: s._tr[k] = s.T.get_translation_from_codes(a, b)
        return s._tr[k].translate(text)
    def one(s, en, zh=None):
        """en (Han-free English) -> {locale: text}. zh: optional human zh-Hans text (else machine-translated)."""
        en = (en or '').strip()
        if not en: return {L: '' for L in LOCS}
        if HAN.search(en): raise ValueError('English source contains Han: ' + en[:60])
        key = en if zh is None else en + '\x00' + zh
        if key in s.C:
            r = dict(s.C[key])
            if JA_KANJI and s.ok and r.get('ja') == en:   # cached in strict mode: fill in the Japanese now
                try: r['ja'] = s.x(en, 'en', 'ja').strip(); s.C[key] = dict(r)
                except Exception: pass
        else:
            r = {'en': en}
            for L, a in AC.items():
                if L == 'zh-Hans' and zh: r[L] = zh; continue
                if L == 'ja' and not JA_KANJI: r[L] = en; continue
                if not s.ok: r[L] = en; continue
                try: r[L] = s.x(en, 'en', a).strip()
                except Exception as ex: print('  tr fail', L, ex); r[L] = en
            r['zh-Hant'] = s.s2t.convert(r['zh-Hans']) if s.ok else (zh or en)
            if s.ok: s.C[key] = r; s.n += 1
            if s.n and s.n % 25 == 0: s.save()
        for L in NONZH:
            if not ok(L, r.get(L)): r[L] = en
        return r
    def many(s, ens, zhs=None):
        """list of paragraphs -> {locale: [paragraphs]}"""
        zhs = zhs or [None] * len(ens)
        out = {L: [] for L in LOCS}
        for en, zh in zip(ens, zhs):
            r = s.one(en, zh)
            for L in LOCS: out[L].append(r[L])
        return out
    def save(s):
        json.dump(s.C, open(CP, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
