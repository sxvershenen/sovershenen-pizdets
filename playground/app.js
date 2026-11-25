'use strict';
const $ = id => document.getElementById(id);
const svgNS = 'http://www.w3.org/2000/svg';
const STORE = 'sp-type-lab-1';
const legacyTrackingPoints = [[8,65], [14,25], [24,5], [48,0]];
const previousTrackingPoints = [[8,540], [12,420], [24,240], [48,0]];
const defaults = {
  trackingRevision: 4, uRevision: 1,
  sample: 'Широкий жест', size: 80, weight: 650, width: 107, version: 'lab',
  reading: 'station', uppercase: false,
  shelfDefault: 48, ZEXT: 48, ZANG: 50, ZWGT: 50, UANG: 0, UWGT: 80, guides: true, capMatch: false, flexWidth: 100,
  points: [[8,54], [12,38], [24,20], [48,0]],
  refs: {original:[false,35], micro: [false,38], roboto: [false,30], flex: [false,24]}
};
let state = structuredClone(defaults);
try {
  const saved = JSON.parse(localStorage.getItem(STORE));
  if (saved && validPoints(saved.points)) {
    state = {...state,...saved,refs:{...state.refs,...saved.refs}};
    const revision = saved.trackingRevision ?? 0;
    if (revision < defaults.trackingRevision) {
      const curve = JSON.stringify(saved.points);
      if ((revision === 3 && curve === JSON.stringify([[8,54], [12,42], [24,24], [48,0]])) ||
          (revision < 3 && curve === JSON.stringify(previousTrackingPoints)) ||
          (!revision && curve === JSON.stringify(legacyTrackingPoints))) {
        state.points = structuredClone(defaults.points);
      }
      state.trackingRevision = defaults.trackingRevision;
    }
    if (saved.shelfDefault === undefined && saved.ZEXT === 50) state.ZEXT = defaults.ZEXT;
    const updateU = (saved.uRevision ?? 0) < defaults.uRevision;
    if (updateU) {
      state.UANG = defaults.UANG;
      state.UWGT = defaults.UWGT;
      state.uRevision = defaults.uRevision;
    }
    if (revision < defaults.trackingRevision || updateU) save();
  }
} catch {}
function save() { try { localStorage.setItem(STORE, JSON.stringify(state)); } catch {} }
$('reset').onclick = () => {
  state = structuredClone(defaults);
  save();
  location.reload();
};
function validPoints(points) {
  return Array.isArray(points) && points.length>=2 && points.length<=16 &&
    points.every(p=>Array.isArray(p)&&p.length===2&&Number.isInteger(p[0])&&p[0]>=6&&p[0]<=200&&Number.isFinite(p[1])&&p[1]>=-80&&p[1]<=1000) &&
    new Set(points.map(p=>p[0])).size===points.length;
}
const refInfo = {
  original:{name:"Оригинал 3.17",family:"Original",cap:0.667},
  micro: {name:'MicroTechnic Extended Bold',family:'GhostMicro',cap:1021/1284},
  roboto:{name:'Roboto',family:'GhostRoboto',cap:1456/2048},
  flex:{name:'Roboto Flex',family:'GhostFlex',cap:1456/2048}
};
const presets = {'Образец':'Широкий жест','Цифры и буквы':'Н4Н · А47 · Рейс Ю-204 · 0123456789 · ЛУНЬ · УГОЛЬ','Проверка пар':'ВСЛУХ · ТЯНЕТ · ЗАРЯ · ЮЖНЫЙ · люблю · AWAY · EXTRA · blackbird', 'Zz и Э · 175%':'ZEST · zigzag · SIZE · ЭТОТ · ЗАКАЗ · ЭЗЭ · ЗЭЗ', 'Ритм слов':'ножкой · поближе · зевок · zigzag · ЗАКАЗ · ЗВЯКНУЛО · ЮЖ · WAVE · моя','Диагонали':'VЖК · vжк · VIVID WAVE · ЖУК КЛИН · WRYAZXKVNM · ЙУКАЯМ · wryazxkvnmйукаям','Стыки':'rnm gudq Яя MМм Ww Жж Кк', 'Эталоны':'QEUTPHF НКЖ УПТ ЦМ', 'Полки Х':'Хх Xx ЖК', 'Проверка толщин':'QEUTPHF АУRЯ Юю yzv ЧЪЛд5', 'Ножки':'PBR ЯR Vv Ww', 'Перед Д':'НД ОД ТД АД ДД','к, у, Д':'книги у окна · утки у пруда · Дудка','Круглые и ку':'aeogc соаеё · зевнул заебато золото · строчку с буквами','Пары Q':'OQO QO QA QU QV Qq','Жж / Кк':'ЖК Жж Кк жк', 'ж/ч и з/в':'жук и чиж · звук и вызов · жакет и чек · kick и кик'};
const passages = new Map([
  ['print', {title:'Русский · В типографии', lang:'ru', text:'Чек за тираж зажало в принтере. Женя открыла крышку, сняла валик и вытащила узкую полоску бумаги. «А где весь заказ?» — спросил Витя. Из соседней комнаты донёсся треск: второй принтер выплюнул двести афиш с единственным словом «ЖДИТЕ».'}],
  ['lake', {title:'Русский · Лёд на озере', lang:'ru', text:'К вечеру озеро замёрзло. Из камыша торчала жёлтая вешка, а чуть дальше виднелся чей-то башмак. Зоя вышла на крыльцо и прислушалась. Подо льдом что-то звякнуло. Так звенит ложечка, если задеть край пустого стакана.'}],
  ['menu', {title:'Русский · У стойки', lang:'ru', text:'Щи — 240 ₽, ёжики с гречкой — 380 ₽. Вера взяла кофе и кусок пирога. За соседним столом двое шёпотом спорили, чей рюкзак тяжелее. Их пёс лежал под скамьёй и следил за вилкой, на которой ещё держался последний кусок.'}],
  ['dispatch', {title:'Русский · Диспетчерская', lang:'ru', text:'Рейс ЮЖ-204, выход № 7. До посадки 18 минут. «Ключи, рация, журнал», — вслух пересчитала дежурная. В графе «Груз» значились ящики, лыжи и один чёрный рояль. Как его подняли по узкой лестнице, в журнале не уточнялось.'}],
  ['marsh', {title:'Русский · На болоте', lang:'ru', text:'В зарослях зажужжал жук. Чиж прыгнул на ветку чуть выше и склонил голову набок. Я ждал всплеска у брода, где вчера заметил щуку. Поплавок шевельнулся, лёг на воду и медленно поплыл против течения.'}],
  ['record', {title:'English · Record shop', lang:'en', text:'Jack kept the jazz records in a crate by the window. When a customer asked for the quietest one, he picked a blank sleeve. Inside was a field recording of rain on a zinc roof. At the very end, someone sneezed.'}],
  ['ferry', {title:'English · Last ferry', lang:'en', text:'At 06:45 the ferry left Pier 8 with two bicycles, six boxes of wax and a white van. Halfway across, the fog lifted. Beyond the quay we could see a fox walking down the yellow line as if it owned the road.'}],
  ['labels', {title:'Русский / English · Монтаж', lang:'ru', text:'На ящике стояло «ВЕРХ / THIS WAY UP». Саша повернул его надписью к двери. На обороте обнаружилась другая стрелка и записка: «Jack, проверь вход XLR-2». До открытия зала оставалось 15 минут.'}],
  ['wide', {title:'Русский · Этот отрывок', lang:'ru', text:'Этот отрывок я прочёл в июне. Ирина прочла его ещё раз и тихо закрыла книгу. За окном остывал город. Внизу кто-то вывел мелом три слова: «Ищи свой ритм».'}],
  ['station', {title:'Русский · На станции', lang:'ru', text:'На конечной станции ещё лежал снег. Ирина шла вдоль путей и считала шпалы, пока за оградой не показалась теплица. У двери стоял ящик с рассадой. На крышке мелом вывели «Щавель», а внутри уже цвели жёлтые тюльпаны.'}],
  ['radio', {title:'Русский · Ночной эфир', lang:'ru', text:'В три часа ночи в редакцию позвонил мужчина и попросил поставить вальс. Юля отыскала пластинку. Диктор прочёл первую строчку с конверта, в студии щёлкнула игла. В этот миг за стеной кто-то придвинул стул поближе к приёмнику.'}],
  ['key', {title:'English · The brass key', lang:'en', text:'Zoe found a brass key in the pocket of her winter coat. On Queen Street she passed a row of empty shops. Every door had a new lock except the little cinema on the corner. She tried the key. Somewhere above her, a projector began to buzz.'}]
]);
const passageChoice = $('reading-choice');
for (const [key, passage] of passages) passageChoice.add(new Option(passage.title, key));
function displayText(text, lang = 'ru') {
  return state.uppercase ? text.toLocaleUpperCase(lang) : text;
}
function showPassage(key) {
  const passage = passages.get(key);
  passageChoice.value = key;
  $('reading-text').lang = passage.lang;
  $('reading-text').textContent = displayText(passage.text, passage.lang);
  $('reading-page').scrollTop = 0;
}
showPassage(passages.has(state.reading) ? state.reading : defaults.reading);
passageChoice.onchange = () => {
  state.reading = passageChoice.value;
  showPassage(state.reading);
  save();render();
};
$('uppercase').checked = state.uppercase;
$('uppercase').onchange = event => {
  state.uppercase = event.target.checked;
  showPassage(passageChoice.value);
  save();
  render();
};
const status = (message, error=false) => {
  $('status').textContent = message; $('status').dataset.error = error;
};
function svg(tag, attrs, value) {
  const el = document.createElementNS(svgNS,tag);
  Object.entries(attrs).forEach(([k,v])=>el.setAttribute(k,v));
  if (value!==undefined) el.textContent=value;
  return el;
}
function makeButton(label, fn) {
  const b=document.createElement('button'); b.type='button'; b.textContent=label;
  b.addEventListener('click',fn); return b;
}
function control(parent,{key,label,min,max,step=1,unit='',get=()=>state[key],update=v=>state[key]=v}) {
  const id='control-'+key;
  const el=document.createElement('div'); el.className='control';
  el.innerHTML='<div class="controlhead"><label></label><span class="numwrap"><input class="number" type="number"><span></span></span></div><input type="range"><div class="rangeends"><span></span><span></span></div>';
  const [number,range]=el.querySelectorAll('input'); const caption=el.querySelector('label');
  caption.textContent=label; caption.htmlFor=id; number.id=id;
  range.setAttribute('aria-label',label+' — ползунок');
  el.querySelector('.numwrap span').textContent=unit;
  const ends=el.querySelector('.rangeends');
  ends.firstChild.textContent=min; ends.lastChild.textContent=max;
  [number,range].forEach(input=>{input.min=min;input.max=max;input.step=step;input.value=get();});
  function change(v){update(v);range.value=number.value=v;save();render();}
  range.oninput=()=>change(+range.value);
  number.oninput=()=>{if(number.value!=='' && number.validity.valid)change(+number.value);};
  number.onchange=()=>{if(!number.value || !number.validity.valid)number.value=get();};
  parent.append(el);
  return {sync(){range.value=number.value=get();},limit(m){number.max=range.max=m;ends.lastChild.textContent=m;range.value=number.value=get();}};
}
control($('axesControls'),{key:'size',label:'Размер',min:6,max:200,unit:'px'});
control($('axesControls'),{key:'weight',label:'Насыщенность',min:100,max:900,unit:'wght'});
const widthControl=control($('axesControls'),{key:'width',label:'Ширина',min:100,max:175,step:.5,unit:'%'});
const zheNames={ZEXT:'Вылет полок',ZANG:'Наклон ножек',ZWGT:'Толщина ножек'};
const uNames={UANG:'Наклон ветвей',UWGT:'Толщина штрихов'};
const shapeNames={...zheNames,...uNames};
for(const [key,label] of Object.entries(zheNames))control($('shapeControls'),{key,label,min:0,max:100});
const uControls=Object.entries(uNames).map(([key,label])=>control($('uControls'),{key,label,min:0,max:100}));
const uVariants=[['Низкий стык',0],['Средний',50],['Высокий стык',100]];
const uButtons=uVariants.map(([label,angle])=>{
  const button=makeButton(label,()=>{
    state.UANG=angle;
    uControls.forEach(c=>c.sync());save();render();
  });
  const letter=document.createElement('span');letter.textContent='У';letter.setAttribute('aria-hidden','true');
  button.prepend(letter);$('uVariants').append(button);
  return {button,letter,angle};
});
function showWideSample(value){
  if(state.version==='original')changeVersion('lab');
  state.width=state.labWidth=175;widthControl.sync();
  setSample(value);
}
$('showU').onclick=()=>showWideSample('УГОЛЬ · ЛУНА · УЮТ · УЛЕЙ · ПУЛЬС');
function tab(id){
  document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.tab===id));
  for(const name of ['axes','refs','zhe','uform'])$(name).hidden=name!==id;
}
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>tab(b.dataset.tab));
state.labWidth = Math.max(100,Math.min(175,state.labWidth ?? state.width));
function changeVersion(next){
  if(state.version==='lab')state.labWidth=state.width;
  state.version=next;
  state.width=next==='original'?Math.min(125,state.width):state.labWidth;
  $('version').value=next;widthControl.limit(next==='original'?125:175);
  save();render();
}
$('version').value=state.version;
$('version').onchange=e=>changeVersion(e.target.value);
document.addEventListener('keydown',event=>{
  if(event.code!=='KeyV' || event.repeat || event.isComposing || event.defaultPrevented ||
     event.metaKey || event.ctrlKey || event.altKey || event.shiftKey)return;
  const target=event.target;
  if(target instanceof Element && (target.isContentEditable ||
     target.closest('textarea, select, input:not([type="range"]):not([type="checkbox"]):not([type="button"])')))return;
  event.preventDefault();
  changeVersion(state.version==='lab'?'original':'lab');
});
widthControl.limit(state.version==='original'?125:175);
function setSample(value){state.sample=value;$('sample').value=value;save();render();}
$('sample').value=state.sample;$('sample').oninput=e=>setSample(e.target.value);
Object.entries(presets).forEach(([label,value])=>{
  const select=label==='Zz и Э · 175%'?showWideSample:setSample;
  $('presets').append(makeButton(label,()=>select(value)));
});
$('showZhe').onclick=()=>{if(state.version==='original') changeVersion('lab');setSample(presets['Жж / Кк']);};
for(const key of ['guides','capMatch']){
  $(key).checked=state[key];$(key).onchange=e=>{state[key]=e.target.checked;save();render();};
}

