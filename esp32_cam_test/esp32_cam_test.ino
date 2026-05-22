/*
  ESP32-S3 M16R8 + OV5640 - Test de cámara con streaming web
  
  Placa: ESP32-S3 DevKitC (o similar con OV5640)
  
  Instrucciones:
  1. En Arduino IDE, instalar el paquete ESP32 (Espressif Systems) desde Board Manager
  2. Seleccionar placa: "ESP32S3 Dev Module"
  3. Configurar:
     - PSRAM: "OPI PSRAM" (importante para M16R8)
     - Flash Size: "16MB"
     - Partition Scheme: "Huge APP (3MB No OTA/1MB SPIFFS)"
  4. Cambiar TU_WIFI y TU_PASSWORD por los datos de tu red WiFi
  5. Subir el sketch
  6. Abrir Serial Monitor a 115200 baud
  7. Copiar la IP que aparece y abrirla en el navegador
*/

#include "esp_camera.h"
#include <WiFi.h>
#include "esp_http_server.h"

// ===== CONFIGURACIÓN WIFI =====
const char* ssid     = "TU_WIFI";
const char* password = "TU_PASSWORD";

// ===== Pines de cámara para ESP32-S3 con OV5640 =====
#define PWDN_GPIO_NUM     -1
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM     15
#define SIOD_GPIO_NUM     4
#define SIOC_GPIO_NUM     5

#define Y9_GPIO_NUM       16
#define Y8_GPIO_NUM       17
#define Y7_GPIO_NUM       18
#define Y6_GPIO_NUM       12
#define Y5_GPIO_NUM       10
#define Y4_GPIO_NUM       8
#define Y3_GPIO_NUM       9
#define Y2_GPIO_NUM       11

#define VSYNC_GPIO_NUM    6
#define HREF_GPIO_NUM     7
#define PCLK_GPIO_NUM     13

// ===== Variables globales =====
httpd_handle_t stream_httpd = NULL;
httpd_handle_t camera_httpd = NULL;

// ===== Boundary para MJPEG stream =====
#define PART_BOUNDARY "123456789000000000000987654321"
static const char* _STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* _STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* _STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

// ===== Página HTML con visor de stream =====
static const char PROGMEM INDEX_HTML[] = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ESP32-S3 CAM - OV5640</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      background: #1a1a2e;
      color: #eee;
      text-align: center;
      margin: 0;
      padding: 20px;
    }
    h1 { color: #e94560; }
    h2 { color: #0f3460; background: #e94560; display: inline-block; padding: 5px 15px; border-radius: 5px; }
    img {
      max-width: 100%;
      border: 3px solid #e94560;
      border-radius: 10px;
      margin: 10px 0;
    }
    .btn {
      background: #e94560;
      color: white;
      border: none;
      padding: 12px 30px;
      font-size: 16px;
      border-radius: 8px;
      cursor: pointer;
      margin: 5px;
      text-decoration: none;
      display: inline-block;
    }
    .btn:hover { background: #c73050; }
    .info {
      background: #16213e;
      padding: 15px;
      border-radius: 10px;
      margin: 15px auto;
      max-width: 500px;
      text-align: left;
    }
    .info p { margin: 5px 0; }
    .status { color: #4ecca3; font-weight: bold; }
    #stream-container { margin: 20px 0; }
  </style>
</head>
<body>
  <h1>🎥 ESP32-S3 CAM Test</h1>
  <h2>OV5640</h2>
  
  <div class="info">
    <p><strong>Placa:</strong> ESP32-S3 M16R8</p>
    <p><strong>Cámara:</strong> OV5640 (5MP)</p>
    <p><strong>Estado:</strong> <span class="status">✅ Conectada</span></p>
  </div>

  <div>
    <button class="btn" onclick="startStream()">▶ Ver Stream</button>
    <button class="btn" onclick="stopStream()">⏹ Parar</button>
    <a class="btn" href="/capture" target="_blank">📸 Captura</a>
    <button class="btn" onclick="changeRes('low')">Baja Res</button>
    <button class="btn" onclick="changeRes('med')">Media Res</button>
    <button class="btn" onclick="changeRes('high')">Alta Res</button>
  </div>

  <div id="stream-container">
    <img id="stream" src="" alt="Stream de cámara">
  </div>

  <div class="info">
    <p><strong>Endpoints disponibles:</strong></p>
    <p>📺 Stream: <code>/stream</code></p>
    <p>📸 Captura: <code>/capture</code></p>
    <p>📊 Estado: <code>/status</code></p>
    <p>🔧 Resolución: <code>/resolution?res=low|med|high</code></p>
  </div>

  <script>
    function startStream() {
      var streamUrl = window.location.protocol + '//' + window.location.hostname + ':81/stream';
      document.getElementById('stream').src = streamUrl;
    }
    function stopStream() {
      document.getElementById('stream').src = '';
    }
    function changeRes(level) {
      fetch('/resolution?res=' + level)
        .then(r => r.text())
        .then(t => alert(t));
    }
    // Auto-iniciar stream
    window.onload = function() { startStream(); };
  </script>
</body>
</html>
)rawliteral";

// ===== Handler: Página principal =====
static esp_err_t index_handler(httpd_req_t *req) {
  httpd_resp_set_type(req, "text/html");
  return httpd_resp_send(req, INDEX_HTML, strlen(INDEX_HTML));
}

// ===== Handler: Captura una foto =====
static esp_err_t capture_handler(httpd_req_t *req) {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Error: no se pudo capturar frame");
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }

  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=captura.jpg");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  esp_err_t res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
  return res;
}

// ===== Handler: Stream MJPEG =====
static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t *fb = NULL;
  esp_err_t res = ESP_OK;
  char part_buf[64];

  res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
  if (res != ESP_OK) return res;

  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  while (true) {
    fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Error capturando frame");
      res = ESP_FAIL;
      break;
    }

    size_t hlen = snprintf(part_buf, 64, _STREAM_PART, fb->len);
    res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, part_buf, hlen);
    }
    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
    }

    esp_camera_fb_return(fb);

    if (res != ESP_OK) break;
  }

  return res;
}

