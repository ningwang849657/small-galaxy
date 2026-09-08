/* Decorative artwork only: a forest-spirit header band and a rainforest rain scene.
   Everything is drawn here as original SVG/CSS — no film assets, no images, no network. */
const decorRand = mulberry32(70915);

/* ---------- 顶部：森林精灵band（小银河 ↔ 个性化 那一条） ---------- */
function spiritTree(x, baseY, height, width, cls) {
  // 一棵树 = 树干 + 三层由圆弧堆出的树冠，剪影用，不追求植物学准确。
  const g = el('g', { class: cls });
  g.appendChild(el('rect', { x: x - width * 0.045, y: baseY - height * 0.62, width: width * 0.09, height: height * 0.62, rx: width * 0.045 }));
  for (let i = 0; i < 3; i++) {
    const t = i / 2;
    const cy = baseY - height * (0.52 + t * 0.34);
    const rx = width * (0.5 - t * 0.17);
    const ry = height * (0.20 - t * 0.045);
    g.appendChild(el('ellipse', { cx: x, cy: cy.toFixed(1), rx: rx.toFixed(1), ry: ry.toFixed(1) }));
  }
  return g;
}

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

/* viewBox 贴着 header 的实际高度：slice 会按较大的缩放比裁剪，画面太高的话上下都会被切掉。 */
function buildForestBand() {
  const W = 1440, H = 96, ground = H + 4;
  const band = el('svg', { id: 'forest-band', viewBox: '0 0 ' + W + ' ' + H, preserveAspectRatio: 'xMidYMax slice', 'aria-hidden': 'true' });
  const defs = el('defs', {});
  const fade = el('linearGradient', { id: 'forest-fade', x1: '0', y1: '0', x2: '0', y2: '1' });
  fade.appendChild(el('stop', { offset: '0%', class: 'fade-top' }));
  fade.appendChild(el('stop', { offset: '96%', class: 'fade-bottom' }));
  defs.appendChild(fade);
  band.appendChild(defs);
  const far = el('g', { class: 'forest-far' }), near = el('g', { class: 'forest-near' });
  for (let i = 0; i < 11; i++) far.appendChild(spiritTree(20 + i * 134 + decorRand() * 40, ground, 46 + decorRand() * 22, 96 + decorRand() * 36, ''));
  for (let i = 0; i < 7; i++) near.appendChild(spiritTree(-20 + i * 226 + decorRand() * 60, ground, 32 + decorRand() * 16, 124 + decorRand() * 40, ''));
  band.append(far, near);
  // 自上而下的雾：标题所在的上半部几乎被页面底色盖住，树影只在贴近下缘处露出来。
  band.appendChild(el('rect', { x: 0, y: 0, width: W, height: H, class: 'forest-mist' }));
  const spirits = el('g', { class: 'spirits' });
  // 少而大：小到十几像素时，身子和手脚糊成一团，只认得出一颗头。
  [[96, 92, 1.5], [386, 96, 2.05], [606, 90, 1.7], [822, 97, 2.2], [1074, 92, 1.75], [1330, 96, 1.95], [1420, 88, 1.35]].forEach(([x, y, s]) => {
    const seat = el('g', { transform: 'translate(' + x + ' ' + y + ')' });
    seat.appendChild(kodama(s, 3.4 + decorRand() * 3.2));
    spirits.appendChild(seat);
  });
  band.appendChild(spirits);
  const motes = el('g', { class: 'motes' });
  for (let i = 0; i < 26; i++) {
    const mote = el('circle', { cx: (decorRand() * W).toFixed(1), cy: (34 + decorRand() * 58).toFixed(1), r: (0.9 + decorRand() * 1.6).toFixed(2) });
    mote.style.animationDuration = (5 + decorRand() * 7).toFixed(2) + 's';
    mote.style.animationDelay = '-' + (decorRand() * 9).toFixed(2) + 's';
    motes.appendChild(mote);
  }
  band.appendChild(motes);
  header.prepend(band);
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

function place(node, x, y, rotate, scale) {
  const g = el('g', { transform: 'translate(' + x + ' ' + y + ') rotate(' + rotate + ') scale(' + scale + ')' });
  g.appendChild(node);
  return g;
}

function buildRainforest() {
  const scene = document.createElement('div');
  scene.className = 'rain-scene';
  scene.setAttribute('aria-hidden', 'true');

  // 构图沿上下两条边展开、中间给标题留空：窄屏时 slice 只保留中间一竖条，
  // 所以每条边上的叶子要铺满整个宽度，任何裁法都还看得出是雨林。
  const W = 1440, H = 300;
  const foliage = el('svg', { class: 'rain-foliage', viewBox: '0 0 ' + W + ' ' + H, preserveAspectRatio: 'xMidYMid slice' });
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
  foliage.append(back, front);
  scene.appendChild(foliage);

  for (let i = 0; i < 2; i++) {
    const mist = document.createElement('div');
    mist.className = 'rain-mist';
    mist.style.animationDuration = (46 + i * 22) + 's';
    mist.style.animationDelay = '-' + (i * 19) + 's';
    mist.style.top = (14 + i * 44) + '%';
    scene.appendChild(mist);
  }
  // 三层雨：越近的越快、越长、越明显，靠差速拉开纵深。
  [[46, 'rain-far'], [38, 'rain-mid'], [26, 'rain-near']].forEach(([count, cls]) => {
    const layer = document.createElement('div');
    layer.className = 'rain-layer ' + cls;
    for (let i = 0; i < count; i++) {
      const drop = document.createElement('span');
      drop.style.left = (decorRand() * 106 - 3).toFixed(2) + '%';
      drop.style.setProperty('--len', (12 + decorRand() * 30).toFixed(0) + 'px');
      drop.style.animationDuration = (.5 + decorRand() * .55).toFixed(2) + 's';
      drop.style.animationDelay = '-' + (decorRand() * 1.4).toFixed(2) + 's';
      drop.style.opacity = (.3 + decorRand() * .55).toFixed(2);
      layer.appendChild(drop);
    }
    scene.appendChild(layer);
  });
  const splashes = document.createElement('div');
  splashes.className = 'rain-splashes';
  for (let i = 0; i < 11; i++) {
    const ripple = document.createElement('span');
    ripple.style.left = (decorRand() * 100).toFixed(2) + '%';
    ripple.style.animationDuration = (1.6 + decorRand() * 1.5).toFixed(2) + 's';
    ripple.style.animationDelay = '-' + (decorRand() * 3).toFixed(2) + 's';
    splashes.appendChild(ripple);
  }
  scene.appendChild(splashes);
  // 暴雨时压暗天色，放晴时换成暖光和一轮太阳。
  const veil = document.createElement('div');
  veil.className = 'storm-veil';
  const wash = document.createElement('div');
  wash.className = 'sun-wash';
  const sun = document.createElement('div');
  sun.className = 'rain-sun';
  sun.innerHTML = '<span class="sun-rays"></span><span class="sun-halo"></span><span class="sun-core"></span>';
  scene.append(veil, wash, sun);
  document.querySelector('.hero').prepend(scene);
  return scene;
}

/* ---------- 天气：小雨 → 暴雨 → 转小 → 放晴 → 循环 ----------
   相位推进只改几个 CSS 变量，雨滴本身的动画一直跑，不重启、不重排。 */
const WEATHER_KEYFRAMES = [
  // [相位, 雨量 0-1, 阳光 0-1]
  [0, .28, 0], [.14, .55, 0], [.28, 1, 0], [.42, 1, 0], [.56, .45, 0],
  [.66, .12, .1], [.74, 0, .75], [.86, 0, 1], [.94, .1, .35], [1, .28, 0]
];
function weatherAt(phase) {
  for (let i = 1; i < WEATHER_KEYFRAMES.length; i++) {
    const [toPhase, toRain, toSun] = WEATHER_KEYFRAMES[i];
    if (phase > toPhase) continue;
    const [fromPhase, fromRain, fromSun] = WEATHER_KEYFRAMES[i - 1];
    const span = toPhase - fromPhase;
    const t = span > 0 ? (phase - fromPhase) / span : 0;
    const eased = t * t * (3 - 2 * t);
    return { rain: fromRain + (toRain - fromRain) * eased, sun: fromSun + (toSun - fromSun) * eased };
  }
  return { rain: WEATHER_KEYFRAMES[0][1], sun: WEATHER_KEYFRAMES[0][2] };
}
const FIXED_WEATHER = { drizzle: { rain: .3, sun: 0 }, storm: { rain: 1, sun: 0 }, clear: { rain: 0, sun: 1 } };
const rainScene = buildRainforest();
buildForestBand();
let weatherTimer = 0, weatherStart = performance.now();
let weatherMode = 'cycle', weatherCycle = 96;
// 三层雨依次加入：小雨只有远处细丝，暴雨时三层全开，读起来就是雨越下越大。
const LAYER_RANGE = [['far', 0, .34], ['mid', .22, .62], ['near', .5, .95]];
function paintWeather(rain, sun) {
  const style = rainScene.style;
  LAYER_RANGE.forEach(([name, from, to]) => {
    style.setProperty('--rain-' + name, Math.max(0, Math.min(1, (rain - from) / (to - from))).toFixed(3));
  });
  style.setProperty('--storm', (rain * rain).toFixed(3));
  style.setProperty('--sun', sun.toFixed(3));
}
function stepWeather() {
  const phase = ((performance.now() - weatherStart) / (weatherCycle * 1000)) % 1;
  const { rain, sun } = weatherAt(phase);
  paintWeather(rain, sun);
}
function runWeather() {
  clearInterval(weatherTimer); weatherTimer = 0;
  const still = document.body.classList.contains('no-motion');
  if (weatherMode !== 'cycle') { const fixed = FIXED_WEATHER[weatherMode]; paintWeather(fixed.rain, fixed.sun); return; }
  // 停用动画时定格在小雨，不再空转计时器。
  if (still) { paintWeather(.3, 0); return; }
  stepWeather();
  weatherTimer = setInterval(stepWeather, 140);
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
  weatherMode = mode; weatherCycle = Math.max(20, cycleSeconds || 96);
  runWeather();
};
runWeather();
