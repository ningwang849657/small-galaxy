# lab_tracker

## 2026-09 界面升级

新版使用浅灰背景、白色圆角卡片和深色每日目标卡，继续生成离线、自包含 HTML。
新增可保存的每日目标（2–8 小时）、14 天按小时累计活动分布、单日最长连续有效活动与 ≥25 分钟片段统计、前后日期按钮和 CSV 导出。
目标和表格展开状态保存在当前浏览器的 localStorage；禁止本地存储时仍能使用，但偏好不保留。
页面每分钟在未交互时刷新，后台仍每五分钟生成数据。空闲不等同摸鱼，电脑活动不等同科研产出；日均只计算有实际活动的日期。

界面源文件：`dashboard.py`（数据和基础模板）、`dashboard.css`（样式）、`dashboard-enhancements.js`（交互）。CSS/JS 在生成时内嵌，最终页面不依赖网络。
修改 Python 后需 `systemctl --user restart lab-tracker.service`，避免常驻进程使用旧模板。测试：`python3 -m unittest discover -s tests -p 'test_*.py'`。

以下为原始安装说明；其中旧版暖色视觉描述已由新版设计替代。

自动记录"电脑在被使用"的时间段，据此推算每天到达/离开实验室的时间，以及排除中途长时间无操作（开会、发呆、离开工位）后的"有效科研时间"。

原理：假设这台台式机只在你人在实验室时会被使用，通过 `xprintidle` 每 60 秒采样一次系统空闲秒数，同时用 `xprop` 记录当前前台窗口的标题（用于把刷 bilibili/YouTube 的时间单独归为"娱乐"），写入按天分文件的 CSV 日志，再由 `summary.py` / `dashboard.py` 汇总统计、可视化。

## 目录结构

```
lab_tracker.py               后台采样守护进程（自带单实例文件锁；每 5 分钟顺带重新生成一次仪表盘）
summary.py                   统计核心逻辑 + 命令行报告，dashboard.py 和 lab_tracker.py 都复用它的计算函数
dashboard.py                  生成仪表盘 HTML（自包含，无需联网/服务器）并用默认浏览器打开
desktop/lab-tracker.desktop  桌面图标 / 应用菜单的启动器文件（应用名 小银河），Exec 指向 dashboard.py
icons/galaxy.svg              小银河的图标（星系插画）
systemd/lab-tracker.service  systemd --user 服务单元文件
tests/make_fake_day.py       生成模拟数据，验证 summary.py 计算逻辑（不依赖 xprintidle）
```

日志数据写在 `~/.lab_tracker/logs/YYYY-MM-DD.csv`，仪表盘文件在 `~/.lab_tracker/dashboard.html`，娱乐关键词配置在 `~/.lab_tracker/fun_keywords.txt`，单实例锁文件在 `~/.lab_tracker/lab_tracker.lock`（都和代码目录分开，不受项目目录移动/删除影响）。

## 1. 安装依赖

```bash
sudo apt install xprintidle
```

窗口标题采样用的 `xprop` 属于 `x11-utils`，Ubuntu 桌面默认自带，一般不用装（`which xprop` 能看到路径即可；万一没有就 `sudo apt install x11-utils`）。仪表盘是纯 HTML/CSS/JS，用系统默认浏览器打开，不需要额外装 Python GUI 库。

安装后可以手动验证一下（离开键盘鼠标几秒钟再看数字是否在增长，单位是毫秒）：

```bash
xprintidle
```

## 2. 手动测试守护进程（不装 systemd，先跑几分钟看看）

```bash
python3 /home/ning/lab_tracker/lab_tracker.py
```

前台运行，Ctrl+C 停止。跑 1-2 分钟后检查是否生成了日志：

```bash
cat ~/.lab_tracker/logs/$(date +%F).csv
```

如果 `xprintidle` 没装好或者取不到显示器（比如通过 SSH 无 GUI 登录），程序不会崩溃，只会在终端打印警告并跳过采样，可以放心测试。

程序启动时会自动加一把文件锁（`~/.lab_tracker/lab_tracker.lock`），保证同一时间只有一个采样进程在写日志。如果 systemd 服务已经在跑，这时候再手动执行上面这条命令会直接打印"已经有一个 lab_tracker.py 在运行了"然后退出，这是正常保护行为，不是 bug——两个进程同时写同一份 CSV 会导致统计出错。想手动测试的话，先 `systemctl --user stop lab-tracker.service` 停掉服务，测完再 `systemctl --user start lab-tracker.service` 启动回来。

## 3. 安装为开机自启的 systemd 用户服务

```bash
mkdir -p ~/.config/systemd/user
cp /home/ning/lab_tracker/systemd/lab-tracker.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now lab-tracker.service
```

查看运行状态：

