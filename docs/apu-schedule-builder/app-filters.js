const FILTER_LOCALE={
  en:{
    available:'Available',noConflict:'No conflict',rating4:'★ 4.0+',reviews3:'3+ reviews',syllabus:'Syllabus',more:'Filters',
    schedule:'Schedule',course:'Course',aplus:'A+',reset:'Reset',allowedDays:'Allowed days',allowedPeriods:'Allowed periods',
    format:'Format',credits:'Credits',field:'Field',area:'Area',any:'Any',inPerson:'In-person',online:'Online',onDemand:'On-demand',
    minRating:'Minimum rating',minReviews:'Minimum reviews',recommend:'Recommend',reviewedOnly:'Reviewed courses only',
    syllabusOnly:'Syllabus available only',noConflictPlan:'No conflict with active Plan',activeCount:'{count}',resultCount:'{count} shown',
    allDays:'All days',allPeriods:'All periods',term:'Term',language:'Language'
  },
  ja:{
    available:'履修可能',noConflict:'重複なし',rating4:'★ 4.0以上',reviews3:'レビュー3件+',syllabus:'シラバス',more:'フィルター',
    schedule:'時間割',course:'授業',aplus:'A+',reset:'リセット',allowedDays:'授業を入れてよい曜日',allowedPeriods:'授業を入れてよい時限',
    format:'授業形態',credits:'単位',field:'分野',area:'Area',any:'指定なし',inPerson:'対面',online:'オンライン',onDemand:'オンデマンド',
    minRating:'最低評価',minReviews:'最低レビュー数',recommend:'おすすめ率',reviewedOnly:'レビューありのみ',
    syllabusOnly:'シラバスありのみ',noConflictPlan:'現在のPlanと重複なし',activeCount:'{count}',resultCount:'{count}件表示',
    allDays:'全曜日',allPeriods:'全時限',term:'期間',language:'言語'
  }
};
const FILTER_DAYS=['MON','TUE','WED','THU','FRI'];
const FILTER_PERIODS=[1,2,3,4,5,6];
const filterState={
  days:new Set(FILTER_DAYS),periods:new Set(FILTER_PERIODS),format:'',credits:'',field:'',area:'',
  minRating:0,minReviews:0,minRecommend:0,reviewedOnly:false,syllabusOnly:false,noConflict:false,open:false
};
function ft(key,vars={}){const dict=FILTER_LOCALE[currentLocale]||FILTER_LOCALE.en;let text=dict[key]||FILTER_LOCALE.en[key]||key;for(const [k,v] of Object.entries(vars))text=text.replaceAll(`{${k}}`,String(v));return text}
function filterDayLabel(day){return typeof dayLabel==='function'?dayLabel(day):day.slice(0,3)}
function filterSelect(id,label,options=''){return `<label class="advanced-filter-field"><span>${label}</span><select id="${id}">${options}</select></label>`}
function filterOption(value,label){return `<option value="${esc(value)}">${esc(label)}</option>`}
function injectFilterUi(){
  const wrap=document.querySelector('.search-wrap');if(!wrap||$('quickFilters'))return;
  const search=$('search'),slot=$('slotFilter'),baseFilters=wrap.querySelector('.filters'),eligibility=wrap.querySelector('.filter-line');
  const quick=document.createElement('div');quick.id='quickFilters';quick.className='quick-filters';quick.innerHTML=`
    <button data-quick-filter="available"></button><button data-quick-filter="conflict"></button><button data-quick-filter="rating"></button>
    <button data-quick-filter="reviews"></button><button data-quick-filter="syllabus"></button><button class="filter-more" data-filter-more></button>`;
  search.insertAdjacentElement('afterend',quick);
  const panel=document.createElement('div');panel.id='advancedFilters';panel.className='advanced-filters hidden';
  panel.innerHTML=`
    <div class="advanced-filter-head"><strong data-filter-label="schedule"></strong><button data-filter-reset></button></div>
    <div class="advanced-filter-block"><div class="advanced-filter-label" data-filter-label="allowedDays"></div><div class="filter-chip-grid" id="filterDays"></div></div>
    <div class="advanced-filter-block"><div class="advanced-filter-label" data-filter-label="allowedPeriods"></div><div class="filter-chip-grid periods" id="filterPeriods"></div></div>
    <div class="advanced-filter-head compact"><strong data-filter-label="course"></strong></div>
    <div class="advanced-filter-grid" id="filterCourseGrid"></div>
    <div class="advanced-filter-head compact"><strong>A+</strong></div>
    <div class="advanced-filter-grid" id="filterAplusGrid"></div>
    <div class="advanced-filter-checks">
      <label><input type="checkbox" id="filterReviewedOnly"><span data-filter-label="reviewedOnly"></span></label>
      <label><input type="checkbox" id="filterSyllabusOnly"><span data-filter-label="syllabusOnly"></span></label>
      <label><input type="checkbox" id="filterNoConflict"><span data-filter-label="noConflictPlan"></span></label>
    </div>`;
  if(slot)slot.insertAdjacentElement('afterend',panel);else quick.insertAdjacentElement('afterend',panel);
  if(baseFilters){baseFilters.classList.add('advanced-native-filters');panel.querySelector('#filterCourseGrid').prepend(baseFilters);}
  if(eligibility){eligibility.classList.add('advanced-eligibility');panel.appendChild(eligibility);}
  const courseGrid=panel.querySelector('#filterCourseGrid');
  courseGrid.insertAdjacentHTML('beforeend',
    filterSelect('filterFormat','',filterOption('',ft('any'))+filterOption('IN_PERSON',ft('inPerson'))+filterOption('ONLINE',ft('online'))+filterOption('ON_DEMAND',ft('onDemand')))+
    filterSelect('filterCredits','',filterOption('',ft('any')))+filterSelect('filterField','',filterOption('',ft('any')))+filterSelect('filterArea','',filterOption('',ft('any'))));
  const aplusGrid=panel.querySelector('#filterAplusGrid');
  aplusGrid.innerHTML=
    filterSelect('filterMinRating','',filterOption('0',ft('any'))+['3','3.5','4','4.5'].map(v=>filterOption(v,`★ ${Number(v).toFixed(1)}+`)).join(''))+
    filterSelect('filterMinReviews','',filterOption('0',ft('any'))+[1,3,5,10].map(v=>filterOption(v,`${v}+`)).join(''))+
    filterSelect('filterRecommend','',filterOption('0',ft('any'))+[70,80,90,100].map(v=>filterOption(v,`${v}%+`)).join(''));
  injectFilterCss();renderFilterLabels();renderFilterControls();bindFilterControls();
}
function injectFilterCss(){if(document.querySelector('link[data-filter-css]'))return;const link=document.createElement('link');link.rel='stylesheet';link.href='filters.css';link.dataset.filterCss='1';document.head.appendChild(link)}
function renderFilterLabels(){
  document.querySelectorAll('[data-filter-label]').forEach(el=>{const k=el.dataset.filterLabel;el.textContent=ft(k)});
  const q={available:ft('available'),conflict:ft('noConflict'),rating:ft('rating4'),reviews:ft('reviews3'),syllabus:ft('syllabus')};
  document.querySelectorAll('[data-quick-filter]').forEach(b=>b.textContent=q[b.dataset.quickFilter]||b.dataset.quickFilter);
  const more=document.querySelector('[data-filter-more]');if(more)more.innerHTML=`${esc(ft('more'))}<span class="filter-count" id="filterCount"></span>`;
  const reset=document.querySelector('[data-filter-reset]');if(reset)reset.textContent=ft('reset');
  const native=$('advancedFilters')?.querySelector('.advanced-native-filters');if(native){const selects=native.querySelectorAll('select');if(selects[0])selects[0].title=ft('term');if(selects[1])selects[1].title=ft('language')}
  const fields=$('advancedFilters')?.querySelectorAll('.advanced-filter-field')||[];
  const names=[ft('format'),ft('credits'),ft('field'),ft('area'),ft('minRating'),ft('minReviews'),ft('recommend')];fields.forEach((f,i)=>{const span=f.querySelector(':scope > span');if(span&&names[i])span.textContent=names[i]});
  renderFilterControls();
}
function renderFilterControls(){
  const days=$('filterDays');if(days)days.innerHTML=FILTER_DAYS.map(d=>`<button class="filter-chip ${filterState.days.has(d)?'active':''}" data-filter-day="${d}">${esc(filterDayLabel(d))}</button>`).join('');
  const periods=$('filterPeriods');if(periods)periods.innerHTML=FILTER_PERIODS.map(p=>`<button class="filter-chip ${filterState.periods.has(p)?'active':''}" data-filter-period="${p}">${esc(typeof tr==='function'?tr('meeting.period',{period:p}):`P${p}`)}</button>`).join('');
  if($('filterFormat'))$('filterFormat').value=filterState.format;if($('filterCredits'))$('filterCredits').value=filterState.credits;if($('filterField'))$('filterField').value=filterState.field;if($('filterArea'))$('filterArea').value=filterState.area;
  if($('filterMinRating'))$('filterMinRating').value=String(filterState.minRating);if($('filterMinReviews'))$('filterMinReviews').value=String(filterState.minReviews);if($('filterRecommend'))$('filterRecommend').value=String(filterState.minRecommend);
  if($('filterReviewedOnly'))$('filterReviewedOnly').checked=filterState.reviewedOnly;if($('filterSyllabusOnly'))$('filterSyllabusOnly').checked=filterState.syllabusOnly;if($('filterNoConflict'))$('filterNoConflict').checked=filterState.noConflict;
  const panel=$('advancedFilters');if(panel)panel.classList.toggle('hidden',!filterState.open);
  updateFilterQuickStates();
}
function populateFilterOptions(){
  if(!state.data)return;const sections=state.data.sections||[],subjects=state.data.subjects||[];
  const credits=[...new Set(sections.map(s=>Number(s.credits??subjectOfSection(s)?.credits)).filter(Number.isFinite))].sort((a,b)=>a-b);
  const fields=[...new Set(subjects.map(s=>String(s.field||'').trim()).filter(Boolean))].sort((a,b)=>a.localeCompare(b));
  const areas=[...new Set(subjects.map(s=>String(s.area||'').trim()).filter(Boolean))].sort((a,b)=>a.localeCompare(b));
  setDynamicFilterOptions('filterCredits',credits.map(v=>[String(v),`${fmtCredits(v)} cr`]),filterState.credits);
  setDynamicFilterOptions('filterField',fields.map(v=>[v,v]),filterState.field);
  setDynamicFilterOptions('filterArea',areas.map(v=>[v,v]),filterState.area);
}
function setDynamicFilterOptions(id,items,current){const sel=$(id);if(!sel)return;sel.innerHTML=filterOption('',ft('any'))+items.map(([v,l])=>filterOption(v,l)).join('');sel.value=items.some(([v])=>String(v)===String(current))?String(current):'';if(!sel.value){if(id==='filterCredits')filterState.credits='';if(id==='filterField')filterState.field='';if(id==='filterArea')filterState.area=''}}
function sectionFitsActivePlan(s){
  if(blockedConflict(s))return false;
  const current=baseSections();
  const same=current.find(x=>x.subjectCode===s.subjectCode&&String(x.classCode)!==String(s.classCode));
  if(same&&state.universityCodes.includes(String(same.classCode)))return false;
  return !current.some(x=>String(x.classCode)!==String(s.classCode)&&(!same||String(x.classCode)!==String(same.classCode))&&hasConflict(x,s));
}
function sectionPassesExtraFilters(subject,s){
  const meetings=s.meetings||[];
  if(meetings.length&&meetings.some(m=>!filterState.days.has(m.day)||!filterState.periods.has(Number(m.period))))return false;
  if(filterState.format&&s.mode!==filterState.format)return false;
  if(filterState.credits&&Number(credits(s))!==Number(filterState.credits))return false;
  if(filterState.field&&String(subject.field||s.field||'')!==filterState.field)return false;
  if(filterState.area&&String(subject.area||s.area||'')!==filterState.area)return false;
  const a=s.aplusReview,count=Number(a?.reviewCount||0),rating=Number(a?.rating),recommend=Number(a?.recommendPercent);
  if(filterState.minRating&&(!count||!Number.isFinite(rating)||rating<filterState.minRating))return false;
  if(filterState.minReviews&&count<filterState.minReviews)return false;
  if(filterState.minRecommend&&(!count||!Number.isFinite(recommend)||recommend<filterState.minRecommend))return false;
  if(filterState.reviewedOnly&&!count)return false;
  if(filterState.syllabusOnly&&!s.syllabusUrl)return false;
  if(filterState.noConflict&&!sectionFitsActivePlan(s))return false;
  return true;
}
function countActiveExtraFilters(){let n=0;if(filterState.days.size<FILTER_DAYS.length)n++;if(filterState.periods.size<FILTER_PERIODS.length)n++;for(const v of [filterState.format,filterState.credits,filterState.field,filterState.area])if(v)n++;for(const v of [filterState.minRating,filterState.minReviews,filterState.minRecommend])if(Number(v)>0)n++;for(const v of [filterState.reviewedOnly,filterState.syllabusOnly,filterState.noConflict])if(v)n++;if($('termFilter')?.value)n++;if($('languageFilter')?.value)n++;if($('showUnavailable')?.checked)n++;return n}
function updateFilterQuickStates(){
  const set=(name,on)=>document.querySelector(`[data-quick-filter="${name}"]`)?.classList.toggle('active',!!on);
  set('available',!$('showUnavailable')?.checked);set('conflict',filterState.noConflict);set('rating',filterState.minRating>=4);set('reviews',filterState.minReviews>=3);set('syllabus',filterState.syllabusOnly);
  const count=$('filterCount');if(count){const n=countActiveExtraFilters();count.textContent=n?String(n):'';count.classList.toggle('hidden',!n)}
}
function resetExtraFilters(){filterState.days=new Set(FILTER_DAYS);filterState.periods=new Set(FILTER_PERIODS);Object.assign(filterState,{format:'',credits:'',field:'',area:'',minRating:0,minReviews:0,minRecommend:0,reviewedOnly:false,syllabusOnly:false,noConflict:false});if($('termFilter'))$('termFilter').value='';if($('languageFilter'))$('languageFilter').value='';if($('showUnavailable'))$('showUnavailable').checked=false;renderFilterControls();renderCourseList()}
function filterChanged(){renderFilterControls();renderCourseList()}
function bindFilterControls(){
  $('quickFilters').addEventListener('click',e=>{const b=e.target.closest('[data-quick-filter]');if(!b)return;switch(b.dataset.quickFilter){case'available':$('showUnavailable').checked=!$('showUnavailable').checked;break;case'conflict':filterState.noConflict=!filterState.noConflict;break;case'rating':filterState.minRating=filterState.minRating>=4?0:4;break;case'reviews':filterState.minReviews=filterState.minReviews>=3?0:3;break;case'syllabus':filterState.syllabusOnly=!filterState.syllabusOnly;break}filterChanged()});
  document.querySelector('[data-filter-more]').addEventListener('click',()=>{filterState.open=!filterState.open;renderFilterControls()});
  document.querySelector('[data-filter-reset]').addEventListener('click',resetExtraFilters);
  $('filterDays').addEventListener('click',e=>{const b=e.target.closest('[data-filter-day]');if(!b)return;const d=b.dataset.filterDay;if(filterState.days.has(d)){if(filterState.days.size>1)filterState.days.delete(d)}else filterState.days.add(d);filterChanged()});
  $('filterPeriods').addEventListener('click',e=>{const b=e.target.closest('[data-filter-period]');if(!b)return;const p=Number(b.dataset.filterPeriod);if(filterState.periods.has(p)){if(filterState.periods.size>1)filterState.periods.delete(p)}else filterState.periods.add(p);filterChanged()});
  for(const [id,key,number] of [['filterFormat','format',false],['filterCredits','credits',false],['filterField','field',false],['filterArea','area',false],['filterMinRating','minRating',true],['filterMinReviews','minReviews',true],['filterRecommend','minRecommend',true]])$(id).addEventListener('change',e=>{filterState[key]=number?Number(e.target.value||0):e.target.value;filterChanged()});
  for(const [id,key] of [['filterReviewedOnly','reviewedOnly'],['filterSyllabusOnly','syllabusOnly'],['filterNoConflict','noConflict']])$(id).addEventListener('change',e=>{filterState[key]=e.target.checked;filterChanged()});
  for(const id of ['termFilter','languageFilter','showUnavailable'])$(id).addEventListener('change',()=>{updateFilterQuickStates()});
  $('uiLanguage').addEventListener('change',()=>setTimeout(()=>{renderFilterLabels();populateFilterOptions();renderCourseList()},0));
}

function installCourseFilters(){
  injectFilterUi();
  const baseFilteredSubjectGroups=filteredSubjectGroups;
  filteredSubjectGroups=function(){return baseFilteredSubjectGroups().map(({subject,sections})=>({subject,sections:sections.filter(s=>sectionPassesExtraFilters(subject,s))})).filter(g=>g.sections.length)};
  const baseRenderCourseList=renderCourseList;
  renderCourseList=function(){baseRenderCourseList();updateFilterQuickStates();if(state.data){const groups=filteredSubjectGroups(),count=groups.reduce((n,g)=>n+g.sections.length,0);const summary=$('listSummary');if(summary)summary.title=ft('resultCount',{count})}};
  const baseAfterData=afterData;
  afterData=function(){baseAfterData();populateFilterOptions();renderFilterLabels();};
}
if(typeof document!=='undefined')installCourseFilters();
if(typeof module!=='undefined'&&module.exports)module.exports={filterState,sectionPassesExtraFilters,relaxedCoursePlanFit:sectionFitsActivePlan,resetExtraFilters};
