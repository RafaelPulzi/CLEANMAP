# TCC Model1 CNN SWM

API em **Python/Flask** que serve um modelo de detecção de objetos (**YOLOv11s**, via Ultralytics) para classificar imagens de resíduos descartados em quatro categorias (papelão, garrafa, lata e tênis). Quando a confiança da predição é suficiente, o serviço aciona automaticamente a API de geração de rotas do pipeline, conectando a etapa de "visão computacional" à etapa de "roteirização" sem intervenção manual.

Este repositório é um dos componentes do projeto de TCC **Gestão de Resíduos Sólidos Urbanos (SWM)**, composto pelos seguintes repositórios:

| Repositório | Papel no fluxo |
|---|---|
| [APS_Android_SWM_Images](https://github.com/Gusta9s/APS_Android_SWM_Images) | Aplicativo mobile (Expo/React Native) usado para capturar e enviar as fotos dos resíduos descartados. |
| [TCC_workflow_data_SWM](https://github.com/Gusta9s/TCC_workflow_data_SWM) | Pipeline em Python que baixa as imagens recebidas, trata os dados e orquestra as chamadas entre o modelo de classificação e o serviço de rotas. |
| **TCC_Model1_CNN_SWM** *(este repositório)* | API com o modelo de visão computacional (YOLOv11s) que classifica o tipo de resíduo na imagem e decide se aciona a geração de rota. |
| [TCC-Routing-Machine-SWM](https://github.com/Gusta9s/TCC-Routing-Machine-SWM) | Recebe origem/destino, calcula a rota, gera a imagem do mapa (Leaflet.js) e a salva em um volume Docker compartilhado. |
| [TCC_Orchestrator](https://github.com/Gusta9s/TCC_Orchestrator) | Orquestra, via Docker Compose, a subida integrada de todos os serviços (rede, volumes compartilhados e ordem de inicialização). |

## O problema

Depois que uma imagem de descarte chega ao pipeline, alguém (ou algo) precisa decidir, de forma automática e confiável, se aquele item pertence a uma das categorias de resíduo reciclável mapeadas — e com confiança suficiente para justificar acionar o restante do fluxo (geração de rota, registro do resultado, etc.). Sem essa etapa, o pipeline correria o risco de tratar fotos irrelevantes, borradas ou sem nenhum objeto reconhecível como se fossem descartes válidos, gerando rotas e resultados sem sentido a partir de imagens ruins. O desafio, portanto, é técnico: classificar imagens variadas com precisão suficiente e, principalmente, saber identificar quando **não** classificar (rejeitar a predição) em vez de forçar uma resposta.

## A solução

Optou-se por um modelo de detecção de objetos **YOLOv11s** (Ultralytics) em vez de um classificador de imagem simples, porque ele já localiza e identifica o objeto na cena (em vez de apenas dizer "a imagem é da classe X"), é leve o suficiente para rodar inferência sem exigir GPU dedicada em produção, e já embute pré-processamento e data augmentation otimizados internamente — eliminando a necessidade de um pipeline manual de tratamento de imagem. O modelo é servido atrás de uma API **Flask** simples em **Python**, escolha natural por ser a mesma linguagem usada para treinar o modelo (PyTorch/Ultralytics), evitando troca de stack entre treinamento e inferência. Um **limiar de confiança de 80%** foi definido no código para decidir se uma predição é confiável o suficiente para dar sequência ao pipeline; abaixo disso, a imagem é tratada como "Vazio" e a rota não é gerada.

## O resultado

O modelo treinado atingiu **mAP50 de 0.939** e **precisão de 0.91** no conjunto de validação (293 imagens, 510 instâncias), com destaque para a classe "lata" (mAP50 de 0.976, recall de 0.92). A API `/predict` entrega exatamente o que promete: recebe uma imagem, classifica entre as 4 categorias (ou descarta como "Vazio" quando abaixo do limiar de confiança) e, quando a confiança é suficiente, aciona automaticamente a API de rotas do pipeline — sem intervenção manual e sem necessidade de reprocessamento. O comportamento da API (incluindo os casos de falha e de baixa confiança) é validado por uma suíte de testes automatizados (Pytest) com mais de 10 cenários cobrindo sucesso, validação de entrada, falha da API de rotas e rejeição por baixa confiança.

## Entradas e saídas

### Entrada — `POST /predict`

Requisição `multipart/form-data` com os seguintes campos:

| Campo | Tipo | Descrição |
|---|---|---|
| `image` | arquivo | Imagem do resíduo a ser classificada. |
| `command` | texto | Comando da operação (`predict`). |
| `origem_latitude` / `origem_longitude` | texto | Coordenadas de origem, repassadas para a geração de rota. |
| `destino_latitude` / `destino_longitude` | texto | Coordenadas de destino, repassadas para a geração de rota. |

### Saída

- Predição bem-sucedida, com rota gerada:

```json
{
  "prediction": "lata",
  "confidence": 95.5,
  "status": "success"
}
```

- Predição com confiança insuficiente (abaixo de 80%) ou classe "Vazio" — a API de rotas **não** é acionada:

```json
{
  "prediction": "Vazio",
  "confidence": 42.0,
  "status": "warning"
}
```

- Predição bem-sucedida, mas com falha ao contatar/gerar a rota (a classificação em si não é perdida):

```json
{
  "prediction": "caixa_de_papelao",
  "confidence": 91.2,
  "status": "warning",
  "route_error": "Não foi possível conectar ao serviço de rotas."
}
```

- Erros de validação (`400`): imagem ausente ou coordenadas ausentes.
- Erro de configuração (`500`): `config.yaml` não encontrado.

O endpoint `GET /` funciona como healthcheck, retornando uma mensagem simples confirmando que o servidor está no ar.

## Modelo de visão computacional

- **Arquitetura**: YOLOv11s (Ultralytics), com *transfer learning* a partir de pesos pré-treinados no COCO.
- **Classes**: `caixa_de_papelao`, `garrafa`, `lata`, `tenis`.
- **Dataset**: agregação de datasets públicos do [Roboflow](https://roboflow.com), normalizados e traduzidos para português.
- **Treinamento**: 50 épocas, imagens 640×640, seed fixa (42) para reprodutibilidade, treinado em GPU NVIDIA A100.
- **Métricas de validação**:

| Classe | Precisão | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|
| Todas | 0.910 | 0.882 | 0.939 | 0.754 |
| Caixa de papelão | 0.887 | 0.892 | 0.941 | 0.728 |
| Garrafa | 0.906 | 0.934 | 0.962 | 0.703 |
| Lata | 0.964 | 0.920 | 0.976 | 0.912 |
| Tênis | 0.882 | 0.783 | 0.875 | 0.673 |

Mais detalhes sobre a metodologia de treinamento (pré-processamento, dataset, scripts) estão em [`new_model/readme.md`](new_model/readme.md).

## Segurança do container Docker

- A imagem é baseada em `pytorch/pytorch:latest` e instala apenas as dependências de sistema necessárias para OpenCV/FFmpeg.
- A aplicação roda com um **usuário não-root** (`appuser`), criado explicitamente no `Dockerfile`, e o diretório `/app` (incluindo os logs) tem seu dono ajustado para esse usuário antes da troca de contexto de execução (`USER appuser`).
- Segredos e chaves (ex.: `config.yaml` com endpoints internos) não são versionados por padrão e devem ser fornecidos em tempo de execução.

## Como executar

### Localmente

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

O servidor sobe em `http://localhost:3001`.

### Via Docker

```bash
docker build -t tcc-modelo-cnn .
docker run --add-host=host.docker.internal:host-gateway -p 3001:3001 tcc-modelo-cnn
```

> Para subir este serviço já integrado aos demais componentes do pipeline (API de rotas e pipeline de dados), utilize o [TCC_Orchestrator](https://github.com/Gusta9s/TCC_Orchestrator) com `docker compose up --build`.

## Testes

```bash
pytest
```

Cobre o endpoint `/predict` (sucesso, validação de entrada, baixa confiança, falha da API de rotas) e as funções auxiliares (`load_config_from_secret`, `gerar_imagem_de_rota`), com mocks para o modelo YOLO e para a chamada HTTP à API de rotas.

## Estrutura do projeto

```
.
├── app.py                       # API Flask: endpoint /predict e integração com a API de rotas
├── src/tcc_modelo_swm/
│   └── predict.py               # Carregamento do modelo YOLO e lógica de inferência
├── new_model/                   # Notebooks e artefatos do treinamento do modelo (dataset, métricas, pesos)
├── data/script/setup.py         # Script auxiliar para organizar dados em treino/validação
├── docs/                        # Guias de setup, execução e Docker
├── tests/                       # Testes automatizados (Pytest)
└── requirements.txt
```

## Tecnologias principais

- Python / Flask
- YOLOv11s (Ultralytics) / PyTorch
- OpenCV
- Docker
- Pytest

## Autor

Gustavo de Almeida Pacheco — desenvolvido como parte do Trabalho de Conclusão de Curso (TCC) sobre Gestão de Resíduos Sólidos Urbanos.

