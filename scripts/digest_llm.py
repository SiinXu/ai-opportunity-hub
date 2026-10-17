#!/usr/bin/env python3
"""Optional LLM rewrite for digest items (OpenAI-compatible chat completions API, stdlib only).

Enabled only when a key is present:  DIGEST_LLM_API_KEY  (or OPENAI_API_KEY)
Optional: DIGEST_LLM_BASE_URL (default https://api.openai.com/v1), DIGEST_LLM_MODEL (default gpt-4o-mini).
Without a key, or on any error / failed check, rewrite() returns None and the item falls back to summary + excerpt
(marked not rewritten); the run is never blocked.

Checks on every rewrite (also applied to editor-written rewrites in scripts/digest_rewrites/):
- every number in the rewrite must appear in the source text (no invented figures),
- no run of 12+ consecutive words copied verbatim from the source (no long verbatim passages),
- English output must not contain Han characters."""
import json, os, re, urllib.request
HAN = re.compile(r'[\u3400-\u9fff\uf900-\ufaff]')

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
    for L in ('en', 'zh-Hans'):
        txt = ' '.join((rw.get(L) or {}).get('body', []) + (rw.get(L) or {}).get('take', []))
        if not txt: bad.append(f'{L}: empty'); continue
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
