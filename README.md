# PokeDraw - Dibuja un Pokemon y la IA lo identifica

App que analiza dibujos de Pokemon usando inteligencia artificial (CLIP de OpenAI).
Subis/sacas una foto de un dibujo y la IA te dice que Pokemon es, con HP, ataque, similitud y rareza.

## Arquitectura

```
[Celular con APK]  ---WiFi--->  [Arduino UNO Q con servidor Python]
     (Flet app)                    (FastAPI + CLIP AI)
```

- **Cliente (APK)**: App Android hecha con Flet (Python). Permite seleccionar una imagen y enviarla al servidor.
- **Servidor**: API REST con FastAPI que usa el modelo CLIP para analizar imagenes y determinar que Pokemon es.

## Estructura del proyecto

```
pokemonapp/
├── client/
│   ├── main.py              # App Flet (cliente Android)
│   └── build/               # Build Flutter (generado por flet build)
├── server/
│   ├── main.py              # Servidor FastAPI + CLIP
│   ├── deck.json            # Mazo de cartas guardadas
│   ├── images/              # Imagenes de referencia
│   └── uploads/             # Imagenes subidas por usuarios
├── requirements.txt          # Dependencias del servidor
└── README.md
```

## Paso 1: Generar el APK (en tu PC con Windows)

### Requisitos previos
- Python 3.10+ instalado
- Android Studio instalado (para el SDK de Android)

### Instrucciones

```bash
# 1. Instalar Flet
pip install flet==0.85.0

# 2. Ir a la carpeta del cliente
cd client

# 3. Generar el APK
flet build apk --project pokedraw --product "PokeDraw" --org "com.pokedraw"
```

El APK se genera en `client/build/apk/pokedraw.apk`.

### Instalar en el celular
1. Copiar el archivo `pokedraw.apk` al celular (por USB, email, o Google Drive)
2. En el celular, abrir el archivo APK
3. Si pide permiso para instalar apps desconocidas, aceptar
4. Instalar la app

## Paso 2: Configurar el servidor en Arduino UNO Q (con PuTTY)

### 2.1 Conectar la placa

1. Conecta la Arduino UNO Q a tu router con cable Ethernet o configurale el WiFi
2. Conecta la placa a la corriente con el cable USB-C
3. Espera 1-2 minutos a que arranque

### 2.2 Encontrar la IP de la placa

Desde tu PC Windows, abri CMD y escribi:
```
ping arduinoq.local
```
Si no funciona, fijate en tu router la lista de dispositivos conectados para ver la IP de la placa.

### 2.3 Conectarse con PuTTY

1. Abri PuTTY
2. En **Host Name**: pone la IP de la placa (ej: `192.168.1.105`)
3. En **Port**: deja `22`
4. En **Connection type**: selecciona `SSH`
5. Toca **Open**
6. Si te sale una advertencia de seguridad, toca **Accept**
7. Escribi el **usuario** de la placa (generalmente `arduino` o `root`)
8. Escribi la **contraseña** de la placa

### 2.4 Instalar el servidor (copiar estos comandos uno por uno en PuTTY)

```bash
# 1. Actualizar el sistema
sudo apt update && sudo apt upgrade -y

# 2. Instalar Python y herramientas necesarias
sudo apt install -y python3 python3-pip python3-venv git

# 3. Descargar el proyecto desde GitHub
git clone https://github.com/momitomylov123/pokemonapp.git
cd pokemonapp

# 4. Crear entorno virtual de Python
python3 -m venv venv
source venv/bin/activate

# 5. Instalar dependencias (version CPU, sin GPU)
pip install --extra-index-url https://download.pytorch.org/whl/cpu \
    fastapi uvicorn[standard] python-multipart \
    torch torchvision transformers pillow

# 6. Iniciar el servidor (la primera vez descarga el modelo, tarda ~10min)
cd server
python3 main.py
```

Cuando veas esto, el servidor esta listo:
```
Modelo listo.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2.5 Ver la IP de la placa (para ponerla en la app)

En la terminal de PuTTY, abri otra sesion o presiona Ctrl+C para parar el servidor, y escribi:
```bash
hostname -I
```
Te va a mostrar algo como `192.168.1.105`. Esa IP la pones en la app del celular.

Para volver a iniciar el servidor:
```bash
cd ~/pokemonapp && source venv/bin/activate && cd server && python3 main.py
```

### 2.6 (Opcional) Que el servidor arranque solo cuando prendas la placa

```bash
sudo tee /etc/systemd/system/pokedraw.service << EOF
[Unit]
Description=PokeDraw AI Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/pokemonapp/server
ExecStart=$HOME/pokemonapp/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable pokedraw.service
sudo systemctl start pokedraw.service

# Verificar que esta corriendo:
sudo systemctl status pokedraw.service
```

## Paso 3: Usar la app

1. **Conectar** el celular y la placa Arduino UNO Q a la **misma red WiFi**
2. **Abrir** la app PokeDraw en el celular
3. **Escribir** la IP de la placa en el campo de texto (ej: `192.168.1.105`)
4. **Tocar** "Seleccionar Imagen" y elegir una foto de un dibujo
5. **Tocar** "Enviar al servidor"
6. La IA analiza el dibujo y te muestra:
   - Nombre del Pokemon
   - HP (vida)
   - ATK (ataque)
   - Similitud (porcentaje)
   - Rareza (BASICO, COMUN, RARO, EPICO, LEGENDARIO)

## Notas importantes

- La **primera vez** que inicies el servidor, va a descargar el modelo CLIP (~600MB). Tarda unos minutos.
- El celular y la placa tienen que estar en la **misma red WiFi**.
- El modelo CLIP corre en **CPU** (no necesita GPU).
- Con 2GB de RAM, el servidor funciona pero puede tardar unos segundos en responder.
- Si tenes la version de 4GB de RAM, va a ser mas rapido.

## Tecnologias usadas

- **Servidor**: Python, FastAPI, PyTorch, CLIP (openai/clip-vit-base-patch32)
- **Cliente**: Python, Flet 0.85 (compila a APK con Flutter)
- **Hardware**: Arduino UNO Q (Qualcomm Dragonwing QRB2210 + Linux Debian)