```bash
systemctl --user status lab-tracker.service
```

查看运行日志（含前面提到的警告信息）：

```bash
tail -f ~/.lab_tracker/lab_tracker.log
```

这个服务依赖你已经登录了图形桌面（需要访问 X11 的 DISPLAY），所以设置了 `WantedBy=graphical-session.target`，只要你登录桌面它就会自动启动，不需要额外配置 `loginctl enable-linger`。

### 常见问题：服务启动了但日志一直报"无法获取空闲时间"

多数情况是 systemd 用户会话没有拿到 `DISPLAY` / `XAUTHORITY` 环境变量（尤其是通过 SSH 启动 systemctl，或者某些窗口管理器不会自动导入这两个变量）。排查方法：

```bash
# 在图形桌面里打开一个终端，确认这两个变量存在
echo $DISPLAY
echo $XAUTHORITY

# 把它们导入到 systemd 用户会话
systemctl --user import-environment DISPLAY XAUTHORITY
systemctl --user restart lab-tracker.service
```

如果导入一次之后还是不行（比如每次重新登录变量又丢了），可以直接在 `~/.config/systemd/user/lab-tracker.service` 的 `[Service]` 里写死（先用 `echo $DISPLAY` / `echo $XAUTHORITY` 确认实际值）：

```ini
Environment=DISPLAY=:0
Environment=XAUTHORITY=/run/user/1000/gdm/Xauthority
```

改完记得 `systemctl --user daemon-reload && systemctl --user restart lab-tracker.service`。

## 4. 查看报告（命令行）

```bash
# 今天
python3 /home/ning/lab_tracker/summary.py

# 指定某一天
python3 /home/ning/lab_tracker/summary.py --date 2026-07-08

# 最近 7 天周报（以某天为截止日，默认今天）
python3 /home/ning/lab_tracker/summary.py --week

# 调整"有效科研时间"的空闲阈值（默认 300 秒 = 5 分钟）
python3 /home/ning/lab_tracker/summary.py --threshold 600
```

想每天/每周自己看，可以加个 shell 别名（写进 `~/.bashrc`）：

```bash
alias labreport='python3 /home/ning/lab_tracker/summary.py'
alias labweek='python3 /home/ning/lab_tracker/summary.py --week'
```

## 5. 仪表盘：桌面图标点击运行（应用名 小银河）

`dashboard.py` 生成一份自包含的 HTML 仪表盘（`~/.lab_tracker/dashboard.html`），用系统默认浏览器打开。视觉上是一套暖色晨光主题（米色纸面 + 顶部一片晨光渐晕和细小的琥珀色光尘；品牌标保留深色星系小方块呼应应用图标，这是刻意选择的单主题设计），布局：

- **顶部状态徽章**：记录中（绿）/ 未在记录（红）——判断依据是 `systemctl --user is-active lab-tracker.service`，避免服务悄悄挂了却不知道。
- **3 个统计卡片**：今日有效科研时间（附与日均的升降对比）、近 7 天有效科研时间（附与前 7 天的对比）、近 14 天日均（附 14 天迷你趋势图）。
- **最近 14 天柱状图**：每根柱子是当天的"有效科研时间"（蓝）+"娱乐"（玫红）+"摸鱼/中断"（沙色）三层堆叠柱，横贯一条"14 天日均"参考线；悬停看具体数字，点一根柱子在下面展开那天的明细。选中的日期记在网址的 `#` 后面，页面每 60 秒自动刷新后选中状态不会丢。
- **单日时间线**：选中某一天后，24 小时横向时间轴显示当天什么时候在专注、什么时候中断，两端有"到达/离开"小旗标注，悬停每一段能看到起止时间和时长。
- **数据表格**（默认折叠）：14 天的原始数字，图表之外的兜底查看方式（也是低对比色块的无障碍兜底）。

图表配色用 dataviz 校验脚本验证过（主蓝 #3B72D9 在暖色表面上通过亮度带/色度/色觉安全/对比度四项检查；两个系列的色觉色差 ΔE≈74，远超安全线）。

`summary.py` 和 `dashboard.py` 共用同一套 `build_day_segments` / `compute_stats` 计算逻辑，两边数字保证一致。仪表盘本身是"生成一次静态网页"，不是常驻服务：每次点桌面图标都会用最新数据重新生成并打开；如果开着浏览器标签页不关，`lab_tracker.py` 守护进程每 5 分钟会在后台重新生成一次这个文件，网页自己每 60 秒 `<meta refresh>` 一次，所以放着不动也会准实时刷新，不需要手动点刷新按钮。

