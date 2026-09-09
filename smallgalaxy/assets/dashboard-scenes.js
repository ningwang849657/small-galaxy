/* Scene names never change what a data source measures. Manual entries stay separate. */
const SCENES = {
  research:{name:'科研', source:'computer', title:'每一点专注，都有自己的光。', signature:DEFAULT_PREFS.signature, eyebrow:'YOUR RESEARCH, IN TIME'},
  work:{name:'工作', source:'computer', title:'认真工作，也认真生活。', signature:'看见今天的投入，也为生活留出空白。', eyebrow:'A LITTLE MORE BALANCE'},
  exercise:{name:'运动', source:'manual', title:'每一次出发，都算数。', signature:'按照自己的节奏动起来。记录每一段运动，也记得好好恢复。', eyebrow:'MOVE AT YOUR OWN PACE'},
  custom:{name:'自定义', source:'manual', title:'把时间，留给你在意的事。', signature:'学习、阅读、创作，或者任何值得记录的小事。', eyebrow:'TIME FOR WHAT MATTERS'}
};
let computerData=DATA;
function currentScene() {
  const preset=SCENES[preferences.scene] || SCENES.research;
  return preferences.scene==='custom' ? {...preset,name:(preferences.customName.trim() || '自定义').slice(0,12),source:preferences.customSource} : preset;
}
const sceneField=document.createElement('fieldset');
sceneField.className='scene-settings';
sceneField.innerHTML=`<legend>记录什么，由你决定</legend><label for="setting-scene">使用场景</label>
  <select id="setting-scene"><option value="research">科研 · 自动记录</option><option value="work">工作 · 自动记录</option><option value="exercise">运动 · 手动记录</option><option value="custom">自定义</option></select>
  <div id="custom-scene-fields"><label for="setting-custom-name">活动名称</label><input id="setting-custom-name" maxlength="24" placeholder="例如：阅读、学习、创作">
  <label for="setting-custom-source">记录方式</label><select id="setting-custom-source"><option value="manual">手动记录起止时间</option><option value="computer">自动记录</option></select></div>
  <p class="muted" id="scene-explanation"></p>
  <label class="motion-setting"><input id="setting-animations" type="checkbox"> 数字与图表动画</label><p class="muted">数值变化时平滑增减；系统开启“减少动态效果”时自动停用。</p>`;
document.getElementById('appearance-form').prepend(sceneField);
let draftScene=preferences.scene;
function updateSceneFields() {
  const key=document.getElementById('setting-scene').value;
  document.getElementById('custom-scene-fields').hidden=key!=='custom';
  const manual=key==='exercise' || (key==='custom' && document.getElementById('setting-custom-source').value==='manual');
  document.getElementById('scene-explanation').textContent=manual
    ? '只统计你亲自填写的活动记录，与电脑采样分开保存。不会把键鼠操作当作运动。'
    : '沿用同一份自动记录，仅切换展示场景；不自动区分科研与工作，也不重复计时。';
}
window.syncSceneSettings=()=>{
  draftScene=preferences.scene;
  document.getElementById('setting-scene').value=preferences.scene;
  document.getElementById('setting-custom-name').value=preferences.customName;
  document.getElementById('setting-custom-source').value=preferences.customSource;
  document.getElementById('setting-animations').checked=preferences.animations;
  updateSceneFields();
};
window.readSceneSettings=()=>{
  preferences.scene=document.getElementById('setting-scene').value;
  preferences.customName=document.getElementById('setting-custom-name').value.trim().slice(0,12) || '自定义';
  preferences.customSource=document.getElementById('setting-custom-source').value;
  preferences.animations=document.getElementById('setting-animations').checked;
};
document.getElementById('setting-scene').onchange=event=>{
  const previous=SCENES[draftScene] || SCENES.research;
  const next=SCENES[event.target.value];
  // Replace preset copy only; retain the user's own title and signature.
  for(const key of ['title','signature']) {
    const input=document.getElementById('setting-'+key);
    if(!input.value.trim() || input.value===previous[key]) input.value=next[key];
  }
  draftScene=event.target.value;updateSceneFields();
};
document.getElementById('setting-custom-source').onchange=updateSceneFields;

