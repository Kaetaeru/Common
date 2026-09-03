const DAYS=['MON','TUE','WED','THU','FRI'];
const PRESET_IDS=['A','B','C'];
const $=id=>document.getElementById(id);
const themeKey='apu-schedule-theme-v07';
const SYLLABUS_PORTAL='https://syllabus.apu.ac.jp/syllabus/s/?language=en_US';
function applyTheme(theme){const next=theme==='light'?'light':'dark';document.documentElement.dataset.theme=next;try{localStorage.setItem(themeKey,next)}catch{}if($('themeText'))$('themeText').textContent=next==='dark'?tr('theme.light'):tr('theme.dark');if($('themeButton'))$('themeButton').setAttribute('aria-label',next==='dark'?tr('theme.toLight'):tr('theme.toDark'));}
function loadTheme(){let saved=null;try{saved=localStorage.getItem(themeKey)}catch{}applyTheme(saved||'dark');}
function toggleTheme(){applyTheme(document.documentElement.dataset.theme==='dark'?'light':'dark');}
function emptyPresets(){return{A:[],B:[],C:[]};}
const state={data:null,tab:'FIND',quarter:'Q1',selectedCodes:[],activePreset:'A',presets:emptyPresets(),universityCodes:[],blockedSlots:new Set(),slotFilter:null,activeSlot:null,detailCode:null,previewCodes:[]};
for(let i=1;i<=8;i++)$('semesterLevel').insertAdjacentHTML('beforeend',`<option value="${i}" ${i===5?'selected':''}>${i}</option>`);

