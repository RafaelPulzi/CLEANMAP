<div align="center">

# 🧹 CLEANMAP — Sistema Inteligente de Priorização da Limpeza Urbana

**Visão computacional + IoT + roteamento otimizado para priorizar a coleta de resíduos sólidos urbanos.**

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![YOLOv11](https://img.shields.io/badge/YOLOv11s-Ultralytics-00FFFF?logo=pytorch&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-%3E%3D18-339933?logo=node.js&logoColor=white)
![Docker](https://img.shields.io/badge/Docker%20Compose-orquestrado-2496ED?logo=docker&logoColor=white)
![ESP32](https://img.shields.io/badge/ESP32%20%2B%20Arduino-IoT-E7352C?logo=espressif&logoColor=white)
![Patente](https://img.shields.io/badge/INPI-Patente%20registrada-success)
![License](https://img.shields.io/badge/License-MIT-blue)

</div>

> **Trabalho de Conclusão de Curso — Ciência da Computação, Universidade Paulista (UNIP), 2026.**
> Projeto com **patente registrada** (ver [`docs/Certificado_Patente_INPI.pdf`](docs/Certificado_Patente_INPI.pdf)) e monografia completa em [`docs/`](docs/).
>
> Este repositório **consolida, em um só lugar**, os microsserviços, o firmware e a documentação que originalmente ficavam espalhados em seis repositórios separados (ver [Repositórios de origem](#-repositórios-de-origem-citação)). O objetivo é apresentar o sistema ponta a ponta como uma única solução coerente.

---

## O problema

A gestão de resíduos sólidos urbanos (RSU) no Brasil esbarra em coleta reativa e rotas fixas: as equipes passam onde está programado, não onde há de fato acúmulo de lixo. Isso desperdiça recurso público (combustível, hora de equipe) em pontos vazios e deixa pontos críticos sem atendimento. Faltava uma forma **automática** de (1) enxergar onde há resíduo descartado, (2) classificar o que é, e (3) transformar isso em uma rota de coleta priorizada — sem depender de alguém observando câmera por câmera.

## A solução

Um pipeline embarcado + nuvem + visão computacional que fecha o ciclo "imagem → classificação → rota":

1. **Captura (IoT):** câmeras **ESP32-CAM** registram imagens de vias públicas em intervalos configuráveis e sobem para armazenamento em nuvem (Backblaze B2, compatível com S3). Um **Arduino UNO + GPS NEO-6M** fornece a geolocalização, publicada por um gateway **ESP32** / servidor Node.js.
2. **Classificação (CNN):** um modelo **YOLOv11s** (Ultralytics/PyTorch) servido por uma API Flask detecta o tipo de resíduo (papelão, garrafa, lata, tênis) e só dá sequência quando a confiança passa de **80%**.
3. **Roteamento:** confirmada a detecção, um microsserviço Node.js calcula a rota de coleta e renderiza o mapa com **Leaflet.js**.
4. **Orquestração:** tudo sobe com um comando via **Docker Compose**, com `healthcheck` e ordem de inicialização garantida entre os serviços.

## O resultado

- **82% de acurácia média** na detecção de resíduos em ambiente controlado (resultado do sistema reportado na monografia).
- Modelo de visão com **mAP50 de 0,939** e **precisão de 0,91** no conjunto de validação (293 imagens, 510 instâncias) — destaque para a classe *lata* (mAP50 0,976).
- Pipeline completo sobe com **um único `docker compose up --build`**, eliminando as falhas de "conexão recusada" que aconteciam ao iniciar os serviços manualmente.
- Cada serviço Python tem **suíte de testes automatizados (Pytest)** cobrindo caminhos de sucesso, validação e *fallback*.

---

## 🏗️ Arquitetura

```
                        ☁️  Backblaze B2 (armazenamento S3-compatível)
                                   ▲  (upload de imagens)
                                   │
 [ESP32-CAM] ──captura───────────┘
 [Arduino UNO + GPS NEO-6M] ──serial──▶ [ESP32 gateway / Servidor GEO Node.js] ──coordenadas──┐
                                                                                              │
          ┌───────────────────────────────────────────────────────────────────────────────┘
          ▼
 ┌─────────────────┐   imagem    ┌────────────────────┐  classe+conf.  ┌──────────────────────┐
 │  data-workflow  │ ──────────▶ │   ml-model-cnn      │ ─────────────▶ │   routing-machine    │
 │  (Python)       │             │  (YOLOv11s / Flask) │  (se > 80%)    │  (Node.js / Leaflet) │
 │  busca imagem,  │ ◀────────── │  detecta resíduo    │                │  gera imagem da rota │
 │  valida, mede   │  resultado  └────────────────────┘                └──────────────────────┘
 └─────────────────┘
          ▲
          └────────── orquestrado por  ▶  [ orchestrator — Docker Compose ]
```

## 📦 Componentes deste repositório

| Pasta | Stack | Papel no sistema |
|---|---|---|
| [`services/ml-model-cnn/`](services/ml-model-cnn/) | Python · Flask · YOLOv11s · PyTorch · OpenCV | API de visão computacional: classifica o resíduo e decide se aciona a rota. |
| [`services/data-workflow/`](services/data-workflow/) | Python · boto3 · Pillow · Requests | Pipeline que busca a imagem mais recente no B2, valida, redimensiona, chama o modelo e registra o resultado com *fallback* em cascata. |
| [`services/routing-machine/`](services/routing-machine/) | Node.js · Express · Leaflet.js · Puppeteer | Calcula a rota entre origem/destino e gera a imagem estática do mapa. |
| [`services/orchestrator/`](services/orchestrator/) | Docker Compose | Sobe os três serviços na ordem certa, com rede e volume compartilhado. |
| [`firmware/gps-tracker-esp32/`](firmware/gps-tracker-esp32/) | C/C++ · Arduino · ESP32 · ESP32-CAM | Firmware de captura de GPS (Arduino→ESP32 via serial) e de captura/upload de imagem (ESP32-CAM→B2). |
| [`firmware/geo-server-arduino/`](firmware/geo-server-arduino/) | Node.js · SerialPort | Servidor de geolocalização que lê o GPS pela serial e expõe a última posição por HTTP. |
| [`docs/`](docs/) | — | Monografia completa (TCC), apresentação e certificado de patente (INPI). |

## 🚀 Como executar o pipeline completo

```bash
# a partir de services/orchestrator/
cp .env.example .env     # preencha MAPBOX_API_KEY
docker compose up --build
```

> Os três serviços (`routing-api`, `ml-api`, `pipeline-core`) sobem na ordem correta graças aos `healthcheck` + `depends_on`. Cada serviço também pode ser executado isolado — veja o README dentro de cada pasta.

Para acompanhar os logs organizados por serviço:

```bash
docker compose logs -f pipeline-core ml-api routing-api
```

## 🔐 Segurança

- **Nenhum segredo é versionado.** Chaves (Mapbox, Backblaze B2) são injetadas por variável de ambiente (`.env`, fora do controle de versão). O `.env.example` mostra o formato esperado.
- As APIs Python rodam em container com **usuário não-root**.

## 👥 Autoria

TCC desenvolvido por cinco autores na UNIP (2026), sob orientação do Prof. Me. Marco Gomes:

- **Rafael Atala Pulzi** — subsistema de **geolocalização e IoT** (firmware Arduino/ESP32 do GPS, gateway ESP32, servidor GEO em Node.js) e consolidação/engenharia deste repositório.
- **Gustavo de Almeida Pacheco** — modelo de visão computacional (CNN/YOLO), pipeline de dados, microsserviço de roteamento e orquestração.
- **João Pedro Grasson de Brito**, **Bruno Capovilla**, **Matheus Ferreira** — pesquisa, modelagem e validação.

## 🔗 Repositórios de origem (citação)

Este repositório consolida o código que originalmente vivia em repositórios separados. Os repositórios abaixo permanecem como referência e crédito aos respectivos autores:

- `TCC_Model1_CNN_SWM` — https://github.com/Gusta9s/TCC_Model1_CNN_SWM *(Gustavo Pacheco)*
- `TCC_workflow_data_SWM` — https://github.com/Gusta9s/TCC_workflow_data_SWM *(Gustavo Pacheco)*
- `TCC-Routing-Machine-SWM` — https://github.com/Gusta9s/TCC-Routing-Machine-SWM *(Gustavo Pacheco)*
- `TCC_Orchestrator` — https://github.com/Gusta9s/TCC_Orchestrator *(Gustavo Pacheco)*
- `APS_Android_SWM_Images` — https://github.com/Gusta9s/APS_Android_SWM_Images *(app mobile de captura; não incluído aqui)*
- `IoT-GPS-Tracker-System---Arduino-ESP32-Gateway` — https://github.com/RafaelPulzi/IoT-GPS-Tracker-System---Arduino-ESP32-Gateway *(Rafael Pulzi)*
- `ServidorGEO-ArduinoUno` — https://github.com/RafaelPulzi/ServidorGEO-ArduinoUno *(Rafael Pulzi)*
- `Patentes` — https://github.com/RafaelPulzi/Patentes *(certificado de patente)*

## 📄 Licença

[MIT](LICENSE).
