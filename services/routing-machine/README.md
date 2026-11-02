# TCC Routing Machine SWM

Microsserviço em **Node.js** responsável por gerar e salvar, de forma automatizada, a imagem estática de uma rota entre dois pontos geográficos. A partir de coordenadas de origem e destino, o serviço calcula a rota, renderiza um mapa interativo com **Leaflet.js**, captura essa renderização como imagem (via navegador headless) e a persiste em um volume Docker compartilhado.

Este repositório é um dos componentes do projeto de TCC **Gestão de Resíduos Sólidos Urbanos (SWM)**, composto pelos seguintes repositórios:

| Repositório | Papel no fluxo |
|---|---|
| [APS_Android_SWM_Images](https://github.com/Gusta9s/APS_Android_SWM_Images) | Aplicativo mobile (Expo/React Native) usado para capturar e enviar as fotos dos resíduos descartados. |
| [TCC_workflow_data_SWM](https://github.com/Gusta9s/TCC_workflow_data_SWM) | Pipeline em Python que baixa as imagens recebidas, trata os dados e orquestra as chamadas entre o modelo de classificação e este serviço de rotas. |
| [TCC_Model1_CNN_SWM](https://github.com/Gusta9s/TCC_Model1_CNN_SWM) | API em Python/Flask com o modelo de visão computacional (CNN) que classifica o tipo de resíduo na imagem. |
| [TCC_Orchestrator](https://github.com/Gusta9s/TCC_Orchestrator) | Orquestra, via Docker Compose, a subida integrada de todos os serviços (rede, volumes compartilhados e ordem de inicialização). |
| **TCC-Routing-Machine-SWM** *(este repositório)* | Recebe origem/destino, calcula a rota, gera a imagem do mapa e a disponibiliza para o restante do pipeline. |

## Qual problema ele resolve

Depois que uma imagem de resíduo é classificada com confiança suficiente pelo modelo de CNN, o pipeline precisa registrar visualmente a rota de coleta associada àquela ocorrência (do ponto de origem até o destino), sem depender de um cliente front-end ou de captura manual de tela. Este serviço resolve isso expondo uma API simples que, dado um par de coordenadas, automatiza de ponta a ponta a geração da imagem de rota (cálculo, desenho no mapa e captura), entregando um artefato pronto para ser consumido pelas demais etapas do pipeline.

## Entradas e saídas

### Entrada — `POST /api/gerar-imagem-rota`

Corpo da requisição em JSON:

```json
{
  "origem_latitude": -23.550276,
  "origem_longitude": -46.641542,
  "destino_latitude": -23.584444,
  "destino_longitude": -46.581944
}
```

Variáveis de ambiente necessárias:

| Variável | Descrição |
|---|---|
| `PORT` | Porta em que o servidor Express é iniciado. |
| `MAPBOX_API_KEY` | Chave de API da Mapbox, usada para calcular a rota e renderizar os tiles do mapa. Não é versionada — deve ser fornecida via variável de ambiente/secret. |

### Saída

- Resposta JSON de sucesso:

```json
{
  "success": true,
  "message": "Imagem gerada com sucesso.",
  "filename": "rota7.png"
}
```

- Arquivo de imagem (`.png`) da rota, salvo em `assets/images/`, com numeração incremental automática (`rota1.png`, `rota2.png`, ...).
- Em caso de falha (chave da API ausente, rota não encontrada, erro de renderização), a API responde com status `500` e uma mensagem de erro descritiva.

Há também o endpoint interno `GET /render-map`, usado pelo próprio servidor para renderizar o HTML que será capturado como imagem — não é destinado a uso externo direto.

## Por que Leaflet.js

O Leaflet.js foi escolhido por ser uma biblioteca de mapas leve, open-source e totalmente controlável via HTML/CSS/JS puro, sem depender de um SDK proprietário pesado. Isso permite:

- Montar o mapa (tiles, marcadores de origem/destino e a geometria da rota) dinamicamente a partir dos dados retornados pela API de rotas da Mapbox.
- Renderizar essa página em um navegador headless (Puppeteer) e tirar um screenshot fiel do elemento do mapa, algo simples de fazer com uma página HTML comum, mas inviável com soluções de mapa que dependem de canvas nativo fechado ou de serviços externos de "mapa estático".
- Customizar livremente o estilo dos marcadores e da rota (ícones de origem em azul, destino em verde, linha da rota destacada) sem custos adicionais.

## Por que Node.js

O servidor é construído em Node.js/Express porque:

- Permite usar a mesma linguagem (JavaScript) tanto na camada de servidor quanto na página renderizada pelo Leaflet, simplificando a geração dinâmica do HTML do mapa.
- O ecossistema do Node integra bem com o Puppeteer (também em JS), que controla o Chromium headless usado para capturar a imagem do mapa renderizado.
- Seu modelo assíncrono e não-bloqueante é adequado ao fluxo do serviço: chamada à API de rotas da Mapbox, renderização da página e captura do screenshot podem ser encadeadas sem travar o processo.
- É simples expor uma API REST enxuta e rápida de subir, o que facilita a integração deste serviço com os demais containers do pipeline (chamado internamente pela API do modelo de CNN e consumido pelo pipeline de dados).

## Por que salvar as imagens em volumes do Docker de forma segura

Cada container do pipeline (API de rotas, API do modelo e pipeline de dados) roda isolado, mas a imagem gerada por este serviço precisa ser lida por outro container (o pipeline de processamento). Para isso:

- As imagens são gravadas em um **volume Docker nomeado e compartilhado** (`shared_assets`, definido no `docker-compose.yml` do orquestrador) em vez de serem gravadas na camada da imagem do container, o que evita perda de dados quando o container é recriado e mantém a imagem Docker do serviço enxuta.
- O `Dockerfile` usa um build em múltiplos estágios e roda a aplicação com um usuário sem privilégios (`node`), nunca como `root`.
- Um script de entrypoint ajusta o dono (`chown`) do diretório montado como volume em tempo de execução e, em seguida, troca para o usuário `node` (via `gosu`) antes de iniciar o servidor — garantindo que o volume montado tenha as permissões corretas sem exigir que a aplicação rode com privilégios elevados.
- Segredos (chave da Mapbox, `.env`) nunca são copiados para a imagem Docker nem versionados no repositório (ver `.gitignore`); são injetados em tempo de execução via variáveis de ambiente.

## Resultados obtidos

- **Geolocalização efetuada**: a partir das coordenadas de origem e destino recebidas, o serviço consulta a API de Directions da Mapbox e obtém a geometria real da rota entre os dois pontos.
- **Mapa com desenho de rota gerado**: a geometria retornada é desenhada sobre um mapa Leaflet, com marcador de origem (azul), marcador de destino (verde) e a rota destacada em linha, com o mapa ajustado automaticamente aos limites da rota (`fitBounds`).
- **Salvamento de imagem no Docker efetuado com sucesso**: a página do mapa é capturada via Puppeteer e salva como `.png` dentro do volume compartilhado, com numeração incremental automática e disponível para o restante do pipeline.
- **Cobertura de testes**: suíte de testes automatizados (Jest + Supertest) cobrindo os cenários de sucesso e de falha da API (chave ausente, rota não encontrada, falha de rede, falha do navegador headless), validada também manualmente via Postman.

## Como executar localmente

```bash
# 1. Instalar as dependências
npm install

# 2. Definir as variáveis de ambiente (PORT e MAPBOX_API_KEY)

# 3. Iniciar o servidor
npm start
```

## Como executar via Docker

```bash
docker build -t map-generator .
docker run -p 3004:3004 --name map-generator-app -v "${pwd}/assets/images:/app/assets/images" map-generator
```

> Para subir este serviço já integrado aos demais componentes do pipeline (modelo de CNN e pipeline de dados), utilize o [TCC_Orchestrator](https://github.com/Gusta9s/TCC_Orchestrator) com `docker compose up --build`.

## Testes

```bash
npm test
```

Executa a suíte de testes com Jest (`--coverage --verbose`), cobrindo tanto as funções utilitárias (`getNextRouteNumber`, `generateMapHtml`) quanto os endpoints da API.

## Estrutura do projeto

```
.
├── server.js          # Servidor Express, geração do HTML do mapa e endpoint de geração de imagem
├── dockerfile          # Build multi-stage e execução segura (usuário não-root)
├── docs/                # Guias de uso e execução do serviço
├── tests/               # Testes automatizados (Jest + Supertest)
└── package.json
```

## Tecnologias principais

- Node.js / Express
- Leaflet.js
- Puppeteer (Chromium headless)
- Mapbox Directions API
- Docker
- Jest / Supertest

## Autor

Gustavo de Almeida Pacheco — desenvolvido como parte do Trabalho de Conclusão de Curso (TCC) sobre Gestão de Resíduos Sólidos Urbanos.