function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function college(){return $('college').value;}
function prefsKey(){return 'apu-schedule-prefs-v06';}
function maxCredits(){const s=Number($('semesterLevel').value);return $('accelerated').checked&&s>=3?24:s<=2?18:s<=6?20:24;}
function sectionByCode(code){return state.data?.sections.find(x=>String(x.classCode)===String(code));}
function subjectByCode(code){return state.data?.subjects.find(x=>x.subjectCode===code);}
function subjectOfSection(section){return section?subjectByCode(section.subjectCode):null;}
function slotKey(q,d,p){return `${q}:${d}:${p}`;}
function sectionSlots(section){const qs=section.term==='SEMESTER'?['Q1','Q2']:[section.term];const out=[];if(!['SEMESTER','Q1','Q2'].includes(section.term))return out;for(const m of section.meetings||[])for(const q of qs)out.push(slotKey(q,m.day,Number(m.period)));return out;}
function dayLabel(day){return tr(`day.${day}`)||day;}
function meetingText(section){if(!section?.meetings?.length)return tr('meeting.none');return section.meetings.map(m=>tr('meeting.dayPeriod',{day:dayLabel(m.day),period:m.period})).join(' · ');}
function credits(section){return Number(section?.credits??subjectOfSection(section)?.credits??2);}
function eligible(section){const min=Number(section?.availableFromSemester||subjectOfSection(section)?.availableFromSemester||0);return !min||Number($('semesterLevel').value)>=min;}
function unavailableReason(section){const min=Number(section?.availableFromSemester||subjectOfSection(section)?.availableFromSemester||0);if(min&&Number($('semesterLevel').value)<min)return tr('eligibility.semester',{semester:min});return '';}
function selectedSections(){return state.selectedCodes.map(sectionByCode).filter(Boolean);}
function presetSections(preset){return(state.presets[preset]||[]).map(sectionByCode).filter(Boolean);}
function universitySections(){return state.universityCodes.map(sectionByCode).filter(Boolean);}
function previewSections(){return state.previewCodes.map(sectionByCode).filter(Boolean);}
function baseSections(){return [...universitySections(),...selectedSections()];}
function allDisplayedSections(){return state.previewCodes.length?previewSections():baseSections();}
function currentCredits(){const seen=new Set();let total=0;for(const s of baseSections()){if(seen.has(s.subjectCode))continue;seen.add(s.subjectCode);total+=credits(s)}return total;}
function hasConflict(a,b){const bset=new Set(sectionSlots(b));return sectionSlots(a).some(k=>bset.has(k));}
function blockedConflict(section){return sectionSlots(section).some(k=>state.blockedSlots.has(k));}
function fixedOccupies(key){return universitySections().some(s=>sectionSlots(s).includes(key));}
function selectedOccupies(key){return selectedSections().some(s=>sectionSlots(s).includes(key));}
function fmtCredits(n){return Number(n)%1===0?String(Number(n)):Number(n).toFixed(1);}
function toast(message,error=false){const t=$('toast');t.textContent=message;t.className=`toast show${error?' error':''}`;clearTimeout(toast.timer);toast.timer=setTimeout(()=>t.className='toast',2600);}
function normalizePresetMap(raw,legacy=[]){const out=emptyPresets();if(raw&&typeof raw==='object'){for(const id of PRESET_IDS)if(Array.isArray(raw[id]))out[id]=raw[id].map(String);}else out.A=Array.isArray(legacy)?legacy.map(String):[];return out;}
function syncActivePreset(){state.presets[state.activePreset]=[...state.selectedCodes];}
function activatePreset(preset,{notify=true}={}){if(!PRESET_IDS.includes(preset)||preset===state.activePreset)return;syncActivePreset();state.activePreset=preset;state.selectedCodes=[...(state.presets[preset]||[])];state.previewCodes=[];state.detailCode=null;state.activeSlot=null;save();renderAll();if(notify)toast(tr('preset.switched',{preset}));}
function resetAllPresets(){state.activePreset='A';state.presets=emptyPresets();state.selectedCodes=[];state.previewCodes=[];}
async function openSyllabus(code){const section=sectionByCode(code);if(!section)return;const direct=section.syllabusUrl;if(direct){const tab=window.open(direct,'_blank');if(tab)tab.opener=null;else toast(tr('syllabus.popupBlocked'),true);return}const tab=window.open(SYLLABUS_PORTAL,'_blank');if(tab)tab.opener=null;let copied=false;try{await navigator.clipboard.writeText(String(section.classCode));copied=true}catch{}if(!tab)toast(tr('syllabus.popupBlocked'),true);else toast(copied?tr('syllabus.copied',{classCode:section.classCode}):tr('syllabus.opened'));}
function save(){syncActivePreset();localStorage.setItem(prefsKey(),JSON.stringify({college:college(),semesterLevel:$('semesterLevel').value,track:$('track').value,accelerated:$('accelerated').checked,targetCredits:$('targetCredits').value,activePreset:state.activePreset,presets:state.presets,selectedCodes:state.selectedCodes,universityCodes:state.universityCodes,blockedSlots:[...state.blockedSlots],quarter:state.quarter}));}
function loadPrefs(){try{const newer=JSON.parse(localStorage.getItem(prefsKey())||'null');const v05=JSON.parse(localStorage.getItem('apu-schedule-prefs-v05')||'null');const old=JSON.parse(localStorage.getItem('apu-schedule-prefs-v04')||'null');const p=newer||v05||old||{};if(p.college)$('college').value=p.college;if(p.semesterLevel)$('semesterLevel').value=p.semesterLevel;if(p.track)$('track').value=p.track;if(p.accelerated!==undefined)$('accelerated').checked=!!p.accelerated;if(p.targetCredits)$('targetCredits').value=p.targetCredits;state.activePreset=PRESET_IDS.includes(p.activePreset)?p.activePreset:'A';state.presets=normalizePresetMap(p.presets,p.selectedCodes);state.selectedCodes=[...state.presets[state.activePreset]];state.universityCodes=Array.isArray(p.universityCodes)?p.universityCodes.map(String):(Array.isArray(p.fixedCodes)?p.fixedCodes.map(String):[]);state.blockedSlots=new Set(Array.isArray(p.blockedSlots)?p.blockedSlots:[]);state.quarter=p.quarter||p.availabilityQuarter||'Q1'}catch{resetAllPresets();}}
function clampTarget(){const max=maxCredits();$('targetCredits').max=max;if(Number($('targetCredits').value)>max)$('targetCredits').value=max;}
