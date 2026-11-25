'use strict';
const el=id=>document.getElementById(id);
const svgNS='http://www.w3.org/2000/svg';
const query=new URLSearchParams(location.search);
let data, page=1;
function glyphLink(i,k){
 const [w,d]=k.split('-');
 return '../strokes.html?'+new URLSearchParams({glyph:data.glyphs[i][0],w,d});
}
function sheet(i,k,missing,n,slot){
 const [name,chars]=data.glyphs[i];
 const a=document.createElement('a');a.className='card';a.href=glyphLink(i,k);
 const image=document.createElementNS(svgNS,'image');
 const svg=document.createElementNS(svgNS,'svg');
 image.setAttribute('href','plates/'+String(n+1).padStart(2,'0')+'-'+el('layer').value+'.webp');
 image.setAttribute('width',1140);image.setAttribute('height',973);
 svg.setAttribute('viewBox',[(slot%6)*190,Math.floor(slot/6)*139,186,102].join(' '));svg.setAttribute('aria-hidden','true');svg.append(image);
 const tile=document.createElement('span');tile.className='tile';tile.append(svg);
 const title=document.createElement('strong');title.textContent=(chars?chars+' · ':'')+name;
 const axis=document.createElement('small');axis.textContent=k.replace('-',' / ')+'%';
 a.title='Границы без замера: '+missing.map(v=>v+1).join(', ');a.append(tile,title,axis);return a;
}
function matches(i){
 const q=el('query').value.trim().toLowerCase(),[n,c]=data.glyphs[i];
 return !q||c.includes(el('query').value.trim())||n.toLowerCase()===q||q.length>1&&n.toLowerCase().includes(q);
}
function draw(){
 const entries=data.cards.filter(([i])=>matches(i));const pages=Math.max(1,Math.ceil(entries.length/42));page=Math.min(Math.max(1,page),pages);
 el('page').replaceChildren(...Array.from({length:pages},(_,i)=>new Option(String(i+1)+' / '+pages,String(i+1),false,i+1===page)));
 el('prev').disabled=page===1;el('next').disabled=page===pages;
 el('status').textContent=entries.length?entries.length+' карточек · лист '+page+' из '+pages:'Совпадений нет';
 el('plates').replaceChildren(...entries.slice((page-1)*42,page*42).map(r=>sheet(...r)));
}
function signals(){
 const tbody=el('signals');tbody.replaceChildren();let count=0;
 for(const [i,[name,chars]] of data.glyphs.entries()){
  const before=new Map((data.before[name]||[]).map(([k,...v])=>[k,v]));
  const after=new Map((data.after?.[name]||[]).map(([k,...v])=>[k,v]));
  const keys=new Set([...before.keys(),...after.keys()]);
  const columns=v=>v?v[0]+' / '+v[1]+' → '+v[2]+' / '+v[3]:'совпадает с 125%';
  for(const k of keys){
   if(el('which').value==='remaining'&&!after.has(k))continue;
   count++;const row=tbody.insertRow();const link=document.createElement('a');link.href=glyphLink(i,k);link.textContent=(chars?chars+' · ':'')+name;
   row.insertCell().append(link);row.insertCell().textContent=k.replace('-',' / ');row.insertCell().textContent=columns(before.get(k));row.insertCell().textContent=data.after?columns(after.get(k)):'ожидает пересчёта';
  }
 }
 el('total').textContent=count+' сочетаний глифа и начертания';
}
function openSection(){
 const section=document.getElementById(location.hash.slice(1));
 if(section?.tagName==='DETAILS'){section.open=true;section.scrollIntoView();}
}
async function init(){
 const response=await fetch('atlas.json');if(!response.ok)throw Error(String(response.status));data=await response.json();
 el('query').value=query.get('q')||'';page=Number(query.get('page'))||1;
 el('query').oninput=()=>{page=1;draw()};el('layer').onchange=draw;
 el('prev').onclick=()=>{page--;draw()};el('next').onclick=()=>{page++;draw()};el('page').onchange=()=>{page=+el('page').value;draw()};
 el('which').onchange=signals;el('topo').ontoggle=()=>{if(el('topo').open)signals()};draw();
 window.addEventListener('hashchange',openSection);openSection();
}
init().catch(e=>el('status').textContent='Не удалось открыть атлас через локальную лабораторию. '+e.message);
