#!/usr/bin/env python3
"""Optional LLM rewrite for digest items (OpenAI-compatible chat completions API, stdlib only).

Enabled only when a key is present:  DIGEST_LLM_API_KEY  (or OPENAI_API_KEY)
Optional: DIGEST_LLM_BASE_URL (default https://api.openai.com/v1), DIGEST_LLM_MODEL (default gpt-4o-mini).
Without a key, or on any error / failed check, rewrite() returns None and the item falls back to summary + excerpt
(marked not rewritten); the run is never blocked.

Checks on every rewrite (also applied to editor-written rewrites in scripts/digest_rewrites/):
- every number in the rewrite must appear in the source text (no invented figures),
- no run of 12+ consecutive words copied verbatim from the source (no long verbatim passages),
- English output must not contain Han characters.
- optional editor-written Japanese ("ja": body/take/summary): same number rule, kanji only together with kana."""
import json, os, re, urllib.request
HAN = re.compile(r'[\u3400-\u9fff\uf900-\ufaff]'); KANA = re.compile(r'[\u3040-\u30ff]')

def key(): return os.environ.get('DIGEST_LLM_API_KEY') or os.environ.get('OPENAI_API_KEY') or ''

PROMPT = """You write for OPC Radar, a daily digest for indie developers, designers and one-person companies.
Rewrite the SOURCE below as an original short article in our own voice, then give our opinion.
Hard rules:
- Use ONLY facts stated in SOURCE. Do not add numbers, names, dates, quotes or claims that are not in SOURCE.
- Do not copy sentences; never reuse more than 8 consecutive words from SOURCE. No direct quotes.
- If SOURCE is thin, write less rather than inventing.
Return JSON only:
{"en":{"body":[3-5 paragraphs, 180-320 words total],"take":[1-2 paragraphs, 60-120 words: why it matters, who can use it, an opportunity or a risk]},
 "zh-Hans":{"body":[same content in natural Simplified Chinese, 300-600 characters],"take":[same opinion in Simplified Chinese]}}
The "take" is clearly opinion; the "body" is factual."""

def nums(s): return set(re.findall(r'\d+(?:[.,]\d+)*', s))
def words(s): return re.findall(r"[a-z0-9']+", s.lower())

def check(rw, source):
    """Return a list of problems (empty = ok)."""
    bad = []
    src_n = nums(source.replace(',', '')) | nums(source)
    sw = words(source); grams = {' '.join(sw[i:i + 12]) for i in range(max(0, len(sw) - 11))}
    for L in ('en', 'zh-Hans', 'ja'):
        if L == 'ja' and not isinstance(rw.get('ja'), dict): continue   # optional editor-written Japanese
        part = rw.get(L) or {}
        txt = ' '.join(part.get('body', []) + part.get('take', []) + ([part['summary']] if isinstance(part.get('summary'), str) else []))
        if not txt: bad.append(f'{L}: empty'); continue
        if L == 'ja':
            for p_ in part.get('body', []) + part.get('take', []):
                if HAN.search(p_) and not KANA.search(p_): bad.append('ja: paragraph with kanji but no kana: ' + p_[:40])
            w = words(txt)   # Latin words copied from the (English) source: same 12-word verbatim rule
            for i in range(max(0, len(w) - 11)):
                if ' '.join(w[i:i + 12]) in grams: bad.append('ja: 12+ words copied verbatim: ' + ' '.join(w[i:i + 12])); break
        for n in nums(txt):
            if n not in src_n and n.replace(',', '') not in src_n: bad.append(f'{L}: number {n} not in source')
        if L == 'en':
            if HAN.search(txt): bad.append('en: contains Han')
            w = words(txt)
            for i in range(max(0, len(w) - 11)):
                if ' '.join(w[i:i + 12]) in grams: bad.append('en: 12+ words copied verbatim: ' + ' '.join(w[i:i + 12])); break
    return bad

