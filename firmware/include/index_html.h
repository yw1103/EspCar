 // The H5 phone controller from v1, kept byte-for-byte so the
 // existing mobile UX still works on a fresh AP connection.
 // (Pointer Events prevent "press to start, release to stop" misfires.)
 #pragma once

const char INDEX_HTML[] PROGMEM = R"HTML(
 <!doctype html><html><head><meta charset="utf-8">
 <meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
 <title>DeskCar</title>
 <style>
   html,body{margin:0;height:100%;background:#111;color:#eee;font-family:system-ui;
     -webkit-touch-callout:none;-webkit-user-select:none;user-select:none;
     -webkit-tap-highlight-color:rgba(0,0,0,0)}
   .pad{position:fixed;inset:0;display:grid;grid-template-columns:1fr 1fr 1fr;grid-template-rows:1fr 1fr 1fr;gap:8px;padding:8px}
   .b{background:#222;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:24px;
     touch-action:none}
   .b:active{background:#0a84ff}
   .f{grid-column:2;grid-row:1}
   .b{grid-column:1;grid-row:2}
   .r{grid-column:3;grid-row:2}
   .k{grid-column:2;grid-row:3;background:#a22}
   .wifi{position:fixed;right:12px;top:10px;color:#9cc7ff;text-decoration:none;font-size:14px;z-index:2}
 </style></head>
 <body><a class="wifi" href="/wifi">Wi-Fi</a><div class="pad">
   <div class="b f" onpointerdown="go('F')" onpointerup="go('S')" onpointercancel="go('S')">F</div>
   <div class="b b" onpointerdown="go('B')" onpointerup="go('S')" onpointercancel="go('S')">B</div>
   <div class="b l" onpointerdown="go('L')" onpointerup="go('S')" onpointercancel="go('S')">L</div>
   <div class="b r" onpointerdown="go('R')" onpointerup="go('S')" onpointercancel="go('S')">R</div>
   <div class="b k" onpointerdown="go('S')">STOP</div>
 </div>
 <script>
   function go(d){fetch('/control?dir='+d)}
 </script></body></html>
)HTML";

const char WIFI_HTML[] PROGMEM = R"HTML(
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DeskCar Wi-Fi</title>
<style>
  :root{color-scheme:light dark}
  *{box-sizing:border-box}
  body{margin:0;min-height:100vh;font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#f4f6f8;color:#18202a;display:flex;align-items:center;justify-content:center;padding:20px}
  main{width:min(420px,100%);background:#fff;border:1px solid #d7dde5;border-radius:8px;padding:22px;box-shadow:0 10px 30px rgba(20,30,40,.08)}
  h1{font-size:22px;margin:0 0 6px}
  p{margin:0 0 18px;color:#596575;line-height:1.45}
  label{display:block;font-size:13px;font-weight:650;margin:14px 0 6px}
  input{width:100%;height:42px;border:1px solid #c7d0dc;border-radius:6px;padding:0 11px;font-size:16px;background:#fff;color:#18202a}
  button{height:42px;border:0;border-radius:6px;background:#1463ff;color:white;font-weight:700;font-size:15px;padding:0 14px}
  button.secondary{background:#e8edf4;color:#18202a}
  .row{display:flex;gap:10px;margin-top:18px}
  .row button{flex:1}
  #status{margin-top:16px;font-size:14px;white-space:pre-wrap;color:#364150}
  .ok{color:#0a7a34}.bad{color:#b00020}
  @media (prefers-color-scheme:dark){
    body{background:#101419;color:#eef3f8}
    main{background:#161c23;border-color:#2b3542}
    p,#status{color:#aab5c2}
    input{background:#101419;color:#eef3f8;border-color:#3a4654}
    button.secondary{background:#2a3441;color:#eef3f8}
  }
</style></head>
<body><main>
  <h1>DeskCar Wi-Fi Setup</h1>
  <p>Connect the car to a 2.4 GHz Wi-Fi network. After saving, restart the ESP32 and return your computer or phone to the same network.</p>
  <label for="ssid">Wi-Fi SSID</label>
  <input id="ssid" autocomplete="off" maxlength="31" placeholder="LabWiFi">
  <label for="pass">Password</label>
  <input id="pass" type="password" maxlength="63" placeholder="Leave blank for open Wi-Fi">
  <div class="row">
    <button onclick="save()">Save</button>
    <button class="secondary" onclick="clearWifi()">Clear</button>
  </div>
  <div id="status">Loading...</div>
</main>
<script>
const s=document.getElementById('status');
async function refresh(){
  try{
    const r=await fetch('/api/v1/wifi');
    const j=await r.json();
    document.getElementById('ssid').value=j.ssid||'';
    s.className='';
    s.textContent='Mode: '+j.wifi+'\nIP: '+j.ip+'\nAP: '+j.ap_ip+'\nSTA: '+(j.sta_ip||'not connected');
  }catch(e){s.className='bad';s.textContent='Cannot read Wi-Fi status.'}
}
async function save(){
  const ssid=document.getElementById('ssid').value.trim();
  const pass=document.getElementById('pass').value;
  if(!ssid){s.className='bad';s.textContent='SSID is required.';return}
  s.className='';s.textContent='Saving...';
  try{
    const r=await fetch('/api/v1/wifi',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ssid:ssid,pass:pass})});
    if(!r.ok)throw new Error(await r.text());
    s.className='ok';s.textContent='Saved. Restart the ESP32, then connect your device back to "'+ssid+'".';
  }catch(e){s.className='bad';s.textContent='Save failed: '+e.message}
}
async function clearWifi(){
  s.className='';s.textContent='Clearing...';
  try{
    const r=await fetch('/api/v1/wifi',{method:'DELETE'});
    if(!r.ok)throw new Error(await r.text());
    document.getElementById('ssid').value='';
    document.getElementById('pass').value='';
    s.className='ok';s.textContent='Cleared. Restart the ESP32 to return to AP provisioning mode.';
  }catch(e){s.className='bad';s.textContent='Clear failed: '+e.message}
}
refresh();
</script></body></html>
)HTML";
