const CH=["ai","repos","products","news","deals","ideas"];
const ICON={ai:"✦",repos:"⌥",products:"◇",news:"◎",deals:"¥",ideas:"✧"};
let L=detectLang(),DATA={items:[]};const t=k=>I18N[L][k]||I18N.en[k];
const $=s=>document.querySelector(s),esc=s=>String(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const host=u=>{try{return new URL(u).hostname.replace(/^www\./,'')}catch(e){return''}};
const TT=i=>(i.title_i18n&&i.title_i18n[L])||i.title,SS=i=>(i.summary_i18n&&i.summary_i18n[L])||i.summary||'';
function ago(d){if(!d)return'';const m=(Date.now()-Date.parse(d.replace(' ','T')+(d.length>10&&!/Z$/.test(d)?'Z':'')))/6e4;if(!isFinite(m))return'';const f=new Intl.RelativeTimeFormat(L,{numeric:'auto'});return m<60?f.format(-Math.max(1,Math.round(m)),'minute'):m<1440?f.format(-Math.round(m/60),'hour'):f.format(-Math.round(m/1440),'day')}
function langBadge(i){return `<span class="lb">${i.lang==='zh'?'中文':'EN'}</span>`}
function row(i,n){return `<a class="row" href="#/item/${i.id}">${n!=null?`<span class="num">${String(n).padStart(2,'0')}</span>`:''}
<span class="fav"><img loading="lazy" alt="" src="https://www.google.com/s2/favicons?sz=64&domain=${host(i.url)}"></span>
<span class="rt"><b>${esc(TT(i))}</b><small>${esc(SS(i)||host(i.url))}</small></span>
<span class="rm">${i.meta?`<em>${esc(i.meta)}</em>`:''}<time>${ago(i.date)}</time><span class="chip c-${i.ch}">${t(i.ch)}</span><i>→</i></span></a>`}
function tile(i){return `<a class="tile" href="#/item/${i.id}"><div class="stage"><span class="ic">${ICON[i.ch]}</span><b>${esc(TT(i))}</b><p>${esc(SS(i)||host(i.url))}</p></div>
<div class="tf"><span><em class="c-${i.ch}">${t(i.ch)}</em>${i.meta?' · '+esc(i.meta):''}</span><span>${t('open')} →</span></div></a>`}
function picks(){const p=[];CH.forEach(c=>{const x=DATA.items.filter(i=>i.ch===c&&i.source!=='精选'||i.ch===c&&(c==='deals'||c==='ideas'));p.push(...x.slice(0,c==='repos'||c==='ai'?3:1))});p.sort((a,b)=>!!SS(b)-!!SS(a)||0);const f=p.findIndex(i=>i.ch==='repos');if(f>0)p.unshift(p.splice(f,1)[0]);return p.slice(0,10)}
function home(){const pk=picks(),ex=DATA.items.find(i=>i.ch==='repos');
return `<section class="hero">
<div class="hl"><a class="pill rise" href="#/c/ideas"><b>${t('pill1')}</b><span>${t('pill2')}</span>›</a>
<h1 class="rise d1">${t('h1a')}<br><span class="grad">${t('h1b')}</span></h1>
<p class="lede rise d2">${t('lede1')} <span>${t('lede2')}</span></p>
<div class="ctas rise d3"><a class="btn pri" href="#picks">${t('cta1')}</a><a class="btn" href="#/search">${t('cta2')} <kbd>/</kbd></a></div>
<div class="stats rise d3">${CH.map(c=>{const n=DATA.items.filter(i=>i.ch===c).length;return `<a href="#/c/${c}"><b>${n}</b>${t(c)}<u style="--w:${Math.min(100,n*6)}%"></u></a>`}).join('')}</div><div class="term rise d3"><span>$</span> opc-radar --watch ai,repos,deals <em>▍</em></div></div>
<div class="win rise d2"><div class="wbar"><i></i><i></i><i></i><span>opc-radar / live</span><b class="live">● ${ago(DATA.updated)}</b></div>
<div class="wtabs">${['repos','ai','deals'].map((c,k)=>`<button class="${k?'':'on'}" data-c="${c}">${t(c)}</button>`).join('')}</div>
<div class="wbody" id="wbody">${winList('repos')}</div></div></section>
<div class="ticker"><div>${[...DATA.items].filter(i=>i.source!=='精选').sort((a,b)=>b.date.localeCompare(a.date)).slice(0,16).map(i=>`<a href="#/item/${i.id}"><em class="c-${i.ch}">${t(i.ch)}</em>${esc(TT(i))}<time>${ago(i.date)}</time></a>`).join('').repeat(2)}</div></div>
<section class="sec" id="picks"><div class="sh"><h2>${t('picks')}</h2><span class="muted">${t('foot')}</span></div>
<div class="tray bento">${pk.map(tile).join('')}</div></section>
<section class="sec"><div class="sh"><h2>${t('channels')}</h2></div><div class="cells">${CH.map(c=>`<a class="cell" href="#/c/${c}"><span class="ic">${ICON[c]}</span><b>${t(c)}</b><small>${DATA.items.filter(i=>i.ch===c).slice(0,3).map(i=>esc(TT(i))).join(' · ')}</small><i>→</i></a>`).join('')}</div></section>
<section class="sec"><div class="sh"><h2>${t('latest')} <span class="live">● LIVE</span></h2><span class="muted">${t('updated')} ${ago(DATA.updated)}</span></div><div class="list">${[...DATA.items].filter(i=>i.source!=='精选').sort((a,b)=>b.date.localeCompare(a.date)).slice(0,24).map((i,n)=>row(i,n+1)).join('')}</div></section>`}
function winList(c){return DATA.items.filter(i=>i.ch===c).sort((a,b)=>b.date.localeCompare(a.date)).slice(0,6).map(i=>`<a href="#/item/${i.id}"><b>${esc(TT(i))}</b><span>${esc(i.meta||host(i.url))} · ${ago(i.date)}</span></a>`).join('')}
function channel(c){const x=DATA.items.filter(i=>i.ch===c);return `<section class="page"><div class="tabs">${CH.map(k=>`<a class="${k===c?'on':''}" href="#/c/${k}">${ICON[k]} ${t(k)}</a>`).join('')}</div>
<h1 class="ph">${t(c)} <span class="muted">${x.length}</span></h1><div class="list">${x.map((i,n)=>row(i,n+1)).join('')}</div></section>`}
function search(q){q=q||'';const ql=q.toLowerCase(),r=q?DATA.items.filter(i=>(i.title+' '+TT(i)+' '+i.summary+' '+SS(i)+' '+i.tags.join(' ')+' '+t(i.ch)).toLowerCase().includes(ql)):[];
return `<section class="page"><h1 class="ph">${t('search')}</h1><div class="sbox"><span>⌕</span><input id="q" autofocus value="${esc(q)}" placeholder="${t('ph')}"><kbd>/</kbd></div>
<div class="sugg">${['agent','MCP','LLM','免费','跨境','OPC','Show HN','Cloud'].map(s=>`<a href="#/search/${encodeURIComponent(s)}">↳ ${s}</a>`).join('')}</div>
${q?`<p class="muted">${r.length} ${t('results')}</p><div class="list">${r.map(i=>row(i)).join('')||`<p class="muted">${t('none')}</p>`}</div>`:''}</section>`}
function item(id){const i=DATA.items.find(x=>x.id===id);if(!i)return home();const rel=DATA.items.filter(x=>x.ch===i.ch&&x.id!==i.id).slice(0,5);
return `<section class="page detail"><a class="muted" href="#/c/${i.ch}">← ${t(i.ch)}</a>
<div class="dh"><span class="fav big"><img alt="" src="https://www.google.com/s2/favicons?sz=128&domain=${host(i.url)}"></span><div><h1>${esc(TT(i))}</h1><p class="muted">${host(i.url)}</p></div></div>
${SS(i)?`<p class="dsum">${esc(SS(i))}</p>`:''}
<dl class="meta"><div><dt>${t('source')}</dt><dd>${esc(i.source)}</dd></div><div><dt>${t('updated')}</dt><dd>${i.date}</dd></div>${i.meta?`<div><dt>★/▲</dt><dd>${esc(i.meta)}</dd></div>`:''}<div><dt>${t('contentLang')}</dt><dd>${i.lang==='zh'?'中文':'English'}</dd></div></dl>
<div class="tagz">${i.tags.map(g=>`<a class="chip" href="#/search/${encodeURIComponent(g)}">${esc(g)}</a>`).join('')}</div>
<div class="ctas"><a class="btn pri" href="${i.url}" target="_blank" rel="noopener">${t('open')} ↗</a>${i.discuss?`<a class="btn" href="${i.discuss}" target="_blank" rel="noopener">${t('discuss')} ↗</a>`:''}</div>
<h2 class="rh">${t('related')}</h2><div class="list">${rel.map(x=>row(x)).join('')}</div></section>`}
function about(){return `<section class="page prose"><h1 class="ph">${t('aboutTitle')}</h1><p>${t('aboutBody')}</p><p class="note">${t('social')}</p>
<p class="muted">${Object.values(LANGS).join(' · ')}</p></section>`}
function nav(){$('#navlinks').innerHTML=['ai','repos','products','deals','ideas','about'].map(k=>`<a href="#/${k==='about'?'about':'c/'+k}">${t(k)}</a>`).join('');
$('#footTxt').textContent='OPC Radar · '+t('foot');$('#updated').textContent=t('updated')+' '+(DATA.updated||'').replace('T',' ').slice(0,16)+' UTC · '+DATA.items.length;document.documentElement.lang=L}
function route(){const h=location.hash.slice(1)||'/';if(h==='picks')return;const p=h.split('/').filter(Boolean);let html;
if(!p.length)html=home();else if(p[0]==='c')html=channel(p[1]);else if(p[0]==='search')html=search(decodeURIComponent(p[1]||''));else if(p[0]==='item')html=item(p[1]);else if(p[0]==='about')html=about();else html=home();
$('#app').innerHTML=html;scrollTo(0,0);document.querySelectorAll('#navlinks a').forEach(a=>a.classList.toggle('on',location.hash===a.getAttribute('href')));
const q=$('#q');if(q){q.focus();q.setSelectionRange(q.value.length,q.value.length);q.oninput=()=>{clearTimeout(q._t);q._t=setTimeout(()=>{history.replaceState(null,'','#/search/'+encodeURIComponent(q.value));const v=q.value;$('#app').innerHTML=search(v);route2()},250)}}
document.querySelectorAll('.wtabs button').forEach(b=>b.onclick=()=>{document.querySelectorAll('.wtabs button').forEach(x=>x.classList.remove('on'));b.classList.add('on');const w=$('#wbody');w.classList.add('fade');setTimeout(()=>{w.innerHTML=winList(b.dataset.c);w.classList.remove('fade')},160)})}
function route2(){const q=$('#q');if(q){q.focus();q.setSelectionRange(q.value.length,q.value.length);q.oninput=()=>{clearTimeout(q._t);q._t=setTimeout(()=>{history.replaceState(null,'','#/search/'+encodeURIComponent(q.value));$('#app').innerHTML=search(q.value);route2()},250)}}}
const sel=$('#langSel');sel.innerHTML=Object.entries(LANGS).map(([k,v])=>`<option value="${k}">${v}</option>`).join('');sel.value=L;
sel.onchange=()=>{L=sel.value;localStorage.setItem('lang',L);nav();route()};
$('#themeBtn').onclick=()=>{const n=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=n;localStorage.setItem('theme',n)};
$('#searchBtn').onclick=()=>location.hash='#/search';
addEventListener('keydown',e=>{if(e.key==='/'&&!/INPUT|SELECT/.test(document.activeElement.tagName)){e.preventDefault();location.hash='#/search'}});
addEventListener('hashchange',route);
addEventListener('pointermove',e=>{const c=e.target.closest&&e.target.closest('.tile,.cell,.row,.win');if(c){const r=c.getBoundingClientRect();c.style.setProperty('--mx',(e.clientX-r.left)+'px');c.style.setProperty('--my',(e.clientY-r.top)+'px')}});
fetch('data/items.json?'+Date.now()).then(r=>r.json()).then(d=>{DATA=d;nav();route()});
