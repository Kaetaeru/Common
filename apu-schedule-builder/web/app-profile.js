const LANGUAGE_LEVELS={JA:['Foundation Japanese I','Foundation Japanese II','Foundation Japanese III','Intermediate Japanese','Pre-Advanced Japanese','Advanced Japanese'],EN:['Elementary English','Pre-Intermediate English','Intermediate English','Upper-Intermediate English','Advanced English 1','Advanced English 2']};
function basisLanguage(){return $('track').value==='E'?'EN':'JA';}
function studyLanguage(){return basisLanguage()==='EN'?'JA':'EN';}
function basisLabel(){return basisLanguage()==='EN'?'English Basis':'Japanese Basis';}
function updateLanguageLevelOptions(value=0){
  const lang=studyLanguage(),labels=LANGUAGE_LEVELS[lang],select=$('languageLevel'),keep=Number(value||0);
  select.innerHTML=`<option value="0">${esc(tr('eligibility.noCompleted'))}</option>`+labels.map((label,i)=>`<option value="${i+1}">${esc(label)}</option>`).join('');
  select.value=String(Math.min(Math.max(keep,0),labels.length));
  $('languageLevelLabel').textContent=tr('eligibility.languageLabel',{language:lang==='JA'?'Japanese':'English'});
  const advanced=$('track').value==='JAT'?tr('eligibility.advancedHelp'):'';
  $('languageLevelHelp').textContent=lang==='JA'?tr('eligibility.englishHelp'):tr('eligibility.japaneseHelp',{advanced});
}
function semesterUnavailableReason(section){const min=Number(section?.availableFromSemester||subjectOfSection(section)?.availableFromSemester||0);return min&&Number($('semesterLevel').value)<min?tr('eligibility.semester',{semester:min}):'';}
function languageUnavailableReason(section){
  const subject=subjectOfSection(section),core=section?.languageCore||subject?.languageCore,rank=Number(section?.languageLevelRank||subject?.languageLevelRank||0),label=section?.languageLevelLabel||subject?.languageLevelLabel||section?.name||tr('eligibility.coreLanguage');
  if(!core||!rank)return'';
  const track=$('track').value;
  if(track==='E'&&core==='EN')return tr('eligibility.basisEnglish');
  if((track==='JST'||track==='JAT')&&core==='JA')return tr('eligibility.basisJapanese');
  let completed=Number($('languageLevel').value||0);
  if(track==='JAT'&&core==='EN')completed=Math.max(completed,4);
  const opposite=(track==='E'&&core==='JA')||((track==='JST'||track==='JAT')&&core==='EN');
  if(opposite&&completed&&rank<=completed)return tr('eligibility.completed',{label});
  return'';
}
function eligibilitySummary(){const level=Number($('languageLevel').value||0),labels=LANGUAGE_LEVELS[studyLanguage()],levelText=level?tr('eligibility.levelSuffix',{level:labels[level-1]}):'';return tr('eligibility.summary',{semester:$('semesterLevel').value,basis:basisLabel(),level:levelText});}

eligible=function(section){return !semesterUnavailableReason(section)&&!languageUnavailableReason(section);};
unavailableReason=function(section){return semesterUnavailableReason(section)||languageUnavailableReason(section);};

save=function(){
  syncActivePreset();
  localStorage.setItem(prefsKey(),JSON.stringify({profileConfirmed:!!state.profileConfirmed,college:college(),semesterLevel:$('semesterLevel').value,track:$('track').value,languageLevel:$('languageLevel').value,accelerated:$('accelerated').checked,targetCredits:$('targetCredits').value,activePreset:state.activePreset,presets:state.presets,selectedCodes:state.selectedCodes,universityCodes:state.universityCodes,blockedSlots:[...state.blockedSlots],quarter:state.quarter}));
};
loadPrefs=function(){
  try{
    const newer=JSON.parse(localStorage.getItem(prefsKey())||'null'),v05=JSON.parse(localStorage.getItem('apu-schedule-prefs-v05')||'null'),old=JSON.parse(localStorage.getItem('apu-schedule-prefs-v04')||'null'),p=newer||v05||old||{};
    if(p.college)$('college').value=p.college;if(p.semesterLevel)$('semesterLevel').value=p.semesterLevel;if(p.track)$('track').value=p.track;
    updateLanguageLevelOptions(p.languageLevel||0);
    if(p.accelerated!==undefined)$('accelerated').checked=!!p.accelerated;if(p.targetCredits)$('targetCredits').value=p.targetCredits;
    // Saves written before this flow existed have no profileConfirmed field at all; those students already chose a college, so treat them as set up. Newer saves always carry the flag, so an unfinished setup stays unfinished.
    state.profileConfirmed=p.profileConfirmed===undefined?!!p.college:p.profileConfirmed===true;state.activePreset=PRESET_IDS.includes(p.activePreset)?p.activePreset:'A';state.presets=normalizePresetMap(p.presets,p.selectedCodes);state.selectedCodes=[...state.presets[state.activePreset]];
    state.universityCodes=Array.isArray(p.universityCodes)?p.universityCodes.map(String):(Array.isArray(p.fixedCodes)?p.fixedCodes.map(String):[]);state.blockedSlots=new Set(Array.isArray(p.blockedSlots)?p.blockedSlots:[]);state.quarter=p.quarter||p.availabilityQuarter||'Q1';
  }catch{state.profileConfirmed=false;resetAllPresets();updateLanguageLevelOptions(0)}
};

