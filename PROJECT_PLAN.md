 # DeskCar v2 鈥?妗岄潰鏅鸿兘搴曠洏浜у搧鍖栨柟妗?
 > 杈撳叆锛氫氦鎺ユ枃妗ｃ€奅SP32 鍙岃疆杞紡灏忚溅椤圭洰鎶€鏈氦鎺ャ€?v1, 宸茶惤鍦扮‖浠?
 > 鐩爣锛氫粠鍗曟満鐜╁叿鎵╁睍涓?妗岄潰鏅鸿兘搴曠洏"浜у搧绾匡紝瑕嗙洊鎰熺煡銆佸喅绛栥€佷緵鐢点€佹墿灞曘€丼DK 鍏ㄩ摼璺? > 璁″垝妯″紡浜х墿锛氬疄鏂藉墠涓庡紑鍙戣€呭榻愮殑鍐崇瓥瀹屾暣 (decision-complete) 璁捐绋?
 ## 1. Summary

 鍦ㄧ幇鏈?ESP32-WROOM-32 + DRV8833 + N20 鍙岃疆搴曠洏涓婂彔鍔犲洓灞傝兘鍔涳細

 1. **涓婂笣瑙嗚瑙嗚瀛愮郴缁?*锛氬浐瀹氭闈㈡敮鏋剁殑 USB 鎽勫儚澶?+ 涓绘満 PC (OpenCV) 璺戣瑙夋劅鐭ャ€佺洰鏍囪窡韪€侀伩闅滀笌鍏ㄥ眬璺緞瑙勫垝銆? 2. **鏃犵嚎鎰熷簲鍏呯數**锛氬簳鐩樺祵鍏?Qi 鎺ユ敹绔?(BQ51025B)锛屾闈㈠厖鐢靛簳搴у彂灏勭 + AprilTag 鎻愪緵鍏ㄥ眬浣嶅Э鍩哄噯銆? 3. **纾佸惛鎵╁睍瑙︾偣**锛氳溅椤?5-pin pogo (3.3V / GND / SDA / SCL / INT) + 4脳 N52 纾侀搧锛屼负寮€鍙戣€呭璁炬彁渚涗緵鐢?+ I2C + 浜嬩欢涓柇銆? 4. **閫氱敤 Python SDK** (`deskcar`)锛氱函寮傛銆佸己绫诲瀷銆佸彲 `pip install`锛涘悓姝ュ叕寮€ JSON/WS 鍗忚鏂囨。渚涘叾浠栬瑷€瀹㈡埛绔噸鍐欍€?
 鍏抽敭绾︽潫锛堟潵鑷?v1 浜ゆ帴鏂囨。锛屼笉鍙繚鍙嶏級锛?
 * 涓ョ鎶?GPIO 34/35/36/39 褰撹緭鍑虹敤锛汸WM 鎬ュ仠蹇呴』鐢?`analogWrite(pin, 0)`銆? * 缂栫爜鍣?VCC 涓?ESP32 蹇呴』鍚屾簮 3.3V锛屽惁鍒?GPIO 婕忕數鍊掔亴瀵艰嚧鑺墖閿佹銆? * 鐢垫満鐢垫簮杞ㄩ渶淇濈暀 470碌F 閫€鑰︾數瀹癸紱`setup()` 鍐呯鐢?`BROWN_OUT`銆? * PWM 鏀瑰彉鏂瑰悜鏃堕渶 50~100ms 鎱㈠惎鍔ㄦ绾с€?
 ## 2. 绯荤粺鏋舵瀯

 ```mermaid
 flowchart LR
   subgraph DESK["妗岄潰"]
     Cam["USB Camera\n1080p 路 90掳+ FOV\n(妗岄潰鏀灦)"]
     Dock["Charging Dock\nQi TX + AprilTag"]
     Car["Chassis\nESP32 + 2xN20\nQi RX + ArUco\n纾佸惛鎵╁睍"]
     Dev["Expansion Peripheral\nI2C 浼犳劅鍣?鑸垫満/灞?]
   end
   PC["PC Orchestrator\nPython - OpenCV - asyncio"]

   Cam -->|MJPEG/YUYV| PC
   PC -->|WebSocket / HTTP| Car
   PC -. 瑙嗚璇?ArUco .-> Car
   PC -. 瑙嗚璇?AprilTag .-> Dock
   Car <-.|Qi 5W 鎰熷簲| Dock
   Dev <-.|纾佸惛 + pogo| Car
 ```

 ## 3. 纭欢鍙樻洿

 ### 3.1 Chassis锛堟部鐢?+ 澧為噺锛?
 * 娌跨敤锛欵SP32-WROOM-32銆丏RV8833銆?x 6V N20銆丄B 鐩哥紪鐮佸櫒 (7PPR)銆佸崟鑺?18650銆? * 鏂板锛?   * **Qi 鎺ユ敹绔?*锛欱Q51025B + 鐩村緞 38mm 鎺ユ敹绾垮湀锛屽浐瀹氬簳鐩樺簳閮ㄥ眳涓€傜嚎鍦堜笂鏂圭甯冮噾灞?鐢垫睜銆?   * **鍏呯數绠＄悊**锛歍P4056 + DW01A + FS8205 (BMS 涓€浣撴澘)锛屽 18650 杩涜 CC/CV 涓庤繃鏀句繚鎶ゃ€?   * **鐢垫睜閬ユ祴**锛欼NA219 (I2C, 0x40) 娴?V/I/SOC銆?   * **杞﹂《纾佸惛鎵╁睍**锛?-pin pogo (3.3V / GND / SDA / SCL / INT) 灞呬腑锛?x N52 纾侀搧缃簬鍥涜銆?   * **杞﹂《 ArUco 鏍囪瘑**锛欰rUco 4x4 dict, ID=0, 杈归暱 32mm锛屽妗嗙櫧搴曢粦杈癸紝缁曞紑纾佸惛闃靛垪銆?   * **鐢垫満鐢垫簮閫€鑰?*锛?70碌F 閾濈數瑙?+ 100nF 闄剁摲骞惰仈鍦?DRV8833 `VM`銆?   * **閫昏緫鐢垫簮**锛氬師 3.3V LDO 鏇挎崲涓哄杈撳叆 BUCK锛岀‘淇濇劅搴斿厖鐢垫椂鐢靛帇瑁曞害銆?
 ### 3.2 Charging Dock

 * 5V/3A USB-C PD 杈撳叆 鍒?XKT-510 鎴?BQ500100 鍙戝皠绔?鍒?鐩村緞 40mm 鍙戝皠绾垮湀銆? * 椤堕潰璐?AprilTag (tag36h11, ID=0)锛屾彁渚涘叏灞€浣嶅Э鍘熺偣銆? * 鐘舵€?LED (绾?缁?钃? + 鎵嬪姩寮硅捣鎸夐挳 (GPIO 杈撳叆)銆? * 搴曢儴纭呰兌闃叉粦鍨紱楂樺害 鈮?18mm锛屼笉闃绘尅鎽勫儚澶磋閲庛€?
 ### 3.3 Vision Mount

 * 妗岄潰澶瑰叿鎮噦 (1/4"-20 铻轰笣) + 90掳+ FOV USB 鎽勫儚澶?(Logitech C270 / ELP 1080p)銆? * USB 鈮?3m锛岀‘淇?USB 2.0 淇″彿瀹屾暣鎬с€? * 榛樿瀹夎楂樺害 70cm锛岃鐩?1.4m x 0.8m 妗岄潰銆?
 ### 3.4 鍏抽敭鐢垫皵绾︽潫

 * ESP32 3.3V 涓庣紪鐮佸櫒 VCC 鍚屾簮锛涙墿灞?I2C 鎬荤嚎蹇呴』浠?ESP32 鐨?3.3V 鍙栫數锛岀姝㈠鐏屻€? * 鎵╁睍绔彛淇″彿绾夸覆鑱?1k惟 闄愭祦锛岄槻姝㈠璁惧弽鍚戜緵鐢?ESP32銆? * 鎰熷簲鍏呯數鏃跺簳鐩樹笉寰楁湁 >2cm 閲戝睘鍑歌捣閬尅绾垮湀銆?
 ## 4. 杞欢妯″潡

 ### 4.1 ESP32 Firmware锛圓rduino锛屾部鐢?v1 妗嗘灦锛?
 妯″潡鎷嗗垎锛?
 * `motor.{h,cpp}` 鈥?DRV8833 + 杞惎鍔?(50ms 姊骇) + `analogWrite(0)` 鎬ュ仠銆? * `encoder.{h,cpp}` 鈥?`pcnt` 鍗曞厓姝ｄ氦瑙ｇ爜锛屾孩鍑哄洖鍗枫€? * `battery.{h,cpp}` 鈥?INA219 鍛ㄦ湡閲囨牱锛屽簱浠戠Н鍒?+ 寮€璺數鍘嬩慨姝ｃ€? * `charge.{h,cpp}` 鈥?鐩戝惉 BQ51025B `CHRG`/`STBY` 寮曡剼锛屼笂鎶ョ姸鎬佹満銆? * `expansion.{h,cpp}` 鈥?INT 杈规部妫€娴?+ 鐑彃鎷?I2C 鎵弿 (鍦板潃鍐茬獊浠茶)銆? * `wifi.{h,cpp}` 鈥?AP+STA 鍙屾ā锛欰P 淇濈暀 v1 鐨?`ESP32_Car_Control` 缁欐墜鏈?H5锛汼TA 鍔犲叆瀹跺涵 Wi-Fi 缁?PC SDK 鐢ㄣ€? * `server.{h,cpp}` 鈥?`WebServer.h` + `WebSocketServer.h`锛岃矾鐢辫 搂5銆? * `protocol.{h,cpp}` 鈥?ArduinoJSON 搴忓垪鍖?鍙嶅簭鍒楀寲銆?
 寮曡剼琛紙鍦?v1 鍩虹涓婅拷鍔狅級锛?
 | 鍔熻兘 | GPIO | 澶囨敞 |
 | :--- | :--- | :--- |
 | INA219 SDA/SCL | 21/22 | 榛樿 I2C 鎬荤嚎 |
 | BQ51025 CHRG | 25 | 杈撳叆锛岄厤缃?`INPUT_PULLUP` |
 | 鎵╁睍 INT | 26 | 杈撳叆锛岄厤缃?`INPUT_PULLUP`锛屽弻杈规部涓柇 |
 | 鎵嬪姩寮硅捣鎸夐敭 | 13 | 杈撳叆 (LED 鍙鐢? |

 GPIO 16/17 淇濈暀涓?v1 鐨勫彸鐢垫満 PWM (閬垮紑 strapping 闄愬埗)锛汫PIO 34/35 浠呰緭鍏ョ敤浜庡乏缂栫爜鍣ㄣ€?
 ### 4.2 PC Orchestrator (`orchestrator/`, Python 3.10+)

 * `vision/camera.py` 鈥?`cv2.VideoCapture`锛岄噰闆?+ 鍗曟鏍囧畾銆? * `vision/homography.py` 鈥?妗岄潰鍥涜鍒颁笘鐣屽潗鏍囩殑閫忚鍙樻崲 (mm)銆? * `vision/tracker.py` 鈥?ArUco 4x4 杞︿綋璺熻釜锛屽彂甯?6D pose銆? * `vision/dock.py` 鈥?tag36h11 AprilTag dock 妫€娴嬶紝鍙戝竷 dock 鍏ㄥ眬浣嶅Э銆? * `vision/obstacles.py` 鈥?MOG2 鑳屾櫙鍑忛櫎 + 杩為€氬煙锛岃繑鍥為殰纰嶆爡鏍笺€? * `controller/visual_servo.py` 鈥?P-controller `(vx, w) = K_p 路 e_pose`锛岄棴鐜?30 Hz銆? * `planning/charge_sm.py` 鈥?搂6 鐘舵€佹満銆? * `bridge/ws_client.py` 鈥?`websockets` 寮傛瀹㈡埛绔紝鎺夌嚎閲嶈繛銆? * `bridge/serial_fallback.py` 鈥?USB-CDC (115200) 鍏滃簳锛屽浐浠剁儳褰?+ 鎵嬪姩鎺у埗銆?
 渚濊禆锛歚opencv-python`, `opencv-contrib-python` (ArUco), `numpy`, `websockets`, `pydantic`, `deskcar-sdk`銆?
 ### 4.3 Python SDK (`sdk/`, 鍖呭悕 `deskcar`)

 * 瀹夎锛歚pip install deskcar`銆? * 渚濊禆浠?`websockets` + `pydantic` (閬垮厤浼犳煋 OpenCV 缁欎笂灞?銆? * 鍏紑 API锛堣崏妗堬級锛?
 ```python
 from deskcar import Chassis

 car = await Chassis.discover()         # mDNS / UDP 鎵弿
 await car.connect()

 await car.move(linear=0.30, angular=0.0)
 await car.goto(x=1.20, y=0.40, theta=0.0)   # 涓栫晫鍧愭爣锛屼緷璧栬瑙? await car.dock()                            # 鑷姩鍥炲厖
 await car.undock()

 devices = await car.scan_expansion()        # 鎵弿鎵╁睍 I2C 璁惧
 async for ev in car.events():               # 浜嬩欢娴?     if ev.type == "device_attached":
         ...
 ```

 * 浜嬩欢绫诲瀷锛歚state`, `encoder`, `battery`, `device_attached`, `device_detached`, `dock_visible`, `obstacle`, `error`銆? * 绫诲瀷娉ㄨВ 100% 瑕嗙洊锛沗py.typed` 鏍囪锛沵ypy --strict 骞插噣銆? * CI锛歱ytest + ruff + mypy銆?
 ## 5. 閫氫俊鍗忚

 * **HTTP REST** (鍏煎 v1)锛氫繚鐣?`/`, `/control`, `/speed`, `/data`锛涙柊澧?`/api/v1/*` 鍛藉悕绌洪棿銆? * **WebSocket**锛歚/api/v1/stream` 鍙屽悜锛汮SON 鎺у埗甯?+ 浜岃繘鍒剁紪鐮佸櫒/IMU 娴佸抚銆? * **mDNS**锛歚deskcar.local` (STA 妯″紡涓嬪箍鎾?銆? * **USB-CDC**锛?15200 bps锛屾渶鍚庢墜娈典笌鍥轰欢鐑у綍鍏辩敤閫氶亾銆?
 鏂板绔偣锛?
 | 鏂规硶 | 璺緞 | 璇存槑 |
 | :--- | :--- | :--- |
 | GET  | `/api/v1/state` | 瀹屾暣閬ユ祴 JSON |
 | POST | `/api/v1/move` | `{linear: m/s, angular: rad/s}` 楂橀鎺у埗 |
 | WS   | `/api/v1/stream` | 鍙屽悜娴?(50Hz) |
 | GET  | `/api/v1/devices` | 鎵╁睍鍙?I2C 鎵弿缁撴灉 |

 v1 鐨?`?dir=` 绔偣淇濈暀浣滀负鎵嬫満 H5 婕旂ず鍏ュ彛锛屼笉杩涘叆 SDK 鎺ㄨ崘璺緞銆?
 ## 6. 鑷姩鍏呯數鐘舵€佹満

 ```mermaid
 stateDiagram-v2
   [*] --> IDLE
   IDLE --> SEEK_DOCK : battery < threshold
   SEEK_DOCK --> ALIGN : AprilTag visible
   ALIGN --> APPROACH : tag in target zone
   APPROACH --> COUPLE : CHRG pin asserted
   COUPLE --> CHARGING : INA219 current > 50mA
   CHARGING --> FULL : INA219 current < 50mA
   FULL --> UNDOCK : user command
   UNDOCK --> IDLE : clear of dock
 ```

 * `SEEK_DOCK` 榛樿闅忔満婕父 + 娌胯竟绛栫暐锛涘彲琚敤鎴疯鐩栦负缁欏畾鐐广€? * `ALIGN` / `APPROACH` 鏈熼棿瑙嗚鎺夌嚎鍗抽€€鍥?`SEEK_DOCK`銆? * `COUPLE` 瓒呮椂 30s 鏈Е鍙?`CHRG` 鈫?閫€鍥?`ALIGN`銆?
 ## 7. 浠撳簱缁撴瀯

 ```
 deskcar/
   firmware/                ESP32 Arduino 宸ョ▼ (PlatformIO)
     src/
     include/
     test/
   sdk/                     deskcar Python 鍖?     src/deskcar/
     tests/
     py.typed
   orchestrator/            PC 绔瑙変笌瑙勫垝
     deskcar_orch/
     configs/
     calib/
   hardware/                KiCad + 缁撴瀯
     chassis_v2/
     dock/
     mount/
     bom/
   docs/
     PROTOCOL.md
     SDK_REFERENCE.md
     CALIBRATION.md
     HARDWARE.md
   examples/
     keyboard_teleop.py
     vision_dock_demo.py
     i2c_oled.py
     web_dashboard.py
   .github/workflows/
     sdk-ci.yml
     firmware-ci.yml
   README.md
   LICENSE
   PROJECT_PLAN.md
 ```

 ## 8. 娴嬭瘯涓庨獙鏀?
 * **鍗曞厓**锛氱紪鐮佸櫒璁℃暟绮惧害銆丳WM ramp銆両NA219 閲囨牱鍋忓樊銆佸崗璁簭鍒楀寲寰€杩斻€? * **闆嗘垚**锛欻TTP RTT p99 < 50ms锛沇S RTT p99 < 20ms锛涙柇缃?5s 鍐呰嚜鍔ㄩ噸杩炪€? * **瑙嗚**锛欰rUco 璺熻釜鎴愬姛鐜?> 99% (1.4mx0.8m 妗岄潰锛岃嚜鐒跺厜)锛汚prilTag 妫€娴?> 95% @ 1m銆? * **鑷姩鍥炲厖**锛?0 娆￠殢鏈鸿捣鐐瑰埌鍥炴々鎴愬姛鐜?> 90%锛屽崟娆″洖妗?< 60s銆? * **閬块殰**锛?00 娆￠殢鏈洪殰纰嶅垎甯冿紝纰版挒娆℃暟 = 0銆? * **鍏呯數**锛?% 鍒?80% 鈮?60 min锛涚嚎鍦堣〃闈㈡俯搴?鈮?50掳C銆? * **SDK**锛歅ython 3.10/3.11/3.12 鍦?Linux/macOS/Windows 鍚勮窇閫?quickstart锛沵ypy --strict 闆堕敊璇€? * **缁埅**锛氬崟娆″厖鐢佃繛缁椹?鈮?40 min銆?
 ## 9. 鍏抽敭鍐崇瓥锛堝凡閿佸畾锛?
 | 椤?| 閫夋嫨 | 澶囨敞 |
 | :--- | :--- | :--- |
 | 瑙嗚璁＄畻浣嶇疆 | 涓绘満 PC + USB 鎽勫儚澶?| 宸茬瓟 |
 | 鍏呯數鏂瑰紡 | 鏃犵嚎鎰熷簲 (Qi 5W) | 宸茬瓟锛涚害 5W 鍏呯數閫熺巼闇€鐢垫睜 鈮?2500mAh |
 | 鎵╁睍瑙︾偣 | 3.3V/GND/SDA/SCL/INT (5-pin) | 宸茬瓟 |
 | 瀹氫綅鏂瑰紡 | 杞﹂《 ArUco + dock AprilTag 鍙屾簮 | 宸茬瓟锛涘彲鎶楄瑙夐伄鎸?|
 | SDK 褰㈡€?| Python 浼樺厛 + 鍗忚鏂囨。 | 宸茬瓟 |

 ## 10. 鍋囪涓庨粯璁ゅ€硷紙璇锋牎瀵癸級

 * 妗岄潰灏哄 1.4m x 0.8m锛涙憚鍍忓ご瀹夎楂樺害 70cm銆? * 鎽勫儚澶?FOV 鈮?90掳锛屽垎杈ㄧ巼 1080p@30fps銆? * 1S 閿傜數姹?(3.7V / 1000mAh) 鍒?杩炵画琛岄┒绾?45 min锛?鈫?0% 鍏呯數绾?50 min銆? * N20 鐢垫満 + 7PPR 缂栫爜鍣ㄦ部鐢?v1锛涢棴鐜敱 ESP32 鍐呴儴瀹屾垚銆? * 瑙嗚寤惰繜 鈮?33ms (30Hz)锛涙帶鍒跺洖璺?鈮?50Hz銆? * Wi-Fi锛欰P+STA 鍙屾ā锛孉P 淇濈暀 v1 SSID 缁欐墜鏈?H5銆? * 鎵╁睍 I2C 榛樿閫熺巼 400kHz锛涘閮ㄦ€荤嚎涓婃媺 4.7k惟銆? * 妗岄潰杈圭紭瑙嗕负纭锛堥伩闅滅鍖猴級銆?
 ## 11. 寰呭姙涓庢湭鏉ュ伐浣?
 * ROS2 humble/jazzy 鍖咃紙v1.1锛夈€? * iOS / Android 鍘熺敓 SDK锛坴1.1锛夈€? * 澶氳溅鍗忓悓璋冨害 (v2)銆? * 妗岄潰澶栧満鏅殑杞婚噺 SLAM (v2)銆? * 宓屽叆寮?IMU (BNO085) 鍔犲叆杞︿綋锛屾彁楂樼煭鏆傝瑙変涪璺熻釜鏃剁殑浣嶅Э鎺ㄧ畻 (v2)銆? * "纾佸惛澶栬搴?锛氬紑绠卞嵆鐢ㄧ殑 OLED銆乀oF銆丷GB銆佽埖鏈恒€佸す鐖ā鍧?(涓?SDK 鍚屾鍙戝竷)銆?