def rewrite(title, source, url):
    k = key()
    if not k or len(source) < 200: return None
    base = (os.environ.get('DIGEST_LLM_BASE_URL') or 'https://api.openai.com/v1').rstrip('/')
    model = os.environ.get('DIGEST_LLM_MODEL') or 'gpt-4o-mini'
    body = {'model': model, 'temperature': 0.4, 'response_format': {'type': 'json_object'},
            'messages': [{'role': 'system', 'content': PROMPT},
                         {'role': 'user', 'content': f'TITLE: {title}\nURL: {url}\nSOURCE:\n{source[:6000]}'}]}
    try:
        req = urllib.request.Request(base + '/chat/completions', data=json.dumps(body).encode(),
                                     headers={'Authorization': 'Bearer ' + k, 'Content-Type': 'application/json'})
        r = json.load(urllib.request.urlopen(req, timeout=90))
        rw = json.loads(r['choices'][0]['message']['content'])
        rw = {L: {'body': [str(p).strip() for p in rw[L]['body'] if str(p).strip()],
                  'take': [str(p).strip() for p in rw[L]['take'] if str(p).strip()]} for L in ('en', 'zh-Hans')}
    except Exception as ex:
        print('  llm skip', url[:70], type(ex).__name__, str(ex)[:80]); return None
    bad = check(rw, source)
    if bad: print('  llm rejected', url[:70], bad[:3]); return None
    return rw

NAMES = {'zh-Hans': 'Simplified Chinese', 'ja': 'Japanese', 'ko': 'Korean', 'ms': 'Malay', 'vi': 'Vietnamese',
         'fr': 'French', 'es': 'Spanish', 'de': 'German'}
TPROMPT = """Translate the English JSON fields of an OPC Radar digest entry into each requested language, as a native
editor would write them (natural, idiomatic; keep product, company and person names, URLs and code as they are).
Translate only: do not add, drop or change facts, numbers, names or claims. Keep the same number of paragraphs.
Non-Chinese, non-Japanese outputs must contain no Chinese characters. Japanese must be real Japanese (kana + kanji).
Return JSON only: {"<lang code>": {"title": "...", "summary": "...", "body": [...], "take": [...], "ex": [...]}, ...}"""

def translate(en, locs):
    """en: {title, summary, body, take, ex} -> {locale: same fields} or None. Every locale is checked (numbers from the
    English only, Han rules, paragraph counts); a failing locale is left out so the caller uses the translator."""
    k = key()
    if not k or not en.get('title'): return None
    base = (os.environ.get('DIGEST_LLM_BASE_URL') or 'https://api.openai.com/v1').rstrip('/')
    model = os.environ.get('DIGEST_LLM_MODEL') or 'gpt-4o-mini'
    ask = {L: NAMES[L] for L in locs if L in NAMES}
    body = {'model': model, 'temperature': 0.2, 'response_format': {'type': 'json_object'},
            'messages': [{'role': 'system', 'content': TPROMPT},
                         {'role': 'user', 'content': 'LANGUAGES: ' + json.dumps(ask) + '\nENGLISH: ' + json.dumps(en, ensure_ascii=False)}]}
    try:
        req = urllib.request.Request(base + '/chat/completions', data=json.dumps(body).encode(),
                                     headers={'Authorization': 'Bearer ' + k, 'Content-Type': 'application/json'})
        r = json.loads(json.load(urllib.request.urlopen(req, timeout=120))['choices'][0]['message']['content'])
    except Exception as ex:
        print('  llm translate skip', type(ex).__name__, str(ex)[:80]); return None
    src_n = nums(' '.join([en['title'], en['summary']] + en['body'] + en['take'] + en['ex']))
    out = {}
    for L in ask:
        x = r.get(L)
        if not isinstance(x, dict): continue
        y = {f: str(x.get(f) or '').strip() for f in ('title', 'summary')}
        for f in ('body', 'take', 'ex'):
            y[f] = [str(p).strip() for p in (x.get(f) or []) if str(p).strip()]
            if len(y[f]) != len(en[f]): y = None; break
        if not y or not y['title']: continue
        txt = ' '.join([y['title'], y['summary']] + y['body'] + y['take'] + y['ex'])
        if {re.sub(r'\D', '', n) for n in nums(txt)} - {re.sub(r'\D', '', n) for n in src_n}: print('  llm translate rejected', L, 'number'); continue
        if L not in ('zh-Hans', 'ja') and HAN.search(txt): print('  llm translate rejected', L, 'Han'); continue
        if L == 'ja' and any(HAN.search(p) and not KANA.search(p) for p in [y['title'], y['summary']] + y['body'] + y['take']): continue
        out[L] = y
    return out or None
