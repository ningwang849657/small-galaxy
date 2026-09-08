"""Run real Chrome interaction checks in an isolated temporary page/profile."""
import subprocess
import json
import time
import threading
import base64
from http.server import ThreadingHTTPServer
from urllib.request import build_opener, ProxyHandler
from unittest.mock import patch
import websocket
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dashboard
import dashboard_server

CHECKS = r"""
<script>
(async()=>{
try {
 const check=(v,m)=>{if(!v)throw Error(m);};
 const settle=ms=>new Promise(resolve=>setTimeout(resolve,ms));
 check(document.getElementById('goal-ring'),'enhancements loaded');
 document.getElementById('prev-day').click();
 check(selectedDate===DATA.days[12].date,'previous day');
 document.getElementById('today-button').click();
 check(selectedDate===TODAY.date,'today');
 goalSelect.value='8'; goalSelect.dispatchEvent(new Event('change'));
 await settle(950);
 check(storage.get('goal')==='8','goal persistence');
 check(document.getElementById('goal-percent').textContent===Math.round(TODAY.active_seconds/28800*100)+'%','goal calculation');
 check(document.querySelectorAll('#hour-bars span').length===24,'hour bins');
 check(!document.querySelector('iframe'),'music must not contact YouTube before Play');
 check(document.getElementById('hero-title').querySelector('br')===null,'headline stays one line');
 // Decorative artwork is drawn locally and must never pull an external asset.
 check(document.querySelectorAll('#forest-band .kodama').length===7,'forest spirits drawn');
 check(document.querySelectorAll('.rain-layer span').length===110,'rain drops drawn');
 // Weather runs as a phase: drizzle builds to a downpour, eases off, then the sun comes out.
 const weatherOf=p=>{const w=weatherAt(p);return [Number(w.rain.toFixed(3)),Number(w.sun.toFixed(3))];};
 check(weatherOf(0)[0]>0 && weatherOf(0)[0]<.4 && weatherOf(0)[1]===0,'cycle starts on light rain');
 check(weatherOf(.35)[0]===1,'cycle reaches a downpour');
 check(weatherOf(.6)[0]<weatherOf(.35)[0],'downpour eases off');
 check(weatherOf(.86)[0]===0 && weatherOf(.86)[1]===1,'cycle clears to full sun');
 check(Math.abs(weatherOf(1)[0]-weatherOf(0)[0])<.001 && weatherOf(1)[1]===weatherOf(0)[1],'cycle wraps seamlessly');
 const rainLevel=()=>Number(getComputedStyle(document.querySelector('.rain-scene')).getPropertyValue('--rain-near'));
 window.applyWeatherSettings('storm',96); check(rainLevel()>.9,'fixed storm');
 window.applyWeatherSettings('clear',96); check(rainLevel()===0,'fixed clear sky');
 window.applyWeatherSettings(preferences.weatherMode,preferences.weatherCycle);
 // The YouTube player is only an audio source: parked off screen, never taking space on the card.
 const wrapStyle=getComputedStyle(document.getElementById('youtube-wrap'));
 check(wrapStyle.position==='absolute' && parseFloat(wrapStyle.left)<-1000,'player box is parked off screen');
 check(document.getElementById('music-external').hidden,'no YouTube link until a YouTube source plays');
 check([...document.images].every(i=>i.src.startsWith('data:')),'no externally hosted images');
 const avatar=document.querySelector('.author-chip img');
 await avatar.decode();
 check(avatar.naturalWidth===192,'GitHub avatar decodes from its data URI');
 check(document.querySelector('.author-chip').href==='https://github.com/'+GITHUB_USER,'avatar links to the profile');
 document.getElementById('open-settings').click();
 check(dialog.open,'settings dialog');
 document.getElementById('setting-title').value='<img src=x onerror=alert(1)> 今天也慢慢来';
 document.getElementById('setting-signature').value='这是我的签名';
 document.getElementById('setting-theme').value='dark';
 document.getElementById('setting-accent').value='green';
 document.getElementById('setting-showRhythm').checked=false;
 document.getElementById('setting-showDecor').checked=false;
 document.getElementById('setting-goal').value='4.5';
 document.getElementById('appearance-form').requestSubmit();
 check(getComputedStyle(document.querySelector('.rain-scene')).display==='none','decor can be switched off');
 document.getElementById('setting-showDecor').checked=true;
 document.getElementById('appearance-form').requestSubmit();
 check(getComputedStyle(document.getElementById('forest-band')).display!=='none','decor can be switched back on');
 check(document.getElementById('hero-title').textContent.startsWith('<img'),'literal user text');
 check(!document.querySelector('#hero-title img'),'no HTML injection');
 check(document.getElementById('hero-signature').textContent==='这是我的签名','signature');
 check(goalSelect.value==='4.5','half-hour goals');
 check(document.documentElement.dataset.theme==='dark','theme');
 check(document.querySelector('.insight-grid').children[1].hidden,'card visibility');
 check(readPreferences().signature==='这是我的签名','persisted signature');
 // Interrupted upward/downward animations settle to the latest real value.
 const probe=document.createElement('div');document.body.appendChild(probe);
 preferences.animations=false;setDurParts(probe,3600);
 preferences.animations=true;setDurParts(probe,7200);await settle(160);
 const rising=Number(probe.dataset.displaySeconds);check(rising>3600 && rising<7200,'count-up intermediate');
 setDurParts(probe,1800);await settle(160);
 check(Number(probe.dataset.displaySeconds)<rising,'interrupted count-down');
 await settle(900);check(Number(probe.dataset.displaySeconds)===1800,'exact final animated value');
 preferences.animations=false;setDurParts(probe,300);check(Number(probe.dataset.displaySeconds)===300,'disabled animation');
 probe.remove();numberTransitions.delete(probe);
 // Research/work share sampled data; exercise uses a distinct manual ledger.
 const computerSeconds=computerData.days.at(-1).active_seconds;
 document.getElementById('setting-scene').value='work';document.getElementById('setting-scene').dispatchEvent(new Event('change'));
 document.getElementById('appearance-form').requestSubmit();
 check(document.querySelector('.tile .label').textContent==='今日有效工作时间','work labels');
 check(TODAY.active_seconds===computerSeconds,'work preserves original data');
 check(document.getElementById('hero-signature').textContent==='这是我的签名','scene preserves own signature');
 document.getElementById('setting-scene').value='exercise';document.getElementById('setting-scene').dispatchEvent(new Event('change'));
 document.getElementById('appearance-form').requestSubmit();
 check(TODAY.active_seconds===0 && !TODAY.has_data,'exercise does not reuse keyboard time');
 check(!document.getElementById('manual-card').hidden,'manual form visible');
 document.getElementById('session-start').value='09:00';document.getElementById('session-end').value='10:00';
 document.getElementById('session-note').value='<b>跑步</b>';
 document.getElementById('session-form').requestSubmit();
 check(TODAY.active_seconds===3600 && readSessions().length===1,'manual save and statistics');
 check(!document.querySelector('#session-list b'),'safe session note');
 document.getElementById('session-start').value='09:30';document.getElementById('session-end').value='10:30';
 document.getElementById('session-form').requestSubmit();
 check(TODAY.active_seconds===3600 && sessions.length===1,'overlap rejected');
 document.querySelector('.session-row-actions button').click();
 document.getElementById('session-end').value='09:30';document.getElementById('session-form').requestSubmit();
 check(TODAY.active_seconds===1800,'manual duration decrease');
 document.querySelector('.session-row-actions button:last-child').click();
 check(TODAY.active_seconds===0 && sessions.length===0,'manual delete');
 document.querySelector('#session-feedback button').click();check(TODAY.active_seconds===1800,'manual undo');
 document.getElementById('setting-scene').value='custom';document.getElementById('setting-custom-name').value='阅读';
 document.getElementById('setting-custom-source').value='manual';document.getElementById('appearance-form').requestSubmit();
 check(TODAY.active_seconds===0 && document.querySelector('.tile .label').textContent==='今日阅读时间','custom manual isolation');
 document.getElementById('setting-scene').value='research';document.getElementById('appearance-form').requestSubmit();
 check(TODAY.active_seconds===computerSeconds,'original computer data restored');
 const merged=manualData(computerData,'exercise',[
   {scene:'exercise',date:TODAY.date,start:9*3600,end:10*3600},
   {scene:'exercise',date:TODAY.date,start:9.5*3600,end:11*3600},
   {scene:'exercise',date:TODAY.date,start:12*3600,end:13*3600}
 ]).days.at(-1);
 check(merged.active_seconds===3*3600 && merged.idle_seconds===3600 && merged.total_presence_seconds===4*3600,'manual overlap union and gap accounting');
 check(youtubeId('https://youtu.be/8OFbtrDZESo')===OFFICIAL_TRACKS[0].id,'YouTube link parsing');
 check(youtubeId('https://evil.example/watch?v=bm00ve67x5U')===null,'reject unknown video host');
 // Four built-in tracks: the chips, the settings dropdown and the player all read one preference.
 check(OFFICIAL_TRACKS.length===4 && new Set(OFFICIAL_TRACKS.map(t=>t.id)).size===4,'four distinct built-in tracks');
 check(document.querySelectorAll('#track-chips button').length===4,'a chip per track');
 document.querySelectorAll('#track-chips button')[2].click();
 check(preferences.officialTrack==='paradiso','chip switches track');
 check(document.getElementById('track-title').textContent==='天堂电影院 · 主题曲','chip updates the title');
 check(document.querySelector('#track-chips .current').dataset.track==='paradiso','chip marks the current track');
 check(readPreferences().officialTrack==='paradiso','track choice persists');
 syncSettings();
 check(settingTrack.value==='paradiso' && !document.getElementById('official-track-field').hidden,'settings mirror the chip');
 settingTrack.value='sangreal'; settingTrack.dispatchEvent(new Event('change'));
 document.getElementById('music-form').requestSubmit();
 check(preferences.officialTrack==='sangreal' && preferences.musicTitle==='Chevaliers de Sangreal','settings switch track');
 check(!document.querySelector('iframe'),'switching tracks still contacts nothing');
 document.getElementById('setting-music-mode').value='file';
 document.getElementById('setting-music-mode').dispatchEvent(new Event('change'));
 check(document.getElementById('official-track-field').hidden,'track picker hides for other sources');
 // Everything on the page can be renamed; blank fields fall back to the scene wording.
 syncSettings();
 document.getElementById('setting-brand').value='我的银河';
 document.getElementById('setting-kpiToday').value='今天写了多久';
 document.getElementById('setting-footerNote').value='© 我自己';
 document.getElementById('setting-tagline').value='一天一点';
 document.getElementById('setting-decorStrength').value='40';
 document.getElementById('appearance-form').requestSubmit();
 check(document.querySelector('.brand h1').textContent==='我的银河','brand is editable');
 check(document.querySelector('.tile .label').textContent==='今天写了多久','KPI labels are editable');
 check(document.getElementById('footer-note').textContent==='© 我自己','footer is editable');
 check(document.querySelector('.tagline').textContent==='一天一点','tagline is editable');
 document.getElementById('setting-tagline').value='';
 document.getElementById('setting-focusStyle').value='forest';
 document.getElementById('setting-theme').value='night';
 document.getElementById('setting-accent').value='teal';
 document.getElementById('appearance-form').requestSubmit();
 check(document.documentElement.dataset.focus==='forest','goal card palette applies');
 check(document.documentElement.hasAttribute('data-dark'),'new dark themes are flagged dark');
 check(getComputedStyle(document.querySelector('.focus-card')).backgroundColor==='rgb(20, 38, 29)','goal card uses its own colour');
 check(getComputedStyle(document.documentElement).getPropertyValue('--active').trim()==='#7fd3dd','dark themes get the light accent variant');
 document.getElementById('setting-theme').value='light';
 document.getElementById('setting-accent').value='blue';
 document.getElementById('appearance-form').requestSubmit();
 check(!document.documentElement.hasAttribute('data-dark'),'light themes clear the dark flag');
 // The three time cards run deep to light so their order reads at a glance.
 const waveMix=n=>getComputedStyle(document.querySelectorAll('.kpi-row .tile')[n]).getPropertyValue('--wave-deep');
 const alphaOf=v=>{const m=v.match(/[\d.]+%/g);return m?parseFloat(m[m.length-1]):NaN;};
 check(alphaOf(waveMix(0))>alphaOf(waveMix(1)) && alphaOf(waveMix(1))>alphaOf(waveMix(2)),'time cards shade deep to light');
 check(getComputedStyle(document.documentElement).getPropertyValue('--decor-strength').trim()==='0.4','decor strength applies');
 document.getElementById('setting-kpiToday').value='';
 document.getElementById('appearance-form').requestSubmit();
 check(document.querySelector('.tile .label').textContent.startsWith('今日'),'blank label returns to the scene wording');
 document.getElementById('setting-accentCustom').value='#c2185b';
 document.getElementById('setting-accentCustom').dispatchEvent(new Event('input'));
 check(getComputedStyle(document.documentElement).getPropertyValue('--active').trim()==='#c2185b','custom accent applies');
 document.getElementById('clear-accent').click();
 check(getComputedStyle(document.documentElement).getPropertyValue('--active').trim()!=='#c2185b','preset accent restored');
 // Water level in the time cards tracks the real numbers against the daily goal.
 goalSelect.value='4'; goalSelect.dispatchEvent(new Event('change'));
 const level=Number(document.querySelector('.kpi-row .tile').style.getPropertyValue('--level'));
 check(Math.abs(level-waveLevel(TODAY.active_seconds/14400))<.001,'wave level matches the real ratio');
 check(waveLevel(0)===0 && waveLevel(1)>waveLevel(.5) && waveLevel(9)<=.78,'level rises with the value and never fills the card');
 check(document.querySelectorAll('.kpi-row .tile .wave-fill').length===3,'a wave in each time card');
 check(!httpsAudioURL('javascript:alert(1)'),'reject non-HTTPS media');
 check(!httpsAudioURL('https://user:pass@example.com/song.mp3'),'reject credential URLs');
 // A generated, silent WAV exercises local-file storage and native audio with no copyrighted asset.
 const wave=new ArrayBuffer(16044), view=new DataView(wave);
 const str=(offset,s)=>[...s].forEach((c,i)=>view.setUint8(offset+i,c.charCodeAt(0)));
 str(0,'RIFF');view.setUint32(4,16036,true);str(8,'WAVE');str(12,'fmt ');view.setUint32(16,16,true);
 view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,8000,true);view.setUint32(28,16000,true);
 view.setUint16(32,2,true);view.setUint16(34,16,true);str(36,'data');view.setUint32(40,16000,true);
 const track=new File([wave],'test-silence.wav',{type:'audio/wav'});
 await musicFileDB(track); check((await musicFileDB()).name==='test-silence.wav','IndexedDB music persistence');
 preferences.musicMode='file';preferences.fileName=track.name;syncMusicControls();
 await playButton.onclick();check(!audioPlayer.paused,'local audio playback');
 document.getElementById('music-volume').value='20';document.getElementById('music-volume').dispatchEvent(new Event('input'));
 check(audioPlayer.volume===.2,'audio volume');
 const originalFetch=window.fetch;
 window.fetch=async()=>({ok:true,json:async()=>structuredClone(DATA)});
 // /data is a read-only loopback endpoint; test successful update without replacing the audio element.
 if(location.protocol!=='file:') {await refreshDashboard();check(!audioPlayer.paused,'refresh preserves music');}
 window.fetch=originalFetch;
 await playButton.onclick();check(audioPlayer.paused,'pause audio');
 stopMusic();dialog.close();
 // The local library plays straight off disk through the loopback server — no platform involved.
 if(location.protocol!=='file:') {
   await loadMusicLibrary();
   check(libraryTracks.length===1 && libraryTracks[0].name==='library silence.wav','library lists the folder');
   selectLibraryTrack('library silence.wav');
   check(preferences.musicMode==='library' && document.getElementById('track-title').textContent==='library silence','library switches source');
   check(document.querySelectorAll('#track-chips button').length===1,'chips follow the library');
   await playButton.onclick();
   check(!audioPlayer.paused,'library track plays from disk');
   check(new URL(audioPlayer.src).pathname==='/music/library%20silence.wav','library track is served by name');
   stopMusic();
   // A track deleted from the folder is reported plainly instead of failing silently.
   selectLibraryTrack('gone.wav'); await playButton.onclick();
   check(audioPlayer.paused && musicStatus.textContent.includes('不在音乐库里'),'missing library track is reported');
   stopMusic();
 }
 document.getElementById('reset-appearance').click();
 let exported;
 URL.createObjectURL=b=>{exported=b;return 'blob:test';};
 HTMLAnchorElement.prototype.click=function(){};
 document.getElementById('export-csv').click();
 check(exported instanceof Blob,'CSV blob');
 check((await exported.text()).split('\r\n').length===15,'CSV rows');
 check((await exported.text()).includes('自动记录'),'CSV includes data source');
 // textContent would also read this script, so compare against a script-free clone of the page.
 const visible=document.body.cloneNode(true);
 visible.querySelectorAll('script,style').forEach(node=>node.remove());
 check(!visible.textContent.includes('电脑活动估算') && !visible.textContent.includes('电脑记录'),'both phrasings are gone from the page');
 preferences.scene='exercise';document.getElementById('export-sessions').click();
 check((await exported.text()).includes('09:30') && (await exported.text()).includes('<b>跑步</b>'),'manual CSV preserves entries and literal notes');
 preferences.scene='research';
 check(document.documentElement.scrollWidth<=window.innerWidth,'page overflow');
 preferences={...DEFAULT_PREFS};savePreferences();syncMusicControls();applyAppearance();
 document.body.setAttribute('data-test-result','PASS');
}catch(e){document.body.setAttribute('data-test-result','FAIL: '+e.message);}
})();
</script>
"""

