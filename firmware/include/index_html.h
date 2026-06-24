// Tiny H5 controller + Wi-Fi setup pages. Keep these lean: they live in flash.
#pragma once

const char INDEX_HTML[] PROGMEM = R"HTML(
<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1,user-scalable=no"><title>DeskCar</title>
<style>
html,body{margin:0;height:100%;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;background:#f5f5f7;color:#1d1d1f;-webkit-touch-callout:none;-webkit-user-select:none;user-select:none;-webkit-tap-highlight-color:#0000}
a{position:fixed;right:18px;top:16px;color:#777;text-decoration:none;font-size:22px}
.w{height:100%;display:grid;place-items:center}.p{width:min(82vw,330px);aspect-ratio:1;border-radius:50%;background:#e8e8ed;display:grid;grid-template:1fr 1fr 1fr/1fr 1fr 1fr;gap:10px;padding:18px;box-shadow:inset 0 1px #fff,0 12px 30px #0001}.x{border:0;border-radius:50%;background:#fff;color:#333;font-size:28px;box-shadow:0 1px 8px #0002;touch-action:none}.x:active{background:#d7d7dc}.s{background:#333;color:white;font-size:14px}.f{grid-area:1/2}.l{grid-area:2/1}.s{grid-area:2/2}.r{grid-area:2/3}.b{grid-area:3/2}
</style><a href=/wifi>⚙</a><div class=w><div class=p>
<button class="x f" onpointerdown=g('F') onpointerup=g('S') onpointercancel=g('S')>↑</button>
<button class="x l" onpointerdown=g('L') onpointerup=g('S') onpointercancel=g('S')>←</button>
<button class="x s" onpointerdown=g('S')>STOP</button>
<button class="x r" onpointerdown=g('R') onpointerup=g('S') onpointercancel=g('S')>→</button>
<button class="x b" onpointerdown=g('B') onpointerup=g('S') onpointercancel=g('S')>↓</button>
</div></div><script>function g(d){fetch('/control?dir='+d)}</script>
)HTML";

const char WIFI_HTML[] PROGMEM = R"HTML(
<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Wi-Fi</title>
<style>
*{box-sizing:border-box}body{margin:0;min-height:100vh;padding:22px;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;background:#f5f5f7;color:#1d1d1f;display:grid;place-items:center}main{width:min(390px,100%)}h1{font-size:26px;margin:0 0 22px}label{display:block;margin:14px 0 6px;color:#666;font-size:13px}input{width:100%;height:46px;border:1px solid #d2d2d7;border-radius:10px;background:white;padding:0 12px;font-size:17px}button{height:44px;border:0;border-radius:10px;background:#1d1d1f;color:white;font-size:15px;font-weight:600}.c{background:#e8e8ed;color:#333}.r{display:flex;gap:10px;margin-top:18px}.r button{flex:1}#m{margin-top:16px;color:#666;font-size:14px;white-space:pre-wrap}.ok{color:#177a3b}.bad{color:#b00020}a{color:#777;text-decoration:none}
</style><main><a href=/>&lt;</a><h1>Wi-Fi</h1>
<label>SSID</label><input id=s maxlength=31 autocomplete=off>
<label>Password</label><input id=p maxlength=63 type=password>
<div class=r><button onclick=save()>Save</button><button class=c onclick=clr()>Clear</button></div><div id=m></div></main>
<script>
let M=document.getElementById('m'),S=document.getElementById('s'),P=document.getElementById('p');
fetch('/api/v1/wifi').then(r=>r.json()).then(j=>{S.value=j.ssid||'';M.textContent=j.wifi+'  '+j.ip}).catch(_=>M.textContent='offline');
async function save(){if(!S.value.trim()){M.className='bad';M.textContent='SSID required';return}M.textContent='Saving...';let r=await fetch('/api/v1/wifi',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ssid:S.value.trim(),pass:P.value})});M.className=r.ok?'ok':'bad';M.textContent=r.ok?'Saved. Restart ESP32.':'Failed'}
async function clr(){let r=await fetch('/api/v1/wifi',{method:'DELETE'});S.value=P.value='';M.className=r.ok?'ok':'bad';M.textContent=r.ok?'Cleared. Restart ESP32.':'Failed'}
</script>
)HTML";