/* Interpolate real values; cancel in-flight transitions when newer data arrives. */
const reducedMotion=matchMedia('(prefers-reduced-motion: reduce)');
const numberTransitions=new Map();
function motionEnabled() {return preferences.animations && !reducedMotion.matches;}
function tweenNumber(node,target,draw,initial=0) {
  const previous=numberTransitions.get(node);
  if(previous?.frame) cancelAnimationFrame(previous.frame);
  const from=previous ? previous.current : initial;
  const state={current:from,target,frame:0,draw};numberTransitions.set(node,state);
  node.dataset.targetValue=String(target);
  if(target===null || !motionEnabled() || Math.abs(from-target)<.001) {
    state.current=target;draw(target);return;
  }
  const start=performance.now(),duration=850;
  const begin=Number.isFinite(from)?from:0;
  function frame(now) {
    const progress=Math.min(1,(now-start)/duration);
    state.current=begin+(target-begin)*(1-Math.pow(1-progress,3));
    draw(state.current);
    if(progress<1) state.frame=requestAnimationFrame(frame);
    else {state.frame=0;state.current=target;draw(target);}
  }
  state.frame=requestAnimationFrame(frame);
}
function finishAnimations() {
  numberTransitions.forEach(state=>{cancelAnimationFrame(state.frame);state.frame=0;state.current=state.target;state.draw(state.target);});
  document.querySelectorAll('.bar-a,.bar-f,.bar-i,.tile').forEach(shape=>shape.getAnimations().forEach(animation=>animation.finish()));
}
const plainDuration=setDurParts;
setDurParts=function(node,seconds) {
  const target=seconds==null?null:Math.max(0,seconds);
  const oldTarget=numberTransitions.get(node)?.target;
  node.setAttribute('aria-label',target===null?'暂无记录':fmtDur(target));
  tweenNumber(node,target,value=>{plainDuration(node,value);node.dataset.displaySeconds=value===null?'':String(value);});
  if(motionEnabled() && Number.isFinite(oldTarget) && Number.isFinite(target) && Math.abs(target-oldTarget)>=60) {
    const tile=node.closest('.tile');
    tile?.getAnimations().forEach(animation=>animation.cancel());
    tile?.animate([{boxShadow:'0 0 0 2px var(--active)'},{boxShadow:'0 0 0 0 transparent'}],{duration:950,easing:'ease-out'});
  }
};
const plainGoal=renderGoal;
renderGoal=function() {
  plainGoal();
  const ring=document.getElementById('goal-ring');
  const percent=document.getElementById('goal-percent');
  const target=TODAY.has_data?Math.round(TODAY.active_seconds/(Number(goalSelect.value)*3600)*100):null;
  percent.setAttribute('aria-label',target===null?'暂无记录':`今日目标完成 ${target}%`);
  tweenNumber(percent,target,value=>{
    percent.textContent=value===null?'—':Math.round(value)+'%';
    ring.style.setProperty('--progress',Math.min(100,Math.max(0,value || 0))+'%');
  });
};
const plainBarChart=renderBarChart;
renderBarChart=function() {
  const previous=new Map();
  document.querySelectorAll('#bar-chart .bar-group').forEach(group=>{
    group.querySelectorAll('.bar-a,.bar-f,.bar-i').forEach(shape=>{
      const box=shape.getBBox();previous.set(group.dataset.date+shape.getAttribute('class'),{y:box.y,height:box.height});
    });
  });
  plainBarChart();
  if(!motionEnabled()) return;
  document.querySelectorAll('#bar-chart .bar-group').forEach(group=>{
    group.querySelectorAll('.bar-a,.bar-f,.bar-i').forEach(shape=>{
      const box=shape.getBBox(),old=previous.get(group.dataset.date+shape.getAttribute('class'));
      const scale=old && box.height?old.height/box.height:0;
      const offset=old?old.y+old.height-box.y-box.height:0;
      if(Math.abs(scale-1)<.001 && Math.abs(offset)<.001) return;
      shape.style.transformBox='fill-box';shape.style.transformOrigin='center bottom';
      shape.animate([{transform:`translateY(${offset}px) scaleY(${scale})`},{transform:'translateY(0) scaleY(1)'}],{duration:750,easing:'cubic-bezier(.2,.7,.2,1)'});
    });
  });
};
reducedMotion.addEventListener('change',()=>{document.body.classList.toggle('no-motion',!motionEnabled());window.refreshWeather?.();if(!motionEnabled()) finishAnimations();});