addUniversity=function(raw){
  const code=String(raw||'').trim(),section=sectionByCode(code);if(!section){toast(tr('class.notFound',{code}),true);return}
  const semesterReason=semesterUnavailableReason(section);if(semesterReason){toast(semesterReason,true);return}
  const lockedConflict=universitySections().find(s=>s.classCode!==section.classCode&&(hasConflict(s,section)||s.subjectCode===section.subjectCode));if(lockedConflict){toast(tr('class.fixedConflict'),true);return}
  syncActivePreset();
  const collisionsByPlan={};
  for(const id of PRESET_IDS){const hits=presetSections(id).filter(s=>hasConflict(s,section)||s.subjectCode===section.subjectCode);if(hits.length)collisionsByPlan[id]=hits;}
  const affected=Object.keys(collisionsByPlan);
  if(affected.length&&!confirm(tr('preset.conflictSummary',{plans:affected.map(id=>tr('preset.plan',{preset:id})).join(', ')})))return;
  for(const id of affected){const remove=new Set(collisionsByPlan[id].map(s=>String(s.classCode)));state.presets[id]=state.presets[id].filter(c=>!remove.has(c));}
  state.selectedCodes=[...state.presets[state.activePreset]];
  for(const key of sectionSlots(section))state.blockedSlots.delete(key);
  if(!state.universityCodes.includes(code))state.universityCodes.push(code);
  save();$('universityCode').value='';renderAll();
};
revalidateSemesterSelection=function(){
  if(!state.data)return;syncActivePreset();let removed=0;
  for(const id of PRESET_IDS){const before=state.presets[id].length;state.presets[id]=state.presets[id].filter(code=>{const s=sectionByCode(code);return s&&eligible(s)});removed+=before-state.presets[id].length;}
  state.selectedCodes=[...state.presets[state.activePreset]];
  if(removed)toast(tr('profile.revalidate',{count:removed}),true);
  const invalidLocked=universitySections().filter(s=>!!semesterUnavailableReason(s));if(invalidLocked.length)toast(tr('profile.fixedSemester',{count:invalidLocked.length}),true);
};
buildAutofillConfig=function(){const fixed=[...new Set([...state.universityCodes,...state.selectedCodes])];return{college:college(),semesterLevel:Number($('semesterLevel').value),accelerated:$('accelerated').checked,track:$('track').value,languageLevel:Number($('languageLevel').value||0),targetCredits:Number($('targetCredits').value),maxCredits:maxCredits(),fixedClassCodes:fixed,blockedSlots:[...state.blockedSlots],autofill:true,maxCampusDays:5,maxGap:5,statuses:{}};};

