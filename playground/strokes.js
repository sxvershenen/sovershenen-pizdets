'use strict';
const el=id=>document.getElementById(id);
const fmt=x=>x.toLocaleString('ru',{maximumFractionDigits:1});
const signed=x=>(x>0?'+':'')+fmt(x);
const direction=['Стойка','Горизонталь','Диагональ'];
const cache=new Map();
let index, data, baseline, selected, originalPaths, requestNumber=0;
const params=new URLSearchParams(location.search);

async function load(key){
  if(cache.has(key))return cache.get(key);
  const response=await fetch('stroke-data/'+key+'.json.gz', {cache:'no-cache'});
  if(!response.ok)throw new Error('HTTP '+response.status);
  const result=await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).json();
  if(cache.size>=3)cache.delete(cache.keys().next().value);
  cache.set(key,result);
  return result;
}
function outside(v,k){
  const [low,high]=data.bands[k];
  const tol=Math.max(2,.075*(low+high)/2)*(k<3?1:2);
  return v<low-tol?v-low+tol:v>high+tol?v-high-tol:0;
}
function badge(v){return v<0?'thin':v>0?'thick':'';}
function dominant(row){return -row[0]>row[1]?row[0]:row[1];}
function addOptions(id,values,start){
  for(const v of values)el(id).add(new Option(String(v),String(v),false,String(v)===String(start)));
}
function chooseRay(p,tr){
  for(const t of el('pairs').rows)t.classList.toggle('active',t===tr);
  el('ray').setAttribute('x1',p[7]);el('ray').setAttribute('y1',p[8]);
  el('ray').setAttribute('x2',p[9]);el('ray').setAttribute('y2',p[10]);
  el('start').setAttribute('cx',p[7]);el('start').setAttribute('cy',p[8]);
  el('selection').textContent='Граница '+(p[0]+1)+' → '+(p[1]+1)+'  ·  '+direction[p[2]%3]+'  ·  '+fmt(p[4])+'–'+fmt(p[5])+' ед.';
}
function showGlyph(i){
  selected=i;
  for(const b of el('list').children)b.setAttribute('aria-current',String(+b.dataset.i===i));
  const [name,chars]=index.glyphs[i];
  const [path,edges,pairs,missing]=data.rows[i];
  el('title').textContent=(chars||'Глиф без Unicode')+'  ·  '+name;
  el('outline').setAttribute('d',path);
  el('original-path').setAttribute('d',originalPaths?.[name]||'');
  const b=el('outline').getBBox(),pad=55;
  el('plot').setAttribute('viewBox',[b.x-pad,-b.y-b.height-pad,b.width+2*pad,b.height+2*pad].join(' '));
  el('missing').textContent=edges?(missing.length?'Границы без принятого замера ('+missing.length+' из '+edges+'): '+missing.map(x=>x+1).join(', '):'Замеры получены на всех '+edges+' границах.'):'Глиф без контура.';
  el('peak').textContent='';
  const stat=index.peaks[i];
  if(stat[0]){
    const button=document.createElement('button');
    const [w,d]=stat[1].split('-');
    button.textContent='Максимум за сетку · '+signed(stat[0])+' за допуском · вес '+w+' / ширина '+d;
    button.onclick=()=>{el('weight').value=w;el('width').value=d;changeLocation();};
    el('peak').append(button);
  }
  const ordered=[...pairs].sort((a,b)=>(a[2]>=3)-(b[2]>=3)
    ||Math.abs(outside(b[3],b[2]))-Math.abs(outside(a[3],a[2]))||a[0]-b[0]);
  const nativePairs=new Map(baseline.rows[i][2].map(p=>[p.slice(0,3).join('/'),p[3]]));
  const body=el('pairs');body.replaceChildren();
  for(const p of ordered){
    const tr=body.insertRow();tr.tabIndex=0;
    tr.onclick=()=>chooseRay(p,tr);tr.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();chooseRay(p,tr);}};
    const k=p[2],band=data.bands[k];
    const at125=nativePairs.get(p.slice(0,3).join('/'));
    const values=[(p[0]+1)+' → '+(p[1]+1),direction[k%3]+(k<3?'':k<6?' · дуга':' · короткий'),fmt(p[4]),fmt(p[3]),fmt(p[5]),band.map(fmt).join('–'),at125==null?'—':fmt(at125),at125==null?'—':signed(Math.round((p[3]-at125)*10)/10),p[6]];
    for(let col=0;col<values.length;col++){
      const td=tr.insertCell();td.textContent=values[col];
      if(col>=2&&col<=4)td.className=badge(outside([p[4],p[3],p[5]][col-2],k));
    }
  }
  el('ray').style.display=el('start').style.display=ordered.length?'':'none';
  if(ordered.length)chooseRay(ordered[0],body.rows[0]);else el('selection').textContent='Нет подходящей пары границ.';
}
function inventory(){
  const query=el('query').value.trim(),filter=el('filter').value,order=el('sort').value;
  const hits=[];
  index.glyphs.forEach(([n,c],i)=>{
    const r=data.summary[i],score=dominant(r);
    if(query&&!(c.includes(query)||n===query||query.length>1&&n.toLowerCase().includes(query.toLowerCase())))return;
    if(filter==='letters'&&!/[\p{Script=Latin}\p{Script=Cyrillic}]/u.test(c)&&!query)return;
    if(filter==='main'&&!score||filter==='tips'&&!r[7]||filter==='weak'&&!r[2]||filter==='missing'&&!r[3])return;
    hits.push(i);
  });
  hits.sort((a,b)=>order==='name'?index.glyphs[a][0].localeCompare(index.glyphs[b][0]):
    Math.abs(order==='peak'?index.peaks[b][0]:dominant(data.summary[b]))-Math.abs(order==='peak'?index.peaks[a][0]:dominant(data.summary[a]))||a-b);
  const fragment=document.createDocumentFragment();
  for(const i of hits){
    const [n,c]=index.glyphs[i],v=dominant(data.summary[i]);
    const b=document.createElement('button');b.type='button';b.className='entry';b.dataset.i=i;
    b.append((c||'·')+'  '+n);const span=document.createElement('span');span.className=badge(v);span.textContent=v?signed(v):'—';b.append(span);b.onclick=()=>showGlyph(i);fragment.append(b);
  }
  el('list').replaceChildren(fragment);
  el('status').textContent=hits.length+' из '+index.glyphs.length+' глифов · '+index.weights.length+' весов × '+index.widths.length+' ширин';
  if(hits.length){showGlyph(hits.includes(selected)?selected:hits[0]);}
  else {el('title').textContent='Совпадений нет';el('pairs').replaceChildren();el('outline').setAttribute('d','');el('original-path').setAttribute('d','');el('ray').style.display=el('start').style.display='none';for(const id of ['selection','peak','missing'])el(id).textContent='';}
}
async function changeLocation(){
  const ticket=++requestNumber;
  el('status').textContent='Загрузка начертания…';
  try{
    const key=el('weight').value+'-'+el('width').value;
    const native=el('weight').value+'-125';
    const result=await load(key);
    const at125=key===native?result:await load(native);
    const originalKey='original/'+el('weight').value+'-'+Math.min(125,+el('width').value);
    const original=el('original-toggle').checked?await load(originalKey):null;
    if(ticket!==requestNumber)return;
    originalPaths=original;
    data=result;baseline=at125;
    el('refs').textContent='QEUTPHF  ·  стойки '+data.bands[0].map(fmt).join('–')+'  ·  горизонтали '+data.bands[1].map(fmt).join('–')+' ед.';
    inventory();
  }catch(e){if(ticket===requestNumber)el('status').textContent='Не удалось загрузить измерения. '+e.message;}
}
async function start(){
  index=await load('index');
  index.peaks=index.glyphs.map((_,i)=>{
    let peak=0,key='';
    for(const [location,rows] of Object.entries(index.summary)){
      const val=dominant(rows[i]);if(Math.abs(val)>Math.abs(peak)){peak=val;key=location;}
    }
    return [peak,key];
  });
  selected=index.glyphs.findIndex(([n,c])=>n===params.get('glyph')||c==='А'&&!params.has('glyph'));
  if(params.has('glyph'))el('filter').value='all';
  addOptions('weight',index.weights,params.get('w')||650);addOptions('width',index.widths,params.get('d')||175);
  try{
    const ref=JSON.parse(localStorage.getItem('sp-type-lab-1'))?.refs?.original;
    if(ref){el('original-toggle').checked=ref[0];el('original-opacity').value=ref[1];}
  }catch{}
  const opacity=()=>el('original-path').setAttribute('opacity',el('original-opacity').value/100);
  opacity();el('original-opacity').oninput=opacity;
  await changeLocation();
  for(const id of ['weight','width','original-toggle'])el(id).oninput=changeLocation;
  for(const id of ['query','filter','sort'])el(id).oninput=inventory;
}
start().catch(e=>el('status').textContent='Откройте аудит через локальную лабораторию. '+e.message);
