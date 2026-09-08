"""Run real Chrome interaction checks in an isolated temporary page/profile."""
import subprocess
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dashboard

CHECKS = r"""
<script>
(async()=>{
try {
 const check=(v,m)=>{if(!v)throw Error(m);};
 check(document.getElementById('goal-ring'),'enhancements loaded');
 document.getElementById('prev-day').click();
 check(selectedDate===DATA.days[12].date,'previous day');
 document.getElementById('today-button').click();
 check(selectedDate===TODAY.date,'today');
 goalSelect.value='8'; goalSelect.dispatchEvent(new Event('change'));
 check(storage.get('goal')==='8','goal persistence');
 check(document.getElementById('goal-percent').textContent===Math.round(TODAY.active_seconds/28800*100)+'%','goal calculation');
 check(document.querySelectorAll('#hour-bars span').length===24,'hour bins');
 let exported;
 URL.createObjectURL=b=>{exported=b;return 'blob:test';};
 HTMLAnchorElement.prototype.click=function(){};
 document.getElementById('export-csv').click();
 check(exported instanceof Blob,'CSV blob');
 check((await exported.text()).split('\r\n').length===15,'CSV rows');
 check(document.documentElement.scrollWidth<=window.innerWidth,'page overflow');
 document.body.setAttribute('data-test-result','PASS');
}catch(e){document.body.setAttribute('data-test-result','FAIL: '+e.message);}
})();
</script>
"""

with tempfile.TemporaryDirectory(prefix='galaxy-test-') as tmp:
    data = dashboard.build_dashboard_data()
    page = Path(tmp) / 'test.html'
    page.write_text(dashboard.render_html(data).replace('</body>', CHECKS+'</body>'))
    for width in (1440, 390):
        result = subprocess.run(['google-chrome','--headless','--no-sandbox','--disable-gpu',
            '--user-data-dir='+str(Path(tmp)/str(width)), '--virtual-time-budget=2000',
            '--window-size='+str(width)+',1000','--dump-dom',page.as_uri()],capture_output=True,text=True,timeout=25)
        assert 'data-test-result="PASS"' in result.stdout, result.stdout[-2000:] + result.stderr
        print(f'{width}px: date navigation, target persistence, hourly bins, CSV and overflow PASS')