// ===== Handler: Estado del sistema =====
static esp_err_t status_handler(httpd_req_t *req) {
  char buf[256];
  sensor_t *s = esp_camera_sensor_get();
  
  snprintf(buf, sizeof(buf),
    "{\"camera\":\"OV5640\",\"framesize\":%d,\"quality\":%d,"
    "\"wifi_rssi\":%d,\"free_heap\":%lu,\"psram_free\":%lu}",
    s->status.framesize, s->status.quality,
    WiFi.RSSI(), (unsigned long)ESP.getFreeHeap(),
    (unsigned long)ESP.getFreePsram()
  );

  httpd_resp_set_type(req, "application/json");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(req, buf, strlen(buf));
}

// ===== Handler: Cambiar resolución =====
static esp_err_t resolution_handler(httpd_req_t *req) {
  char buf[32];
  size_t buf_len = httpd_req_get_url_query_len(req) + 1;

  if (buf_len > 1 && buf_len <= sizeof(buf)) {
    httpd_req_get_url_query_str(req, buf, buf_len);

    char param[10];
    if (httpd_query_key_value(buf, "res", param, sizeof(param)) == ESP_OK) {
      sensor_t *s = esp_camera_sensor_get();

      if (strcmp(param, "low") == 0) {
        s->set_framesize(s, FRAMESIZE_QVGA);    // 320x240
        httpd_resp_sendstr(req, "Resolución: QVGA (320x240)");
      } else if (strcmp(param, "med") == 0) {
        s->set_framesize(s, FRAMESIZE_VGA);      // 640x480
        httpd_resp_sendstr(req, "Resolución: VGA (640x480)");
      } else if (strcmp(param, "high") == 0) {
        s->set_framesize(s, FRAMESIZE_SXGA);     // 1280x1024
        httpd_resp_sendstr(req, "Resolución: SXGA (1280x1024)");
      } else {
        httpd_resp_sendstr(req, "Opciones: low, med, high");
      }
      return ESP_OK;
    }
  }

  httpd_resp_sendstr(req, "Uso: /resolution?res=low|med|high");
  return ESP_OK;
}