const faces = {};
async function reference(key,source) {
  const info=refInfo[key];
  const face=await new FontFace(info.family,source,{weight:key==='micro'?'700':'100 1000'}).load();
  if(faces[key])document.fonts.delete(faces[key]);
  document.fonts.add(face); faces[key]=face; render();
}
for(const [key,info] of Object.entries(refInfo)){
  const box=document.createElement('div');box.className='ghost';
  const row=document.createElement('label');row.className='check';
  const cb=document.createElement('input');cb.type='checkbox';cb.checked=state.refs[key][0];cb.id='ghost-'+key;
  cb.onchange=()=>{state.refs[key][0]=cb.checked;save();render();};
  row.append(cb,info.name);box.append(row);
  control(box,{key:'opacity-'+key,label:'Непрозрачность',min:0,max:100,unit:'%',get:()=>state.refs[key][1],update:v=>state.refs[key][1]=v});
  if(key==='flex')control(box,{key:'flexWidth',label:'Ширина Roboto Flex',min:25,max:151,unit:'%'});
  $('ghostControls').append(box);
}
async function loadRefs(){
  await Promise.all(['roboto','flex'].map(async key=>{
    try{await reference(key,'url(assets/'+(key==='flex'?'robotoflex':'roboto')+'.ttf)');}
    catch{$('ghost-'+key).disabled=true;status('Ошибка загрузки '+refInfo[key].name,true);}
  }));
  try{
    await reference('micro','local("MicroTechnicExtendedRUSby-Bold"), local("Micro Technic Extended Bold"), url(/reference/micro)');
    $('microStatus').textContent='MicroTechnic Extended Bold подключён локально.';
  } catch{
    $('ghost-micro').disabled=true;
    $('microStatus').textContent='Выбери локальный файл MicroTechnic для наложения.';
  }
}
$('microFile').onchange=async e=>{
  const file=e.target.files[0];if(!file)return;
  try{await reference('micro',await file.arrayBuffer());$('ghost-micro').disabled=false;
    state.refs.micro[0]=$('ghost-micro').checked=true;$('microStatus').textContent=file.name;save();render();
  }catch{$('microStatus').textContent='Не удалось прочитать файл шрифта.';}
};
function interpolate(px,points=state.points) {
  if(px<=points[0][0])return points[0][1];
  for(let i=1;i<points.length;i++){
    const [x,y]=points[i], [a,b]=points[i-1];
    if(px<=x)return b+(y-b)*(px-a)/(x-a);
  }
  return points.at(-1)[1];
}
let readyGeneration=-1, generation=0, currentFace=null, currentFamily='Original', debounce, exporting=false;
async function getFont(body) {
  const response=await fetch('/api/font',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(!response.ok)throw Error('HTTP '+response.status);
  return response.arrayBuffer();
}
function refreshExport() {
  $('export').disabled=exporting || generation!==readyGeneration || !!$('knotError').textContent || state.version==='original';
}
function rebuild(delay=220) {
  const job=++generation;clearTimeout(debounce);
  $('export').disabled=true;status('Сборка оси opsz…');
  debounce=setTimeout(async()=>{
    try{
      const bytes=await getFont({points:state.points});
      const name='SPPreview'+job;
      const face=await new FontFace(name,bytes,{weight:'100 900',stretch:'100% 175%'}).load();
      if(job!==generation)return;
      document.fonts.add(face);
      const old=currentFace;currentFace=face;currentFamily=name;render();
      if(old)document.fonts.delete(old);
      readyGeneration=job;refreshExport();status('Профиль сохранён локально');
    } catch(e){if(job===generation)status('Не удалось собрать шрифт. Открой лабораторию через файл запуска. '+e.message,true);}
  },delay);
}
$('export').onclick=async()=>{
  exporting=true;$('export').disabled=true;status('Сборка TTF с выбранными формами Жж и У…');
  try{
    const shape=Object.fromEntries(Object.keys(shapeNames).map(k=>[k,state[k]]));
    const bytes=await getFont({points:state.points,shape});
    const url=URL.createObjectURL(new Blob([bytes],{type:'font/ttf'}));
    const a=document.createElement('a');a.href=url;a.download='SovershenenPizdetsV4-Lab.ttf';a.click();
    setTimeout(()=>URL.revokeObjectURL(url),2000);status('TTF собран для скачивания');
  }catch(e){status('Ошибка экспорта. '+e.message,true);}
  finally{exporting=false;refreshExport();}
};

function varSettings(size) {
  const settings={wght:state.weight,wdth:state.width};
  if(state.version!=='original')Object.assign(settings,{opsz:size,...Object.fromEntries(Object.keys(shapeNames).map(k=>[k,state[k]]))});
  return Object.entries(settings).map(([k,v])=>'"'+k+'" '+v).join(', ');
}
function styleSample(el, size) {
  Object.assign(el.style, {
    fontFamily: state.version === 'original' ? 'Original' : currentFamily,
    fontSize: size + 'px', fontWeight: state.weight,
    fontOpticalSizing: 'none', fontVariationSettings: varSettings(size)
  });
}
function activeRefs(size){
  return Object.entries(refInfo).filter(([key])=>state.refs[key][0] && (key==='original'||faces[key])).map(([key,ref])=>{
    const px=state.capMatch?size*.667/ref.cap:size;
    const width=key==='original'?Math.min(125,state.width):key==='flex'?state.flexWidth:100;
    return {family:ref.family,px,weight:key==='micro'?700:state.weight,opacity:state.refs[key][1]/100,
      settings:key==='micro'?'normal':'"wght" '+state.weight+', "wdth" '+width+', "opsz" '+px};
  });
}
function ghostText(layer,text,top,lineHeight){
  const span=document.createElement('span');
  span.className='ghost-text';span.setAttribute('aria-hidden','true');span.textContent=text;
  Object.assign(span.style,{top:top+'px',fontFamily:layer.family,fontSize:layer.px+'px',
    lineHeight:lineHeight+'px',fontWeight:layer.weight,fontVariationSettings:layer.settings,opacity:layer.opacity});
  return span;
}
function drawReadingRefs(){
  const host=$('reading-ghosts'),base=$('reading-text'),layers=activeRefs(state.size);
  host.replaceChildren();
  if(!layers.length || !base.firstChild)return;
  const node=base.firstChild,range=document.createRange(),lines=[];
  let offset=0,lastY;
  // Use the actual line breaks of the master, including words split by overflow-wrap.
  for(const char of node.data){
    range.setStart(node,offset);offset+=char.length;range.setEnd(node,offset);
    const rect=range.getBoundingClientRect();
    if(!rect.width)continue;
    if(lastY===undefined || Math.abs(lastY-rect.top)>1){lines.push('');lastY=rect.top;}
    lines[lines.length-1]+=char;
  }
  const lh=parseFloat(getComputedStyle(base).lineHeight);
  for(const layer of layers)lines.forEach((line,i)=>host.append(ghostText(layer,line,i*lh,lh)));
}
function drawStage(){
  const canvas=$('specimen'), area=$('stage'), size=state.size;
  area.style.minHeight=Math.ceil(size*1.4)+'px';
  const baseline=area.clientHeight*.51+size*.31;
  canvas.replaceChildren();canvas.setAttribute('height',area.clientHeight);
  const layers=[];
  function text(family,px,settings,color,opacity,weight){
    const t=svg('text',{x:24,y:baseline,'font-family':family,'font-size':px,'font-weight':weight,fill:color,opacity},displayText(state.sample));
    t.style.fontVariationSettings=settings;t.style.whiteSpace='pre';t.style.fontOpticalSizing='none';canvas.append(t);layers.push(t);
  }
  text(state.version==='original'?'Original':currentFamily,size,varSettings(size),'#20241e',1,state.weight);
  for(const layer of activeRefs(size))text(layer.family,layer.px,layer.settings,'#e12821',layer.opacity,layer.weight);
  const width=Math.max(area.clientWidth,Math.ceil(Math.max(...layers.map(t=>t.getComputedTextLength())))+50);
  canvas.setAttribute('width',width);
  if(state.guides){
    for(const y of [baseline,baseline-size*.667])canvas.prepend(svg('line',{x1:0,y1:y,x2:width,y2:y,stroke:'#8a9886','stroke-opacity':.65,'stroke-dasharray':'5 4'}));
  }
}
const waterfallSizes=[8,12,14,24,40];
for(const size of waterfallSizes){
  const row=document.createElement('div');row.className='waterrow';
  const label=document.createElement('span');label.className='waterlabel';label.textContent=size+' px';
  const sample=document.createElement('span');sample.className='watertext';
  row.append(label,sample);$('waterfall').append(row);
}
function render(){
  refreshExport();drawStage();
  for(const {button,letter,angle} of uButtons){
    letter.style.fontFamily=currentFamily;
    letter.style.fontVariationSettings='"wght" '+state.weight+', "wdth" 175, "opsz" 48, "UANG" '+angle+', "UWGT" '+state.UWGT;
    button.setAttribute('aria-pressed',state.UANG===angle);
  }
  $('activeVersion').textContent=state.version==='original'?'Оригинал 3.17':'v4';
  $('coordinates').textContent=state.size+' px  /  '+state.weight+' wght  /  '+state.width+' wdth';
  $('trackingValue').textContent=state.version==='original'?'Релиз 3.17':(Math.round(interpolate(state.size)*10)/100)+' % em';
  [...$('presets').children].forEach(b=>b.setAttribute('aria-pressed',presets[b.textContent]===state.sample));
  styleSample($('reading-text'), state.size);
  drawReadingRefs();
  const text = displayText(state.sample);
  [...document.querySelectorAll('.watertext')].forEach((el,i)=>{
    el.textContent=text;
    const px=waterfallSizes[i];
    styleSample(el,px);
    for(const layer of activeRefs(px))el.append(ghostText(layer,text,0,px*1.13));
  });
}
function graph(){
  const graph=$('graph');graph.replaceChildren();
  const points=state.points,minX=points[0][0],maxX=points.at(-1)[0];
  const minY=Math.min(0,...points.map(p=>p[1])),maxY=Math.max(minY+10,...points.map(p=>p[1]));
  const x=n=>38+(n-minX)/(maxX-minX)*535, y=n=>132-(n-minY)/(maxY-minY)*107;
  for(let i=0;i<5;i++){
    const v=minY+(maxY-minY)*i/4, pos=y(v);
    graph.append(svg('line',{x1:36,y1:pos,x2:580,y2:pos,stroke:'#c8ccc3','stroke-dasharray':'3 5'}));
    graph.append(svg('text',{x:29,y:pos+4,'text-anchor':'end','font-size':12,fill:'#60675d'},Math.round(v)/10));
  }
  graph.append(svg('polyline',{points:points.map(p=>x(p[0])+','+y(p[1])).join(' '),fill:'none',stroke:'#c63828','stroke-width':2.5}));
  let previous=-100;
  for(const [px,value] of points){
    graph.append(svg('circle',{cx:x(px),cy:y(value),r:4.5,fill:'#f5f6f1',stroke:'#c63828','stroke-width':2}));
    if(x(px)-previous>=25 || px===maxX){
      graph.append(svg('text',{x:x(px),y:155,'text-anchor':'middle','font-size':12,fill:'#60675d'},px));previous=x(px);
    }
  }
}
function drawKnots(){
  $('knots').replaceChildren();
  for(const [i,point] of state.points.entries()){
    const row=document.createElement('div');row.className='knotrow';
    point.forEach((v,j)=>{
      const inp=document.createElement('input');inp.type='number';inp.value=j?v/10:v;
      inp.min=j?-8:6;inp.max=j?100:200;inp.step=j?0.1:1;
      inp.setAttribute('aria-label',(j?'Трекинг':'Размер')+' точки '+(i+1));
      inp.oninput=()=>{
        const all=[...$('knots').children].map(r=>[...r.querySelectorAll('input')].map((n,j)=>n.value===''?NaN:Number(n.value)*(j?10:1)));
        if(!validPoints(all)){
          $('knotError').textContent='Разные целые размеры 6–200 px, трекинг −8…100 % em.';$('export').disabled=true;return;
        }
        $('knotError').textContent='';state.points=all.sort((a,b)=>a[0]-b[0]);save();graph();render();rebuild();
      };
      inp.onchange=()=>{
        if($('knotError').textContent)return;
        const rows=[...$('knots').children];
        rows.sort((a,b)=>a.firstChild.valueAsNumber-b.firstChild.valueAsNumber);
        for(const [index,r] of rows.entries()){
          if($('knots').children[index]!==r)$('knots').insertBefore(r,$('knots').children[index]);
          r.children[0].setAttribute('aria-label','Размер точки '+(index+1));
          r.children[1].setAttribute('aria-label','Трекинг точки '+(index+1));
          r.children[2].setAttribute('aria-label','Удалить точку '+r.firstChild.value+' px');
        }
      };
      row.append(inp);
    });
    const del=makeButton('×',()=>{
      const x=+row.querySelector('input').value;
      if(state.points.some(p=>p[0]===x))state.points=state.points.filter(p=>p[0]!==x);
      else state.points.splice(i,1);
      if(state.points.length<2)state.points=structuredClone(defaults.points);
      acceptPoints();
    });del.setAttribute('aria-label','Удалить точку '+point[0]+' px');del.disabled=state.points.length<=2;
    row.append(del);$('knots').append(row);
  }
  $('addKnot').disabled=state.points.length>=16;
}
function acceptPoints(){$('knotError').textContent='';save();drawKnots();graph();render();rebuild();}
$('addKnot').onclick=()=>{
  let px=state.points.at(-1)[0]+8;
  if(px>200){px=6;while(state.points.some(p=>p[0]===px))px++;}
  state.points.push([px,Math.round(interpolate(px))]);state.points.sort((a,b)=>a[0]-b[0]);acceptPoints();
};

drawKnots();graph();render();rebuild(0);loadRefs();
new ResizeObserver(()=>{drawStage();drawReadingRefs();}).observe($('stage'));
document.fonts.ready.then(render);