const _afterDataProfile=afterData;
afterData=function(){_afterDataProfile();$('eligibilityText').textContent=eligibilitySummary();};
aplusLink=function(s,detail=false){
  const a=s?.aplusReview;if(!a)return'';
  const count=Number(a.reviewCount||0),rating=Number(a.rating),recommend=a.recommendPercent,hasRating=count&&Number.isFinite(rating),scoreText=hasRating?rating.toFixed(1):'N/A';
  const reviewText=count?tr('aplus.reviews',{count,suffix:count===1?'':'s'}):tr('aplus.noReviews'),recommendText=count&&recommend!==null&&recommend!==undefined?tr('aplus.recommend',{percent:recommend}):'';
  const href=esc(a.sourceUrl||'https://apluscoursereview.com/'),meta=[`<span class="aplus-brand">A+</span>`,`<span>${esc(reviewText)}</span>`];if(recommendText)meta.push(`<span>${esc(recommendText)}</span>`);meta.push('<span class="aplus-arrow">↗</span>');
  const link=`<a class="aplus-badge${detail?' detail':''}" href="${href}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()" title="${esc(tr('aplus.open'))}"><span class="aplus-main"><span class="aplus-star">★</span><span class="aplus-score">${scoreText}</span></span><span class="aplus-meta">${meta.join('<span class="aplus-dot">·</span>')}</span></a>`;
  return detail?`<div class="aplus-row detail">${link}</div>`:`<div class="aplus-row">${link}</div>`;
};

$('track').addEventListener('change',()=>updateLanguageLevelOptions(0));
$('languageLevel').addEventListener('change',()=>{if(state.profileEditing)return;state.previewCodes=[];revalidateSemesterSelection();save();$('eligibilityText').textContent=eligibilitySummary();renderAll();});


/* ── profile: chosen once, then fixed until explicitly edited ─────────────
 * College and semester decide which classes are even offered, so they are
 * shown as a locked summary. Editing opens the form; nothing takes effect
 * until Apply, which is the only place a college switch reloads the data. */

const PROFILE_FIELDS=['college','semesterLevel','track','languageLevel','accelerated','targetCredits'];

function profileValues(){
  const out={};
  for(const id of PROFILE_FIELDS)out[id]=$(id).type==='checkbox'?$(id).checked:$(id).value;
  return out;
}
function restoreProfileValues(v){
  if(!v)return;
  $('college').value=v.college;$('semesterLevel').value=v.semesterLevel;$('track').value=v.track;
  updateLanguageLevelOptions(v.languageLevel||0);$('languageLevel').value=v.languageLevel;
  $('accelerated').checked=!!v.accelerated;$('targetCredits').value=v.targetCredits;
}
function trackLabel(){const o=$('track').selectedOptions[0];return o?o.textContent:$('track').value}
function languageLevelLabel(){const o=$('languageLevel').selectedOptions[0];return o?o.textContent:''}

function renderProfileSummary(){
  const box=$('profileSummary');if(!box)return;
  if(!state.profileConfirmed){box.innerHTML=`<div class="empty-inline">${esc(tr('profile.none'))}</div>`;return}
  const rows=[
    [tr('settings.college'),college()],
    [tr('settings.semester'),tr('profile.semesterValue',{semester:$('semesterLevel').value})],
    [tr('settings.track'),trackLabel()],
    [tr('settings.completedLanguage'),languageLevelLabel()],
    [tr('settings.targetCredits'),$('targetCredits').value],
    [tr('settings.accelerated'),$('accelerated').checked?tr('profile.on'):tr('profile.off')],
  ];
  box.innerHTML=rows.map(([k,v])=>`<div class="profile-row"><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join('');
}

function openProfile(setup=false){
  state.profileEditing=true;
  state.profileSetup=!!setup;
  state.profileSnapshot=profileValues();
  $('profileDrawerTitle').textContent=setup?tr('profile.setupTitle'):tr('profile.title');
  $('profileIntro').textContent=setup?tr('profile.setupIntro'):tr('profile.editIntro');
  $('profileApplyButton').textContent=setup?tr('profile.start'):tr('profile.apply');
  $('profileCancelButton').classList.toggle('hidden',setup);
  openDrawer('profileDrawer');
}
function cancelProfile(){
  restoreProfileValues(state.profileSnapshot);
  state.profileEditing=false;state.profileSetup=false;
  closeDrawers();
}
async function applyProfile(){
  const before=state.profileSnapshot||{};
  // Also true during first-time setup: picking a college there must load its data.
  const collegeChanged=!!before.college&&before.college!==college();
  state.profileEditing=false;state.profileSetup=false;
  state.profileConfirmed=true;
  clampTarget();state.previewCodes=[];
  closeDrawers();
  if(collegeChanged){await switchCollege();}
  else{revalidateSemesterSelection();save();renderAll();}
  $('eligibilityText').textContent=eligibilitySummary();
  renderProfileSummary();renderTop();
  toast(tr('profile.applied'));
}