with tempfile.TemporaryDirectory(prefix='galaxy-test-') as tmp:
    data = dashboard.build_dashboard_data()
    page = Path(tmp) / 'test.html'
    online='--online-music' in sys.argv
    online_checks='''<script>playButton.onclick(); setInterval(()=>{
      if(youtubeState===1) document.body.setAttribute('data-test-result','PASS');
      if(musicStatus.textContent.includes('无法') || musicStatus.textContent.includes('未能')) document.body.setAttribute('data-test-result','FAIL: '+musicStatus.textContent);
    },200);</script>'''
    page.write_text(dashboard.render_html(data).replace('</body>', (online_checks if online else CHECKS)+'</body>'))
    # A generated silent WAV on disk stands in for the user's own music library.
    music=Path(tmp)/'music';music.mkdir()
    header=(b'RIFF'+(16036).to_bytes(4,'little')+b'WAVEfmt '+(16).to_bytes(4,'little')
            +(1).to_bytes(2,'little')+(1).to_bytes(2,'little')+(8000).to_bytes(4,'little')
            +(16000).to_bytes(4,'little')+(2).to_bytes(2,'little')+(16).to_bytes(2,'little')
            +b'data'+(16000).to_bytes(4,'little'))
    (music/'library silence.wav').write_bytes(header+bytes(16000))
    with patch.object(dashboard_server,'PAGE',page),patch.object(dashboard_server,'MUSIC_DIR',music):
        server=ThreadingHTTPServer(('127.0.0.1',0),dashboard_server.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            for width in ((1440,) if online else (1440,390)):
                profile=Path(tmp)/str(width)
                process=subprocess.Popen(['google-chrome','--headless','--no-sandbox','--disable-gpu','--mute-audio',
                    '--user-data-dir='+str(profile),'--remote-debugging-port=0','--autoplay-policy=no-user-gesture-required',
                    '--window-size='+str(width)+',1100','about:blank'],
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                socket=None
                try:
                    portfile=profile/'DevToolsActivePort'
                    deadline=time.monotonic()+30
                    while not portfile.exists() and time.monotonic()<deadline: time.sleep(.1)
                    debugport=int(portfile.read_text().splitlines()[0])
                    opener=build_opener(ProxyHandler({}))
                    with opener.open(f'http://127.0.0.1:{debugport}/json/list') as result: targets=json.load(result)
                    target=next(t for t in targets if t['type']=='page')
                    socket=websocket.create_connection(target['webSocketDebuggerUrl'],suppress_origin=True,timeout=5)
                    serial=0
                    def cdp(method,params):
                        global serial
                        serial+=1;socket.send(json.dumps({'id':serial,'method':method,'params':params}))
                        while True:
                            response=json.loads(socket.recv())
                            if response.get('id')==serial: return response
                    cdp('Emulation.setDeviceMetricsOverride',{'width':width,'height':1100,'deviceScaleFactor':1,'mobile':False})
                    cdp('Page.navigate',{'url':f'http://127.0.0.1:{server.server_port}/'})
                    outcome=None
                    while time.monotonic()<deadline:
                        result=cdp('Runtime.evaluate',{'expression':"document.body?.getAttribute('data-test-result')",'returnByValue':True})
                        outcome=result.get('result',{}).get('result',{}).get('value')
                        if outcome: break
                        time.sleep(.1)
                    if not outcome:
                        status=cdp('Runtime.evaluate',{'expression':"document.getElementById('music-status')?.textContent",'returnByValue':True})
                        outcome='Timed out: '+str(status)
                    assert outcome=='PASS',outcome
                    if not online:
                        cdp('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'reduce'}]})
                        result=cdp('Runtime.evaluate',{'expression':"(()=>{preferences.animations=true;const p=document.createElement('div');setDurParts(p,1234);return p.dataset.displaySeconds==='1234' && !motionEnabled();})()",'returnByValue':True})
                        assert result['result']['result']['value'],'reduced-motion fallback'
                        cdp('Emulation.setEmulatedMedia',{'features':[]})
                    cdp('Runtime.evaluate',{'expression':"window.scrollTo(0,0); document.getElementById('hero-title').style.animation='none';"})
                    time.sleep(.8)
                    shot=cdp('Page.captureScreenshot',{'format':'png'})
                    Path(f'/tmp/galaxy-personalized-{width}.png').write_bytes(base64.b64decode(shot['result']['data']))
                    if not online:
                        cdp('Runtime.evaluate',{'expression':"preferences.scene='exercise'; preferences.title=SCENES.exercise.title; preferences.signature=SCENES.exercise.signature; applyAppearance(); window.scrollTo(0,0);"})
                        time.sleep(1)
                        result=cdp('Runtime.evaluate',{'expression':"document.documentElement.scrollWidth<=innerWidth",'returnByValue':True})
                        assert result['result']['result']['value'],'manual scene page overflow'
                        shot=cdp('Page.captureScreenshot',{'format':'png'})
                        Path(f'/tmp/galaxy-exercise-{width}.png').write_bytes(base64.b64decode(shot['result']['data']))
                        cdp('Runtime.evaluate',{'expression':"preferences={...DEFAULT_PREFS};applyAppearance();"})
                        cdp('Runtime.evaluate',{'expression':"openSettings(); document.getElementById('setting-title').focus();"})
                        shot=cdp('Page.captureScreenshot',{'format':'png'})
                        Path(f'/tmp/galaxy-settings-{width}.png').write_bytes(base64.b64decode(shot['result']['data']))
                    print('Official YouTube track reached PLAYING' if online else f'{width}px: animation increase/decrease/interruption/reduced-motion, scene isolation, manual add/edit/delete/undo, settings, music, refresh and export PASS')
                finally:
                    if socket: socket.close()
                    process.terminate();process.wait(timeout=10)
        finally:
            server.shutdown();server.server_close();thread.join()
