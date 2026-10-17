#!/usr/bin/env python3
"""OPC Radar · automatic daily digest (每日简报).

Builds one issue for a Shanghai calendar date from real items in site/data/items.json, then updates
site/data/digests.json, site/digest/<date>/index.html, the archive page site/digest/index.html and the
digest sitemaps. Stdlib only.

usage: python3 scripts/digest.py [--date YYYY-MM-DD] [--now ISO8601] [--force]

Rules
- Issue date = Asia/Shanghai date. Publish time 07:30 Asia/Shanghai; the issue's cutoff is that moment.
  --date may backfill a missed day up to 7 days back (marked catch-up).
  Without --date, a run before 07:30 Shanghai exits 0 without doing anything (too early).
- Idempotent: if site/digest/<date>/ or a digests.json entry for <date> already exists -> exit 0, no change.
  --force (workflow_dispatch force=true) rebuilds an existing issue in place: same date, same selected items (no
  re-picking, the dedup set is untouched), fresh summaries / reader content / page. Never adds a new date.
- Every entry gets a 1-2 sentence summary from its real source text (digest_src.py: page meta/first paragraphs,
  GitHub description/README, HN text), translated to all 10 locales (digest_i18n.py, Argos + OpenCC); with no
  source text a factual fallback from real fields is used, never invented text.
- In-page reader: per-locale lazy JSON site/digest/<date>/<locale>.json with an editor rewrite
  (scripts/digest_rewrites/<date>.json) or an LLM rewrite (digest_llm.py, only when DIGEST_LLM_API_KEY /
  OPENAI_API_KEY is set) plus "our take"; otherwise summary + real excerpt, marked not rewritten.
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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from digest_src import source_text
from digest_i18n import Tr, ok as dok, JA_KANJI
import digest_llm

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
    r = {'force': '--force' in a}
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
    if v and dok(L, v): return v
    if L != 'en' and not L.startswith('zh'):
        v = (m.get('en') or '').strip()
        if v and not HAN.search(v): return v
    base = (i.get(f) or '').strip()
    return base if (L.startswith('zh') or not HAN.search(base)) else ''

def host(u):
    try: return (urlparse(u).hostname or '').removeprefix('www.')
    except Exception: return ''

FACT = {
 'zh-Hans': {'hn': 'Hacker News {p} 分 · {c} 条评论', 'gh': 'GitHub {s} 星', 'src': '来源：{x}'},
 'zh-Hant': {'hn': 'Hacker News {p} 分 · {c} 則留言', 'gh': 'GitHub {s} 星', 'src': '來源：{x}'},
 'en': {'hn': '{p} points · {c} comments on Hacker News', 'gh': '{s} stars on GitHub', 'src': 'Source: {x}'},
 'ja': {'hn': 'Hacker News {p} ポイント · コメント {c} 件', 'gh': 'GitHub スター {s}', 'src': 'ソース: {x}'},
 'ko': {'hn': 'Hacker News {p}점 · 댓글 {c}개', 'gh': 'GitHub 스타 {s}개', 'src': '출처: {x}'},
 'ms': {'hn': '{p} mata · {c} komen di Hacker News', 'gh': '{s} bintang di GitHub', 'src': 'Sumber: {x}'},
 'vi': {'hn': '{p} điểm · {c} bình luận trên Hacker News', 'gh': '{s} sao trên GitHub', 'src': 'Nguồn: {x}'},
 'fr': {'hn': '{p} points · {c} commentaires sur Hacker News', 'gh': '{s} étoiles sur GitHub', 'src': 'Source : {x}'},
 'es': {'hn': '{p} puntos · {c} comentarios en Hacker News', 'gh': '{s} estrellas en GitHub', 'src': 'Fuente: {x}'},
 'de': {'hn': '{p} Punkte · {c} Kommentare auf Hacker News', 'gh': '{s} Sterne auf GitHub', 'src': 'Quelle: {x}'},
}
# factual fallback summary (no source text at all): only real fields - source name and host
FALLBACK = {'zh-Hans': '{src} 上的链接，原文来自 {h}。', 'zh-Hant': '{src} 上的連結，原文來自 {h}。',
 'en': 'Shared on {src}; original at {h}.', 'ja': '{src} で共有されたリンク。元記事は {h} にあります。',
 'ko': '{src}에서 공유된 링크입니다. 원문은 {h}에 있습니다.', 'ms': 'Dikongsi di {src}; artikel asal di {h}.',
 'vi': 'Được chia sẻ trên {src}; bài gốc tại {h}.', 'fr': 'Partagé sur {src} ; original sur {h}.',
 'es': 'Compartido en {src}; original en {h}.', 'de': 'Geteilt auf {src}; Original auf {h}.'}
def fact(i, L):
    h = i.get('hot') or {}; F = FACT[L]
    if h.get('s'): return F['gh'].format(s=f"{h['s']:,}")
    m = re.search(r'★\s*([\d,]+)', i.get('meta') or '')
    if m and (i.get('source') or '').startswith('GitHub'): return F['gh'].format(s=m.group(1))
    if h.get('p') and i.get('source') == 'Hacker News': return F['hn'].format(p=h['p'], c=h.get('c', 0))
    src = (i.get('source') or '').replace(' · new', '')
    return F['src'].format(x=src) if src and not HAN.search(src) else ''

def title(i, L):
    t = loc(i, 'title', L) or (i.get('title') or '')
    if not L.startswith('zh') and HAN.search(t) and not dok(L, t): t = loc(i, 'title', 'en')
    if not L.startswith('zh') and HAN.search(t) and not dok(L, t): return ''
    return t

T = {
 'zh-Hans': dict(home='首页', arch='每日简报', h1='早间技术热点 · {d}', h1b='早间技术热点 · {d}（补发）',
   lede='上海时间 {d} 07:30 自动生成：从上一期以来 OPC Radar 新收录的 {n} 条信号里，按热度挑出最值得看的内容。',
   ledeb='补发：按上海时间 {d} 07:30 的截止点事后自动生成，收录当时新出现的 {n} 条信号。',
   top='① 今日热点（Top {k}）', more='② 更多新信号', follow='③ 值得跟进',
   note='全部条目来自公开来源（Hacker News、GitHub、Hugging Face 等），附原文链接；自动生成，未编造数据。点任意条目可在页内阅读。',
   label='早间技术热点', labelb='早间技术热点（补发）', disc='讨论'),
 'zh-Hant': dict(home='首頁', arch='每日簡報', h1='早間技術熱點 · {d}', h1b='早間技術熱點 · {d}（補發）',
   lede='上海時間 {d} 07:30 自動生成：從上一期以來 OPC Radar 新收錄的 {n} 條信號裡，按熱度挑出最值得看的內容。',
   ledeb='補發：按上海時間 {d} 07:30 的截止點事後自動生成，收錄當時新出現的 {n} 條信號。',
   top='① 今日熱點（Top {k}）', more='② 更多新信號', follow='③ 值得跟進',
   note='全部條目來自公開來源（Hacker News、GitHub、Hugging Face 等），附原文連結；自動生成，未編造數據。點任意條目可在頁內閱讀。',
   label='早間技術熱點', labelb='早間技術熱點（補發）', disc='討論'),
 'en': dict(home='Home', arch='Daily digests', h1='Morning tech digest · {d}', h1b='Morning tech digest · {d} (catch-up)',
   lede='Generated automatically at 07:30 Asia/Shanghai on {d}: the hottest of the {n} signals OPC Radar picked up since the previous issue.',
   ledeb='Catch-up issue: generated afterwards for the 07:30 Asia/Shanghai cutoff on {d}, from the {n} signals that were new at that time.',
   top="① Today's top {k}", more='② More new signals', follow='③ Worth following',
   note='Every entry comes from a public source (Hacker News, GitHub, Hugging Face, …) with its original link; generated automatically, no invented metrics. Tap any entry to read it here.',
   label='Morning tech digest', labelb='Morning tech digest (catch-up)', disc='discussion'),
 'ja': dict(home='ホーム', arch='デイリーダイジェスト', h1='朝のテックダイジェスト · {d}', h1b='朝のテックダイジェスト · {d}（キャッチアップ）',
   lede='{d} 07:30（上海時間）に自動生成：前号以降に OPC Radar が新たに拾った {n} 件のシグナルから、注目度の高いものを選びました。',
   ledeb='キャッチアップ号：{d} 07:30（上海時間）の締め切りに合わせて後から自動生成し、当時新しかった {n} 件のシグナルから選びました。',
   top='① 今日のトップ {k}', more='② その他の新しいシグナル', follow='③ 注目しておきたいもの',
   note='すべての項目は公開ソース（Hacker News、GitHub、Hugging Face など）からのもので、元記事へのリンク付きです。自動生成で、数値の捏造はありません。項目をタップするとこのページで読めます。',
   label='朝のテックダイジェスト', labelb='朝のテックダイジェスト（キャッチアップ）', disc='ディスカッション'),
 'ko': dict(home='홈', arch='데일리 다이제스트', h1='아침 테크 다이제스트 · {d}', h1b='아침 테크 다이제스트 · {d} (지연 발행)',
   lede='{d} 07:30(상하이 시간)에 자동 생성: 지난 호 이후 OPC Radar가 새로 수집한 신호 {n}개 중 가장 주목받는 것을 골랐습니다.',
   ledeb='지연 발행: {d} 07:30(상하이 시간) 마감 기준으로 나중에 자동 생성했으며, 당시 새로 나온 신호 {n}개에서 골랐습니다.',
   top='① 오늘의 톱 {k}', more='② 더 많은 새 신호', follow='③ 지켜볼 만한 것',
   note='모든 항목은 공개 출처(Hacker News, GitHub, Hugging Face 등)에서 왔으며 원문 링크가 있습니다. 자동 생성되며 수치를 지어내지 않습니다. 항목을 누르면 이 페이지에서 읽을 수 있습니다.',
   label='아침 테크 다이제스트', labelb='아침 테크 다이제스트 (지연 발행)', disc='토론'),
 'ms': dict(home='Utama', arch='Ringkasan harian', h1='Ringkasan teknologi pagi · {d}', h1b='Ringkasan teknologi pagi · {d} (susulan)',
   lede='Dijana secara automatik pada 07:30 waktu Shanghai, {d}: isyarat paling hangat daripada {n} isyarat baharu yang dikutip OPC Radar sejak isu sebelumnya.',
   ledeb='Isu susulan: dijana kemudian untuk had masa 07:30 waktu Shanghai pada {d}, daripada {n} isyarat yang baharu ketika itu.',
   top='① {k} teratas hari ini', more='② Lebih banyak isyarat baharu', follow='③ Patut diikuti',
   note='Setiap entri datang daripada sumber awam (Hacker News, GitHub, Hugging Face, …) dengan pautan asal; dijana secara automatik, tiada metrik rekaan. Ketik mana-mana entri untuk membacanya di sini.',
   label='Ringkasan teknologi pagi', labelb='Ringkasan teknologi pagi (susulan)', disc='perbincangan'),
 'vi': dict(home='Trang chủ', arch='Bản tin hằng ngày', h1='Bản tin công nghệ buổi sáng · {d}', h1b='Bản tin công nghệ buổi sáng · {d} (bù)',
   lede='Tự động tạo lúc 07:30 giờ Thượng Hải ngày {d}: những tín hiệu nổi bật nhất trong {n} tín hiệu mới OPC Radar thu thập từ số trước.',
   ledeb='Số bù: tạo sau cho mốc 07:30 giờ Thượng Hải ngày {d}, từ {n} tín hiệu mới tại thời điểm đó.',
   top='① Top {k} hôm nay', more='② Thêm tín hiệu mới', follow='③ Đáng theo dõi',
   note='Mọi mục đều đến từ nguồn công khai (Hacker News, GitHub, Hugging Face, …) kèm liên kết gốc; tạo tự động, không bịa số liệu. Chạm vào một mục để đọc ngay tại đây.',
   label='Bản tin công nghệ buổi sáng', labelb='Bản tin công nghệ buổi sáng (bù)', disc='thảo luận'),
 'fr': dict(home='Accueil', arch='Digests quotidiens', h1='Digest tech du matin · {d}', h1b='Digest tech du matin · {d} (rattrapage)',
   lede='Généré automatiquement à 07:30 heure de Shanghai le {d} : les plus marquants des {n} signaux repérés par OPC Radar depuis le numéro précédent.',
   ledeb='Numéro de rattrapage : généré après coup pour l’échéance de 07:30 heure de Shanghai du {d}, à partir des {n} signaux nouveaux à ce moment-là.',
   top='① Top {k} du jour', more='② Autres nouveaux signaux', follow='③ À suivre',
   note='Chaque entrée provient d’une source publique (Hacker News, GitHub, Hugging Face, …) avec son lien d’origine ; généré automatiquement, aucune donnée inventée. Touchez une entrée pour la lire ici.',
   label='Digest tech du matin', labelb='Digest tech du matin (rattrapage)', disc='discussion'),
 'es': dict(home='Inicio', arch='Resúmenes diarios', h1='Resumen tecnológico matinal · {d}', h1b='Resumen tecnológico matinal · {d} (atrasado)',
   lede='Generado automáticamente a las 07:30 hora de Shanghái del {d}: lo más destacado de las {n} señales que OPC Radar recogió desde el número anterior.',
   ledeb='Número atrasado: generado después para el corte de las 07:30 hora de Shanghái del {d}, a partir de las {n} señales nuevas en ese momento.',
   top='① Top {k} de hoy', more='② Más señales nuevas', follow='③ Para seguir',
   note='Cada entrada procede de una fuente pública (Hacker News, GitHub, Hugging Face, …) con su enlace original; generado automáticamente, sin métricas inventadas. Toca cualquier entrada para leerla aquí.',
   label='Resumen tecnológico matinal', labelb='Resumen tecnológico matinal (atrasado)', disc='debate'),
 'de': dict(home='Start', arch='Tägliche Digests', h1='Morgendlicher Tech-Digest · {d}', h1b='Morgendlicher Tech-Digest · {d} (nachgereicht)',
   lede='Automatisch erstellt um 07:30 Uhr Shanghai-Zeit am {d}: das Wichtigste aus {n} neuen Signalen, die OPC Radar seit der letzten Ausgabe gesammelt hat.',
   ledeb='Nachgereichte Ausgabe: nachträglich für den Stichtag 07:30 Uhr Shanghai-Zeit am {d} erstellt, aus den {n} damals neuen Signalen.',
   top='① Top {k} des Tages', more='② Weitere neue Signale', follow='③ Im Blick behalten',
   note='Jeder Eintrag stammt aus einer öffentlichen Quelle (Hacker News, GitHub, Hugging Face, …) mit Originallink; automatisch erstellt, keine erfundenen Zahlen. Tippe auf einen Eintrag, um ihn hier zu lesen.',
   label='Morgendlicher Tech-Digest', labelb='Morgendlicher Tech-Digest (nachgereicht)', disc='Diskussion'),
}
# in-page reader (modal) strings; shipped inside the lazy per-locale JSON, never in the page shell
UI = {
 'zh-Hans': dict(take='我们怎么看', rw='OPC Radar 编辑改写：事实均来自原文，「我们怎么看」为本站观点。', ex='原文摘录', nrw='尚未改写：以下为原文摘要与摘录（机器翻译）。', go='阅读原文', src='来源', close='关闭', loading='加载中…', fail='内容加载失败，请直接阅读原文。', orig='原标题'),
 'zh-Hant': dict(take='我們怎麼看', rw='OPC Radar 編輯改寫：事實均來自原文，「我們怎麼看」為本站觀點。', ex='原文摘錄', nrw='尚未改寫：以下為原文摘要與摘錄（機器翻譯）。', go='閱讀原文', src='來源', close='關閉', loading='載入中…', fail='內容載入失敗，請直接閱讀原文。', orig='原標題'),
 'en': dict(take='Our take', rw='Rewritten by OPC Radar: facts come only from the original; “Our take” is our opinion.', ex='From the source', nrw='Not rewritten yet: summary and excerpt from the source.', go='Read the original', src='Source', close='Close', loading='Loading…', fail='Could not load this entry; please read the original.', orig=''),
 'ja': dict(take='編集部の視点', rw='OPC Radar による書き直し：事実はすべて元記事から。「編集部の視点」は当サイトの意見です。', rwmt='OPC Radar による書き直し：事実はすべて元記事から。「編集部の視点」は当サイトの意見です（機械翻訳）。', ex='元記事からの抜粋', nrw='まだ書き直していません：元記事の要約と抜粋です（機械翻訳）。', go='元記事を読む', src='ソース', close='閉じる', loading='読み込み中…', fail='読み込めませんでした。元記事をご覧ください。', orig=''),
 'ko': dict(take='우리의 시각', rw='OPC Radar가 다시 쓴 글: 사실은 모두 원문에서 왔으며 \'우리의 시각\'은 사이트의 의견입니다(기계 번역).', ex='원문 발췌', nrw='아직 다시 쓰지 않음: 원문 요약과 발췌입니다(기계 번역).', go='원문 읽기', src='출처', close='닫기', loading='불러오는 중…', fail='불러오지 못했습니다. 원문을 읽어 주세요.', orig=''),
 'ms': dict(take='Pandangan kami', rw='Ditulis semula oleh OPC Radar: fakta hanya daripada sumber asal; “Pandangan kami” ialah pendapat kami (terjemahan mesin).', ex='Petikan daripada sumber', nrw='Belum ditulis semula: ringkasan dan petikan daripada sumber (terjemahan mesin).', go='Baca artikel asal', src='Sumber', close='Tutup', loading='Memuatkan…', fail='Gagal dimuatkan; sila baca artikel asal.', orig=''),
 'vi': dict(take='Góc nhìn của chúng tôi', rw='OPC Radar viết lại: dữ kiện chỉ lấy từ bài gốc; “Góc nhìn của chúng tôi” là ý kiến riêng (dịch máy).', ex='Trích từ nguồn', nrw='Chưa viết lại: tóm tắt và trích đoạn từ nguồn (dịch máy).', go='Đọc bài gốc', src='Nguồn', close='Đóng', loading='Đang tải…', fail='Không tải được; vui lòng đọc bài gốc.', orig=''),
 'fr': dict(take='Notre avis', rw='Réécrit par OPC Radar : les faits viennent uniquement de l’original ; « Notre avis » est notre opinion (traduction automatique).', ex='Extrait de la source', nrw='Pas encore réécrit : résumé et extrait de la source (traduction automatique).', go='Lire l’original', src='Source', close='Fermer', loading='Chargement…', fail='Chargement impossible ; lisez l’original.', orig=''),
 'es': dict(take='Nuestra opinión', rw='Reescrito por OPC Radar: los hechos proceden solo del original; «Nuestra opinión» es nuestra valoración (traducción automática).', ex='Extracto de la fuente', nrw='Aún no reescrito: resumen y extracto de la fuente (traducción automática).', go='Leer el original', src='Fuente', close='Cerrar', loading='Cargando…', fail='No se pudo cargar; lee el original.', orig=''),
 'de': dict(take='Unsere Einschätzung', rw='Von OPC Radar neu geschrieben: Fakten stammen nur aus dem Original; „Unsere Einschätzung“ ist unsere Meinung (maschinell übersetzt).', ex='Auszug aus der Quelle', nrw='Noch nicht neu geschrieben: Zusammenfassung und Auszug aus der Quelle (maschinell übersetzt).', go='Original lesen', src='Quelle', close='Schließen', loading='Wird geladen…', fail='Konnte nicht geladen werden; bitte das Original lesen.', orig=''),
}
BOXES = ['zh-Hans', 'zh-Hant', 'en', 'ja', 'ko', 'ms', 'vi', 'fr', 'es', 'de']
BEACON = ('<!--IA--><script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon=\'{"token":"41d8abdb6f1247c08f2412afcd5f2143"}\'></script>'
          '<script defer src="https://stats.incidental.site/events.js" data-site="opc" data-goal="outbound"></script><!--/IA-->')

def links(it, L):
    a = [it['url']] + it.get('extra', [])
    return ''.join(f'<a href="{e(u)}" rel="noopener" target="_blank">{e(host(u))}</a>' for u in a)

def card_attrs(x):
    return f'class="card" tabindex="0" role="button" aria-haspopup="dialog" data-k="{e(x["id"])}"'

def box(dg, L):
    t = T[L if (L != 'ja' or JA_KANJI) else 'en']; d = dg['date']
    def fct(x): return (x.get('fact') or {}).get(L, '')
    def sm(x): return (x.get('summary') or {}).get(L, '')
    top = ''.join(f'<li {card_attrs(x)}><div><b>{e(x["title"][L])}</b>' + (f'<p>{e(sm(x))}</p>' if sm(x) else '') +
                  f'<div class="ln">' + (f'<span>{e(fct(x))}</span>' if fct(x) else '') + f'{links(x, L)}</div></div></li>' for x in dg['top'])
    h = [f'<div class="langbox" data-lang="{L}"' + ('' if L == 'zh-Hans' else ' hidden') + '>',
         f'<p class="crumb"><a href="../../">{t["home"]}</a><span>/</span><a href="../">{t["arch"]}</a><span>/</span><span>{d}</span></p>',
         f'<h1>{e(dg["title"][L])}</h1>', f'<p class="lede">{e(dg["lede"][L])}</p>',
         f'<h2>{t["top"].format(k=len(dg["top"]))}</h2>', f'<ol class="top box" style="padding:4px 18px 8px">{top}</ol>']
    def ops(lst, cls=''):
        return '<ul class="ops">' + ''.join(
            f'<li {card_attrs(x)}{cls}><b class="t">{e(x["title"][L])}</b> — {e(fct(x) or host(x["url"]))}' +
            (f'<span class="sm">{e(sm(x))}</span>' if sm(x) else '') + '</li>' for x in lst) + '</ul>'
    if dg.get('more'): h += [f'<h2>{t["more"]}</h2>', ops(dg['more'])]
    if dg.get('follow'): h += [f'<h2>{t["follow"]}</h2>', ops(dg['follow']).replace('class="card"', 'class="card follow"')]
    h += [f'<p class="note">{t["note"]}</p>', '</div>']
    return '\n'.join(h)

READER_CSS = """
.dig .card{cursor:pointer;border-radius:var(--rs);outline:none;transition:background .15s}
.dig .card:hover b,.dig .card:hover .t{text-decoration:underline;text-underline-offset:3px;text-decoration-color:var(--ink3)}
.dig .card:focus-visible{box-shadow:0 0 0 2px var(--ink3)}
.dig ul.ops .t{color:var(--ink);font-weight:500}
.dig ul.ops .follow .t{font-weight:600}
.dig ul.ops .sm{display:block;color:var(--ink2);font-size:13px;margin-top:2px}
.dig ol.top .ln span{color:var(--ink3)}
.dm[hidden]{display:none}
.dm{position:fixed;inset:0;z-index:60;display:flex;align-items:center;justify-content:center;padding:24px}
.dm-bg{position:absolute;inset:0;background:rgba(0,0,0,.45);backdrop-filter:blur(2px)}
.dm-card{position:relative;background:var(--sf);color:var(--ink);border:1px solid var(--line);border-radius:var(--r);width:min(680px,100%);max-height:min(86vh,900px);overflow:auto;padding:28px 28px 22px;box-shadow:0 24px 64px rgba(0,0,0,.25);overscroll-behavior:contain}
.dm-x{position:absolute;top:12px;right:12px}
.dm-meta{font:12px "Geist Mono",monospace;color:var(--ink3);display:flex;gap:10px;flex-wrap:wrap;margin:0 36px 10px 0}
.dm-card h2{font-size:clamp(20px,3vw,24px);letter-spacing:-.025em;line-height:1.25;margin:0 0 10px;font-weight:700}
.dm-sum{color:var(--ink2);font-size:15px;margin:0 0 16px}
.dm-body p{font-size:15px;line-height:1.7;margin:0 0 12px}
.dm-body h3{font-size:14px;margin:18px 0 8px;letter-spacing:-.01em}
.dm-take{background:var(--sf2);border:1px solid var(--line2);border-radius:var(--rs);padding:12px 14px;margin:16px 0 6px}
.dm-take p{color:var(--ink);margin:0 0 8px}.dm-take p:last-child{margin:0}
.dm-note{font-size:12px;color:var(--ink3);margin:14px 0 0}
.dm-foot{position:sticky;bottom:-22px;background:var(--sf);padding:14px 0 0;margin-top:14px;border-top:1px solid var(--line2);display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.dm-foot .credit{font-size:12px;color:var(--ink3)}
.dm-foot .btn{white-space:nowrap}
html.dm-open{overflow:hidden}
@media (max-width:640px){.dm{padding:0;align-items:flex-end}.dm-card{width:100%;max-height:92vh;border-radius:var(--r) var(--r) 0 0;padding:22px 18px 18px;animation:dmUp .22s ease-out}.dm-foot{bottom:-18px}.dm-foot .btn{flex:1 0 100%;justify-content:center}}
@keyframes dmUp{from{transform:translateY(24px);opacity:.6}to{transform:none;opacity:1}}
@media (prefers-reduced-motion:reduce){.dm-card{animation:none}}
"""

READER_JS = r"""
(function(){
const V=document.querySelector('main').dataset.v||'';const cache={};
const dm=document.getElementById('dm'),card=dm.querySelector('.dm-card');let last=null,openK=null;
function curL(){return window.__digL||'en'}
function load(L){if(!cache[L])cache[L]=fetch(L+'.json?v='+V).then(r=>{if(!r.ok)throw 0;return r.json()}).catch(e=>{delete cache[L];throw e});return cache[L]}
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function P(a){return (a||[]).map(p=>'<p>'+esc(p)+'</p>').join('')}
function render(D,k){const U=D.ui,x=D.items[k];if(!x){card.querySelector('.dm-in').innerHTML='<p>'+esc(U.fail)+'</p>';return}
  const meta=[x.src,x.date].filter(Boolean).map(esc).join('<span>·</span>');
  let h='<div class="dm-meta">'+meta+(x.f?'<span>·</span>'+esc(x.f):'')+'</div><h2 id="dmT">'+esc(x.t)+'</h2>';
  if(x.orig&&U.orig)h+='<div class="dm-meta">'+esc(U.orig)+'：'+esc(x.orig)+'</div>';
  if(x.s)h+='<p class="dm-sum">'+esc(x.s)+'</p>';
  h+='<div class="dm-body">';
  if(x.rw){h+=P(x.body)+'<div class="dm-take"><h3>'+esc(U.take)+'</h3>'+P(x.take)+'</div><p class="dm-note">'+esc(x.mt&&U.rwmt?U.rwmt:U.rw)+'</p>'}
  else if(x.ex&&x.ex.length){h+='<h3>'+esc(U.ex)+'</h3>'+P(x.ex)+'<p class="dm-note">'+esc(U.nrw)+'</p>'}
  h+='</div><div class="dm-foot"><a class="btn pri" href="'+esc(x.url)+'" target="_blank" rel="noopener">'+esc(U.go)+' ↗</a><span class="credit">'+esc(U.src)+': '+esc(x.src)+'</span>'+(x.disc?'<a class="credit" href="'+esc(x.disc)+'" target="_blank" rel="noopener">'+esc(x.dlabel||'')+'</a>':'')+'</div>';
  card.querySelector('.dm-in').innerHTML=h;card.querySelector('.dm-x').setAttribute('aria-label',U.close);card.scrollTop=0}
function open(k,from){last=from||document.activeElement;openK=k;const L=curL();dm.hidden=false;document.documentElement.classList.add('dm-open');
  card.querySelector('.dm-in').innerHTML='<p class="dm-note">…</p>';card.querySelector('.dm-x').focus();
  load(L).then(D=>{if(openK===k)render(D,k)}).catch(()=>{card.querySelector('.dm-in').innerHTML='<p class="dm-note">—</p>'});
  try{window.ievt&&window.ievt('preview_open',{kind:'digest',id:k,date:document.querySelector('main').dataset.date||'',lang:L})}catch(e){}}
function close(){if(dm.hidden)return;dm.hidden=true;openK=null;document.documentElement.classList.remove('dm-open');if(last&&last.focus)last.focus()}
document.addEventListener('click',ev=>{const t=ev.target;if(t.closest('[data-close]')){close();return}
  if(t.closest('a'))return;const c=t.closest('.card[data-k]');if(c){ev.preventDefault();open(c.dataset.k,c)}});
document.addEventListener('keydown',ev=>{if(!dm.hidden){if(ev.key==='Escape'){ev.preventDefault();close();return}
    if(ev.key==='Tab'){const f=[...card.querySelectorAll('a[href],button,[tabindex]:not([tabindex="-1"])')].filter(n=>n.offsetParent!==null);if(!f.length)return;const a=f[0],b=f[f.length-1];
      if(ev.shiftKey&&document.activeElement===a){ev.preventDefault();b.focus()}else if(!ev.shiftKey&&document.activeElement===b){ev.preventDefault();a.focus()}}return}
  const c=ev.target.closest&&ev.target.closest('.card[data-k]');if(c&&(ev.key==='Enter'||ev.key===' ')){ev.preventDefault();open(c.dataset.k,c)}});
// warm the current locale's JSON on first intent (hover/focus/touch), never on page load
let warmed=0;const warm=()=>{if(warmed)return;warmed=1;load(curL()).catch(()=>{})};
document.addEventListener('pointerover',ev=>{if(ev.target.closest&&ev.target.closest('.card[data-k]'))warm()},{passive:true});
document.addEventListener('focusin',ev=>{if(ev.target.closest&&ev.target.closest('.card[data-k]'))warm()});
})();
"""

def page(dg):
    d = dg['date']; ti = e(dg['title']['en']); de = e(dg['lede']['en']); url = f'{BASE}digest/{d}/'
    v = re.sub(r'\D', '', dg.get('updated') or dg.get('generated') or '')[:12]
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
@media (max-width:760px){{.dig{{padding-left:18px;padding-right:18px}}}}
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
{READER_CSS}</style>
{BEACON}
</head><body>
<header class="nav"><div class="wrap navin">
<a class="brand" href="../../"><span class="logo"></span>OPC Radar</a>
<nav id="navlinks"><a href="../../">Home</a><a href="../">Digests</a></nav>
<div class="tools"><select id="langSel" aria-label="language"></select>
<button class="icon" id="themeBtn" aria-label="theme">◐</button></div></div></header>
<main class="wrap dig" data-date="{d}" data-v="{v}">
{''.join(box(dg, L) for L in BOXES)}
</main>
<div class="dm" id="dm" hidden><div class="dm-bg" data-close></div><div class="dm-card" role="dialog" aria-modal="true" aria-labelledby="dmT"><button class="icon dm-x" data-close aria-label="close">✕</button><div class="dm-in"></div></div></div>
<footer class="wrap foot"><span>OPC Radar · daily digest</span><span>{d}</span></footer>
<script src="../../i18n.js?v=8"></script>
<script>
const LANGS_D={{"zh-Hans":"简体中文","zh-Hant":"繁體中文",en:"English",ja:"日本語",ko:"한국어",ms:"Bahasa Melayu",vi:"Tiếng Việt",fr:"Français",es:"Español",de:"Deutsch"}};
function pickLang(){{try{{const q=new URLSearchParams(location.search).get('lang');if(q&&LANGS_D[q])return q}}catch(e){{}}const s=localStorage.getItem('lang');if(s&&LANGS_D[s])return s;const n=(navigator.language||'en').toLowerCase();if(n.startsWith('zh'))return/(tw|hk|mo|hant)/.test(n)?'zh-Hant':'zh-Hans';const b=n.slice(0,2);return LANGS_D[b]?b:'en'}}
let L=pickLang();
const sel=document.getElementById('langSel');
sel.innerHTML=Object.entries(LANGS_D).map(([k,v])=>`<option value="${{k}}">${{v}}</option>`).join('');
sel.value=L;
function apply(){{
  const has=!!document.querySelector('.langbox[data-lang="'+L+'"]');const box=has?L:(/^zh/.test(L)?'zh-Hans':'en');
  window.__digL=box;document.documentElement.lang=box;
  document.querySelectorAll('.langbox').forEach(el=>{{el.hidden=el.dataset.lang!==box}});
  const h=document.querySelector('.langbox[data-lang="'+box+'"] h1');document.title=(h?h.textContent:'')+' · OPC Radar';
}}
sel.onchange=()=>{{L=sel.value;localStorage.setItem('lang',L);apply()}};
document.getElementById('themeBtn').onclick=()=>{{const n=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=n;localStorage.setItem('theme',n)}};
apply();
</script>
<script>{READER_JS}</script>
</body></html>
'''

LEGACY_LABEL = {  # hand-made issues (e56cd18) keep their original archive labels
 '2026-10-17': {'zh-Hans': '早间技术热点', 'zh-Hant': '早間技術熱點', 'en': 'Morning tech digest'},
 '2026-10-13': {'zh-Hans': '技术热点简报（补发）', 'zh-Hant': '技術熱點簡報（補發）', 'en': 'Tech digest (catch-up)'},
}
ARCH_BOXES = ['zh-Hans', 'zh-Hant', 'en']   # the archive page keeps its 3 boxes (en serves all non-Chinese locales)
def label(dg, L):
    if dg.get('label'): return dg['label'].get(L) or dg['label'].get('en', '')
    return LEGACY_LABEL.get(dg['date'], {}).get(L) or T[L]['label']

def write_archive(digs):
    p = os.path.join(S, 'digest/index.html'); s = open(p, encoding='utf-8').read()
    for L in ARCH_BOXES:
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

RW_DIR = os.path.join(D, 'digest_rewrites')
def rewrites_for(ds):
    """Editor-written rewrites for an issue (scripts/digest_rewrites/<date>.json, keyed by item URL)."""
    p = os.path.join(RW_DIR, f'{ds}.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}

STATS = {'summary_source': 0, 'summary_editor': 0, 'summary_fallback': 0, 'summary_none': 0, 'rw_editor': 0, 'rw_llm': 0, 'rw_none': 0}
def enrich(i, tr, RW, with_extra=True):
    """Digest entry + per-locale reader record for one real item. Every text comes from the item's own source."""
    u = i['url']; src = source_text(i); over = RW.get(u) or {}
    ten = title(i, 'en')
    # 1-2 sentence summary
    if over.get('summary'):
        sm = tr.one(over['summary']['en'], over['summary'].get('zh-Hans')); STATS['summary_editor'] += 1
    elif src['desc'] and not HAN.search(src['desc']):
        sm = tr.one(src['desc']); STATS['summary_source'] += 1
    elif loc(i, 'summary', 'en'):
        sm = {L: loc(i, 'summary', L) for L in BOXES}; STATS['summary_source'] += 1
    else:
        sname = (i.get('source') or '').replace(' · new', '')
        if sname and not HAN.search(sname):
            sm = {L: FALLBACK[L].format(src=sname, h=host(u)) for L in BOXES}; STATS['summary_fallback'] += 1
        else: sm = {L: '' for L in BOXES}; STATS['summary_none'] += 1
    r = {'id': i.get('id'), 'title': {L: title(i, L) for L in BOXES}, 'summary': sm,
         'fact': {L: fact(i, L) for L in BOXES}, 'url': u, 'src': host(u), 'date': (i.get('date') or '')[:10]}
    if with_extra and i.get('discuss') and i['discuss'] != u: r['extra'] = [i['discuss']]
    # reader content: editor rewrite > LLM rewrite (when a key is configured) > summary + real excerpt
    rw = None; how = ''
    if over.get('en') and over.get('zh-Hans'):
        bad = digest_llm.check(over, src['full'] + ' ' + (over.get('extra_source') or ''))
        if bad: print('  editor rewrite check:', u[:60], bad[:3])
        rw, how = over, 'editor'
    else:
        rw = digest_llm.rewrite(ten, src['full'], u); how = 'llm' if rw else ''
    STATS['rw_' + (how or 'none')] += 1
    det = {}
    ja_ed = over.get('ja') if (JA_KANJI and how == 'editor' and isinstance(over.get('ja'), dict)) else None
    if rw:
        body = tr.many(rw['en']['body'], rw['zh-Hans']['body']); take = tr.many(rw['en']['take'], rw['zh-Hans']['take'])
        if ja_ed and ja_ed.get('body') and ja_ed.get('take'):   # editor-written Japanese (human, not machine-translated)
            body['ja'] = list(ja_ed['body']); take['ja'] = list(ja_ed['take'])
        else: ja_ed = None if not ja_ed else {k: v for k, v in ja_ed.items() if k in ('title', 'summary')}
    else:
        ex = tr.one(src['excerpt']) if src['excerpt'] else {L: '' for L in BOXES}
    if ja_ed:   # editor Japanese title / summary replace the machine translation (copies: never mutate the i18n cache)
        if ja_ed.get('title') and dok('ja', ja_ed['title']): r['title'] = dict(r['title'], ja=ja_ed['title'])
        if ja_ed.get('summary') and dok('ja', ja_ed['summary']): sm = dict(sm, ja=ja_ed['summary']); r['summary'] = sm
    for L in BOXES:
        x = {'t': r['title'][L], 's': sm[L], 'f': r['fact'][L], 'src': r['src'], 'date': r['date'], 'url': u, 'rw': bool(rw)}
        if i.get('discuss') and i['discuss'] != u: x['disc'] = i['discuss']; x['dlabel'] = T[L]['disc']
        if L.startswith('zh') and i.get('lang') != 'zh' and r['title'][L] != i.get('title'): x['orig'] = i.get('title')
        if rw:
            x['body'] = body[L]; x['take'] = take[L]; x['by'] = how
            if L == 'ja' and not (ja_ed and ja_ed.get('body')): x['mt'] = 1   # Japanese reader text came from the translator
        elif ex[L]: x['ex'] = [ex[L]]
        det[L] = x
    r['rw'] = how or ''
    if not JA_KANJI:   # strict zero-Han rule: the ja locale mirrors English
        for k in ('title', 'summary', 'fact'): r[k]['ja'] = r[k]['en']
        det['ja'] = dict(det['en'])
    return r, det

def write_reader(ds, dets):
    for L in BOXES:
        out = {'ui': UI[L if (L != 'ja' or JA_KANJI) else 'en'], 'items': {k: v[L] for k, v in dets.items()}}
        json.dump(out, open(os.path.join(S, 'digest', ds, f'{L}.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

def item_from_entry(x):
    """An item that dropped out of the rolling items.json: rebuild the minimum from the stored entry (real fields only)."""
    t = x.get('title') or {}
    return {'id': x.get('id'), 'title': t.get('en') or '', 'url': x['url'], 'title_i18n': t, 'source': '',
            'discuss': (x.get('extra') or [None])[0], 'lang': 'en'}

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
    G = json.load(open(DIG_P, encoding='utf-8')) if os.path.exists(DIG_P) else {'latest': None, 'digests': []}
    old = next((x for x in G['digests'] if x['date'] == ds), None)
    exists = bool(old) or os.path.exists(os.path.join(S, 'digest', ds, 'index.html'))
    if exists and not a['force']:
        done(f'digest {ds}: already published; nothing to do (idempotent)', changed=0, date=ds)
    data = json.load(open(os.path.join(S, 'data/items.json'), encoding='utf-8'))
    tr = Tr(); RW = rewrites_for(ds)
    print('llm rewrite:', 'enabled' if digest_llm.key() else 'off (no DIGEST_LLM_API_KEY / OPENAI_API_KEY)', '· editor rewrites:', len(RW))

    if exists:   # forced in-place rebuild of an existing issue: keep its selection and metadata
        if not old or not old.get('auto'): done(f'digest {ds}: --force only rebuilds auto-generated issues (hand-made issue left untouched)', changed=0, date=ds)
        by = {i['url']: i for i in data['items']}
        def it(x): return by.get(x['url']) or item_from_entry(x)
        dets = {}; dg = dict(old); dg['updated'] = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        n = old.get('new_count', 0); kind = old.get('kind', 'daily')
        tk = 'h1b' if kind == 'catch-up' else 'h1'; lk = 'ledeb' if kind == 'catch-up' else 'lede'
        dg['title'] = {L: T[L][tk].format(d=ds) for L in BOXES}; dg['lede'] = {L: T[L][lk].format(d=ds, n=n) for L in BOXES}
        dg['label'] = {L: T[L]['labelb' if kind == 'catch-up' else 'label'] for L in BOXES}
        for k in ('top', 'more', 'follow'):
            out = []
            for x in old.get(k) or []:
                print(' ', k, x['url'][:80])
                r, det = enrich(it(x), tr, RW, with_extra=(k == 'top'))
                if k == 'top' and x.get('extra'): r['extra'] = x['extra']
                out.append(r); dets[r['id']] = det
            dg[k] = out
        dedup = None
    else:
        if (now - cutoff) > dt.timedelta(days=MAX_BACKFILL_D):
            done(f'digest {ds}: older than {MAX_BACKFILL_D} days; items.json is a rolling snapshot, refusing to backfill', changed=0, date=ds)
        if (now - cutoff) > dt.timedelta(hours=20): kind = 'catch-up'   # generated well after the morning cutoff
        seen = json.load(open(SEEN_P)) if os.path.exists(SEEN_P) else {}
        used = set()
        for x in G['digests']:
            for k in ('top', 'more', 'follow'):
                for it_ in x.get(k) or []: used.add(it_.get('url')); used.update(it_.get('extra') or [])
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
        dets = {}
        def ent(lst, ex):
            out = []
            for i in lst:
                print(' ', i['url'][:80]); r, det = enrich(i, tr, RW, ex); out.append(r); dets[r['id']] = det
            return out
        dg = {'date': ds, 'path': f'digest/{ds}/', 'kind': kind, 'auto': True,
              'cutoff': cutoff.strftime('%Y-%m-%dT%H:%M:%SZ'), 'generated': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'new_count': n,
              'title': {L: T[L][tk].format(d=ds) for L in BOXES}, 'lede': {L: T[L][lk].format(d=ds, n=n) for L in BOXES},
              'label': {L: T[L]['labelb' if kind == 'catch-up' else 'label'] for L in BOXES},
              'top': ent(top, True), 'more': ent(more, False), 'follow': ent(follow, False)}
        # provenance: every URL must be a real item from items.json
        real = {i['url'] for i in data['items']}
        for k in ('top', 'more', 'follow'):
            for it_ in dg[k]:
                assert it_['url'] in real, it_['url']
    tr.save()
    if not JA_KANJI:
        for k in ('title', 'lede', 'label'): dg[k]['ja'] = dg[k]['en']
    G['digests'] = sorted([x for x in G['digests'] if x['date'] != ds] + [dg], key=lambda x: x['date'], reverse=True)
    G['latest'] = G['digests'][0]['date']
    json.dump(G, open(DIG_P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    os.makedirs(os.path.join(S, 'digest', ds), exist_ok=True)
    open(os.path.join(S, 'digest', ds, 'index.html'), 'w', encoding='utf-8').write(page(dg))
    write_reader(ds, dets)
    write_archive(G['digests'])
    for f in ['digest/index.html'] + [f'digest/{x["date"]}/index.html' for x in G['digests']]:
        p = os.path.join(S, f)
        if os.path.exists(p): add_beacon(p)
    sitemaps(ds)
    if dedup is not None:
        seen[ds] = sorted(dedup)
        keep = sorted(seen)[-45:]; seen = {k: seen[k] for k in keep}
        json.dump(seen, open(SEEN_P, 'w'), ensure_ascii=False, indent=0)
    st = ' '.join(f'{k}={v}' for k, v in STATS.items())
    print('stats', st)
    p = os.environ.get('GITHUB_STEP_SUMMARY')
    if p: open(p, 'a').write(f'digest {ds}: {st}\n')
    nt = len(dg['top']); nm = len(dg.get('more') or []); nf = len(dg.get('follow') or [])
    done(f'digest {ds}: {"rebuilt (forced)" if dedup is None else "published"} {kind} issue · top {nt}, more {nm}, follow {nf}', changed=1, date=ds)

if __name__ == '__main__': main()
