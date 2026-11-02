<!-- Shields do Projeto -->
<div align="center">

![MIT License](https://img.shields.io/github/license/RafaelPulzi/SistemaSolarJS?color=blue&label=License)
![Versão do Node](https://img.shields.io/badge/Node.js-%3E%3D18-green?logo=node.js&logoColor=white)
![Plataforma](https://img.shields.io/badge/Arduino%20UNO-Compatible-blue?logo=arduino&logoColor=white)
![GPS](https://img.shields.io/badge/GPS-NEO--6M-orange)
![Status](https://img.shields.io/badge/status-ativo-brightgreen)


</div>

# Servidor de Geolocalização com Arduino UNO + GPS

Este projeto implementa um **servidor de geolocalização** que lê latitude e longitude de um módulo GPS (ex.: NEO-6M) conectado a um **Arduino UNO**, envia os dados em formato **JSON pela Serial**, e expõe uma API HTTP na porta **3006**.

---

## 🛰️ 1. Hardware Necessário

* Arduino UNO
* Módulo GPS (ex.: NEO-6M)
* Cabo USB para o Arduino

### Ligações

* **TX do GPS → TX3**
* **RX do GPS → RX4**
* **GND do GPS → GND do Arduino UNO**
* **VCC do GPS → 3.3V do Arduino UNO**


---

## 💻 2. Código do Arduino

O sketch `gps_arduino.ino` usa a biblioteca [TinyGPSPlus](https://github.com/mikalhart/TinyGPSPlus) e envia JSON via Serial.

Para gravar no Arduino:

1. Abra o arquivo `gps_arduino.ino` na **Arduino IDE**.
2. Selecione a porta correta (ex.: COM3).
3. Faça o upload.
4. ⚠️ Feche o **Serial Monitor da IDE** após o upload, senão a porta fica ocupada.


```C
#include <TinyGPSPlus.h>
#include <SoftwareSerial.h>

// Pinos do Arduino conectados ao GPS
static const int RXPin = 4, TXPin = 3;
static const uint32_t GPSBaud = 9600;

// Cria a serial de comunicação com o GPS
SoftwareSerial gpsSerial(RXPin, TXPin);

// Objeto TinyGPSPlus
TinyGPSPlus gps;

unsigned long lastSend = 0;
const unsigned long sendInterval = 2000; // envia no máximo a cada 2s

void setup() {
  // Inicializa comunicação serial com o PC
  Serial.begin(9600);
  // Inicializa comunicação serial com o GPS
  gpsSerial.begin(GPSBaud);

  delay(2000);
  Serial.println("INICIANDO_GPS_JSON");
}

void loop() {
  // Ler tudo que chega pela UART do GPS
  while (gpsSerial.available() > 0) {
    gps.encode(gpsSerial.read());
  }

  // Se houver localização válida e for hora de enviar
  if (gps.location.isValid() && (millis() - lastSend >= sendInterval)) {
    lastSend = millis();

    double lat = gps.location.lat();
    double lng = gps.location.lng();
    unsigned long fixAge = gps.location.age(); // ms desde o fix

    // Monta payload JSON simples — uma linha por leitura
    Serial.print("{");
    Serial.print("\"latitude\":");
    Serial.print(lat, 6);
    Serial.print(",\"longitude\":");
    Serial.print(lng, 6);
    Serial.print(",\"fixAgeMs\":");
    Serial.print(fixAge);
    Serial.print(",\"ts\":");
    Serial.print(millis());
    Serial.println("}");
  }
}

```

---

## 🌐 3. Servidor Node.js

O backend (`index.js`) lê a porta serial e expõe uma API HTTP.

### Requisitos

* Node.js **>=18** (testado com Node 22.19.0)
* npm (vem junto com o Node.js)

### Instalação

No diretório do projeto (`ServidorGEO-ArduinoUno`):

```powershell
npm install
```

### Executar

No Windows (ajuste a COM conforme necessário):

```powershell
set SERIAL_PORT=COM3
set BAUD_RATE=9600
set PORT=3006
npm start
```

No Linux/macOS:

```bash
export SERIAL_PORT=/dev/ttyACM0
export BAUD_RATE=9600
export PORT=3006
npm start
```

Saída esperada:

```
Geo server rodando na porta 3006
Serial aberta em COM3 @ 9600 baud
```

---

## 📡 4. Endpoints Disponíveis

### `GET /health`

Verifica se o servidor está ativo.
**Exemplo:**

```json
{
  "status": "ok",
  "serialPort": "COM3"
}
```

### `GET /location`

Retorna a última posição recebida do Arduino.
**Exemplo:**

```json
{
  "latitude": -23.550520,
  "longitude": -46.633308,
  "fixAgeMs": 300,
  "ts": 12345678
}
```

* Se não houver dados ainda, retorna `204 No Content`.

---

## 🐳 5. Docker (opcional)

Você pode rodar o backend em um container.

### Build da imagem

```bash
docker build -t geoserver .
```

### Rodar o container (Linux)

```bash
docker run -it --rm \
  --device=/dev/ttyACM0:/dev/ttyACM0 \
  -e SERIAL_PORT=/dev/ttyACM0 \
  -e BAUD_RATE=9600 \
  -p 3006:3006 \
  geoserver
```

> ⚠️ No Windows, containers não acessam COM diretamente. Use o Node.js local.

---

## 🚀 6. Fluxo de execução recomendado

1. Faça o upload do sketch no Arduino.
2. Feche o Serial Monitor da IDE.
3. Suba o servidor Node (`npm start`).
4. Teste os endpoints via navegador ou `curl`.
5. Use `/health` como healthcheck para orquestração de serviços em sequência.

---

## 📌 Notas

* O GPS pode levar até 3 minutos para fixar sinal na primeira vez.
* O servidor só armazena a **última posição recebida**. Para histórico, você pode adaptar para salvar em banco de dados.
* Se quiser logar cada linha recebida do Arduino para debug, adicione no `index.js`:

  ```js
  parser.on('data', line => console.log('[RAW]', line));
  ```

