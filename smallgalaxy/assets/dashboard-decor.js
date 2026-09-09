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
  band.appendChild(el('g', { class: 'spirits' }));
  band.appendChild(el('g', { class: 'focus-stars' }));
  return band;
}

/* 名字叫小银河，那就让"光"真的来自数据：每一段 ≥25 分钟的持续专注 = 一颗星，
   今天的更大更亮。星位固定（同一套种子），数据变化时只增减，不会整片跳动。 */
const STAR_SEATS = (() => {
  const seat = mulberry32(521974), seats = [];
  while (seats.length < 140) {
    const y = 132 + seat() * 288;
    if (y > 424) continue;                      // 再往下就撞到木灵了
    seats.push([seat() * 1440, y, 3.5 + seat() * 6, 4 + seat() * 7, seat() * 9]);
  }
  return seats;
})();
/* 避让区不能写死：wrap 是流式的，文字块的位置随视口宽度变。
   必须逐个元素分别判定——把它们并成一个大矩形的话，几个分散的文字块会把
   整块画面都圈进去（1440 下并集是 x86–1354），装饰就一个都放不下了。 */
const TEXT_NODES = ['#hero-title', '#hero-signature', '.author-chip', '.hero-meta', 'header .brand', '.header-actions'];
/* 块级元素的矩形横跨整行，哪怕文字只有半行；用 Range 取真实的文字包围盒，
   否则一个 <p> 就能把整条画面圈成禁区。 */
function tightRect(node) {
  try {
    const range = document.createRange();
    range.selectNodeContents(node);
    const r = range.getBoundingClientRect();
    if (r.width && r.height) return r;
  } catch {}
  return node.getBoundingClientRect();
}
function textBoxesInViewBox(band) {
  const box = band.getBoundingClientRect();
  if (!box.width || !box.height) return [];
  const scale = Math.max(box.width / 1440, box.height / 480);   // preserveAspectRatio=slice
  const originX = (1440 - box.width / scale) / 2;               // xMid
  const originY = 480 - box.height / scale;                     // YMax：底对齐
  const boxes = [];
  for (const selector of TEXT_NODES) {
    const node = document.querySelector(selector);
    if (!node) continue;
    const r = tightRect(node);
    if (!r.width || !r.height) continue;
    boxes.push({
      x0: originX + (r.left - box.left) / scale, x1: originX + (r.right - box.left) / scale,
      y0: originY + (r.top - box.top) / scale, y1: originY + (r.bottom - box.top) / scale,
    });
  }
  return boxes;
}
const hits = (boxes, x0, x1, y0, y1) =>
  boxes.some(b => x1 > b.x0 - 6 && x0 < b.x1 + 6 && y1 > b.y0 - 5 && y0 < b.y1 + 5);

const SUSTAINED_SECONDS = 25 * 60;
function starPath(r) {
  const waist = r * 0.2;
  return `M0,${-r} L${waist},${-waist} L${r},0 L${waist},${waist} L0,${r} L${-waist},${waist} L${-r},0 L${-waist},${-waist}Z`;
}
const SPIRIT_SEATS = [[96, 430, .92], [214, 446, 1.15], [368, 436, .82], [520, 440, .78],
  [700, 448, .9], [880, 434, .84], [1058, 440, .86], [1208, 448, 1.1], [1348, 433, .95]];

/* ---------- 三只神灵：按天气现身 ----------
   都是现画的剪影，和木灵一套做法，不含任何影片素材。
   出太阳→鹿（山兽神），大雾→白狼，暴雨→夜行的巨神。 */
