/* Local, decorative artwork: an AI-painted forest panorama + procedural SVG/CSS.
   All assets are embedded. Weather is an atmospheric simulation, not live data. */
const decorRand = mulberry32(70915);


function kodama(scale, wobble) {
  // 木灵：大圆头 + 三个填页面底色的凹洞 + 站得住的身子和短手短腿。
  // 身子要够粗、面孔洞要够小，否则在这个尺寸下只剩一颗骷髅头。
  const g = el('g', { class: 'kodama', transform: 'scale(' + scale.toFixed(2) + ')' });
  g.appendChild(el('rect', { x: -2.2, y: 2, width: 1.9, height: 4.4, rx: .9, class: 'spirit-body' }));
  g.appendChild(el('rect', { x: .3, y: 2, width: 1.9, height: 4.4, rx: .9, class: 'spirit-body' }));
  g.appendChild(el('rect', { x: -4.4, y: -6.4, width: 8.8, height: 9.6, rx: 4, class: 'spirit-body' }));
  g.appendChild(el('rect', { x: -7.4, y: -5.2, width: 3.1, height: 6.6, rx: 1.5, class: 'spirit-body' }));
  g.appendChild(el('rect', { x: 4.3, y: -5.2, width: 3.1, height: 6.6, rx: 1.5, class: 'spirit-body' }));
  const head = el('g', { class: 'kodama-head' });
  head.appendChild(el('ellipse', { cx: 0, cy: -13.4, rx: 8.6, ry: 8.9, class: 'spirit-body' }));
  head.appendChild(el('ellipse', { cx: -2.9, cy: -14.8, rx: 1.35, ry: 1.7, class: 'spirit-face' }));
  head.appendChild(el('ellipse', { cx: 2.9, cy: -14.8, rx: 1.35, ry: 1.7, class: 'spirit-face' }));
  head.appendChild(el('ellipse', { cx: 0, cy: -10.4, rx: 1.15, ry: 1.4, class: 'spirit-face' }));
  head.style.animationDuration = wobble.toFixed(2) + 's';
  head.style.animationDelay = '-' + (decorRand() * wobble).toFixed(2) + 's';
  g.appendChild(head);
  return g;
}

/* 页面上只留一块画板：木灵和光尘从原来那条顶栏迁进雨林。
   两块等重的画面会互相抵消，也把数据挤出首屏，所以顶栏那张单独的画卷取消。 */
function buildSpiritLayer() {
  const W = 1440, H = 480;
  const band = el('svg', { id: 'forest-band', viewBox: '0 0 ' + W + ' ' + H, preserveAspectRatio: 'xMidYMax slice', 'aria-hidden': 'true' });
  const spirits = el('g', { class: 'spirits' });
  // 蹲在画面下缘的林床上，靠两侧站；中间那片留给标题。
  [[96, 430, .92], [214, 446, 1.15], [368, 436, .82], [1058, 440, .86], [1208, 448, 1.1], [1348, 433, .95]].forEach(([x, y, s]) => {
    const seat = el('g', { transform: 'translate(' + x + ' ' + y + ')' });
    seat.appendChild(kodama(s, 3.4 + decorRand() * 3.2));
    spirits.appendChild(seat);
  });
  band.appendChild(spirits);
  const motes = el('g', { class: 'motes' });
  for (let i = 0; i < 30; i++) {
    const mote = el('circle', { cx: (decorRand() * W).toFixed(1), cy: (150 + decorRand() * 310).toFixed(1), r: (0.7 + decorRand() * 1.5).toFixed(2) });
    mote.style.animationDuration = (5 + decorRand() * 7).toFixed(2) + 's';
    mote.style.animationDelay = '-' + (decorRand() * 9).toFixed(2) + 's';
    motes.appendChild(mote);
  }
  band.appendChild(motes);
  return band;
}

/* ---------- Hero：东南亚雨林 + 降雨 ---------- */
function leafBlade(len, width) {
  return 'M0,0 C' + (len * .3).toFixed(1) + ',' + (-width).toFixed(1) + ' ' + (len * .72).toFixed(1) + ',' + (-width * .82).toFixed(1) +
    ' ' + len.toFixed(1) + ',0 C' + (len * .7).toFixed(1) + ',' + (width * .5).toFixed(1) + ' ' + (len * .3).toFixed(1) + ',' + (width * .44).toFixed(1) + ' 0,0Z';
}