/* Local manual ledger. No changes to the collector or historical computer logs. */
const SESSION_KEY='sessions.v1';
function validSession(entry) {
  return entry && typeof entry.id==='string' && ['exercise','custom'].includes(entry.scene)
    && /^\d{4}-\d{2}-\d{2}$/.test(entry.date) && typeof entry.note==='string'
    && Number.isInteger(entry.start) && Number.isInteger(entry.end) && entry.start>=0 && entry.end<=86400 && entry.end>entry.start;
}
function readSessions() {
  try {const entries=JSON.parse(storage.get(SESSION_KEY,'[]'));return Array.isArray(entries)?entries.filter(validSession):[];} catch {return [];}
}
let sessions=readSessions();
let formSceneKey='';
function manualData(source,scene,entries=sessions) {
  return {...source,days:source.days.map(day=>{
    const entriesForDay=entries.filter(entry=>entry.scene===scene && entry.date===day.date).sort((a,b)=>a.start-b.start);
    const segments=[];
    // Merge overlaps defensively (normal form submissions reject them).
    entriesForDay.forEach(entry=>{
      const last=segments.at(-1);
      if(last && entry.start<=last.end_sec) last.end_sec=Math.max(last.end_sec,entry.end);
      else {
        if(last) segments.push({kind:'idle',start_sec:last.end_sec,end_sec:entry.start});
        segments.push({kind:'active',start_sec:entry.start,end_sec:entry.end});
      }
    });
    const active=segments.filter(s=>s.kind==='active').reduce((sum,s)=>sum+s.end_sec-s.start_sec,0);
    const span=segments.length?segments.at(-1).end_sec-segments[0].start_sec:0;
    return {...day,has_data:entriesForDay.length>0,no_real_activity:false,sample_count:entriesForDay.length,
      arrival:segments.length?fmtClock(segments[0].start_sec):null,departure:segments.length?fmtClock(segments.at(-1).end_sec):null,
      active_seconds:active,fun_seconds:0,idle_seconds:span-active,total_presence_seconds:span,segments};
  })};
}
document.querySelector('.music-card').insertAdjacentHTML('afterend', `<section class="card manual-card" id="manual-card" hidden>
  <div class="card-head"><div><div class="eyebrow">YOUR OWN RECORD</div><h2 id="manual-heading">记录一段活动</h2></div><button id="export-sessions" type="button">导出逐条记录 ↗</button></div>
  <form id="session-form"><input id="session-id" type="hidden"><div class="session-fields">
    <label>日期<input id="session-date" type="date" required></label><label>开始<input id="session-start" type="time" required></label><label>结束<input id="session-end" type="time" required></label>
    <label class="session-note-label">备注<input id="session-note" maxlength="100" placeholder="例如：慢跑、力量训练"></label></div>
    <div class="session-actions"><button type="button" id="cancel-session" hidden>取消修改</button><button type="submit" class="primary-button" id="save-session">添加记录</button><span id="session-feedback" class="muted" role="status"></span></div>
  </form><div id="session-list"></div></section>`);