图标是 `icons/galaxy.svg`（深空底色 + 旋臂光带 + 光核星点，纯 SVG 渐变绘制），`.desktop` 文件里 `Icon=` 直接写了这个文件的绝对路径，不依赖系统图标主题。想换图标的话直接编辑/替换这个 svg 文件即可，不需要改 `.desktop`。

先手动跑一次，确认浏览器能正常打开仪表盘：

```bash
python3 /home/ning/lab_tracker/dashboard.py
```

确认没问题后，把桌面图标装上：

```bash
mkdir -p ~/Desktop
cp /home/ning/lab_tracker/desktop/lab-tracker.desktop ~/Desktop/
chmod +x ~/Desktop/lab-tracker.desktop
```

之后桌面上会出现一个"小银河"图标。

### 常见问题：双击图标提示"不受信任的应用程序启动器"

这是 GNOME 文件管理器（Nautilus）对桌面 `.desktop` 文件的安全限制。正常的解决方式：**直接双击图标**，Nautilus 会弹出确认对话框，点其中的"信任并启动"（Trust and Launch）即可——点一次之后 Nautilus 会记住这个选择，以后双击直接打开，不会再提示。

也可以尝试用命令行提前标记为受信任（跳过双击确认这一步），但不同 GNOME/gio 版本支持情况不一致，有的版本会报 `gio: 不支持设置属性 metadata::trusted`（不支持就直接忽略这条命令，改用上面双击确认的方法即可，效果一样）：

```bash
gio set ~/Desktop/lab-tracker.desktop metadata::trusted true
```

### 顺便加入应用菜单（可搜索，不止是桌面图标）

如果按 Super 键搜索应用菜单找不到它——是正常的，因为上面只装了桌面图标，没注册到菜单。想让它也能被搜索到（应用名是"小银河"），额外装一份到菜单目录即可：

```bash
mkdir -p ~/.local/share/applications
cp /home/ning/lab_tracker/desktop/lab-tracker.desktop ~/.local/share/applications/
update-desktop-database ~/.local/share/applications/
```

这两份 `.desktop` 文件（桌面图标 + 菜单入口）互相独立，删除其中任意一个不影响另一个。

### 常见问题：桌面上完全看不到图标（连图标本身都没有）

现代 GNOME 默认不在桌面背景上直接画图标，需要启用扩展（Ubuntu 一般叫 "Desktop Icons NG" 或类似名字）才会显示 `~/Desktop` 里的文件。可以打开"扩展"（Extensions）应用检查是否启用；如果不想折腾这个，直接用上面的应用菜单方式更省心，效果一样。

## 6. 统计算法说明 & 本地测试

### 算法：反推"最近一次真实操作时间"，而不是直接相信采样记录

每条采样记录 `(ts, idle)` 都隐含一个更有用的事实：**最近一次真实操作发生在 `ts - idle` 这个时刻**。`summary.py` 是用这个反推出来的时间点做统计，而不是直接拿采样记录本身的时间戳当"到达/离开时间"。这么做是为了修掉一个很容易踩到的坑：

> 如果电脑不是每次离开都关机（很常见——大部分人不会每天下班都关机），日志会一直采样到你实际上早就走了很久之后。老算法直接拿"当天最后一条记录"当离开时间，就会把离开时间错误地拖到你早就不在工位、电脑却还开着的那个时刻；如果电脑开了一整夜，第二天"到达时间"也会被错误地记成 00:00 前后，而不是你真正坐下来的那一刻。

新算法：把每条记录反推出的"最近操作时间"取出来，**到达 = 当天最早的一次真实操作，离开 = 当天最晚的一次真实操作**；相邻两次真实操作之间的间隔，阈值以内的部分算作专注间隙的"宽限期"（哪怕中途完全没碰电脑），超出阈值的部分才算中断/摸鱼。如果一整天日志里一条真实操作都反推不出来（电脑开着但人根本没来），会显示"当天有采样记录，但没有检测到任何真实操作"，不会硬凑一个到达/离开时间出来。

### 娱乐时间识别（bilibili / YouTube 等）

每次采样时会顺便记录**当前前台窗口的标题**。生成报告时，"在电脑前（活跃）"的时间里，凡是前台窗口标题命中娱乐关键词的分钟，会从"有效科研时间"里单独拆出来记为"娱乐"——刷 B 站滚动再欢快，也不会给有效时间贴金。

- **关键词可自定义**：编辑 `~/.lab_tracker/fun_keywords.txt`（每行一个关键词，忽略大小写，`#` 开头是注释；首次启动服务时会自动生成，默认含 bilibili / 哔哩哔哩 / youtube）。想把知乎/微博也算进去就各加一行。改完保存即可，下次生成报告/仪表盘时生效，**不用重启服务**。
- **判定的是前台窗口**：B 站在后台标签页/后台窗口挂着不算娱乐——你正在写论文，算有效。
- **挂机看视频**：完全不碰键鼠地看视频，超过空闲阈值（默认 5 分钟）的部分会落入"中断/摸鱼"（因为底层算法看不到输入）；期间有零星滚动/点击则会被正确记为娱乐。
- **隐私说明**：窗口标题原样记录在本地 CSV 里（截断到 120 字符），只存在你自己的机器上、不会外发。介意的话可以随时删日志文件。