/* 龟背竹：中肋 + 两侧逐渐上扬、逐渐变短的裂叶，剪影上就读成一片开裂的大叶。 */
function monstera(len) {
  const g = el('g', { class: 'leaf' });
  g.appendChild(el('path', { class: 'leaf-rib', d: 'M0,0 C' + (len * .05).toFixed(1) + ',' + (-len * .35).toFixed(1) + ' ' + (len * .035).toFixed(1) + ',' + (-len * .72).toFixed(1) + ' 0,' + (-len).toFixed(1) }));
  const count = 9;
  for (const side of [-1, 1]) {
    for (let i = 0; i < count; i++) {
      const t = i / (count - 1);
      const y = -len * .11 - t * len * .8;
      const blade = (len * .40 + decorRand() * len * .05) * (1 - .58 * t * t);
      const thick = len * .072 * (1 - .45 * t);
      const angle = 18 + t * 48;
      g.appendChild(el('path', { d: leafBlade(blade, thick), transform: 'translate(0 ' + y.toFixed(1) + ') scale(' + side + ' 1) rotate(' + (-angle).toFixed(1) + ')' }));
    }
  }
  return g;
}

/* 棕榈叶：更长的叶轴，两侧许多细长小叶。 */
function palmFrond(len) {
  const g = el('g', { class: 'leaf' });
  g.appendChild(el('path', { class: 'leaf-rib', d: 'M0,0 C' + (len * .1).toFixed(1) + ',' + (-len * .4).toFixed(1) + ' ' + (len * .09).toFixed(1) + ',' + (-len * .76).toFixed(1) + ' 0,' + (-len).toFixed(1) }));
  const count = 15;
  for (const side of [-1, 1]) {
    for (let i = 0; i < count; i++) {
      const t = i / (count - 1);
      const y = -len * .08 - t * len * .88;
      const blade = (len * .30 + decorRand() * len * .04) * (1 - .72 * t * t);
      const angle = 26 + t * 40;
      g.appendChild(el('path', { d: leafBlade(blade, len * .028), transform: 'translate(0 ' + y.toFixed(1) + ') scale(' + side + ' 1) rotate(' + (-angle).toFixed(1) + ')' }));
    }
  }
  return g;
}

/* 垂下的藤蔓，给雨林一点纵向的层次。 */
function vine(length, leaves) {
  const g = el('g', { class: 'leaf' });
  g.appendChild(el('path', { class: 'leaf-rib', d: 'M0,0 C18,' + (length * .34).toFixed(1) + ' -14,' + (length * .68).toFixed(1) + ' 6,' + length.toFixed(1) }));
  for (let i = 0; i < leaves; i++) {
    const t = (i + 1) / (leaves + 1);
    const x = 18 * Math.sin(t * 3.1) - 4 * t;
    g.appendChild(el('ellipse', { cx: x.toFixed(1), cy: (length * t).toFixed(1), rx: 9, ry: 4.6, transform: 'rotate(' + (i % 2 ? 24 : -24) + ' ' + x.toFixed(1) + ' ' + (length * t).toFixed(1) + ')' }));
  }
  return g;
}

/* Broad aroid leaves and fine rattan palms, rather than identical cut-out trees. */
function aroidLeaf(length) {
  const g = el('g', {class:'leaf aroid-leaf'});
  const blade = el('path', {d:'M0,0 C-100,-26 -78,-151 0,-128 C78,-151 100,-26 0,0Z', fill:'url(#leaf-shade)', transform:'scale('+length/150+')'});
  g.appendChild(blade);
  const veins = el('g', {transform:'scale('+length/150+')', class:'leaf-veins'});
  veins.appendChild(el('path', {d:'M0,0 Q9,-74 0,-128'}));
  for(let i=0;i<5;i++) {
    const y=-22-i*18;
    veins.appendChild(el('path', {d:`M3,${y} Q-22,${y-25} ${-45+Math.abs(i-2)*8},${y-26} M3,${y} Q26,${y-25} ${45-Math.abs(i-2)*8},${y-26}`}));
  }
  g.appendChild(veins);
  g.appendChild(el('ellipse', {cx:14,cy:-53,rx:2,ry:3.2,class:'leaf-bead'}));
  return g;
}

function place(node, x, y, rotate, scale) {
  const g = el('g', { transform: 'translate(' + x + ' ' + y + ') rotate(' + rotate + ') scale(' + scale + ')' });
  g.appendChild(node);
  return g;
}