function forestDeer() {
  // 实心剪影：腿、角都用有宽度的填充块，和身体一个重量，别一半实一半线。
  const g = el('g', { class: 'beast beast-deer' });
  [[-19, 2.6], [-10, 1.2], [12, -1.2], [21, -2.6]].forEach(([x, lean]) =>
    g.appendChild(el('path', { d: `M${x - 2.4},-6 L${x + 2.4},-6 L${x + lean + 2},33 L${x + lean - 2},33 Z` })));
  g.appendChild(el('ellipse', { cx: 0, cy: -17, rx: 27, ry: 13.5 }));
  g.appendChild(el('path', { d: 'M17,-24 L26,-52 L36,-49 L27,-19 Z' }));
  g.appendChild(el('ellipse', { cx: 38, cy: -55, rx: 10.5, ry: 6, transform: 'rotate(-20 38 -55)' }));
  g.appendChild(el('path', { d: 'M46,-59 L56,-58 L47,-52 Z' }));
  g.appendChild(el('path', { d: 'M-25,-20 C-39,-27 -43,-14 -33,-8 L-29,-14 C-34,-17 -32,-22 -25,-18 Z' }));
  [[31, -1], [40, 1]].forEach(([base, dir]) => {
    g.appendChild(el('path', { d: `M${base - 2.6},-60 L${base + 2.6},-60 L${base + dir * 11 + 2},-95 L${base + dir * 11 - 2.4},-95 Z` }));
    [[-70, 13, 2.2], [-83, 15, 1.9]].forEach(([y, reach, thick]) =>
      g.appendChild(el('path', {
        d: `M${base + dir * 2},${y} L${base + dir * 2 + dir * reach},${y - 9} L${base + dir * 2 + dir * reach},${y - 9 + thick * 2} L${base + dir * 2},${y + thick * 2} Z` })));
  });
  return g;
}
function whiteWolf() {
  const g = el('g', { class: 'beast beast-wolf' });
  [[-16, 1.8], [-8, .8], [9, -.8], [17, -1.8]].forEach(([x, lean]) =>
    g.appendChild(el('path', { d: `M${x - 2.2},-6 L${x + 2.2},-6 L${x + lean + 1.9},21 L${x + lean - 1.9},21 Z` })));
  g.appendChild(el('ellipse', { cx: 0, cy: -14, rx: 24, ry: 10 }));
  g.appendChild(el('path', { d: 'M15,-18 L27,-31 L37,-26 L23,-13 Z' }));
  g.appendChild(el('path', { d: 'M27,-33 L48,-30 L45,-20 L26,-23 Z' }));
  g.appendChild(el('path', { d: 'M28,-34 L30,-44 L37,-33 Z' }));
  g.appendChild(el('path', { d: 'M31,-45 L33,-53 L39,-42 Z' }));
  g.appendChild(el('path', { d: 'M-22,-17 C-38,-24 -45,-10 -33,-3 L-29,-9 C-36,-13 -32,-20 -22,-14 Z' }));
  return g;
}
function nightSpirit() {
  const g = el('g', { class: 'beast beast-night' });
  g.appendChild(el('path', { d: 'M-14,0 C-10,-54 -8,-106 -5,-152 L5,-152 C8,-106 10,-54 14,0 Z' }));
  g.appendChild(el('ellipse', { cx: 0, cy: -162, rx: 12, ry: 14 }));
  [-1, 1].forEach(side => g.appendChild(el('path', {
    d: `M${side * 8},-140 C${side * 27},-121 ${side * 31},-87 ${side * 21},-55 L${side * 15},-58 C${side * 24},-86 ${side * 20},-117 ${side * 5},-134 Z` })));
  return g;
}
/* 每只给几个备选位置：主位被文字挡住就往旁边挪，而不是干脆不出现。 */
const BEASTS = [
  { make: forestDeer, seats: [[1146, 452], [986, 452], [1292, 450]], scale: 1.05, half: [58, 100] },
  { make: whiteWolf, seats: [[1010, 456], [330, 458], [660, 456]], scale: .95, half: [50, 56] },
  { make: nightSpirit, seats: [[742, 462], [590, 462], [900, 462]], scale: .8, half: [34, 180] },
];

