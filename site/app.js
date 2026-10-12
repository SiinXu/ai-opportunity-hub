const CH=["ai","repos","products","news","deals","ideas"];
const ICON={ai:"✦",repos:"⌥",products:"◇",news:"◎",deals:"¥",ideas:"✧"};
let L=detectLang(),DATA={items:[]};const t=k=>I18N[L][k]||I18N.en[k];
const $=s=>document.querySelector(s),esc=s=>String(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const host=u=>{try{return new URL(u).hostname.replace(/^www\./,'')}catch(e){return''}};
const TT=i=>(i.title_i18n&&i.title_i18n[L])||i.title,SS=i=>(i.summary_i18n&&i.summary_i18n[L])||i.summary||'';
function ago(d){if(!d)return'';const m=(Date.now()-Date.parse(d.replace(' ','T')+(d.length>10&&!/Z$/.test(d)?'Z':'')))/6e4;if(!isFinite(m))return'';const f=new Intl.RelativeTimeFormat(L,{numeric:'auto'});return m<60?f.format(-Math.max(1,Math.round(m)),'minute'):m<1440?f.format(-Math.round(m/60),'hour'):f.format(-Math.round(m/1440),'day')}
const GR_L={ai:"#e0e7ff",repos:"#d1fae5",products:"#ffedd5",news:"#e0f2fe",deals:"#ffe4e6",ideas:"#fef3c7"};
const GR_D={ai:"#1e1b4b",repos:"#064e3b",products:"#7c2d12",news:"#0c4a6e",deals:"#881337",ideas:"#713f12"};
const GR=()=>document.documentElement.dataset.theme==="dark"?GR_D:GR_L;

const fav=(i,s=64)=>`https://www.google.com/s2/favicons?sz=${s}&domain=${host(i.url)}`;
function thumb(i,cls='th',feat=false){
  const g=GR()[i.ch];
  const m=String(i.url||'').match(/github\.com\/([^/]+)\/([^/#?]+)/);
  const gh=(i.ch==='repos'&&m)?`${m[1]}/${m[2]}`:'';
  const owner=m?m[1]:'';
  /* Featured/headline: cohesive channel tile + owner/favicon — never full white GH social card */
  if(feat||!gh){
    const icon=owner?`https://github.com/${owner}.png?size=128`:fav(i,128);
    return `<div class="${cls} th-fb" style="--g:${g}"><span class="thf"><img loading="lazy" alt="" src="${icon}"></span><span class="thw">${esc(gh||host(i.url))}</span></div>`
  }
  /* Feed thumbs: crop GH OG (top ~55%, hide language bar + letterbox) + fade into card */
  return `<div class="${cls} th-gh" style="--g:${g}"><img loading="lazy" alt="" src="https://opengraph.githubassets.com/1/${gh}" onerror="const p=this.parentElement;p.classList.remove('th-gh');p.classList.add('th-fb');p.innerHTML='<span class=\'thf\'><img loading=\'lazy\' alt=\'\' src=\'${fav(i,128)}\'></span><span class=\'thw\'>${esc(host(i.url))}</span>'"></div>`
}
const chip=i=>`<span class="chip c-${i.ch}">${ICON[i.ch]} ${t(i.ch)}</span>`;
function row(i,n){return `<a class="row" href="#/item/${i.id}">${thumb(i,'rth')}
<span class="rt"><span class="rk">${chip(i)}<time>${ago(i.date)}</time>${i.meta?`<em>${esc(i.meta)}</em>`:''}</span><b>${esc(TT(i))}</b><small>${esc(SS(i)||host(i.url))}</small></span><i class="go">↗</i></a>`}
function card(i,cls=''){/* all cards use cohesive tile; feed rows may crop GH OG */return `<a class="card ${cls}" href="#/item/${i.id}">${thumb(i,'th',true)}<div class="cb"><span class="rk">${chip(i)}<time>${ago(i.date)}</time></span><b>${esc(TT(i))}</b><p>${esc(SS(i)||host(i.url))}</p><span class="cf"><img alt="" src="${fav(i)}">${esc(host(i.url))}${i.meta?`<em>${esc(i.meta)}</em>`:''}</span></div></a>`}
const tile=card;
function bykind(c,n){return DATA.items.filter(i=>i.ch===c).sort((a,b)=>(!!SS(b)-!!SS(a))||b.date.localeCompare(a.date)).slice(0,n)}
function picks(){const p=[],u=new Set();[['repos',3],['ai',2],['products',2],['ideas',2],['deals',2],['news',1]].forEach(([c,n])=>bykind(c,n+3).filter(i=>!u.has(i.id)).slice(3,3+n).forEach(i=>{u.add(i.id);p.push(i)}));return p}
function home(){const heads=[bykind('repos',1)[0],bykind('ai',1)[0],bykind('products',1)[0]].filter(Boolean),pk=picks(),mx=Math.max(...CH.map(k=>DATA.items.filter(i=>i.ch===k).length)),hid=new Set([...heads,...pk].map(i=>i.id));
const latest=[...DATA.items].filter(i=>!hid.has(i.id)).sort((a,b)=>b.date.localeCompare(a.date)).slice(0,36);
return `<section class="hero"><div class="glow"></div>
<a class="pill rise" href="#/c/ideas"><span class="dot"></span><b>${t('pill1')}</b><span>${t('pill2')}</span>›</a>
<h1 class="rise d1">${t('h1a')} <span class="grad">${t('h1b')}</span></h1>
<p class="lede rise d2">${t('lede1')} ${t('lede2')}</p>
<div class="ctas rise d2"><a class="btn pri" href="#picks"><span>${t('cta1')} →</span></a><a class="btn" href="#/search">⌕ ${t('cta2')} <kbd>/</kbd></a><span class="livep"><i></i>${DATA.items.length} · ${t('updated')} ${ago(DATA.updated)}</span></div>
<div class="heads rise d3">${heads.map((i,k)=>card(i,'head')).join('')}</div></section>
<section class="sec"><div class="mosaic">${CH.map(c=>{const x=DATA.items.filter(i=>i.ch===c);return `<a class="mo" href="#/c/${c}" style="--g:${GR()[c]}"><span class="mi">${ICON[c]}</span><b class="big">${x.length}</b><span class="mt">${t(c)}</span><span class="favs">${x.slice(0,5).map(i=>`<img alt="" src="${fav(i)}">`).join('')}</span><u style="--w:${Math.round(x.length/mx*100)}%"></u></a>`}).join('')}</div></section>
<section class="sec" id="picks"><div class="sh"><h2>${t('picks')}</h2><span class="muted">${t('foot')}</span></div>
<div class="bento">${pk.map((i,k)=>card(i,k===0?"xl":k===5||k===10?"wide":"")).join('')}</div></section>
<section class="sec"><div class="sh"><h2>${t('latest')} <span class="livep"><i></i>LIVE</span></h2><a class="muted" href="#/search">${t('updated')} ${ago(DATA.updated)} →</a></div>
<div class="feed">${latest.map(i=>row(i)).join('')}</div></section>
<section class="sec"><div class="sh"><h2>${t('channels')}</h2></div><div class="cols">${CH.map(c=>`<div class="colx"><a class="ch" href="#/c/${c}" style="--g:${GR()[c]}">${ICON[c]} ${t(c)} <i>→</i></a>${winList(c)}</div>`).join('')}</div></section>`}
function winList(c){return DATA.items.filter(i=>i.ch===c).sort((a,b)=>b.date.localeCompare(a.date)).slice(0,6).map(i=>`<a class="mini" href="#/item/${i.id}"><img alt="" loading="lazy" src="${fav(i)}"><span><b>${esc(TT(i))}</b><small>${esc(i.meta||host(i.url))} · ${ago(i.date)}</small></span></a>`).join('')}
function channel(c){const x=DATA.items.filter(i=>i.ch===c);return `<section class="page"><div class="tabs">${CH.map(k=>`<a class="${k===c?'on':''}" href="#/c/${k}">${ICON[k]} ${t(k)}</a>`).join('')}</div>
<h1 class="ph">${t(c)} <span class="muted">${x.length}</span></h1><div class="feed">${x.map((i,n)=>row(i,n+1)).join('')}</div></section>`}
function search(q){q=q||'';const ql=q.toLowerCase(),r=q?DATA.items.filter(i=>(i.title+' '+TT(i)+' '+i.summary+' '+SS(i)+' '+i.tags.join(' ')+' '+t(i.ch)).toLowerCase().includes(ql)):[];
return `<section class="page"><h1 class="ph">${t('search')}</h1><div class="sbox"><span>⌕</span><input id="q" autofocus value="${esc(q)}" placeholder="${t('ph')}"><kbd>/</kbd></div>
<div class="sugg">${['agent','MCP','LLM','免费','跨境','OPC','Show HN','Cloud'].map(s=>`<a href="#/search/${encodeURIComponent(s)}">↳ ${s}</a>`).join('')}</div>
${q?`<p class="muted">${r.length} ${t('results')}</p><div class="feed">${r.map(i=>row(i)).join('')||`<p class="muted">${t('none')}</p>`}</div>`:''}</section>`}
function item(id){const i=DATA.items.find(x=>x.id===id);if(!i)return home();const rel=DATA.items.filter(x=>x.ch===i.ch&&x.id!==i.id).slice(0,5);
return `<section class="page detail"><a class="muted" href="#/c/${i.ch}">← ${t(i.ch)}</a>
<div class="dh"><span class="fav big"><img alt="" src="https://www.google.com/s2/favicons?sz=128&domain=${host(i.url)}"></span><div><h1>${esc(TT(i))}</h1><p class="muted">${host(i.url)}</p></div></div>
${SS(i)?`<p class="dsum">${esc(SS(i))}</p>`:''}
<dl class="meta"><div><dt>${t('source')}</dt><dd>${esc(i.source)}</dd></div><div><dt>${t('updated')}</dt><dd>${i.date}</dd></div>${i.meta?`<div><dt>★/▲</dt><dd>${esc(i.meta)}</dd></div>`:''}<div><dt>${t('contentLang')}</dt><dd>${i.lang==='zh'?'中文':'English'}</dd></div></dl>
<div class="tagz">${i.tags.map(g=>`<a class="chip" href="#/search/${encodeURIComponent(g)}">${esc(g)}</a>`).join('')}</div>
<div class="ctas"><a class="btn pri" href="${i.url}" target="_blank" rel="noopener">${t('open')} ↗</a>${i.discuss?`<a class="btn" href="${i.discuss}" target="_blank" rel="noopener">${t('discuss')} ↗</a>`:''}</div>
<h2 class="rh">${t('related')}</h2><div class="feed">${rel.map(x=>row(x)).join('')}</div></section>`}
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
$('#themeBtn').onclick=()=>{const n=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=n;localStorage.setItem('theme',n);route()};
$('#searchBtn').onclick=()=>location.hash='#/search';
addEventListener('keydown',e=>{if(e.key==='/'&&!/INPUT|SELECT/.test(document.activeElement.tagName)){e.preventDefault();location.hash='#/search'}});
addEventListener('hashchange',route);
addEventListener('pointermove',e=>{const c=e.target.closest&&e.target.closest('.card,.mo,.row');if(c){const r=c.getBoundingClientRect();c.style.setProperty('--mx',(e.clientX-r.left)+'px');c.style.setProperty('--my',(e.clientY-r.top)+'px')}});
fetch('data/items.json?'+Date.now()).then(r=>r.json()).then(d=>{DATA=d;nav();route()});