### 老数据兼容

旧日志（只有两列、没有窗口标题）读取时按"无标题"处理，娱乐时长为 0，其他统计完全不受影响。服务启动时会把当天已存在的旧格式文件自动升级成三列。

### 用模拟数据验证

`tests/make_fake_day.py` 会在 `~/.lab_tracker/logs/` 下写入几天用未来假日期（2099年）构造的模拟数据，不会和真实记录混在一起：

- `2099-01-01` ~ `2099-01-07`（`01-04` 故意留空模拟没到岗）：正常一天，09:00-12:00 工作、12:00-13:30 午休/开会、13:30-15:00 工作、15:00-15:10 短暂离开、15:10-17:00 工作。
- `2099-01-08`：正常工作到 17:00，之后**忘记关机**，电脑一直采样到 23:59——用来验证离开时间不会被之后的空闲拖晚。
- `2099-01-09`：**昨晚就忘记关机**，今天凌晨到 9:15 之前电脑一直带着隔夜的空闲，9:15 才真正有人开始操作——用来验证到达时间不会被误判成 00:00 前后。
- `2099-01-10`：全天在电脑前操作，但中午 12:00-12:30 前台窗口是 bilibili——用来验证这 30 分钟被归为"娱乐"而不是有效科研时间。

运行：

```bash
python3 /home/ning/lab_tracker/tests/make_fake_day.py
python3 /home/ning/lab_tracker/summary.py --date 2099-01-01
python3 /home/ning/lab_tracker/summary.py --date 2099-01-08
python3 /home/ning/lab_tracker/summary.py --date 2099-01-09
python3 /home/ning/lab_tracker/summary.py --date 2099-01-07 --week
```

**预期输出**（阈值取默认的 300 秒，我在开发时实际跑过，数字和下面完全一致）：

`2099-01-01`（01-02/03/05/06/07 均相同的"正常一天"）：
- 到达 09:00:00，离开 17:00:00
- 总在场时长 8小时0分钟
- 有效科研时间 6小时28分钟（两段中断各扣掉超出 5 分钟宽限期的部分：91 分钟的午休扣剩 5 分钟宽限、11 分钟的短暂离开扣剩 5 分钟宽限）
- 摸鱼/中断时长 1小时32分钟

`2099-01-04` 应显示"当天没有记录"。

`2099-01-08`（忘记关机到 23:59）：
- **离开时间 16:59:00**——没有被之后 7 个小时的空闲拖晚，这就是这次修复要解决的问题。
- 有效科研时间 6小时33分钟

`2099-01-09`（隔夜空闲到 9:15）：
- **到达时间 09:15:00**——没有被凌晨 00:00 的隔夜空闲记录误判成"半夜到岗"。
- 因为这天中途没有额外插入短暂离开，有效科研时间等于总在场时长，都是 7小时44分钟，摸鱼 0分钟。

`2099-01-10`（中午刷了 30 分钟 bilibili）：
- 总在场 8小时0分钟，**有效科研时间 7小时30分钟，娱乐时长 0小时30分钟**，摸鱼/中断 0分钟。

（所有报告现在都会多一行"娱乐时长(bilibili等)"，老测试日该行应为 0。）

周报汇总（截至 01-07）：
- 有记录天数 6 天
- 总在场时长 48小时0分钟
- 总有效科研时间 38小时48分钟
- 日均有效科研时间 6小时28分钟

这些都是 2099 年的假数据，不影响真实记录，想清理的话直接删掉对应文件即可：

```bash
rm ~/.lab_tracker/logs/2099-01-*.csv
```

## 已知局限

- 到达/离开的判定依赖"两次真实操作之间的间隔"，如果工作持续跨越了午夜（比如凌晨还在肝论文），会被自然日分文件的机制从中间切成"昨天的离开"和"今天的到达"两段——这是按天分文件天然带来的边界情况，没有做跨天合并。
- 前提假设是"电脑只在你在实验室时使用"，如果偶尔远程登录这台机器，会被误判为在实验室。
- `xprintidle` 依赖 X11（`echo $XDG_SESSION_TYPE` 现在是 `x11`，没问题）；如果以后这台机器换成纯 Wayland 会话，`xprintidle` 可能会失效，到时候需要换一种取空闲时间的方式（比如换成读 `org.gnome.Mutter.IdleMonitor` 之类的 D-Bus 接口）。
