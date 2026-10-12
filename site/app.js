const CH=["ai","repos","products","news","deals","ideas"];
const ICON={ai:"✦",repos:"⌥",products:"◇",news:"◎",deals:"¥",ideas:"✧"};
let L=detectLang(),DATA={items:[]};const t=k=>I18N[L][k]||I18N.en[k];
const $=s=>document.querySelector(s),esc=s=>String(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const host=u=>{try{return new URL(u).hostname.replace(/^www\./,'')}catch(e){return''}};
const TT=i=>(i.title_i18n&&i.title_i18n[L])||i.title,SS=i=>(i.summary_i18n&&i.summary_i18n[L])||i.summary||'';
function ago(d){if(!d)return'';const m=(Date.now()-Date.parse(d.replace(' ','T')+(d.length>10&&!/Z$/.test(d)?'Z':'')))/6e4;if(!isFinite(m))return'';const f=new Intl.RelativeTimeFormat(L,{numeric:'auto'});return m<60?f.format(-Math.max(1,Math.round(m)),'minute'):m<1440?f.format(-Math.round(m/60),'hour'):f.format(-Math.round(m/1440),'day')}
const DOT={ai:"#6366f1",repos:"#0ea5e9",products:"#f59e0b",news:"#64748b",deals:"#ef4444",ideas:"#10b981"};
const fav=(i,s=64)=>{const o=(String(i.url||'').match(/github\.com\/([^/]+)/)||[])[1];return o?`https://github.com/${o}.png?size=${s}`:`https://www.google.com/s2/favicons?sz=${s}&domain=${host(i.url)}`};
const ico=(i,c='ico')=>`<span class="${c}"><img loading="lazy" alt="" src="${fav(i)}" onerror="this.replaceWith(Object.assign(document.createElement('b'),{textContent:'${ICON[i.ch]}'}))"></span>`;
const chip=i=>`<span class="chip"><i style="background:${DOT[i.ch]}"></i>${t(i.ch)}</span>`;
function row(i,n){return `<a class="row" href="#/item/${i.id}">${n?`<span class="num">${String(n).padStart(2,'0')}</span>`:''}${ico(i)}
<span class="rt"><b>${esc(TT(i))}</b><small>${esc(SS(i)||host(i.url))}</small><span class="rk">${chip(i)}<span>${esc(host(i.url))}</span>${i.meta?`<em>${esc(i.meta)}</em>`:''}<time>${ago(i.date)}</time></span></span></a>`}
function bykind(c,n){return DATA.items.filter(i=>i.ch===c).sort((a,b)=>(!!SS(b)-!!SS(a))||b.date.localeCompare(a.date)).slice(0,n)}
function bytrend(n){return DATA.items.filter(i=>i.trend).sort((a,b)=>(b.heat||0)-(a.heat||0)||b.date.localeCompare(a.date)).slice(0,n)}
function toast(i,k){return `<a class="toast" style="--k:${k}" href="#/item/${i.id}">${ico(i,'ico sm')}<span><b>${esc(TT(i))}</b><small>${t(i.ch)} · ${esc(i.meta||host(i.url))}</small></span><time>${ago(i.date)}</time></a>`}
function feat(i){return `<a class="feat" href="#/item/${i.id}"><span class="fh">${ico(i,'ico lg')}${chip(i)}</span><b>${esc(TT(i))}</b><p>${esc(SS(i)||host(i.url))}</p><span class="ff"><span>${esc(host(i.url))}</span>${i.meta?`<em>${esc(i.meta)}</em>`:''}<i>↗</i></span></a>`}
function panel(c,n){const x=bykind(c,n);return `<section class="panel"><a class="ph2" href="#/c/${c}"><span><i style="background:${DOT[c]}"></i>${t(c)}</span><em>${DATA.items.filter(i=>i.ch===c).length} →</em></a>${x.map(i=>`<a class="mini" href="#/item/${i.id}">${ico(i,'ico sm')}<span><b>${esc(TT(i))}</b><small>${esc(i.meta||host(i.url))} · ${ago(i.date)}</small></span></a>`).join('')}</section>`}
function home(){const used=new Set(),take=a=>a.filter(i=>!used.has(i.id)&&used.add(i.id));
const toasts=take([...DATA.items].sort((a,b)=>b.date.localeCompare(a.date)).slice(0,3));
const feats=take([bykind('repos',2)[1],bykind('ai',2)[1],bykind('products',2)[1],bykind('ideas',2)[0],bykind('ideas',2)[1],bykind('deals',1)[0]].filter(Boolean)).slice(0,4);
const trends=take(bytrend(12));
const deals=take(bykind('deals',10));
const top=take([...DATA.items].filter(i=>SS(i)).sort((a,b)=>b.date.localeCompare(a.date))).slice(0,14);
return `<section class="hero"><div class="dots"></div><div class="hl">
<a class="pill" href="#/c/ideas"><span>${t('pill1')}</span>${t('pill2')} →</a>
<h1>${t('h1a')}<br>${t('h1b')}</h1><p class="lede">${t('lede1')} ${t('lede2')}</p>
<div class="ctas"><a class="btn pri" href="#top">${t('cta1')}</a><a class="btn" href="#/search">${t('cta2')} <kbd>/</kbd></a></div>
<div class="stats">${CH.map(c=>`<a href="#/c/${c}"><b>${DATA.items.filter(i=>i.ch===c).length}</b><span><i style="background:${DOT[c]}"></i>${t(c)}</span></a>`).join('')}</div></div>
<div class="stack"><span class="live"><i></i>LIVE · ${t('updated')} ${ago(DATA.updated)}</span>${toasts.map(toast).join('')}</div></section>
<section class="sec"><div class="sh"><h2>${t('picks')}</h2></div><div class="feats">${feats.map(feat).join('')}</div></section>
<section class="sec split"><div><div class="sh"><h2>${t('trends')}</h2><a class="muted" href="#/c/ai">${t('viewAll')} →</a></div><div class="feed box">${trends.map((i,n)=>row(i,n+1)).join('')}</div></div>
<aside>${panel('news',6)}${panel('ai',5)}</aside></section>
<section class="sec"><div class="sh"><h2>${t('deals')}</h2><a class="muted" href="#/c/deals">${t('viewAll')} →</a></div><div class="feed box">${deals.map((i,n)=>row(i,n+1)).join('')}</div></section>
<section class="sec split" id="top"><div><div class="sh"><h2>${t('latest')}</h2><a class="muted" href="#/search">${t('viewAll')} →</a></div><div class="feed box">${top.map((i,n)=>row(i,n+1)).join('')}</div></div>
<aside>${panel('repos',6)}${panel('products',5)}</aside></section>
<section class="sec"><div class="sh"><h2>${t('channels')}</h2></div><div class="panels">${['ai','products','news','ideas'].map(c=>panel(c,6)).join('')}</div></section>`}
function winList(c){return ''}
function channel(c){const x=DATA.items.filter(i=>i.ch===c);return `<section class="page"><div class="tabs">${CH.map(k=>`<a class="${k===c?'on':''}" href="#/c/${k}">${ICON[k]} ${t(k)}</a>`).join('')}</div>
<h1 class="ph">${t(c)} <span class="muted">${x.length}</span></h1><div class="feed box">${x.map((i,n)=>row(i,n+1)).join('')}</div></section>`}
function search(q){q=q||'';const ql=q.toLowerCase(),r=q?DATA.items.filter(i=>(i.title+' '+TT(i)+' '+i.summary+' '+SS(i)+' '+i.tags.join(' ')+' '+t(i.ch)).toLowerCase().includes(ql)):[];
return `<section class="page"><h1 class="ph">${t('search')}</h1><div class="sbox"><span>⌕</span><input id="q" autofocus value="${esc(q)}" placeholder="${t('ph')}"><kbd>/</kbd></div>
<div class="sugg">${['agent','MCP','LLM','免费','跨境','OPC','Show HN','Cloud'].map(s=>`<a href="#/search/${encodeURIComponent(s)}">↳ ${s}</a>`).join('')}</div>
${q?`<p class="muted">${r.length} ${t('results')}</p><div class="feed box">${r.map(i=>row(i)).join('')||`<p class="muted">${t('none')}</p>`}</div>`:''}</section>`}
function item(id){const i=DATA.items.find(x=>x.id===id);if(!i)return home();const rel=DATA.items.filter(x=>x.ch===i.ch&&x.id!==i.id).slice(0,5);
return `<section class="page detail"><a class="muted" href="#/c/${i.ch}">← ${t(i.ch)}</a>
<div class="dh"><span class="fav big"><img alt="" src="https://www.google.com/s2/favicons?sz=128&domain=${host(i.url)}"></span><div><h1>${esc(TT(i))}</h1><p class="muted">${host(i.url)}</p></div></div>
${SS(i)?`<p class="dsum">${esc(SS(i))}</p>`:''}
<dl class="meta"><div><dt>${t('source')}</dt><dd>${esc(i.source)}</dd></div><div><dt>${t('updated')}</dt><dd>${i.date}</dd></div>${i.meta?`<div><dt>★/▲</dt><dd>${esc(i.meta)}</dd></div>`:''}<div><dt>${t('contentLang')}</dt><dd>${i.lang==='zh'?'中文':'English'}</dd></div></dl>
<div class="tagz">${i.tags.map(g=>`<a class="chip" href="#/search/${encodeURIComponent(g)}">${esc(g)}</a>`).join('')}</div>
<div class="ctas"><a class="btn pri" href="${i.url}" target="_blank" rel="noopener">${t('open')} ↗</a>${i.discuss?`<a class="btn" href="${i.discuss}" target="_blank" rel="noopener">${t('discuss')} ↗</a>`:''}</div>
<h2 class="rh">${t('related')}</h2><div class="feed box">${rel.map(x=>row(x)).join('')}</div></section>`}
function about(){return `<section class="page prose"><h1 class="ph">${t('aboutTitle')}</h1><p>${t('aboutBody')}</p><p class="note">${t('social')}</p>
<p class="muted">${Object.values(LANGS).join(' · ')}</p></section>`}
function nav(){$('#navlinks').innerHTML=['ai','repos','products','deals','ideas','about'].map(k=>`<a href="#/${k==='about'?'about':'c/'+k}">${t(k)}</a>`).join('');
$('#footTxt').textContent='OPC Radar · '+t('foot');$('#updated').textContent=t('updated')+' '+(DATA.updated||'').replace('T',' ').slice(0,16)+' UTC · '+DATA.items.length;document.documentElement.lang=L}
function route(){const h=location.hash.slice(1)||'/';if(h==='top')return;const p=h.split('/').filter(Boolean);let html;
if(!p.length)html=home();else if(p[0]==='c')html=channel(p[1]);else if(p[0]==='search')html=search(decodeURIComponent(p[1]||''));else if(p[0]==='item')html=item(p[1]);else if(p[0]==='about')html=about();else html=home();
$('#app').innerHTML=html;scrollTo(0,0);document.querySelectorAll('#navlinks a').forEach(a=>a.classList.toggle('on',location.hash===a.getAttribute('href')));
const q=$('#q');if(q){q.focus();q.setSelectionRange(q.value.length,q.value.length);q.oninput=()=>{clearTimeout(q._t);q._t=setTimeout(()=>{history.replaceState(null,'','#/search/'+encodeURIComponent(q.value));const v=q.value;$('#app').innerHTML=search(v);route2()},250)}}
document.querySelectorAll('.wtabs button').forEach(b=>b.onclick=()=>{document.querySelectorAll('.wtabs button').forEach(x=>x.classList.remove('on'));b.classList.add('on');const w=$('#wbody');w.classList.add('fade');setTimeout(()=>{w.innerHTML=winList(b.dataset.c);w.classList.remove('fade')},160)})}
function route2(){const q=$('#q');if(q){q.focus();q.setSelectionRange(q.value.length,q.value.length);q.oninput=()=>{clearTimeout(q._t);q._t=setTimeout(()=>{history.replaceState(null,'','#/search/'+encodeURIComponent(q.value));$('#app').innerHTML=search(q.value);route2()},250)}}}
const sel=$('#langSel');sel.innerHTML=Object.entries(LANGS).map(([k,v])=>`<option value="${k}">${v}</option>`).join('');sel.value=L;
sel.onchange=()=>{L=sel.value;localStorage.setItem('lang',L);nav();route()};
$('#themeBtn').onclick=()=>{const n=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=n;localStorage.setItem('theme',n);route()};
$('#searchBtn').onclick=()=>location.hash='#/search';
addEventListener('keydown',e=>{if(e.key==='/'&&!/INPUT|SELECT/.test(document.activeElement.tagName)){e.preventDefault();location.hash='#/search'}});
addEventListener('hashchange',route);
addEventListener('pointermove',e=>{const c=e.target.closest&&e.target.closest('.feat,.panel,.toast');if(c){const r=c.getBoundingClientRect();c.style.setProperty('--mx',(e.clientX-r.left)+'px');c.style.setProperty('--my',(e.clientY-r.top)+'px')}});
fetch('data/items.json?'+Date.now()).then(r=>r.json()).then(d=>{DATA=d;nav();route()});
