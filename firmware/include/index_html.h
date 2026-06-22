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
 </style></head>
 <body><div class="pad">
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