function buildRainforest() {
  const scene = document.createElement('div');
  scene.className = 'rain-scene';
  scene.setAttribute('aria-hidden', 'true');
  const backdropSource='__RAINFOREST_ART__';
  if(backdropSource) {
    const backdrop=document.createElement('img');backdrop.className='rainforest-backdrop';
    backdrop.src=backdropSource;backdrop.alt='';backdrop.decoding='async';scene.appendChild(backdrop);
  }

  // 构图沿上下两条边展开、中间给标题留空：窄屏时 slice 只保留中间一竖条，
  // 所以每条边上的叶子要铺满整个宽度，任何裁法都还看得出是雨林。
  const W = 1440, H = 300;
  const foliage = el('svg', { class: 'rain-foliage', viewBox: '0 0 ' + W + ' ' + H, preserveAspectRatio: 'xMidYMid slice' });
  const definitions = el('defs', {});
  const shade = el('linearGradient', {id:'leaf-shade', x1:0,y1:0,x2:1,y2:1});
  shade.append(el('stop',{offset:'0%', 'stop-color':'var(--decor-jungle)'}),el('stop',{offset:'100%','stop-color':'var(--decor-jungle-deep)'}));
  definitions.appendChild(shade);foliage.appendChild(definitions);
  const trunks = el('g', {class:'rain-trunks'});
  [30,185,1180,1360].forEach((x,i)=>trunks.appendChild(el('path', {d:`M${x},-30 Q${x+25},90 ${x+8},238 L${x+62},300 L${x-50},300 Q${x-14},210 ${x-22},-30Z`,opacity:.5+i*.1})));
  foliage.appendChild(trunks);
  const back = el('g', { class: 'foliage-back' }), front = el('g', { class: 'foliage-front' });
  for (let i = 0; i < 18; i++) {
    back.appendChild(el('ellipse', { cx: (i * 86 + decorRand() * 56).toFixed(1), cy: (10 + decorRand() * 40).toFixed(1), rx: (64 + decorRand() * 50).toFixed(1), ry: (28 + decorRand() * 22).toFixed(1) }));
  }
  for (let i = 0; i < 11; i++) {
    back.appendChild(place(palmFrond(112 + decorRand() * 46), i * 140 + decorRand() * 60, H + 16, (decorRand() * 44 - 22).toFixed(1), 1));
  }
  for (let i = 0; i < 8; i++) {
    back.appendChild(place(palmFrond(96 + decorRand() * 40), 40 + i * 190 + decorRand() * 50, -14, (162 + decorRand() * 36).toFixed(1), 1));
  }
  // 上缘垂下的龟背竹与棕榈。
  [[-10, -22, 148, 1], [186, -30, 166, .82], [430, -24, 154, .7], [712, -28, 178, .66], [988, -26, 196, .74], [1240, -30, 188, .86], [1436, -20, 206, .98]].forEach(([x, y, rot, s]) => {
    front.appendChild(place(monstera(150), x, y, rot, s));
  });
  // 下缘向上生长的一排，压住卡片交界处。
  [[24, H + 18, -12, 1], [214, H + 24, 14, .74], [452, H + 20, -9, .66], [706, H + 26, 11, .6], [962, H + 22, -13, .68], [1206, H + 24, 10, .8], [1418, H + 18, -8, .96]].forEach(([x, y, rot, s]) => {
    front.appendChild(place(monstera(146), x, y, rot, s));
  });
  [[92, -12, 104], [356, -16, 128], [648, -10, 86], [900, -14, 116], [1148, -12, 96], [1372, -16, 122]].forEach(([x, y, len]) => {
    front.appendChild(place(vine(len, 5), x, y, 0, 1));
  });
  [[65,320,-25,1.2],[138,331,18,.8],[1266,323,-16,.85],[1380,330,22,1.3]].forEach(([x,y,r,s])=>front.appendChild(place(aroidLeaf(150),x,y,r,s)));
  [...foliage.querySelectorAll('.leaf'), ...front.querySelectorAll('.leaf'), ...back.querySelectorAll('.leaf')].forEach((leaf,i)=>{
    leaf.style.animationDelay=(-i*.71)+'s';leaf.style.animationDuration=(6+i%5)+'s';
  });
  foliage.append(back, front);
  scene.appendChild(foliage);

  for (let i = 0; i < 3; i++) {
    const mist = document.createElement('div');
    mist.className = 'rain-mist';
    mist.style.animationDuration = (46 + i * 22) + 's';
    mist.style.animationDelay = '-' + (i * 19) + 's';
    mist.style.top = (10 + i * 34) + '%';
    scene.appendChild(mist);
  }
  // 三层雨：越近的越快、越长、越明显，靠差速拉开纵深。
  [[46, 'rain-far', 1.2, 9], [38, 'rain-mid', .72, 21], [26, 'rain-near', .44, 38]].forEach(([count, cls, speed, length]) => {
    const layer = document.createElement('div');
    layer.className = 'rain-layer ' + cls;
    for (let i = 0; i < count; i++) {
      const drop = document.createElement('span');
      drop.style.left = (decorRand() * 106 - 3).toFixed(2) + '%';
      drop.style.setProperty('--len', (length + decorRand() * length*.6).toFixed(0) + 'px');
      drop.style.animationDuration = (speed + decorRand() * speed*.35).toFixed(2) + 's';
      drop.style.animationDelay = '-' + (decorRand() * 1.4).toFixed(2) + 's';
      drop.style.opacity = (.3 + decorRand() * .55).toFixed(2);
      layer.appendChild(drop);
    }
    scene.appendChild(layer);
  });
  const splashes = document.createElement('div');
  splashes.className = 'rain-splashes';
  for (let i = 0; i < 30; i++) {
    const ripple = document.createElement('span');
    ripple.style.left = (decorRand() * 100).toFixed(2) + '%';
    ripple.style.bottom = (decorRand() * 28).toFixed(2) + 'px';
    ripple.style.animationDuration = (1.6 + decorRand() * 1.5).toFixed(2) + 's';
    ripple.style.animationDelay = '-' + (decorRand() * 3).toFixed(2) + 's';
    splashes.appendChild(ripple);
  }
  scene.appendChild(splashes);
  const ground = document.createElement('div');ground.className = 'wet-ground';
  const clouds = document.createElement('div');clouds.className = 'rain-clouds';
  const curtain = document.createElement('div');curtain.className = 'rain-curtain';
  const drips = document.createElement('div');drips.className = 'canopy-drips';
  for(let i=0;i<16;i++) {
    const bead=document.createElement('span');
    bead.style.left=(4+decorRand()*92)+'%';bead.style.top=(6+decorRand()*22)+'%';
    bead.style.animationDuration=(2.2+decorRand()*3.6)+'s';bead.style.animationDelay=(-decorRand()*6)+'s';
    drips.appendChild(bead);
  }
  // Clouds arrive before rain; wet reflections and leaf drip persist after it.
  const veil = document.createElement('div');
  veil.className = 'storm-veil';
  const wash = document.createElement('div');
  wash.className = 'sun-wash';
  const shafts = document.createElement('div');shafts.className = 'sun-shafts';
  for(let i=0;i<5;i++) {
    const ray=document.createElement('span');ray.style.left=(56+i*8)+'%';
    ray.style.width=(22+i%3*19)+'px';ray.style.animationDelay=(-i*1.8)+'s';shafts.appendChild(ray);
  }
  scene.append(clouds, ground, curtain, drips, veil, wash, shafts, buildSpiritLayer());
  const hero=document.querySelector('.hero');hero.prepend(scene);
  // 品牌名、状态徽章和按钮搬进画板，和标题共用同一张画：整页只剩一个画面。
  scene.after(header);
  const travel=new ResizeObserver(()=>scene.style.setProperty('--rain-travel',Math.ceil(scene.clientHeight*1.4)+'px'));
  travel.observe(scene);
  return scene;
}

