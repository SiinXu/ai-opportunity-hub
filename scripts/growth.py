"""Analytics + SEO/GEO + newsletter for OPC Radar (run after refresh.py; idempotent).
Writes IA blocks into site/index.html, crawlable item list inside <main id="app"> (app.js replaces it on load),
robots.txt, sitemaps, llms.txt, llms-full.txt."""
import json, os, re, html, subprocess, collections
D = os.path.dirname(os.path.abspath(__file__)); S = os.path.join(D, '../site'); BASE = 'https://siinxu.github.io/ai-opportunity-hub/'
data = json.load(open(os.path.join(S, 'data/items.json'))); items = data['items']; n = len(items)
cnt = collections.Counter(i['ch'] for i in items)
LC = ['zh-Hans', 'zh-Hant', 'en', 'ja', 'ko', 'ms', 'vi', 'fr', 'es', 'de']
INTRO = {
 'en': f'OPC Radar is a free opportunity radar for one-person companies (OPC), indie developers, designers and cross-border sellers. It collects AI tools, GitHub repos, new products, news, deals and ideas from public sources (Hacker News, GitHub, Hugging Face, DEV, Lobsters and a curated list), translates them into 10 languages and refreshes automatically. Currently {n} items.',
 'zh-Hans': f'OPC Radar 是给一人公司（OPC）、独立开发者、设计师和跨境卖家用的免费商机雷达：从公开来源（Hacker News、GitHub、Hugging Face、DEV、Lobsters 与人工精选）收集 AI 工具、GitHub 仓库、新产品、资讯、优惠和点子，翻译成 10 种语言并自动刷新。当前共 {n} 条。',
 'zh-Hant': f'OPC Radar 是給一人公司（OPC）、獨立開發者、設計師和跨境賣家用的免費商機雷達：從公開來源（Hacker News、GitHub、Hugging Face、DEV、Lobsters 與人工精選）收集 AI 工具、GitHub 倉庫、新產品、資訊、優惠和點子，翻譯成 10 種語言並自動刷新。目前共 {n} 條。',
 'ja': f'OPC Radar は、一人会社（OPC）、個人開発者、デザイナー、越境EC事業者向けの無料のチャンスレーダーです。公開ソース（Hacker News、GitHub、Hugging Face、DEV、Lobsters、厳選リスト）から AI ツール、GitHub リポジトリ、新製品、ニュース、お得情報、アイデアを集め、10 言語に翻訳して自動更新します。現在 {n} 件。',
 'ko': f'OPC Radar는 1인 기업(OPC), 인디 개발자, 디자이너, 크로스보더 셀러를 위한 무료 기회 레이더입니다. 공개 소스(Hacker News, GitHub, Hugging Face, DEV, Lobsters, 큐레이션 목록)에서 AI 도구, GitHub 저장소, 신제품, 뉴스, 혜택, 아이디어를 모아 10개 언어로 번역하고 자동으로 갱신합니다. 현재 {n}개 항목.',
 'ms': f'OPC Radar ialah radar peluang percuma untuk syarikat seorang (OPC), pembangun indie, pereka dan penjual rentas sempadan. Ia mengumpul alat AI, repo GitHub, produk baharu, berita, tawaran dan idea daripada sumber awam (Hacker News, GitHub, Hugging Face, DEV, Lobsters dan senarai pilihan), menterjemah ke 10 bahasa dan dikemas kini secara automatik. Kini {n} item.',
 'vi': f'OPC Radar là radar cơ hội miễn phí cho công ty một người (OPC), lập trình viên độc lập, nhà thiết kế và người bán xuyên biên giới. Trang thu thập công cụ AI, kho GitHub, sản phẩm mới, tin tức, ưu đãi và ý tưởng từ nguồn công khai (Hacker News, GitHub, Hugging Face, DEV, Lobsters và danh sách tuyển chọn), dịch sang 10 ngôn ngữ và tự động cập nhật. Hiện có {n} mục.',
 'fr': f'OPC Radar est un radar d’opportunités gratuit pour les entreprises d’une personne (OPC), développeurs indépendants, designers et vendeurs transfrontaliers. Il collecte outils IA, dépôts GitHub, nouveaux produits, actualités, bons plans et idées depuis des sources publiques (Hacker News, GitHub, Hugging Face, DEV, Lobsters et une sélection), les traduit en 10 langues et se met à jour automatiquement. Actuellement {n} éléments.',
 'es': f'OPC Radar es un radar de oportunidades gratuito para empresas unipersonales (OPC), desarrolladores independientes, diseñadores y vendedores transfronterizos. Reúne herramientas de IA, repos de GitHub, productos nuevos, noticias, ofertas e ideas de fuentes públicas (Hacker News, GitHub, Hugging Face, DEV, Lobsters y una selección), los traduce a 10 idiomas y se actualiza automáticamente. Ahora {n} elementos.',
 'de': f'OPC Radar ist ein kostenloser Chancen-Radar für Ein-Personen-Unternehmen (OPC), Indie-Entwickler, Designer und grenzüberschreitende Händler. Er sammelt KI-Tools, GitHub-Repos, neue Produkte, News, Deals und Ideen aus öffentlichen Quellen (Hacker News, GitHub, Hugging Face, DEV, Lobsters und eine kuratierte Liste), übersetzt sie in 10 Sprachen und aktualisiert sich automatisch. Derzeit {n} Einträge.'}
