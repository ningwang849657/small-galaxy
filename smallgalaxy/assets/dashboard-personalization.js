/* Personal settings and an opt-in music player. No third-party connection until Play. */
/* 内置曲目都选了允许内嵌播放的官方乐团/版权方上传；很多"官方 Topic"频道禁止内嵌（错误 150）。 */
const OFFICIAL_TRACKS = Object.freeze([
  {key:'mononoke',   id:'8OFbtrDZESo', name:'幽灵公主 · 阿席达卡传说',   by:'久石让 · WDR 广播管弦乐团现场'},
  {key:'braveheart', id:'6Z8kqvNOjGg', name:'勇敢的心 · 公主之恋',       by:'James Horner · 丹麦国家交响乐团现场'},
  {key:'paradiso',   id:'TbDE2Rpi4ik', name:'天堂电影院 · 主题曲',       by:'Ennio Morricone · Musica e Oltre'},
  {key:'sangreal',   id:'t-uQe11OIfo', name:'Chevaliers de Sangreal',   by:'Hans Zimmer · 丹麦国家交响乐团现场'}
]);
const trackByKey=key=>OFFICIAL_TRACKS.find(track=>track.key===key) || OFFICIAL_TRACKS[0];
/* 主题、强调色、目标卡配色三套独立清单；深色主题另外标记 data-dark，共用一份深色墨色。 */
const THEME_GROUPS=Object.freeze([
  ['浅色',[['light','月光白'],['warm','暖纸色'],['linen','亚麻灰'],['mist','雾松青'],['sky','海盐蓝'],['dusk','暮山紫'],['blush','藕荷粉']]],
  ['深色',[['dark','深空黑'],['ink','水墨黑'],['midnight','午夜蓝'],['night','深林夜'],['cocoa','可可棕'],['wine','酒红夜']]]
]);
const DARK_THEMES=Object.freeze(THEME_GROUPS[1][1].map(([key])=>key));
const ACCENT_OPTIONS=Object.freeze([['blue','星际蓝'],['purple','星云紫'],['green','森林绿'],['teal','青瓷'],['amber','琥珀金'],['rose','落樱粉'],['clay','陶土橙']]);
const FOCUS_OPTIONS=Object.freeze([['night','深空黑'],['forest','深林绿'],['ocean','深海蓝'],['plum','暗夜紫'],['clay','陶土棕'],['ember','炭烬红'],['paper','月光纸']]);
const THEMES=THEME_GROUPS.flatMap(([,options])=>options.map(([key])=>key));
const ACCENTS=ACCENT_OPTIONS.map(([key])=>key);
const FOCUS_STYLES=FOCUS_OPTIONS.map(([key])=>key);

/* 留空的文案项表示"跟着场景走"，填了就一直用你写的。 */
const TEXT_PREFS = Object.freeze(['title','signature','brand','tagline','eyebrow','kpiToday','kpiWeek','kpiAvg',
  'goalHeading','rhythmHeading','musicEyebrow','footerNote','methodNote','musicUrl','musicTitle','fileName','customName','libraryTrack']);