/* Equatorial rainforest day, compressed in time. Not a forecast or a physical model.
   Reference: Meteorological Service Singapore, "Climate of Singapore".
   Cloud build-up precedes a convective shower; fog, leaf drip and wetness lag it.
   Fixed-duration particle animations never restart as the weather changes. */
const WEATHER_FIELDS=['rain','sun','cloud','mist','wind','wet','drip'];
const WEATHER_KEYFRAMES = [
  // phase, rain, sun, cloud, mist, wind, wet surface, canopy drip
  [0,    0, .12, .26, .82, .10, .60, .16],
  [.12,  0, .70, .18, .30, .16, .36, .08],
  [.24,  0, .24, .82, .22, .55, .28, .02],
  [.30,.35, .02, .95, .32, .86, .62, .32],
  [.36,  1,   0,    1,.52,  1,   1, .85],
  [.45,.92,   0, .96, .60, .85,  1,   1],
  [.56,.34, .03, .75, .78, .40,  1,   1],
  [.64,  0, .16, .54,   1, .18, .94, .86],
  [.74,  0, .74, .24, .72, .12, .82, .64],
  [.86,  0,   1, .12, .32, .14, .56, .30],
  [.94,  0, .34, .18, .52, .12, .48, .12],
  [1,    0, .12, .26, .82, .10, .60, .16]
];
function weatherAt(phase) {
  phase=((phase%1)+1)%1;
  for (let i = 1; i < WEATHER_KEYFRAMES.length; i++) {
    const to = WEATHER_KEYFRAMES[i], from=WEATHER_KEYFRAMES[i-1];
    if (phase > to[0]) continue;
    const t = (phase-from[0])/(to[0]-from[0]);
    const eased = t * t * (3 - 2 * t);
    return Object.fromEntries(WEATHER_FIELDS.map((field,index)=>[field,from[index+1]+(to[index+1]-from[index+1])*eased]));
  }
}
const FIXED_WEATHER = {
  drizzle:{rain:.3,sun:.06,cloud:.7,mist:.6,wind:.25,wet:.8,drip:.65},
  storm:{rain:1,sun:0,cloud:1,mist:.5,wind:1,wet:1,drip:1},
  clear:{rain:0,sun:1,cloud:.12,mist:.35,wind:.12,wet:.6,drip:.32}
};
const rainScene = buildRainforest();

