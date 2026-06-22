 #include <cstddef>

 namespace deskcar {
 // Allocate a doc large enough for the full telemetry payload.
 // ArduinoJson 7 unified on JsonDocument; we size it via capacity.
 constexpr size_t PROTOCOL_DOC_SIZE = 1024;

 constexpr int PROTOCOL_VERSION = 1;

 // ---- commands (PC -> car) -------------------------------------------
 // body: {"type":"drive","left":-255..255,"right":-255..255}
 // body: {"type":"set_speed","value":0..255}
 // body: {"type":"stop"}
 // body: {"type":"scan_expansion"}
 // body: {"type":"reset"}

 // ---- events (car -> PC) ---------------------------------------------
 // {"type":"state", "ts":ms, "v":V, "i":mA, "soc":%, "charge":"charging|...", "exp":[...]}
 // {"type":"encoder", "left":c, "right":c, "dt":ms}
 // {"type":"device_attached","address":0x40}
 // {"type":"device_detached","address":0x40}
 // {"type":"error","msg":"..."}

 } // namespace deskcar