// ===== Iniciar servidores HTTP =====
void startCameraServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;

  // Servidor principal (puerto 80)
  httpd_uri_t index_uri = {
    .uri       = "/",
    .method    = HTTP_GET,
    .handler   = index_handler,
    .user_ctx  = NULL
  };
  httpd_uri_t capture_uri = {
    .uri       = "/capture",
    .method    = HTTP_GET,
    .handler   = capture_handler,
    .user_ctx  = NULL
  };
  httpd_uri_t status_uri = {
    .uri       = "/status",
    .method    = HTTP_GET,
    .handler   = status_handler,
    .user_ctx  = NULL
  };
  httpd_uri_t resolution_uri = {
    .uri       = "/resolution",
    .method    = HTTP_GET,
    .handler   = resolution_handler,
    .user_ctx  = NULL
  };

  Serial.println("Iniciando servidor web en puerto 80...");
  if (httpd_start(&camera_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(camera_httpd, &index_uri);
    httpd_register_uri_handler(camera_httpd, &capture_uri);
    httpd_register_uri_handler(camera_httpd, &status_uri);
    httpd_register_uri_handler(camera_httpd, &resolution_uri);
    Serial.println("Servidor web iniciado OK");
  }

  // Servidor de stream (puerto 81)
  config.server_port = 81;
  config.ctrl_port += 1;

  httpd_uri_t stream_uri = {
    .uri       = "/stream",
    .method    = HTTP_GET,
    .handler   = stream_handler,
    .user_ctx  = NULL
  };

  Serial.println("Iniciando servidor de stream en puerto 81...");
  if (httpd_start(&stream_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(stream_httpd, &stream_uri);
    Serial.println("Servidor de stream iniciado OK");
  }
}

// ===== SETUP =====
void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();
  Serial.println("=================================");
  Serial.println(" ESP32-S3 + OV5640 Camera Test");
  Serial.println("=================================");

  // Configurar cámara
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode    = CAMERA_GRAB_LATEST;

  // Con PSRAM disponible (M16R8 tiene 8MB), usar mayor resolución
  if (psramFound()) {
    Serial.println("PSRAM detectada! Usando alta resolución.");
    config.frame_size   = FRAMESIZE_SXGA;    // 1280x1024
    config.jpeg_quality = 10;                 // Mejor calidad (0-63, menor = mejor)
    config.fb_count     = 2;                  // Doble buffer para streaming fluido
    config.fb_location  = CAMERA_FB_IN_PSRAM;
  } else {
    Serial.println("Sin PSRAM. Usando baja resolución.");
    config.frame_size   = FRAMESIZE_QVGA;    // 320x240
    config.jpeg_quality = 12;
    config.fb_count     = 1;
    config.fb_location  = CAMERA_FB_IN_DRAM;
  }

  // Inicializar cámara
  Serial.println("Inicializando cámara OV5640...");
  esp_err_t err = esp_camera_init(&config);

  if (err != ESP_OK) {
    Serial.printf("ERROR inicializando cámara: 0x%x\n", err);
    Serial.println("Verificá:");
    Serial.println("  - Que la cámara OV5640 esté bien conectada");
    Serial.println("  - Que los pines sean correctos para tu placa");
    Serial.println("  - Que el flex de la cámara no esté dañado");
    return;
  }

  Serial.println("Cámara OV5640 inicializada OK!");

  // Ajustes de imagen para OV5640
  sensor_t *s = esp_camera_sensor_get();
  if (s) {
    s->set_brightness(s, 0);     // -2 a 2
    s->set_contrast(s, 0);       // -2 a 2
    s->set_saturation(s, 0);     // -2 a 2
    s->set_whitebal(s, 1);       // Balance de blancos automático
    s->set_awb_gain(s, 1);       // Ganancia AWB
    s->set_wb_mode(s, 0);        // 0=Auto, 1=Sunny, 2=Cloudy, 3=Office, 4=Home
    s->set_aec2(s, 1);           // Exposición automática
    s->set_ae_level(s, 0);       // -2 a 2
    s->set_aec_value(s, 300);    // 0-1200
    s->set_agc_gain(s, 0);       // 0-30
    s->set_gainceiling(s, (gainceiling_t)6);  // 0-6
    s->set_hmirror(s, 0);        // Espejo horizontal (cambiar a 1 si la imagen sale invertida)
    s->set_vflip(s, 0);          // Voltear vertical (cambiar a 1 si la imagen sale al revés)
    Serial.println("Ajustes de imagen aplicados.");
  }

  // Conectar WiFi
  WiFi.begin(ssid, password);
  WiFi.setSleep(false);  // Desactivar sleep para mejor rendimiento de streaming

  Serial.print("Conectando a WiFi");
  int intentos = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    intentos++;
    if (intentos > 40) {  // 20 segundos de timeout
      Serial.println("\nERROR: No se pudo conectar al WiFi.");
      Serial.println("Verificá el SSID y contraseña.");
      return;
    }
  }

  Serial.println();
  Serial.println("=================================");
  Serial.println(" WiFi conectado!");
  Serial.printf(" SSID: %s\n", ssid);
  Serial.printf(" IP:   %s\n", WiFi.localIP().toString().c_str());
  Serial.printf(" RSSI: %d dBm\n", WiFi.RSSI());
  Serial.println("=================================");

  // Iniciar servidor web
  startCameraServer();

  Serial.println();
  Serial.println("╔═══════════════════════════════════════╗");
  Serial.println("║  CÁMARA LISTA!                        ║");
  Serial.printf( "║  Abrí en el navegador:                ║\n");
  Serial.printf( "║  http://%-30s ║\n", WiFi.localIP().toString().c_str());
  Serial.println("║                                       ║");
  Serial.printf( "║  Stream: http://%-21s  ║\n", (WiFi.localIP().toString() + ":81/stream").c_str());
  Serial.println("╚═══════════════════════════════════════╝");
}

// ===== LOOP =====
void loop() {
  // Monitoreo periódico del estado
  static unsigned long lastPrint = 0;
  if (millis() - lastPrint > 30000) {  // Cada 30 segundos
    lastPrint = millis();
    Serial.printf("[Estado] WiFi: %s | RSSI: %d dBm | Heap libre: %lu | PSRAM libre: %lu\n",
      WiFi.isConnected() ? "OK" : "DESCONECTADO",
      WiFi.RSSI(),
      (unsigned long)ESP.getFreeHeap(),
      (unsigned long)ESP.getFreePsram()
    );

    // Reconectar WiFi si se cayó
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("WiFi desconectado! Reconectando...");
      WiFi.reconnect();
    }
  }
}