const DEFAULT_PREFS = Object.freeze({
  title:'每一点专注，都有自己的光。',
  signature:'不必让每一天都满格。看见投入的时间，也给思考和休息留一点空间。',
  brand:'小银河', tagline:'', eyebrow:'', kpiToday:'', kpiWeek:'', kpiAvg:'',
  goalHeading:'按自己的节奏。', rhythmHeading:'你的活跃时段', musicEyebrow:'A LITTLE SOUND, A LITTLE SPACE',
  footerNote:'✦ 小银河', methodNote:'',
  theme:'light', accent:'blue', accentCustom:'', focusStyle:'night', compact:false,
  showGoal:true, showRhythm:true, showTimeline:true, showDecor:true, showMusic:true,
  decorStrength:100, weatherMode:'cycle', weatherCycle:96,
  scene:'research', customName:'学习', customSource:'manual', animations:true,
  musicMode:'official', officialTrack:OFFICIAL_TRACKS[0].key, libraryTrack:'',
  musicUrl:'', musicTitle:OFFICIAL_TRACKS[0].name, fileName:'', volume:35, loop:true
});
function readPreferences() {
  let saved={};
  try { saved=JSON.parse(storage.get('preferences','{}')) || {}; } catch {}
  const prefs={...DEFAULT_PREFS};
  TEXT_PREFS.forEach(key=>{
    if(typeof saved[key]==='string') prefs[key]=saved[key].slice(0,key==='musicUrl'?2048:key==='methodNote'?600:200);
  });
  ['compact','showGoal','showRhythm','showTimeline','showDecor','showMusic','loop','animations'].forEach(key=>{
    if(typeof saved[key]==='boolean') prefs[key]=saved[key];
  });
  for(const [key,values] of Object.entries({theme:THEMES,accent:ACCENTS,focusStyle:FOCUS_STYLES,musicMode:['official','library','youtube','audio','file'],scene:['research','work','exercise','custom'],customSource:['manual','computer'],officialTrack:OFFICIAL_TRACKS.map(track=>track.key),weatherMode:['cycle','drizzle','storm','clear']})) {
    if(values.includes(saved[key])) prefs[key]=saved[key];
  }
  if(/^#[0-9a-f]{6}$/i.test(saved.accentCustom || '')) prefs.accentCustom=saved.accentCustom;
  for(const [key,low,high] of [['volume',0,100],['decorStrength',0,150],['weatherCycle',20,600]]) {
    if(Number.isFinite(saved[key])) prefs[key]=Math.max(low,Math.min(high,saved[key]));
  }
  return prefs;
}
let preferences=readPreferences();
function savePreferences() { return storage.set('preferences',JSON.stringify(preferences)); }
const nav=document.createElement('div'); nav.className='header-actions';
nav.innerHTML='<button id="refresh-data" title="更新统计，不打断音乐">更新数据</button><button id="open-settings">个性化 <span aria-hidden="true">↗</span></button>';
header.appendChild(nav);
document.querySelector('.hero').insertAdjacentHTML('afterend', `
<section class="music-card" aria-label="背景音乐">
  <div class="music-top"><div class="music-label"><span class="music-icon" aria-hidden="true">♫</span><div><div class="eyebrow" id="music-eyebrow">A LITTLE SOUND, A LITTLE SPACE</div><strong id="track-title"></strong><div class="muted" id="music-status" aria-live="polite">点击播放，让音乐陪你一会儿。</div><a id="music-external" target="_blank" rel="noopener noreferrer" hidden>在 YouTube 打开 ↗</a></div></div>
  <div class="music-actions"><button id="music-play" class="primary-button">播放</button><label class="volume-label" for="music-volume">音量 <input id="music-volume" type="range" min="0" max="100" step="1"></label><label class="loop-label"><input id="music-loop" type="checkbox"> 循环</label><button id="music-settings">换音乐</button></div></div>
  <div class="track-chips" id="track-chips" role="group" aria-label="曲目"></div>
  <div id="youtube-wrap" hidden><div id="youtube-player"></div></div>
  <audio id="background-audio" preload="none"></audio>
</section>`);
// 曲目按钮直接摆在卡片上，点一下就换；设置面板里的下拉是同一份偏好。
const trackChips=document.getElementById('track-chips');
let libraryTracks=[];
const trackLabel=name=>name.replace(/\.[^.]+$/,'');
function renderTrackChips() {
  trackChips.replaceChildren();
  const official=preferences.musicMode==='official';
  const items=official ? OFFICIAL_TRACKS.map(track=>({key:track.key,label:track.name,hint:track.by}))
    : preferences.musicMode==='library' ? libraryTracks.map(track=>({key:track.name,label:trackLabel(track.name),hint:track.name}))
    : [];
  trackChips.hidden=!items.length;
  const active=official?preferences.officialTrack:preferences.libraryTrack;
  items.forEach(item=>{
    const chip=document.createElement('button');
    chip.type='button'; chip.dataset.track=item.key; chip.title=item.hint; chip.textContent=item.label;
    const current=item.key===active;
    chip.classList.toggle('current',current); chip.setAttribute('aria-pressed',String(current));
    chip.onclick=()=>official?selectOfficialTrack(item.key):selectLibraryTrack(item.key);
    trackChips.appendChild(chip);
  });
}
function announceTrack(saved,title) {
  musicStatus.textContent=saved?'已切到《'+title+'》，点击播放。':'已切换曲目，但浏览器禁止保存设置。';
}
function selectOfficialTrack(key) {
  const track=trackByKey(key);
  stopMusic();
  Object.assign(preferences,{musicMode:'official',officialTrack:track.key,musicTitle:track.name});
  const saved=savePreferences(); syncMusicControls(); announceTrack(saved,track.name);
}
function selectLibraryTrack(name) {
  stopMusic();
  Object.assign(preferences,{musicMode:'library',libraryTrack:name,musicTitle:trackLabel(name)});
  const saved=savePreferences(); syncMusicControls(); announceTrack(saved,preferences.musicTitle);
}
/* 本机音乐库：文件放在 ~/.lab_tracker/music/，由本机服务按文件名点播。
   曲目留在磁盘上，不占浏览器存储，换浏览器也不会丢。 */
async function loadMusicLibrary() {
  if(location.protocol==='file:') return libraryTracks;
  try {
    const response=await fetch('/music',{cache:'no-store',signal:AbortSignal.timeout(4000)});
    if(!response.ok) throw Error('library');
    const list=await response.json();
    libraryTracks=Array.isArray(list)?list.filter(item=>item && typeof item.name==='string'):[];
  } catch { libraryTracks=[]; }
  return libraryTracks;
}
document.body.insertAdjacentHTML('beforeend', `
<dialog id="settings-dialog" aria-labelledby="settings-heading">
  <div class="settings-head"><div><div class="eyebrow">MAKE IT YOURS</div><h2 id="settings-heading">你的小银河。</h2></div><button id="close-settings" aria-label="关闭个性化">✕</button></div>
  <form id="appearance-form"><fieldset><legend>写给自己</legend>
    <label for="setting-title">顶部主标题 <span>始终单行，长标题可横向滚动</span></label><input id="setting-title" maxlength="80" required>
    <label for="setting-signature">个性签名</label><textarea id="setting-signature" maxlength="200" rows="3"></textarea>
  </fieldset><fieldset><legend>页面上的每一句话 <span>留空＝跟着场景自动生成</span></legend><div class="settings-grid">
    <label>品牌名<input id="setting-brand" maxlength="24"></label>
    <label>品牌副标题<input id="setting-tagline" maxlength="60" placeholder="自动"></label>
    <label>顶部小字<input id="setting-eyebrow" maxlength="60" placeholder="自动"></label>
    <label>今日卡标题<input id="setting-kpiToday" maxlength="40" placeholder="自动"></label>
    <label>近 7 天卡标题<input id="setting-kpiWeek" maxlength="40" placeholder="自动"></label>
    <label>近 14 天卡标题<input id="setting-kpiAvg" maxlength="40" placeholder="自动"></label>
    <label>目标卡标题<input id="setting-goalHeading" maxlength="40"></label>
    <label>节奏卡标题<input id="setting-rhythmHeading" maxlength="40"></label>
    <label>音乐卡小字<input id="setting-musicEyebrow" maxlength="60"></label>
    <label>页脚文字<input id="setting-footerNote" maxlength="60"></label>
  </div>
    <label for="setting-methodNote">底部说明 <span>留空＝用默认的数据口径说明</span></label><textarea id="setting-methodNote" maxlength="600" rows="3" placeholder="自动"></textarea>
  </fieldset><fieldset><legend>你的节奏与外观</legend><div class="settings-grid">
    <label>每日目标<select id="setting-goal"></select></label>
    <label>页面风格<select id="setting-theme"></select></label>
    <label>强调色<select id="setting-accent"></select></label>
  </div><div class="settings-grid">
    <label>目标卡配色<select id="setting-focusStyle"></select></label>
    <label>自定义强调色<span class="color-row"><input id="setting-accentCustom" type="color"><button type="button" id="clear-accent">用预设</button></span></label>
    <label>天气<select id="setting-weatherMode"><option value="cycle">雨林循环：晨雾 → 积云 → 骤雨 → 雨后透光</option><option value="drizzle">林间细雨</option><option value="storm">热带骤雨</option><option value="clear">雨后晴光</option></select></label>
    <label>一轮天气时长 <span id="weather-cycle-value"></span><input id="setting-weatherCycle" type="range" min="20" max="600" step="4"></label>
  </div>
    <label>装饰画浓度 <span id="decor-strength-value"></span><input id="setting-decorStrength" type="range" min="0" max="150" step="5"></label>
    <div class="settings-checks"><label><input id="setting-compact" type="checkbox"> 紧凑布局</label><label><input id="setting-showGoal" type="checkbox"> 每日目标卡</label><label><input id="setting-showRhythm" type="checkbox"> 活跃时段卡</label><label><input id="setting-showTimeline" type="checkbox"> 单日时间线</label><label><input id="setting-showDecor" type="checkbox"> 森林与雨林背景</label><label><input id="setting-showMusic" type="checkbox"> 音乐卡片</label></div>
  </fieldset><div class="settings-buttons"><button type="button" id="reset-appearance">恢复默认外观</button><button class="primary-button" type="submit">保存外观</button></div></form>
  <form id="music-form"><fieldset><legend>背景音乐</legend>
    <label for="setting-music-mode">音乐来源</label><select id="setting-music-mode"><option value="library">本机音乐库 · 你自己的文件</option><option value="official">内置曲目 · 官方在线版</option><option value="youtube">其他 YouTube 曲目</option><option value="audio">在线音频直链</option><option value="file">本机音频文件</option></select>
    <div id="official-track-field"><label for="setting-official-track">内置曲目</label><select id="setting-official-track"></select><p class="muted" id="official-track-note"></p></div>
    <div id="library-field"><label for="setting-library-track">音乐库曲目</label><select id="setting-library-track"></select>
      <p class="muted" id="library-note"></p><button type="button" id="rescan-library">重新扫描音乐库</button></div>
    <div id="music-url-field"><label for="setting-music-url">音乐链接</label><input id="setting-music-url" type="url" maxlength="2048" placeholder="https://…"><p class="muted">支持 YouTube 视频链接，或可直接播放的 HTTPS 音频文件地址。</p></div>
    <div id="music-file-field"><label for="setting-music-file">选择本机音乐</label><input id="setting-music-file" type="file" accept="audio/*,.mp3,.wav,.ogg,.m4a,.flac"><p class="muted" id="saved-file-note"></p></div>
    <label for="setting-music-title">显示名称</label><input id="setting-music-title" maxlength="100" placeholder="给这首歌起个名字">
    <p class="muted">在线音乐仅在点击播放后联网。本机文件保存在当前浏览器，不上传；首次播放需要点击。在线曲目受网络、地区与平台嵌入权限影响。</p>
  </fieldset><div class="settings-buttons"><button type="submit" class="primary-button" id="save-music">保存音乐</button></div></form>
  <p id="settings-feedback" class="muted" role="status"></p>
</dialog>`);
const dialog=document.getElementById('settings-dialog');
const audioPlayer=document.getElementById('background-audio');
const playButton=document.getElementById('music-play');
const musicStatus=document.getElementById('music-status');
let youtubePlayer=null, youtubeReady=false, youtubeState=-1, playerEpoch=0, playingSource='', localObjectURL=null;
const settingGoal=document.getElementById('setting-goal');
Array.from(goalSelect.options).forEach(option=>settingGoal.add(option.cloneNode(true)));
const settingTrack=document.getElementById('setting-official-track');
OFFICIAL_TRACKS.forEach(track=>settingTrack.add(new Option(track.name,track.key)));
[['accent',ACCENT_OPTIONS],['focusStyle',FOCUS_OPTIONS]].forEach(([key,options])=>{
  const select=document.getElementById('setting-'+key);
  options.forEach(([value,label])=>select.add(new Option(label,value)));
});
// 主题多了以后按浅色/深色分组，下拉里一眼看得出哪些是深色。
const themeSelect=document.getElementById('setting-theme');
THEME_GROUPS.forEach(([label,options])=>{
  const group=document.createElement('optgroup'); group.label=label;
  options.forEach(([value,name])=>group.appendChild(new Option(name,value)));
  themeSelect.appendChild(group);
});
function fitHeadline() {
  const title=document.getElementById('hero-title');
  const width=title.parentElement.clientWidth;
  title.style.fontSize='';
  const size=parseFloat(getComputedStyle(title).fontSize);
  if(title.scrollWidth>width) title.style.fontSize=Math.max(20,Math.floor(size*width/title.scrollWidth))+'px';
}
/* 自定义强调色直接改根变量；值已经过 #rrggbb 校验，拼进 color-mix 是安全的。 */
const ACCENT_VARS=['--active','--warm','--accent-soft','--accent-light','--hour'];
function applyAccent() {
  const root=document.documentElement.style;
  const colour=preferences.accentCustom;
  if(!colour) { ACCENT_VARS.forEach(name=>root.removeProperty(name)); return; }
  root.setProperty('--active',colour);
  root.setProperty('--warm',colour);
  root.setProperty('--accent-soft','color-mix(in srgb,'+colour+' 13%,transparent)');
  root.setProperty('--accent-light','color-mix(in srgb,'+colour+' 58%,white)');
  root.setProperty('--hour','color-mix(in srgb,'+colour+' 24%,transparent)');
}
function applyAppearance() {
  const root=document.documentElement;
  root.dataset.theme=preferences.theme;
  root.dataset.accent=preferences.accent;
  root.dataset.focus=preferences.focusStyle;
  // 深色主题共用一份墨色和装饰配色，靠这个标记选中，不必逐个主题重复写。
  if(DARK_THEMES.includes(preferences.theme)) root.dataset.dark='';
  else root.removeAttribute('data-dark');
  root.style.setProperty('--decor-strength',String(preferences.decorStrength/100));
  applyAccent();
  document.body.classList.toggle('compact',preferences.compact);
  document.getElementById('hero-title').textContent=preferences.title || DEFAULT_PREFS.title;
  document.getElementById('hero-signature').textContent=preferences.signature;
  document.querySelector('.brand h1').textContent=preferences.brand || DEFAULT_PREFS.brand;
  document.getElementById('footer-note').textContent=preferences.footerNote;
  document.getElementById('music-eyebrow').textContent=preferences.musicEyebrow;
  document.getElementById('goal-heading').textContent=preferences.goalHeading;
  document.getElementById('rhythm-heading').textContent=preferences.rhythmHeading;
  document.querySelector('.music-card').hidden=!preferences.showMusic;
  const cards=document.querySelector('.insight-grid').children;
  cards[0].hidden=!preferences.showGoal; cards[1].hidden=!preferences.showRhythm;
  document.querySelector('.insight-grid').classList.toggle('single-card',preferences.showGoal!==preferences.showRhythm);
  detailCard.hidden=!preferences.showTimeline;
  window.applyDecorSettings?.(preferences.showDecor && preferences.decorStrength>0);
  window.applyWeatherSettings?.(preferences.weatherMode,preferences.weatherCycle);
  window.applySceneSettings?.();
  fitHeadline();
}
new ResizeObserver(fitHeadline).observe(document.querySelector('.headline-scroll'));
/* 一处列出所有可编辑项，读、写、恢复默认都走同一份清单。 */
const EDITABLE_TEXT=['title','signature','brand','tagline','eyebrow','kpiToday','kpiWeek','kpiAvg',
  'goalHeading','rhythmHeading','musicEyebrow','footerNote','methodNote'];
const EDITABLE_CHOICE=['theme','accent','focusStyle','weatherMode'];
const EDITABLE_FLAGS=['compact','showGoal','showRhythm','showTimeline','showDecor','showMusic'];
const EDITABLE_RANGE=['decorStrength','weatherCycle'];
function showFeedback(text) { document.getElementById('settings-feedback').textContent=text; }
function showRangeValues() {
  document.getElementById('decor-strength-value').textContent=document.getElementById('setting-decorStrength').value+'%';
  const seconds=Number(document.getElementById('setting-weatherCycle').value);
  document.getElementById('weather-cycle-value').textContent=seconds<60?seconds+' 秒':(seconds/60).toFixed(1).replace(/\.0$/,'')+' 分钟';
}
function syncSettings() {
  [...EDITABLE_TEXT,...EDITABLE_CHOICE,...EDITABLE_RANGE].forEach(k=>document.getElementById('setting-'+k).value=preferences[k]);
  EDITABLE_FLAGS.forEach(k=>document.getElementById('setting-'+k).checked=preferences[k]);
  document.getElementById('setting-accentCustom').value=preferences.accentCustom || '#0071e3';
  showRangeValues();
  settingGoal.value=goalSelect.value;
  document.getElementById('setting-music-mode').value=preferences.musicMode;
  settingTrack.value=preferences.officialTrack;
  document.getElementById('setting-music-url').value=preferences.musicUrl;
  document.getElementById('setting-music-title').value=preferences.musicTitle;
  document.getElementById('setting-music-file').value='';
  document.getElementById('saved-file-note').textContent=preferences.fileName ? '已保存：'+preferences.fileName+'。可选择新文件替换（最大 50 MB）。' : '选择音频文件（最大 50 MB），下次打开仍可使用。';
  fillLibraryOptions();
  updateMusicFields(); showFeedback('设置保存在当前浏览器。');
  window.syncSceneSettings?.();
}
function openSettings(music=false) {
  syncSettings(); dialog.showModal();
  if(music) document.getElementById('music-form').scrollIntoView({block:'start'});
  // 打开面板时顺手重扫一遍，刚丢进去的文件不用刷新页面就能看到。
  loadMusicLibrary().then(()=>{fillLibraryOptions();renderTrackChips();});
}
document.getElementById('open-settings').onclick=()=>openSettings();
document.getElementById('music-settings').onclick=()=>openSettings(true);
document.getElementById('close-settings').onclick=()=>dialog.close();
document.getElementById('appearance-form').onsubmit=event=>{
  event.preventDefault();
  [...EDITABLE_TEXT,...EDITABLE_CHOICE].forEach(k=>preferences[k]=document.getElementById('setting-'+k).value.trim());
  EDITABLE_FLAGS.forEach(k=>preferences[k]=document.getElementById('setting-'+k).checked);
  EDITABLE_RANGE.forEach(k=>preferences[k]=Number(document.getElementById('setting-'+k).value));
  window.readSceneSettings?.();
  goalSelect.value=settingGoal.value; goalSelect.dispatchEvent(new Event('change'));
  const saved=savePreferences(); applyAppearance();
  showFeedback(saved?'已保存，页面已更新。':'已应用，但浏览器禁止保存设置；关闭页面后会丢失。');
};
['setting-decorStrength','setting-weatherCycle'].forEach(id=>document.getElementById(id).oninput=showRangeValues);
document.getElementById('setting-accentCustom').oninput=event=>{
  preferences.accentCustom=event.target.value; savePreferences(); applyAccent();
};
document.getElementById('clear-accent').onclick=()=>{
  preferences.accentCustom=''; savePreferences(); applyAccent(); showFeedback('已改回预设强调色。');
};
document.getElementById('reset-appearance').onclick=()=>{
  [...EDITABLE_TEXT,...EDITABLE_CHOICE,...EDITABLE_FLAGS,...EDITABLE_RANGE,'accentCustom'].forEach(k=>preferences[k]=DEFAULT_PREFS[k]);
  savePreferences(); applyAppearance(); syncSettings(); showFeedback('已恢复默认外观。音乐和每日目标保持原设置。');
};
const settingLibrary=document.getElementById('setting-library-track');
function fillLibraryOptions() {
  settingLibrary.replaceChildren();
  libraryTracks.forEach(track=>settingLibrary.add(new Option(trackLabel(track.name),track.name)));
  if(preferences.libraryTrack && libraryTracks.some(track=>track.name===preferences.libraryTrack)) settingLibrary.value=preferences.libraryTrack;
  settingLibrary.disabled=!libraryTracks.length;
  document.getElementById('library-note').textContent=libraryTracks.length
    ? '共 '+libraryTracks.length+' 首，读自 ~/.lab_tracker/music/。曲目留在磁盘上，不占浏览器存储。'
    : '把 mp3 / m4a / flac / ogg / wav 放进 ~/.lab_tracker/music/，再点下面的按钮。';
}
function updateMusicFields() {
  const mode=document.getElementById('setting-music-mode').value;
  document.getElementById('music-url-field').hidden=!['youtube','audio'].includes(mode);
  document.getElementById('setting-music-url').required=['youtube','audio'].includes(mode);
  document.getElementById('music-file-field').hidden=mode!=='file';
  document.getElementById('official-track-field').hidden=mode!=='official';
  document.getElementById('library-field').hidden=mode!=='library';
  document.getElementById('official-track-note').textContent=trackByKey(settingTrack.value).by+'。四首都选了允许内嵌播放的官方上传。';
}
function suggestedTitle(mode) {
  return mode==='official' ? trackByKey(settingTrack.value).name
    : mode==='library' ? (settingLibrary.value?trackLabel(settingLibrary.value):'') : '';
}
document.getElementById('setting-music-mode').onchange=event=>{
  updateMusicFields();
  document.getElementById('setting-music-title').value=suggestedTitle(event.target.value);
};
settingTrack.onchange=()=>{
  updateMusicFields();
  if(document.getElementById('setting-music-mode').value==='official') document.getElementById('setting-music-title').value=suggestedTitle('official');
};
settingLibrary.onchange=()=>{
  if(document.getElementById('setting-music-mode').value==='library') document.getElementById('setting-music-title').value=suggestedTitle('library');
};
document.getElementById('rescan-library').onclick=async()=>{
  const button=document.getElementById('rescan-library'); button.disabled=true;
  await loadMusicLibrary();
  fillLibraryOptions(); renderTrackChips(); button.disabled=false;
  showFeedback(libraryTracks.length?'音乐库已重新扫描，共 '+libraryTracks.length+' 首。':'音乐库里还没有可播放的音频文件。');
};
function youtubeId(value) {
  try {
    const url=new URL(value);
    if(url.protocol!=='https:') return null;
    let id=null;
    if(url.hostname==='youtu.be') id=url.pathname.slice(1);
    if(['youtube.com','www.youtube.com','m.youtube.com','www.youtube-nocookie.com'].includes(url.hostname)) id=url.searchParams.get('v') || url.pathname.match(/^\/(?:embed|shorts)\/([^/]+)$/)?.[1];
    return /^[a-zA-Z0-9_-]{11}$/.test(id || '')?id:null;
  } catch { return null; }
}
function httpsAudioURL(value) {
  try { const url=new URL(value); return url.protocol==='https:' && !url.username && !url.password?url.href:null; } catch { return null; }
}
function musicFileDB(writeValue) {
  return new Promise((resolve,reject)=>{
    if(!window.indexedDB) return reject(Error('浏览器不支持保存本机音频，请换用音频链接。'));
    const request=indexedDB.open('small-galaxy-music',1);
    request.onupgradeneeded=()=>request.result.createObjectStore('tracks');
    request.onerror=()=>reject(Error('无法打开本机音乐存储，请检查浏览器权限。'));
    request.onsuccess=()=>{
      const db=request.result;
      const tx=db.transaction('tracks',writeValue?'readwrite':'readonly');
      const op=writeValue?tx.objectStore('tracks').put(writeValue,'selected'):tx.objectStore('tracks').get('selected');
      tx.oncomplete=()=>{const result=op.result; db.close(); resolve(result);};
      tx.onabort=()=>{db.close();reject(Error('音频保存失败，可能已达到浏览器存储上限。'));};
      tx.onerror=()=>{};
    };
  });
}
document.getElementById('music-form').onsubmit=async event=>{
  event.preventDefault();
  const button=document.getElementById('save-music'); button.disabled=true;
  try {
    const mode=document.getElementById('setting-music-mode').value;
    const url=document.getElementById('setting-music-url').value.trim();
    let fileName=preferences.fileName;
    if(mode==='youtube' && !youtubeId(url)) throw Error('请输入有效的 HTTPS YouTube 视频链接。');
    if(mode==='audio' && !httpsAudioURL(url)) throw Error('请输入有效的 HTTPS 音频直链。');
    if(mode==='library' && !settingLibrary.value) throw Error('音乐库还是空的。把音频文件放进 ~/.lab_tracker/music/ 再点"重新扫描音乐库"。');
    if(mode==='file') {
      const file=document.getElementById('setting-music-file').files[0];
      if(file) {
        if(file.size>50*1024*1024) throw Error('请选择不超过 50 MB 的音频。');
        if(!file.size || (!file.type.startsWith('audio/') && !/\.(mp3|wav|ogg|m4a|flac)$/i.test(file.name))) throw Error('请选择可播放的音频文件。');
        await musicFileDB(file); fileName=file.name;
      } else if(!(await musicFileDB())) throw Error('请先选择一个本机音频文件。');
    }
    stopMusic();
    Object.assign(preferences,{musicMode:mode,musicUrl:url,fileName,officialTrack:settingTrack.value,libraryTrack:settingLibrary.value || '',
      musicTitle:document.getElementById('setting-music-title').value.trim() || suggestedTitle(mode) || (mode==='file'?fileName:'我的背景音乐')});
    const saved=savePreferences(); syncMusicControls();
    musicStatus.textContent='音乐已更换，点击播放。';
    showFeedback(saved?'音乐已保存，点击播放即可收听。':'已应用，但浏览器禁止保存设置。');
  } catch(error) { showFeedback(error.message); }
  finally { button.disabled=false; }
};
function syncMusicControls() {
  document.getElementById('track-title').textContent=preferences.musicTitle;
  document.getElementById('music-volume').value=preferences.volume;
  document.getElementById('music-loop').checked=preferences.loop;
  audioPlayer.volume=preferences.volume/100; audioPlayer.loop=preferences.loop;
  renderTrackChips();
}
function stopMusic() {
  playerEpoch++; playingSource=''; youtubeReady=false; youtubeState=-1;
  if(youtubePlayer) { youtubePlayer.destroy(); youtubePlayer=null; }
  audioPlayer.pause(); audioPlayer.removeAttribute('src'); audioPlayer.load();
  if(localObjectURL) { URL.revokeObjectURL(localObjectURL); localObjectURL=null; }
  document.getElementById('youtube-wrap').hidden=true;
  document.getElementById('music-external').hidden=true;
  playButton.textContent='播放'; playButton.disabled=false;
  musicStatus.textContent='点击播放，让音乐陪你一会儿。';
}
let youtubeAPI;
function loadYouTubeAPI() {
  if(window.YT?.Player) return Promise.resolve();
  if(youtubeAPI) return youtubeAPI;
  youtubeAPI=new Promise((resolve,reject)=>{
    const script=document.createElement('script');
    const timer=setTimeout(()=>fail(),12000);
    function fail() { clearTimeout(timer); script.remove(); youtubeAPI=null; reject(Error('在线播放器未能加载，请检查网络或换用本机音乐。')); }
    window.onYouTubeIframeAPIReady=()=>{clearTimeout(timer);resolve();};
    script.onerror=fail; script.src='https://www.youtube.com/iframe_api'; document.head.appendChild(script);
  });
  return youtubeAPI;
}
function setPlayState(playing) { playButton.textContent=playing?'暂停':'播放'; }
const SOURCE_NAMES={file:'本机音乐',library:'本机音乐库',audio:'在线音频'};
audioPlayer.addEventListener('play',()=>{setPlayState(true);musicStatus.textContent='正在播放 · '+(SOURCE_NAMES[preferences.musicMode] || '在线音频');});
audioPlayer.addEventListener('pause',()=>{setPlayState(false);if(audioPlayer.hasAttribute('src')) musicStatus.textContent='已暂停。';});
audioPlayer.addEventListener('ended',()=>{setPlayState(false);musicStatus.textContent='播放结束。';});
audioPlayer.addEventListener('error',()=>{if(audioPlayer.hasAttribute('src')) {
  musicStatus.textContent=preferences.musicMode==='library'
    ? '这个文件放不出来，可能是编码浏览器不支持。换一首，或转成 mp3 再放回音乐库。'
    : '音频无法播放，请检查格式或链接，也可以换用本机文件。';
  setPlayState(false);}});
playButton.onclick=async()=>{
  const mode=preferences.musicMode;
  const key=mode+'|'+preferences.officialTrack+'|'+preferences.libraryTrack+'|'+preferences.musicUrl+'|'+preferences.fileName;
  if(key===playingSource && youtubeReady) { youtubeState===1?youtubePlayer.pauseVideo():youtubePlayer.playVideo(); return; }
  if(key===playingSource && audioPlayer.hasAttribute('src')) {
    if(!audioPlayer.paused) audioPlayer.pause();
    else try {await audioPlayer.play();} catch {musicStatus.textContent='浏览器未能播放，请检查音频格式后再试。';}
    return;
  }
  stopMusic(); const epoch=playerEpoch; playingSource=key;
  playButton.disabled=true; musicStatus.textContent='正在准备音乐…';
  try {
    if(mode==='official' || mode==='youtube') {
      const id=mode==='official'?trackByKey(preferences.officialTrack).id:youtubeId(preferences.musicUrl);
      if(!id) throw Error('请在个性化中选择有效的音乐链接。');
      // 播放器只作为音源存在，移到视口外；卡片上只留一个"在 YouTube 打开"的备用入口。
      const wrap=document.getElementById('youtube-wrap'); wrap.hidden=false;
      const external=document.getElementById('music-external');
      external.href='https://www.youtube.com/watch?v='+id; external.hidden=false;
      await loadYouTubeAPI(); if(epoch!==playerEpoch) return;
      let mount=document.getElementById('youtube-player');
      if(!mount) {mount=document.createElement('div');mount.id='youtube-player';wrap.prepend(mount);}
      youtubePlayer=new YT.Player(mount,{width:'100%',height:'240',videoId:id,
        playerVars:{playsinline:1,origin:location.origin,rel:0},
        events:{onReady:event=>{
          if(epoch!==playerEpoch) return;
          youtubeReady=true; event.target.setVolume(preferences.volume); event.target.playVideo();
          musicStatus.textContent='播放器已就绪；若未开始，请点击播放器中的播放键。';
        },onStateChange:event=>{
          if(epoch!==playerEpoch) return;
          youtubeState=event.data;setPlayState(event.data===1);
          if(event.data===1) musicStatus.textContent='正在播放 · YouTube';
          if(event.data===2) musicStatus.textContent='已暂停。';
          if(event.data===0 && preferences.loop) event.target.playVideo();
          else if(event.data===0) musicStatus.textContent='播放结束。';
        },onError:event=>{if(epoch===playerEpoch) {musicStatus.textContent='该曲目暂时无法内嵌播放（'+event.data+'）。可在 YouTube 打开，或换用本机音频。';setPlayState(false);}},
        onAutoplayBlocked:()=>{musicStatus.textContent='请点击播放器中的播放键开始收听。';}
      }});
    } else {
      let src;
      if(mode==='file') {
        const file=await musicFileDB(); if(epoch!==playerEpoch) return;
        if(!file) throw Error('本机音乐已被浏览器清理，请重新选择文件。');
        src=localObjectURL=URL.createObjectURL(file);
      } else if(mode==='library') {
        if(location.protocol==='file:') throw Error('音乐库需要通过桌面图标打开的本机地址才能播放。');
        if(!preferences.libraryTrack) throw Error('音乐库还是空的。把音频文件放进 ~/.lab_tracker/music/ 再点"重新扫描"。');
        await loadMusicLibrary(); if(epoch!==playerEpoch) return;
        if(!libraryTracks.some(track=>track.name===preferences.libraryTrack)) throw Error('《'+preferences.musicTitle+'》已经不在音乐库里了，请重新选一首。');
        src='/music/'+encodeURIComponent(preferences.libraryTrack);
      } else {src=httpsAudioURL(preferences.musicUrl);if(!src) throw Error('请先设置有效的 HTTPS 音频直链。');}
      audioPlayer.src=src; await audioPlayer.play();
    }
  } catch(error) {if(epoch===playerEpoch) {musicStatus.textContent=error.name==='NotAllowedError'?'请再次点击播放以允许浏览器播放音频。':error.message; playingSource='';}}
  finally {if(epoch===playerEpoch) playButton.disabled=false;}
};
document.getElementById('music-volume').oninput=event=>{
  preferences.volume=Number(event.target.value);audioPlayer.volume=preferences.volume/100;
  if(youtubeReady) youtubePlayer.setVolume(preferences.volume);savePreferences();
};
document.getElementById('music-loop').onchange=event=>{preferences.loop=event.target.checked;audioPlayer.loop=preferences.loop;savePreferences();};
let refreshing=false, lastRefreshAttempt=0;
function calendarDate() {const now=new Date();return [now.getFullYear(),String(now.getMonth()+1).padStart(2,'0'),String(now.getDate()).padStart(2,'0')].join('-');}
let observedCalendarDate=calendarDate();
async function refreshDashboard() {
  if(refreshing) return;
  const button=document.getElementById('refresh-data');
  if(location.protocol==='file:') {button.textContent='请双击桌面图标更新';return;}
  refreshing=true;button.disabled=true;lastRefreshAttempt=performance.now();
  try {
    const response=await fetch('/data',{cache:'no-store',signal:AbortSignal.timeout(5000)});
    if(!response.ok) throw Error('refresh');
    const next=await response.json();
    if(!Array.isArray(next.days) || !next.days.length) throw Error('data');
    const followedToday=selectedDate===TODAY.date;
    if(window.acceptDashboardData) window.acceptDashboardData(next);
    else { DATA=next;TODAY=DATA.days.at(-1); }
    renderStatus();renderKPIs();renderTable();renderGoal();renderRhythm();
    selectDay(!followedToday && DATA.days.some(d=>d.date===selectedDate)?selectedDate:TODAY.date);
    document.getElementById('hero-date').textContent=TODAY.date+' · '+TODAY.weekday+'  /  你的私人科研时间记录';
    window.renderSceneLabels?.();
    window.renderEmptyState?.();
    button.textContent='已更新';
  } catch {button.textContent='更新失败 · 重试';}
  finally {refreshing=false;button.disabled=false;}
}
document.getElementById('refresh-data').onclick=refreshDashboard;
// Timers may be suspended overnight. Resume/focus/BFCache all revalidate data;
// midnight updates do not reload the document, music, preferences or form drafts.
function refreshIfDue(resumed=false) {
  if(document.hidden || location.protocol==='file:') return;
  const date=calendarDate(), rolled=date!==observedCalendarDate;
  observedCalendarDate=date;
  if(rolled || performance.now()-lastRefreshAttempt >= (resumed?5000:60000)) refreshDashboard();
}
setInterval(refreshIfDue,1000);
document.addEventListener('visibilitychange',()=>refreshIfDue(true));
window.addEventListener('focus',()=>refreshIfDue(true));
window.addEventListener('pageshow',()=>refreshIfDue(true));
setTimeout(refreshDashboard,0);
window.addEventListener('pagehide',()=>storage.set('scroll',String(window.scrollY)));
applyAppearance();syncMusicControls();
loadMusicLibrary().then(()=>{fillLibraryOptions();renderTrackChips();});
