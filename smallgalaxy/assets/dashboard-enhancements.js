/* Activity stays local; optional music is handled by dashboard-personalization.js. */
const storage = {
  get(key, fallback) { try { return localStorage.getItem('galaxy.' + key) ?? fallback; } catch { return fallback; } },
  set(key, value) { try { localStorage.setItem('galaxy.' + key, value); return true; } catch { return false; } }
};
const header = document.querySelector('header');
// 头像在生成时就内嵌成 data URI；文件缺失时 AVATAR_SRC 为空串，这里直接省略这块署名。
const authorChip = AVATAR_SRC ? `<a class="author-chip" href="https://github.com/${GITHUB_USER}" target="_blank" rel="noopener noreferrer"><img src="${AVATAR_SRC}" alt="${GITHUB_USER} 的 GitHub 头像" width="34" height="34" decoding="async"><span><strong>${GITHUB_USER}</strong><small>GITHUB</small></span></a>` : '';
header.insertAdjacentHTML('afterend', `<section class="hero"><div class="eyebrow">SMALL GALAXY · YOUR RESEARCH, IN TIME</div><div class="headline-scroll"><h2 id="hero-title">每一点专注，都有自己的光。</h2></div><p id="hero-signature">不必让每一天都满格。看见投入的时间，也给思考和休息留一点空间。</p><div class="hero-foot">${authorChip}<p class="hero-meta" id="hero-date"></p></div></section>`);
document.getElementById('hero-date').textContent = TODAY.date + ' · ' + TODAY.weekday + '  /  你的私人科研时间记录';
document.querySelector('.tagline').textContent = '记录日常，看见积累';
document.querySelector('.kpi-row').insertAdjacentHTML('afterend', `
<section class="insight-grid" aria-label="个人节奏">
  <div class="card focus-card"><div class="eyebrow">ONE DAY AT A TIME</div><h2 id="goal-heading">按自己的节奏。</h2>
    <div class="focus-layout"><div class="ring" id="goal-ring"><div class="ring-inner"><strong id="goal-percent">—</strong><small>今日目标</small></div></div>
    <div><p id="goal-message" class="muted" aria-live="polite"></p><div class="goal-controls"><label for="daily-goal">每日目标</label><select id="daily-goal"><option value="2">2 小时</option><option value="3">3 小时</option><option value="4">4 小时</option><option value="5">5 小时</option><option value="6">6 小时</option><option value="8">8 小时</option></select></div><p class="muted">目标只是参考，不是考核。</p></div></div>
  </div>
  <div class="card"><div class="eyebrow">FIND YOUR RHYTHM</div><h2 id="rhythm-heading" style="font-size:20px;margin:0">你的活跃时段</h2><div class="insight-number" id="peak-time">—</div><div class="muted" id="peak-description"></div><div class="hour-bars" id="hour-bars" role="img" aria-label="过去 14 天按小时累计的有效活动时长"></div><div class="hour-labels"><span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>24:00</span></div></div>
</section>`);
const goalSelect = document.getElementById('daily-goal');
// Half-hour increments, including values outside the original preset list.
goalSelect.textContent = '';
for(let value=.5;value<=12;value+=.5) goalSelect.add(new Option(value+' 小时',String(value)));
const savedGoal = Number(storage.get('goal', '4'));
goalSelect.value = savedGoal>=.5 && savedGoal<=12 && savedGoal*2===Math.floor(savedGoal*2) ? String(savedGoal) : '4';
function renderGoal() {
  const target = Number(goalSelect.value) * 3600;
  const done = TODAY.active_seconds;
  const percent = Math.round(done / target * 100);
  document.getElementById('goal-ring').style.setProperty('--progress', Math.min(percent,100) + '%');
  document.getElementById('goal-percent').textContent = TODAY.has_data ? percent + '%' : '—';
  document.getElementById('goal-message').textContent = !TODAY.has_data ? '还没有今天的记录，慢慢开始。' : done >= target ? '今日目标已完成。也记得适时休息。' : '已积累 ' + fmtDur(done) + '，距目标还有 ' + fmtDur(target-done) + '。';
}
/* 三张时间卡里的"水位"：下深上浅，水面有波动，高度按真实数值相对每日目标涨落。
   高度用 CSS transition 过渡，所以是从当前水位逐渐升到真实值，不会先冲高再回落。 */
