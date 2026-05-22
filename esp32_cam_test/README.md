# ESP32-S3 + OV5640 - Test de Cámara

Sketch completo para probar la cámara OV5640 con una placa ESP32-S3 M16R8 (16MB Flash, 8MB PSRAM).

## Qué hace

- Inicializa la cámara OV5640 con los pines correctos para ESP32-S3
- Se conecta a tu WiFi
- Levanta un servidor web con:
  - **Página principal** (`http://IP/`) - Interfaz visual para ver el stream
  - **Stream MJPEG** (`http://IP:81/stream`) - Video en tiempo real
  - **Captura** (`http://IP/capture`) - Foto individual en JPG
  - **Estado** (`http://IP/status`) - Info del sistema en JSON
  - **Resolución** (`http://IP/resolution?res=low|med|high`) - Cambiar resolución en vivo

## Configuración en Arduino IDE

### 1. Instalar soporte ESP32

En Arduino IDE:
1. Ir a **File > Preferences**
2. En "Additional Board Manager URLs" agregar:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. Ir a **Tools > Board > Boards Manager**
4. Buscar "ESP32" e instalar **esp32 by Espressif Systems** (v2.x o v3.x)

### 2. Configurar la placa

En **Tools**, configurar:

| Opción | Valor |
|--------|-------|
| Board | ESP32S3 Dev Module |
| PSRAM | OPI PSRAM |
| Flash Size | 16MB (128Mb) |
| Partition Scheme | Huge APP (3MB No OTA/1MB SPIFFS) |
| Upload Speed | 921600 |
| USB CDC On Boot | Enabled |

### 3. Configurar WiFi

En el archivo `.ino`, cambiar estas líneas con los datos de tu red:

```cpp
const char* ssid     = "TU_WIFI";
const char* password = "TU_PASSWORD";
```

### 4. Subir y probar

1. Conectar la ESP32-S3 por USB
2. Seleccionar el puerto COM correcto en **Tools > Port**
3. Click en **Upload**
4. Abrir **Serial Monitor** a 115200 baud
5. Esperar a que se conecte al WiFi
6. Copiar la IP que aparece y abrirla en el navegador

## Pinout de la cámara

```
OV5640 Pin  →  ESP32-S3 GPIO
─────────────────────────────
XCLK        →  GPIO 15
SIOD (SDA)  →  GPIO 4
SIOC (SCL)  →  GPIO 5
D0 (Y2)     →  GPIO 11
D1 (Y3)     →  GPIO 9
D2 (Y4)     →  GPIO 8
D3 (Y5)     →  GPIO 10
D4 (Y6)     →  GPIO 12
D5 (Y7)     →  GPIO 18
D6 (Y8)     →  GPIO 17
D7 (Y9)     →  GPIO 16
VSYNC       →  GPIO 6
HREF        →  GPIO 7
PCLK        →  GPIO 13
PWDN        →  No conectado (-1)
RESET       →  No conectado (-1)
```

> Si tu placa tiene un pinout diferente, modificá los `#define` al principio del `.ino`.

## Resoluciones disponibles

| Nivel | Resolución | Uso recomendado |
|-------|-----------|-----------------|
| low | QVGA (320x240) | Stream rápido, bajo ancho de banda |
| med | VGA (640x480) | Balance entre calidad y velocidad |
| high | SXGA (1280x1024) | Máxima calidad (requiere PSRAM) |

## Solución de problemas

| Problema | Solución |
|----------|----------|
| `Error cámara: 0x105` | Verificar conexión del flex de la cámara |
| `Error cámara: 0x106` | Pines incorrectos - revisar pinout |
| No se conecta WiFi | Verificar SSID y contraseña |
| Stream lento | Bajar resolución con el botón "Baja Res" |
| Imagen invertida | Cambiar `set_hmirror` o `set_vflip` a 1 en el código |