function resetSessionForm() {
  document.getElementById('session-form').reset();
  document.getElementById('session-id').value='';
  document.getElementById('session-date').value=TODAY.date;
  document.getElementById('save-session').textContent='添加记录';
  document.getElementById('cancel-session').hidden=true;
}
function persistSessions(entries) {
  if(!storage.set(SESSION_KEY,JSON.stringify(entries))) throw Error('浏览器未能保存记录，请检查本地存储权限。');
  sessions=entries;
}
function renderSessions() {
  const list=document.getElementById('session-list');list.replaceChildren();
  const visible=sessions.filter(entry=>entry.scene===preferences.scene && DATA.days.some(day=>day.date===entry.date)).sort((a,b)=>b.date.localeCompare(a.date)||b.start-a.start);
  if(!visible.length) {const p=document.createElement('p');p.className='muted';p.textContent='近 14 天还没有记录。从一小段时间开始吧。';list.appendChild(p);}
  visible.forEach(entry=>{
    const row=document.createElement('div');row.className='session-row';
    const text=document.createElement('div');
    const strong=document.createElement('strong');strong.textContent=entry.date+' · '+fmtClock(entry.start)+' – '+fmtClock(entry.end);
    const sub=document.createElement('span');sub.className='muted';sub.textContent=fmtDur(entry.end-entry.start)+(entry.note?' · '+entry.note:'');
    text.append(strong,sub);
    const buttons=document.createElement('div');buttons.className='session-row-actions';
    const edit=document.createElement('button');edit.textContent='修改';edit.onclick=()=>{
      document.getElementById('session-id').value=entry.id;document.getElementById('session-date').value=entry.date;
      document.getElementById('session-start').value=fmtClock(entry.start);document.getElementById('session-end').value=fmtClock(entry.end);
      document.getElementById('session-note').value=entry.note;document.getElementById('save-session').textContent='保存修改';
      document.getElementById('cancel-session').hidden=false;document.getElementById('session-start').focus();
    };
    const remove=document.createElement('button');remove.textContent='删除';remove.onclick=()=>{
      try {sessions=readSessions();persistSessions(sessions.filter(item=>item.id!==entry.id));resetSessionForm();applySceneSettings();
        const feedback=document.getElementById('session-feedback');feedback.textContent='已删除。';
        const undo=document.createElement('button');undo.textContent='撤销';undo.onclick=()=>{
          try {sessions=readSessions();if(sessions.some(item=>item.scene===entry.scene && item.date===entry.date && entry.start<item.end && entry.end>item.start)) throw Error('记录与现有时段重叠，请手动恢复。');
            persistSessions([...sessions,entry]);applySceneSettings();feedback.textContent='已恢复。';
          } catch(error) {feedback.textContent=error.message;}
        };feedback.append(' ',undo);
      } catch(error) {document.getElementById('session-feedback').textContent=error.message;}
    };
    buttons.append(edit,remove);row.append(text,buttons);list.appendChild(row);
  });
}
document.getElementById('cancel-session').onclick=resetSessionForm;
document.getElementById('session-form').onsubmit=event=>{
  event.preventDefault();const feedback=document.getElementById('session-feedback');
  try {
    if(currentScene().source!=='manual') throw Error('请先切换到手动记录场景。');
    sessions=readSessions();
    const toSeconds=value=>{const [h,m]=value.split(':').map(Number);return h*3600+m*60;};
    const entry={id:document.getElementById('session-id').value || crypto.randomUUID(),scene:preferences.scene,
      date:document.getElementById('session-date').value,start:toSeconds(document.getElementById('session-start').value),end:toSeconds(document.getElementById('session-end').value),note:document.getElementById('session-note').value.trim()};
    if(!validSession(entry)) throw Error('结束时间需要晚于开始时间，跨天活动请分成两条记录。');
    if(!computerData.days.some(day=>day.date===entry.date)) throw Error('请选择最近 14 天内的日期。');
    const remaining=sessions.filter(item=>item.id!==entry.id);
    if(remaining.some(item=>item.scene===entry.scene && item.date===entry.date && entry.start<item.end && entry.end>item.start)) throw Error('这段时间与已有记录重叠，请修改原记录。');
    persistSessions([...remaining,entry]);resetSessionForm();applySceneSettings();feedback.textContent='已保存，统计已更新。';
  } catch(error) {feedback.textContent=error.message;}
};
const originalSceneSelectDay=selectDay;
selectDay=function(date) {
  originalSceneSelectDay(date);
  if(currentScene().source==='manual') {
    const day=DATA.days.find(d=>d.date===date);
    const entries=sessions.filter(s=>s.scene===preferences.scene && s.date===date);
    const longest=Math.max(0,...entries.map(s=>s.end-s.start));
    document.getElementById('session-summary').textContent=entries.length?`手动记录 ${entries.length} 段 · 最长一段 ${fmtDur(longest)} · 间隔不计入活动时长。`:'这一天尚未添加活动记录。';
    if(!day.has_data) document.getElementById('detail-empty').textContent='添加起止时间后，这里会显示你的活动时间线。';
  }
};
window.renderSceneLabels=function() {
  const scene=currentScene(),manual=scene.source==='manual';
  const activity=manual?scene.name:'有效'+scene.name;
  LABELS={active:activity,idle:manual?'活动间隔':'空闲 / 中断',fun:'娱乐',arrival:manual?'开始':'到达',departure:manual?'结束':'离开',presence:manual?'首尾跨度':'总在场',manual};
  // 自己写过的文案一律优先；留空的才按场景自动生成。
  const chosen=(own,auto)=>own && own.trim()?own:auto;
  [['kpiToday','今日'+activity+'时间'],['kpiWeek','近 7 天'+activity+'时间'],['kpiAvg','近 14 天日均'+activity+'时间']]
    .forEach(([key,auto],index)=>{document.querySelectorAll('.tile .label')[index].textContent=chosen(preferences[key],auto);});
  document.querySelector('.hero .eyebrow').textContent=chosen(preferences.eyebrow,'SMALL GALAXY · '+scene.eyebrow);
  document.querySelector('.tagline').textContent=chosen(preferences.tagline,scene.name+' · 最近 14 天');
  document.getElementById('hero-date').textContent=TODAY.date+' · '+TODAY.weekday+'  /  '+scene.name+'时间记录';
  const legend=document.querySelectorAll('.legend .key');
  [activity,LABELS.fun,LABELS.idle].forEach((label,index)=>{legend[index].lastChild.textContent=label;});
  legend[1].hidden=manual;
  const heads=document.querySelectorAll('#data-table th');
  [LABELS.arrival,LABELS.departure,LABELS.presence,activity,LABELS.fun,LABELS.idle].forEach((label,index)=>heads[index+1].textContent=label);
  document.getElementById('bar-chart').setAttribute('aria-label','最近 14 天'+scene.name+'时长与'+LABELS.idle+'堆叠柱状图');
  document.getElementById('timeline').setAttribute('aria-label','选中日期的'+scene.name+'活动时间线');
  document.getElementById('manual-heading').textContent='记录一段'+scene.name;
  document.querySelector('.method-note').textContent=chosen(preferences.methodNote,manual
    ? '这些数字来自你手动填写的起止时间，不是传感器测量。活动间隔不计入总时长，无记录日不参与日均。记录保存在当前浏览器，请使用 CSV 导出备份；清理站点数据会清除手动记录。自定义场景更名不会删除或重新分类已有记录。'
    : '这些数字来自键盘、鼠标空闲时间与窗口标题的采样，不能等同实际'+scene.name+'成果。离线思考和讨论可能计入空闲，无记录日不参与日均。科研与工作共用同一份自动记录，不会自动分类或重复计时。所有原始记录保存在本机。');
  if(manual) {
    document.getElementById('status-pill').className='pill na';document.getElementById('status-text').textContent='手动记录';
    document.getElementById('meta-line').textContent='手动记录 · 最近 14 天 · 浏览器本地保存 · 修改后即时更新';
  }
};
window.acceptDashboardData=function(next) {
  const previousToday=TODAY.date;
  computerData=next;
  DATA=currentScene().source==='manual'?manualData(computerData,preferences.scene):computerData;
  TODAY=DATA.days.at(-1);renderSceneLabels();renderSessions();
  const dateField=document.getElementById('session-date');
  dateField.min=DATA.days[0].date;dateField.max=TODAY.date;
  // Advance a pristine form, but keep the date of a half-written activity.
  const draft=['session-start','session-end','session-note'].some(id=>document.getElementById(id).value);
  if(!draft && (!dateField.value || dateField.value===previousToday)) dateField.value=TODAY.date;
};
window.applySceneSettings=function() {
  document.body.classList.toggle('no-motion',!motionEnabled());
  window.refreshWeather?.();
  if(!motionEnabled()) finishAnimations();
  const oldDate=selectedDate;
  acceptDashboardData(computerData);
  document.getElementById('manual-card').hidden=currentScene().source!=='manual';
  const nextFormKey=preferences.scene+'|'+currentScene().source;
  if(formSceneKey!==nextFormKey) {resetSessionForm();document.getElementById('session-feedback').textContent='';formSceneKey=nextFormKey;}
  document.getElementById('session-date').min=DATA.days[0].date;document.getElementById('session-date').max=TODAY.date;
  if(!document.getElementById('session-date').value) resetSessionForm();
  renderStatus();renderSceneLabels();renderKPIs();renderGoal();renderRhythm();renderTable();
  window.renderEmptyState?.();
  window.renderSpirits?.();
  window.renderFocusStars?.();
  selectDay(DATA.days.some(day=>day.date===oldDate)?oldDate:TODAY.date);
  document.getElementById('peak-description').textContent+=currentScene().source==='manual'?' 按手动记录统计。':'';
};
// Exports identify the source, so manual exercise cannot be confused with computer activity.
function downloadSceneCSV(rows,name) {
  const cell=value=>'"'+String(value).replace(/^[=+@-]/,"'$&").replaceAll('"','""')+'"';
  const url=URL.createObjectURL(new Blob(['\uFEFF'+rows.map(row=>row.map(cell).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8;'}));
  const link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
document.getElementById('export-sessions').onclick=()=>{
  const rows=[['日期','开始','结束','时长秒数','备注','场景','数据来源'],...readSessions().filter(entry=>entry.scene===preferences.scene)
    .sort((a,b)=>a.date.localeCompare(b.date)||a.start-b.start)
    .map(entry=>[entry.date,fmtClock(entry.start),fmtClock(entry.end),entry.end-entry.start,entry.note,currentScene().name,'手动记录'])];
  downloadSceneCSV(rows,'小银河-逐条记录-'+preferences.scene+'-'+TODAY.date+'.csv');
};
document.getElementById('export-csv').onclick=()=>{
  const scene=currentScene();
  const rows=[['日期','星期','记录状态','开始','结束','首尾跨度秒数',scene.name+'活动秒数','娱乐秒数','间隔或空闲秒数','场景','数据来源'],
    ...DATA.days.map(day=>[day.date,day.weekday,isValid(day)?'有活动':'无记录',day.arrival || '',day.departure || '',day.total_presence_seconds,day.active_seconds,day.fun_seconds,day.idle_seconds,scene.name,scene.source==='manual'?'手动记录':'自动记录'])];
  downloadSceneCSV(rows,'小银河-'+preferences.scene+'-'+TODAY.date+'.csv');
};
window.addEventListener('storage',event=>{if(event.key==='galaxy.'+SESSION_KEY) {sessions=readSessions();applySceneSettings();}});
applySceneSettings();
