"""Keep non-Chinese locales free of Chinese characters.
- en_of(text): English for a source string (manual override > CJK-free bilingual segment > stripped text).
- scrub(items): post-pass over title_i18n / summary_i18n; any non-zh locale value with Chinese falls back to the English value.
Run standalone to clean site/data/items.json without re-translating:  python3 scripts/nocjk.py"""
import json,os,re
D=os.path.dirname(os.path.abspath(__file__))
CJK=re.compile(r'[\u3400-\u9fff\uf900-\ufaff]')
KANA=re.compile(r'[\u3040-\u30ff]')
OV=json.load(open(os.path.join(D,'en_overrides.json')))
NONZH=['en','ja','ko','ms','vi','fr','es','de']
def strip(t):
    t=re.sub(r'[（(《「][^）)》」]*[\u3400-\u9fff][^）)》」]*[）)》」]','',t)
    t=re.sub(r'[\u3400-\u9fff\uf900-\ufaff\u3000-\u303f\uff01-\uff0f\uff1a-\uff1f「」『』《》【】]+',' ',t)
    t=re.sub(r'\s*([/|·,;:—–-]\s*)+$','',t); t=re.sub(r'^\s*([/|·,;:—–-]\s*)+','',t)
    t=re.sub(r'\(\s*[/,]?\s*\)','',t)
    return re.sub(r'\s{2,}',' ',t).strip()
def en_of(text):
    if not text or not CJK.search(text): return text
    k=text.strip()
    if k in OV: return OV[k]
    segs=[s.strip() for s in re.split(r'\s[/|·—–-]\s|。|——|\s\|\s',text) if s.strip()]
    lat=[strip(s) for s in segs if len(CJK.findall(s))<=4 and len(re.findall(r'[A-Za-z]{2,}',strip(s)))>=3]
    if lat: return ' — '.join(lat)
    s=strip(text)
    return s if len(re.findall(r'[A-Za-z]{2,}',s))>=2 else ''
def ok(L,v):
    if not v or not CJK.search(v): return True
    return L=='ja' and bool(KANA.search(v))   # Japanese text with kana is real Japanese
def scrub(items):
    n=0
    for i in items:
        for f in ('title','summary'):
            m=i.get(f+'_i18n')
            if not m: continue
            en=m.get('en') or ''
            if CJK.search(en): en=en_of(i.get(f) or en) or en_of(en); m['en']=en; n+=1
            for L in NONZH[1:]:
                if not ok(L,m.get(L)): m[L]=en; n+=1
    return n
if __name__=='__main__':
    p=os.path.join(D,'../site/data/items.json'); d=json.load(open(p))
    print('scrubbed',scrub(d['items']))
    json.dump(d,open(p,'w'),ensure_ascii=False,indent=1)