const CREST_PERIOD = 120, CREST_SPAN = 4;
function crestPath(amplitude) {
  let d = 'M0,10';
  for (let i = 0; i < CREST_SPAN * 2; i++) {
    const from = i * CREST_PERIOD / 2, to = from + CREST_PERIOD / 2;
    const peak = 10 + (i % 2 ? amplitude : -amplitude);
    d += ` C${from + CREST_PERIOD / 6},${peak} ${to - CREST_PERIOD / 6},${peak} ${to},10`;
  }
  return d + ` L${CREST_SPAN * CREST_PERIOD},20 L0,20 Z`;
}
document.querySelectorAll('.kpi-row .tile').forEach(tile => {
  tile.insertAdjacentHTML('afterbegin',
    `<div class="tile-wave" aria-hidden="true"><div class="wave-fill"><svg class="wave-crest" viewBox="0 0 240 20" preserveAspectRatio="none"><path class="crest-back" d="${crestPath(4.5)}"/><path class="crest-front" d="${crestPath(7)}"/></svg></div></div>`);
});
// 达标≈62% 水位，超额再慢慢往上加：水面始终留在卡片里，看得见波动，也看得出超额了多少。
function waveLevel(ratio) {
  const reached = Math.max(0, Math.min(1, ratio || 0));
  const beyond = Math.max(0, Math.min(1, (ratio || 0) - 1));
  return .62 * reached + .16 * beyond;
}
function renderTileWaves() {
  const goal = Number(goalSelect.value) * 3600;
  const valid = DATA.days.filter(isValid);
  const average = valid.length ? valid.reduce((sum, day) => sum + day.active_seconds, 0) / valid.length : 0;
  const week = DATA.days.slice(7).filter(isValid).reduce((sum, day) => sum + day.active_seconds, 0);
  const ratios = [TODAY.active_seconds / goal, week / (goal * 7), average / goal];
  document.querySelectorAll('.kpi-row .tile').forEach((tile, index) => {
    tile.style.setProperty('--level', waveLevel(ratios[index]).toFixed(4));
  });
}
goalSelect.addEventListener('change', () => { storage.set('goal', goalSelect.value); renderGoal(); renderTileWaves(); });
renderGoal();
const plainKPIs = renderKPIs;
renderKPIs = function () { plainKPIs(); renderTileWaves(); };
renderTileWaves();
function renderRhythm() {
document.getElementById('hour-bars').textContent='';
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
}
renderRhythm();
/* 第一次打开时页面是全空的：14 根柱子、三个卡片全是 0。不解释一句的话，
   用户看不出是"还没开始记录"还是"坏了"。这块只在完全没有数据时出现。 */
document.querySelector('.kpi-row').insertAdjacentHTML('beforebegin',
  '<section class="card first-run" id="first-run" hidden></section>');
window.renderEmptyState = function () {
  const card = document.getElementById('first-run');
  const auto = !LABELS.manual;
  const empty = !DATA.days.some(day => day.has_data);
  card.hidden = !(auto && empty);
  if (card.hidden) return;
  card.replaceChildren();
  const running = DATA.daemon_started || DATA.daemon_status === 'active';
  const heading = document.createElement('h2');
  heading.textContent = running ? '已经开始记录了。' : '还没有开始记录。';
  const lead = document.createElement('p');
  lead.className = 'muted';
  lead.textContent = running
    ? '后台采样正在运行。每 60 秒采一次，第一根柱子大约一分钟后出现，这个页面每分钟自己刷新，放着不用管。'
    : '这个页面只负责展示，数据要靠后台的采样进程收集。在终端里跑下面这行，然后回到这个页面：';
  card.append(document.createElement('div'), heading, lead);
  card.firstChild.className = 'eyebrow';
  card.firstChild.textContent = running ? 'COLLECTING' : 'ONE MORE STEP';
  if (!running) {
    const command = document.createElement('code');
    command.className = 'start-command';
    command.textContent = DATA.start_hint || 'small-galaxy-daemon';
    card.appendChild(command);
  }
  const note = document.createElement('p');
  note.className = 'muted';
  note.textContent = running
    ? '想让它开机自动启动，看项目里的 autostart/ 目录。'
    : '想让它开机自动启动，看项目里的 autostart/ 目录。已经在跑的话，重复启动会被单实例锁挡下，不会重复记录。';
  card.appendChild(note);
};

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
dataCard.insertAdjacentHTML('afterend','<p class="method-note">关于这些数字：来自键盘、鼠标空闲时间与窗口标题的采样，不能等同实际科研产出。阅读、讨论和离线思考可能计入空闲；无记录日不参与日均。所有记录保存在本机，导出文件不包含窗口标题。</p>');
// Keep reading position and open table when the locally generated page refreshes.
const savedScroll = Number(storage.get('scroll','0'));
const details = dataCard.querySelector('details');
details.open = storage.get('table','false') === 'true';
if (Number.isFinite(savedScroll)) window.scrollTo(0,savedScroll);
details.addEventListener('toggle',()=>storage.set('table',String(details.open)));
// The personalization module updates statistics without reloading the music player.
