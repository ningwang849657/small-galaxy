/* No network requests. Preferences stay in this browser. */
const storage = {
  get(key, fallback) { try { return localStorage.getItem('galaxy.' + key) ?? fallback; } catch { return fallback; } },
  set(key, value) { try { localStorage.setItem('galaxy.' + key, value); } catch {} }
};
const header = document.querySelector('header');
header.insertAdjacentHTML('afterend', `<section class="hero"><div class="eyebrow">SMALL GALAXY · YOUR RESEARCH, IN TIME</div><h2>每一点专注，<br><span>都有自己的光。</span></h2><p>不必让每一天都满格。看见投入的时间，也给思考和休息留一点空间。</p><p class="hero-meta" id="hero-date"></p></section>`);
document.getElementById('hero-date').textContent = TODAY.date + ' · ' + TODAY.weekday + '  /  你的私人科研时间记录';
document.querySelector('.tagline').textContent = '记录日常，看见积累';
document.querySelector('.kpi-row').insertAdjacentHTML('afterend', `
<section class="insight-grid" aria-label="个人节奏">
  <div class="card focus-card"><div class="eyebrow">ONE DAY AT A TIME</div><h2>按自己的节奏。</h2>
    <div class="focus-layout"><div class="ring" id="goal-ring"><div class="ring-inner"><strong id="goal-percent">—</strong><small>今日目标</small></div></div>
    <div><p id="goal-message" class="muted" aria-live="polite"></p><div class="goal-controls"><label for="daily-goal">每日目标</label><select id="daily-goal"><option value="2">2 小时</option><option value="3">3 小时</option><option value="4">4 小时</option><option value="5">5 小时</option><option value="6">6 小时</option><option value="8">8 小时</option></select></div><p class="muted">目标只是参考，不是考核。</p></div></div>
  </div>
  <div class="card"><div class="eyebrow">FIND YOUR RHYTHM</div><h2 style="font-size:20px;margin:0">你的活跃时段</h2><div class="insight-number" id="peak-time">—</div><div class="muted" id="peak-description"></div><div class="hour-bars" id="hour-bars" role="img" aria-label="过去 14 天按小时累计的有效活动时长"></div><div class="hour-labels"><span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>24:00</span></div></div>
</section>`);
const goalSelect = document.getElementById('daily-goal');
const savedGoal = storage.get('goal', '4');
goalSelect.value = ['2','3','4','5','6','8'].includes(savedGoal) ? savedGoal : '4';
function renderGoal() {
  const target = Number(goalSelect.value) * 3600;
  const done = TODAY.active_seconds;
  const percent = Math.round(done / target * 100);
  document.getElementById('goal-ring').style.setProperty('--progress', Math.min(percent,100) + '%');
  document.getElementById('goal-percent').textContent = TODAY.has_data ? percent + '%' : '—';
  document.getElementById('goal-message').textContent = !TODAY.has_data ? '还没有今天的记录，慢慢开始。' : done >= target ? '今日目标已完成。也记得适时休息。' : '已积累 ' + fmtDur(done) + '，距目标还有 ' + fmtDur(target-done) + '。';
}
goalSelect.addEventListener('change', () => { storage.set('goal', goalSelect.value); renderGoal(); });
renderGoal();
const hours = Array(24).fill(0);
DATA.days.forEach(day => day.segments.filter(s => s.kind === 'active').forEach(seg => {
  hours.forEach((_,h) => { hours[h] += Math.max(0, Math.min(seg.end_sec,(h+1)*3600)-Math.max(seg.start_sec,h*3600)); });
}));
const maximum = Math.max(...hours);
const peak = hours.indexOf(maximum);
document.getElementById('peak-time').textContent = maximum ? fmtClock(peak*3600) + ' – ' + fmtClock((peak+1)*3600) : '等待第一点星光';
document.getElementById('peak-description').textContent = maximum ? '近 14 天，这一小时段累计有效活动最多：' + fmtDur(maximum) + '。' : '有了有效活动记录，这里会呈现你的日常节奏。';
hours.forEach((seconds,h) => {
  const bar = document.createElement('span');
  bar.style.height = maximum ? Math.max(5,seconds/maximum*100)+'%' : '5%';
  if (maximum && seconds === maximum) bar.className = 'peak';
  bar.title = fmtClock(h*3600) + '–' + fmtClock((h+1)*3600) + ' · ' + fmtDur(seconds);
  document.getElementById('hour-bars').appendChild(bar);
});
const detailCard = document.getElementById('detail-title').closest('.card');
detailCard.querySelector('.hint').remove();
detailCard.querySelector('.card-head').insertAdjacentHTML('beforeend','<div class="detail-actions"><button id="prev-day" aria-label="前一天">←</button><button id="today-button">今天</button><button id="next-day" aria-label="后一天">→</button></div>');
detailCard.insertAdjacentHTML('beforeend','<div class="session-summary" id="session-summary" aria-live="polite"></div>');
const originalSelectDay = selectDay;
selectDay = function(date) {
  originalSelectDay(date);
  const day = DATA.days.find(d => d.date === date);
  const segments = day.segments.filter(s => s.kind === 'active');
  const longest = Math.max(0,...segments.map(s => s.end_sec-s.start_sec));
  const sustained = segments.filter(s => s.end_sec-s.start_sec >= 25*60).length;
  document.getElementById('session-summary').textContent = isValid(day) ? '最长连续有效活动 ' + fmtDur(longest) + '  ·  ≥25 分钟的活动片段 ' + sustained + ' 段。连续活动按空闲阈值划分，不代表认知专注。' : '没有足够的活动记录，暂不计算连续片段。';
  document.getElementById('prev-day').disabled = date === DATA.days[0].date;
  document.getElementById('next-day').disabled = date === TODAY.date;
};
document.getElementById('prev-day').onclick = () => selectDay(DATA.days[DATA.days.findIndex(d=>d.date===selectedDate)-1].date);
document.getElementById('next-day').onclick = () => selectDay(DATA.days[DATA.days.findIndex(d=>d.date===selectedDate)+1].date);
document.getElementById('today-button').onclick = () => selectDay(TODAY.date);
selectDay(selectedDate);
// Preserve readable axis labels on narrow screens instead of shrinking the SVG.
['bar-chart','timeline'].forEach(id => {
  const chart = document.getElementById(id);
  const scroll = document.createElement('div');
  scroll.className = 'chart-scroll';
  chart.parentNode.insertBefore(scroll,chart); scroll.appendChild(chart);
});
const dataCard = document.getElementById('data-table').closest('.card');
dataCard.insertAdjacentHTML('afterbegin','<div class="card-head"><h2>带走你的记录。</h2><button id="export-csv">导出 CSV ↗</button></div>');
const table = document.getElementById('data-table');
const tableScroll = document.createElement('div'); tableScroll.className = 'table-scroll';
table.parentNode.insertBefore(tableScroll,table); tableScroll.appendChild(table);
document.getElementById('export-csv').onclick = () => {
  const rows = [['日期','星期','记录状态','到达','最近活动或离开','在场秒数','有效活动秒数','娱乐秒数','空闲秒数'],...DATA.days.map(d=>[d.date,d.weekday,isValid(d)?'有活动':d.has_data?'无真实操作':'无记录',d.arrival??'',d.departure??'',d.total_presence_seconds,d.active_seconds,d.fun_seconds,d.idle_seconds])];
  const csv = '\uFEFF' + rows.map(r=>r.map(v=>'"'+String(v).replaceAll('"','""')+'"').join(',')).join('\r\n');
  const url = URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8;'}));
  const a = document.createElement('a'); a.href=url; a.download='小银河-'+TODAY.date+'.csv'; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
};
dataCard.insertAdjacentHTML('afterend','<p class="method-note">关于这些数字：根据键盘、鼠标空闲时间与窗口标题估算电脑活动，不能等同实际科研产出。阅读、讨论和离线思考可能计入空闲；无记录日不参与日均。所有记录保存在本机，导出文件不包含窗口标题。</p>');
// Keep reading position and open table when the locally generated page refreshes.
const savedScroll = Number(storage.get('scroll','0'));
const details = dataCard.querySelector('details');
details.open = storage.get('table','false') === 'true';
if (Number.isFinite(savedScroll)) window.scrollTo(0,savedScroll);
details.addEventListener('toggle',()=>storage.set('table',String(details.open)));
let lastInteraction = Date.now();
['pointerdown','keydown','scroll'].forEach(type=>window.addEventListener(type,()=>{lastInteraction=Date.now();},{passive:true}));
setInterval(()=>{
  if(document.hidden || Date.now()-lastInteraction<15000 || ['SELECT','INPUT','TEXTAREA'].includes(document.activeElement.tagName)) return;
  storage.set('scroll',String(window.scrollY)); location.reload();
},60000);