let weatherTimer = 0, weatherStart = performance.now();
let weatherMode = 'cycle', weatherCycle = 96;
// 三层雨依次加入：小雨只有远处细丝，暴雨时三层全开，读起来就是雨越下越大。
const LAYER_RANGE = [['far', 0, .34], ['mid', .22, .62], ['near', .5, .95]];
function paintWeather(climate) {
  const {rain,sun,wind}=climate;
  const style = rainScene.style;
  LAYER_RANGE.forEach(([name, from, to]) => {
    style.setProperty('--rain-' + name, Math.max(0, Math.min(1, (rain - from) / (to - from))).toFixed(3));
  });
  style.setProperty('--storm', (rain * rain).toFixed(3));
  style.setProperty('--sun', sun.toFixed(3));
  for(const field of ['cloud','mist','wet','drip']) style.setProperty('--'+field,climate[field].toFixed(3));
  const gust=.7+.3*Math.sin(performance.now()/2100)+.1*Math.sin(performance.now()/770);
  style.setProperty('--wind-tilt',(wind*gust*4).toFixed(2)+'deg');
  style.setProperty('--rain-slant',(-2-wind*gust*13).toFixed(2)+'deg');
  rainScene.dataset.weather=rain>.7?'storm':rain>.05?'rain':sun>.6?'sun':'mist';
}
function stepWeather() {
  const phase = ((performance.now() - weatherStart) / (weatherCycle * 1000)) % 1;
  paintWeather(weatherMode==='cycle'?weatherAt(phase):FIXED_WEATHER[weatherMode]);
}
function runWeather() {
  clearInterval(weatherTimer); weatherTimer = 0;
  const still = document.body.classList.contains('no-motion') || matchMedia('(prefers-reduced-motion: reduce)').matches;
  const paused = document.hidden || document.body.classList.contains('no-decor');
  document.body.classList.toggle('decor-paused',paused);
  if (still) {paintWeather(weatherMode==='cycle'?weatherAt(.74):FIXED_WEATHER[weatherMode]);return;}
  stepWeather();
  if(!paused) weatherTimer = setInterval(stepWeather, 160);
}
// 由 applyAppearance() 驱动：装饰画是纯外观开关，不影响任何统计。
window.applyDecorSettings = show => {
  document.body.classList.toggle('no-decor', !show);
  runWeather();
};
// 场景模块切换 no-motion 之后调一次，免得动画关掉了计时器还在空转。
window.refreshWeather = runWeather;
window.applyWeatherSettings = (mode, cycleSeconds) => {
  if (mode !== weatherMode) weatherStart = performance.now();
  weatherMode = mode==='cycle' || FIXED_WEATHER[mode]?mode:'cycle';
  weatherCycle = Math.max(20, Math.min(600, Number(cycleSeconds) || 96));
  runWeather();
};
document.addEventListener('visibilitychange',runWeather);
runWeather();