window.renderSpirits = function () {
  const group = document.querySelector('#forest-band .spirits');
  if (!group) return;
  group.replaceChildren();
  const boxes = textBoxesInViewBox(group.ownerSVGElement);
  // 木灵大致向上占 24 个单位、左右各 11 个（都乘缩放）。
  const clear = ([x, y, scale]) => !hits(boxes, x - 11 * scale, x + 11 * scale, y - 24 * scale, y);
  SPIRIT_SEATS.filter(clear).slice(0, 7).forEach(([x, y, scale], index) => {
    const seat = el('g', { transform: 'translate(' + x + ' ' + y + ')' });
    seat.appendChild(kodama(scale, 3.4 + ((index * 37) % 32) / 10));
    group.appendChild(seat);
  });
  // 神灵和木灵共用同一套避让：它们体型大，压到标题上会很难看。
  BEASTS.forEach(({ make, seats, scale, half: [halfW, halfH] }) => {
    const spot = seats.find(([x, y]) =>
      !hits(boxes, x - halfW * scale, x + halfW * scale, y - halfH * scale, y));
    if (!spot) return;
    const seat = el('g', { transform: `translate(${spot[0]} ${spot[1]}) scale(${scale})` });
    seat.appendChild(make());
    group.appendChild(seat);
  });
};
window.renderFocusStars = function () {
  const group = document.querySelector('#forest-band .focus-stars');
  if (!group) return;
  group.replaceChildren();
  let todays = 0, earlier = 0;
  DATA.days.forEach(day => day.segments.forEach(segment => {
    if (segment.kind !== 'active' || segment.end_sec - segment.start_sec < SUSTAINED_SECONDS) return;
    if (day === TODAY) todays++; else earlier++;
  }));
  // 今天的排在前面，用最显眼的几个星位。
  const boxes = textBoxesInViewBox(group.ownerSVGElement);
  const clear = ([x, y, radius]) => !hits(boxes, x - radius, x + radius, y - radius, y + radius);
  const usable = STAR_SEATS.filter(clear);
  const total = Math.min(todays + earlier, usable.length);
  for (let i = 0; i < total; i++) {
    const [x, y, radius, spin, delay] = usable[i];
    const fresh = i < todays;
    const star = el('path', {
      d: starPath(fresh ? radius * 1.45 : radius),
      class: fresh ? 'star today' : 'star',
      transform: `translate(${x.toFixed(1)} ${y.toFixed(1)})`,
    });
    star.style.animationDuration = spin.toFixed(2) + 's';
    star.style.animationDelay = '-' + delay.toFixed(2) + 's';
    group.appendChild(star);
  }
};

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
  // 前三层是常态的雨；第四层 rain-squall 只在雨量接近满格时才浮现——
  // 190 条又长又快的雨丝，这才是"雨下得很大"看起来的样子。数量固定、常驻，
  // 靠透明度浮现，所以不会在骤雨来时重排 DOM 或重启动画。
  [[46, 'rain-far', 1.2, 9], [38, 'rain-mid', .72, 21], [26, 'rain-near', .44, 38],
   [190, 'rain-squall', .3, 74]].forEach(([count, cls, speed, length]) => {
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
  const bow = el('svg', { class: 'rainbow', viewBox: '0 0 1440 480', preserveAspectRatio: 'xMidYMax slice', 'aria-hidden': 'true' });
  const bowDefs = el('defs', {});
  const bowFade = el('linearGradient', { id: 'bow-fade', x1: '0', y1: '0', x2: '1', y2: '0' });
  [['0%', 0], ['16%', .85], ['50%', 1], ['84%', .85], ['100%', 0]].forEach(([offset, alpha]) => {
    bowFade.appendChild(el('stop', { offset, 'stop-color': '#fff', 'stop-opacity': alpha }));
  });
  const bowMask = el('mask', { id: 'bow-mask' });
  bowMask.appendChild(el('rect', { x: 0, y: 0, width: 1440, height: 480, fill: 'url(#bow-fade)' }));
  bowDefs.append(bowFade, bowMask);
  bow.appendChild(bowDefs);
  const arcs = el('g', { mask: 'url(#bow-mask)' });
  // 由外到内：红橙黄绿青蓝紫。半径逐圈收小，描边很宽、很淡，靠 blur 化开。
  ['#e0685f', '#e59a52', '#e3c75c', '#7fbf72', '#5fa9c4', '#6b7fc4', '#9a72bd'].forEach((colour, index) => {
    arcs.appendChild(el('path', {
      d: 'M120,470 A 600,600 0 0 1 1320,470'.replace(/600,600/, `${600 - index * 15},${600 - index * 15}`)
         .replace('M120,470', `M${120 + index * 15},470`).replace('1320,470', `${1320 - index * 15},470`),
      class: 'bow-band', stroke: colour,
    }));
  });
  bow.appendChild(arcs);
  scene.appendChild(bow);
  const shafts = document.createElement('div');shafts.className = 'sun-shafts';
  for(let i=0;i<5;i++) {
    const ray=document.createElement('span');ray.style.left=(56+i*8)+'%';
    ray.style.width=(22+i%3*19)+'px';ray.style.animationDelay=(-i*1.8)+'s';shafts.appendChild(ray);
  }
  scene.append(clouds, ground, curtain, drips, veil, wash, shafts, buildSpiritLayer());
  const hero=document.querySelector('.hero');hero.prepend(scene);
  // 品牌名、状态徽章和按钮搬进画板，和标题共用同一张画：整页只剩一个画面。
  scene.after(header);
  window.renderSpirits?.();
  window.renderFocusStars?.();
  new ResizeObserver(()=>{window.renderSpirits?.();window.renderFocusStars?.();}).observe(document.querySelector('.hero'));
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
  //
  // 一天里有两场雨，而且是两种雨：
  //   .20–.50  午后对流阵雨——云先堆 12% 周期，看得见它要来；
  //   .76–.90  骤雨（squall）——晴空底下毫无征兆，一阵疾风先到，
  //            两三秒内雨墙就砸下来，收得同样快。东南亚那种。
  [0,    0, .12, .26, .82, .10, .60, .16],
  [.10,  0, .70, .18, .30, .16, .36, .08],
  [.20,  0, .24, .82, .22, .55, .28, .02],
  [.26,.35, .02, .95, .32, .86, .62, .32],
  [.32,  1,   0,    1, .52,  1,   1, .85],
  [.40,.92,   0, .96, .60, .85,  1,   1],
  [.50,.34, .03, .75, .78, .40,  1,   1],
  [.58,  0, .16, .54,   1, .18, .94, .86],
  [.68,  0, .78, .20, .66, .12, .80, .58],
  [.76,  0, .96, .08, .24, .09, .54, .26],   // 完全放晴，一片云都没有
  [.785, 0, .90, .30, .20, .92, .50, .20],   // 一阵疾风先到，天还是亮的
  [.805, 1, .16, .88, .28,  1,  .74, .50],   // 雨墙落下：约 2 秒
  [.85,  1,   0,    1, .40,  1,   1,   1],   // 最猛
  [.88, .70,   0, .92, .52, .78,  1,   1],
  [.905,.06, .38, .48, .74, .28,  1,  .92],  // 收得和来时一样快
  [.95,  0, .58, .22, .66, .12, .80, .50],
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
  const wall = Math.max(0, Math.min(1, (rain - .55) / .38));
  style.setProperty('--squall', (wall * wall * (3 - 2 * wall)).toFixed(3));
  style.setProperty('--sun', sun.toFixed(3));
  // 彩虹不是独立天气，而是三件事同时成立：太阳出来、雨停了、空气还是湿的。
  const bow = sun * climate.wet * Math.max(0, 1 - rain * 3.2);
  style.setProperty('--rainbow', Math.min(1, bow * 1.9).toFixed(3));
  // 谁在什么天气现身：太阳→鹿，大雾→白狼，暴雨→夜行的巨神。
  const band = (value, from, to) => Math.max(0, Math.min(1, (value - from) / (to - from)));
  style.setProperty('--deer', band(sun, .55, .92).toFixed(3));
  style.setProperty('--wolf', (band(climate.mist, .72, .98) * (1 - Math.min(1, rain * 2))).toFixed(3));
  style.setProperty('--night', band(rain, .82, 1).toFixed(3));
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