CH = {'ai': 'AI', 'repos': 'GitHub repos', 'products': 'New products', 'news': 'News', 'deals': 'Deals', 'ideas': 'Ideas'}
SRC = {'精选': 'Curated'}  # non-Chinese outputs carry no Chinese
def en(i, k): return (i.get(k + '_i18n') or {}).get('en') or i.get(k) or ''
e = html.escape
ssr = f'<h1>OPC Radar — opportunity radar for one-person companies</h1><p>{e(INTRO["en"])}</p>' + ''.join(
    f'<h2>{e(CH.get(c, c))} ({cnt[c]})</h2><ul>' + ''.join(f'<li><a href="{e(i["url"])}" rel="noopener">{e(en(i, "title"))}</a> — {e(en(i, "summary"))[:200]}</li>' for i in [x for x in items if x['ch'] == c][:8]) + '</ul>' for c in CH if cnt[c])
cfg = {'root': S, 'base': BASE, 'name': 'OPC Radar', 'site': 'opc', 'cf_token': '41d8abdb6f1247c08f2412afcd5f2143', 'goal': 'outbound', 'og_image': 'og.png', 'hreflang': True, 'locales': LC,
       'subcss_path': os.path.join(D, 'subscribe.css'),
       'desc': 'Opportunity radar for one-person companies: AI tools, GitHub repos, new products, news, deals and ideas for indie developers, designers and cross-border sellers. 10 languages, refreshed automatically.',
       'intro': INTRO, 'intro_after': '</header>', 'intro_fallback': 'zh-Hans',
       'intro_css': 'max-width:1120px;margin:14px auto 0;padding:0 20px;font-size:12.5px;line-height:1.55;opacity:.72',
       'sub_before': '<footer', 'sub_css': 'max-width:1120px;margin:24px auto;padding:0 20px;--ie-acc:#16a34a;--ie-acc-ink:#fff',
       'pages': [{'file': 'index.html', 'rel': '', 'ld': [{'@type': 'CollectionPage', 'name': 'OPC Radar', 'url': BASE, 'about': 'Opportunities for one-person companies', 'numberOfItems': n, 'dateModified': data.get('updated'), 'publisher': {'@id': 'https://incidental.site/#org'}}]}]}
llms = f'# OPC Radar\n> {INTRO["en"]}\n\n- Site: {BASE}\n- Data (JSON): {BASE}data/items.json\n- Languages: {", ".join(LC)} (append ?lang=<code>)\n- Publisher: Incidental AI (https://incidental.site/)\n- Full list: {BASE}llms-full.txt\n- Updated: {data.get("updated")}\n\n## Channels\n' + ''.join(f'- {CH.get(c, c)}: {cnt[c]} items\n' for c in CH)
cfg['llms.txt'] = llms
cfg['llms-full.txt'] = llms + '\n' + ''.join(f'\n## {CH.get(c, c)}\n' + ''.join(f'- [{en(i, "title")}]({i["url"]}) ({SRC.get(i.get("source", ""), i.get("source", ""))}, {i.get("date", "")}): {en(i, "summary")}\n' for i in items if i['ch'] == c) for c in CH)
p = '/tmp/opc-ia.json'; json.dump(cfg, open(p, 'w'), ensure_ascii=False)
subprocess.run(['python3', os.path.join(D, 'ia_inject.py'), p], check=True)
ip = os.path.join(S, 'index.html'); s = open(ip, encoding='utf-8').read()
s = re.sub(r'(<main id="app" class="wrap">).*?(</main>)', lambda m: m.group(1) + ssr + m.group(2), s, count=1, flags=re.S)
open(ip, 'w', encoding='utf-8').write(s); print('growth ok', n)
