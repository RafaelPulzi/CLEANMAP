<div align="center">

![Arduino](https://img.shields.io/badge/Arduino-UNO%20%7C%20Nano-blue?logo=arduino&logoColor=white)
![ESP32](https://img.shields.io/badge/ESP32-WROOM%20Gateway-red?logo=espressif&logoColor=white)
![GPS](https://img.shields.io/badge/GPS-NEO--6M-orange)
![Node.js](https://img.shields.io/badge/Node.js-%3E%3D18-green?logo=node.js&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)
[![MIT License](https://img.shields.io/github/license/RafaelPulzi/SistemaSolarJS?color=blue&label=License)](https://github.com/RafaelPulzi/SistemaSolarJS/blob/main/LICENSE)

</div>

# 🛰️ ESP32 + Arduino GPS Data Sender

### 📖 Descrição do Repositório

Este projeto integra um **Arduino com módulo GPS** e um **ESP32**, permitindo a **coleta e transmissão automática de coordenadas geográficas** para um **servidor Node.js (Docker ou local)**.
O Arduino é responsável por ler os dados do GPS e enviar as coordenadas formatadas em JSON via comunicação serial. O ESP32 atua como um gateway inteligente, recebendo essas informações e publicando-as em um endpoint HTTP configurável.

Ideal para aplicações de **rastreamento veicular, monitoramento ambiental, logística inteligente e protótipos IoT**.

---

## ⚙️ Arquitetura do Sistema

```
[Módulo GPS] → [Arduino UNO/Nano] → Serial → [ESP32-WROOM] → HTTP POST → [Servidor Node.js / Docker]
```

* **Arduino**: coleta latitude/longitude do GPS e envia em JSON pela serial.
* **ESP32**: recebe as coordenadas, conecta ao Wi-Fi e envia para uma API HTTP.
* **Servidor Node.js (localhost:3004)**: processa os dados e pode gerar mapas ou imagens de rota.

---

## 🔧 Requisitos de Hardware

| Componente                 | Função                                     |
| -------------------------- | ------------------------------------------ |
| 🧭 Módulo GPS (ex: NEO-6M) | Coleta coordenadas de localização          |
| 🔌 Arduino UNO / Nano      | Interpreta sinais NMEA do GPS              |
| 📡 ESP32-WROOM             | Conecta ao Wi-Fi e envia dados ao servidor |
| 🔋 Jumpers / Cabos Dupont  | Comunicação Serial entre Arduino e ESP32   |

### 🔌 Conexões

| Arduino | GPS | ESP32    |
| ------- | --- | -------- |
| RX (4)  | TX  | TX2 (17) |
| TX (3)  | RX  | RX2 (16) |
| GND     | GND | GND      |
| 5V      | VCC | —        |

> ⚠️ Atenção:
>
> * O Arduino deve estar **alimentado via USB**.
> * O ESP32 **não deve ser alimentado diretamente pelo 5V do Arduino**, use alimentação USB separada ou regulada (3.3V).
> * Ambos devem **compartilhar o mesmo GND**.

---

## 💾 Código do Arduino

O Arduino lê dados do módulo GPS (via `TinyGPSPlus`) e imprime na Serial em formato JSON:

```cpp
{"latitude": -23.499873, "longitude": -46.695907, "fixAgeMs": 937, "ts": 2645600}
```

Esses dados são lidos pelo ESP32 via UART.

---

## 📡 Código do ESP32

O ESP32:

1. Conecta ao Wi-Fi.
2. Recebe o JSON da serial.
3. Envia as coordenadas para o servidor configurado (`serverUrl`).

O payload enviado é compatível com uma API REST padrão:

```json
{
  "origem_latitude": -23.499873,
  "origem_longitude": -46.695907,
  "destino_latitude": -23.555000,
  "destino_longitude": -46.639000
}
```

---

## ⚙️ Configuração

### 1. Instalar bibliotecas no Arduino IDE:

* **ArduinoJson**
* **TinyGPSPlus**
* **WiFi** (nativo no ESP32)
* **HTTPClient** (nativo no ESP32)

### 2. Configurar o código:

No arquivo do ESP32, altere:

```cpp
const char* ssid = "SEU_WIFI";
const char* password = "SUA_SENHA";
const char* serverUrl = "http://SEU_IP:3004/api/gerar-imagem-rota";
```

Para obter o IP do seu servidor local (Windows):

```
ipconfig
```

Use o IPv4 mostrado (ex: `192.168.0.105`).

---

## 🧠 Funcionamento

1. O Arduino coleta dados GPS e envia via serial.
2. O ESP32 recebe, formata e envia via HTTP POST.
3. O servidor Node.js processa a rota e responde.
4. O sistema reinicia automaticamente em caso de desconexão Wi-Fi.

---

## 🧰 Exemplo de Resposta do Servidor

```
🌍 POST enviado (200): {"status":"ok","mensagem":"Imagem gerada com sucesso"}
```

---

## 🐳 Integração com Docker

Caso o servidor esteja rodando em Docker, use o **IP da rede do host** (ex: `172.17.0.1`) no campo `serverUrl`.

```cpp
const char* serverUrl = "http://172.17.0.1:3004/api/gerar-imagem-rota";
```



# 📸 Módulo de Captura de Imagens — ESP32-CAM

### 🧩 Descrição

O módulo **ESP32-CAM** atua como um subsistema independente de captura de imagens integrado ao projeto.
Sua função é registrar imagens periódicas de um ponto remoto e enviá-las automaticamente para um **repositório em nuvem (Backblaze B2)**, permitindo a análise posterior ou integração com o servidor principal (Docker).

Essa câmera pode ser instalada em locais estratégicos para **monitoramento de áreas, coleta de evidências visuais ou registro de eventos ambientais**, operando de forma autônoma, mas sincronizada com o restante da infraestrutura IoT do projeto.

---

### ⚙️ Arquitetura Expandida do Sistema

| Módulo                     | Função                                        | Comunicação   |
| -------------------------- | --------------------------------------------- | ------------- |
| Arduino UNO/Nano           | Leitura de dados GPS e envio em JSON          | Serial UART   |
| ESP32-WROOM                | Gateway de rede e envio de dados GPS via HTTP | Wi-Fi / HTTP  |
| **ESP32-CAM (AI Thinker)** | Captura e upload de imagens para Backblaze B2 | Wi-Fi / HTTPS |
| Servidor Node.js / Docker  | Processamento de dados, rotas e imagens       | API REST      |

Fluxo geral:

```
[Arduino UNO + GPS] → [ESP32-WROOM] → HTTP POST → [Servidor Docker]
                           ↘
                            ↘
                         [ESP32-CAM] → Upload → [Backblaze B2 / Docker]
```

---

### 🔧 Principais Funcionalidades da ESP32-CAM

* 📷 **Captura automática de imagens** em resolução VGA.
* 🌐 **Conexão Wi-Fi** configurável (SSID e senha personalizáveis).
* ☁️ **Autenticação e upload direto para Backblaze B2**, utilizando credenciais seguras.
* 🧠 **Processamento local básico**, reduzindo carga no servidor principal.
* ⏱️ **Envio periódico configurável** (a cada 60 segundos, por padrão).
* 🧾 **Logs via Serial Monitor** para depuração e validação de autenticação/upload.
* 🔄 **Reconexão automática** em caso de falha de rede.

---

### 🧰 Código e Estrutura

Arquivos principais do módulo ESP32-CAM:

| Arquivo                              | Descrição                                 |
| ------------------------------------ | ----------------------------------------- |
| `app_httpd.cpp`                      | Funções de inicialização da câmera e HTTP |
| `board_config.h`                     | Definições de pinos da placa AI Thinker   |
| `camera_index.h`                     | Interface web da câmera (caso ativada)    |
| `camera_pins.h`                      | Mapeamento dos pinos GPIO da câmera       |
| `ci.json`                            | Configurações de compilação               |
| `partitions.csv`                     | Layout de partições da memória Flash      |
| `tcc_v1_ino_copy_20251101111846.ino` | Código principal do firmware              |

---

### 🚀 Integração com Docker e o Projeto Principal

* O **servidor Node.js em Docker** pode consumir as imagens enviadas ao Backblaze, processando-as conforme necessário (ex: análise de resíduos, monitoramento urbano ou ambiental).
* A ESP32-CAM pode ser **adicionada a qualquer ponto do sistema**, operando de forma independente do Arduino e do ESP32 principal.
* Ideal para **monitoramento remoto, captura de imagens ambientais** e registro de eventos em tempo real.

---

### 🪛 Configurações Importantes

* Modifique o SSID e senha no início do código para sua rede Wi-Fi:

  ```cpp
  const char* ssid = "SEU_WIFI";
  const char* password = "SUA_SENHA";
  ```
* Configure suas credenciais Backblaze B2:

  ```cpp
  String keyID = "SEU_KEY_ID";
  String applicationKey = "SUA_APPLICATION_KEY";
  String bucketId = "SEU_BUCKET_ID";
  String bucketName = "NOME_DO_BUCKET";
  ```
* Intervalo de captura (em milissegundos):

  ```cpp
  delay(60000); // 60 segundos
  ```

---

### 🧩 Compatibilidade

| Placa                | Suporte                |
| -------------------- | ---------------------- |
| ESP32-CAM AI Thinker | ✅ Total                |
| ESP32-WROOM          | ⚙️ Gateway GPS         |
| Arduino UNO/Nano     | 🧭 GPS via TinyGPSPlus |


