# TCC Workflow Data SWM

Pipeline em **Python** que orquestra, de ponta a ponta, o processamento de uma imagem de resíduo descartado: busca a imagem mais recente em um bucket **Backblaze B2**, valida e redimensiona o arquivo, monta as coordenadas de origem e destino, envia a imagem para a API de classificação e registra o resultado (aceito ou rejeitado) em disco — com métricas de tempo de cada etapa.

Este repositório é um dos componentes do projeto de TCC **Gestão de Resíduos Sólidos Urbanos (SWM)**, composto pelos seguintes repositórios:

| Repositório | Papel no fluxo |
|---|---|
| [APS_Android_SWM_Images](https://github.com/Gusta9s/APS_Android_SWM_Images) | Aplicativo mobile (Expo/React Native) usado para capturar e enviar as fotos dos resíduos descartados. |
| **TCC_workflow_data_SWM** *(este repositório)* | Baixa a imagem mais recente do armazenamento em nuvem, valida, redimensiona, monta as coordenadas e orquestra as chamadas entre o modelo de classificação e o serviço de rotas. |
| [TCC_Model1_CNN_SWM](https://github.com/Gusta9s/TCC_Model1_CNN_SWM) | API com o modelo de visão computacional (YOLOv11s) que classifica o tipo de resíduo na imagem. |
| [TCC-Routing-Machine-SWM](https://github.com/Gusta9s/TCC-Routing-Machine-SWM) | Recebe origem/destino, calcula a rota, gera a imagem do mapa (Leaflet.js) e a salva em um volume Docker compartilhado. |
| [TCC_Orchestrator](https://github.com/Gusta9s/TCC_Orchestrator) | Orquestra, via Docker Compose, a subida integrada de todos os serviços (rede, volumes compartilhados e ordem de inicialização). |

## O problema

As imagens de resíduos chegam de fontes assíncronas e heterogêneas — o aplicativo mobile envia fotos para um bucket na nuvem, a origem pode vir de uma API de localização (GPS/Arduino) ou de um arquivo local de contingência, e o destino pode vir de uma rota já calculada ou também de um arquivo de contingência. O desafio técnico é orquestrar essas fontes de forma confiável: encontrar sempre a imagem e as coordenadas mais recentes, validar que o arquivo recebido é realmente uma imagem utilizável (não corrompida, dentro do tamanho limite) antes de gastar tempo processando-a, e não deixar o pipeline inteiro falhar quando uma única fonte (API de localização, API de predição) está temporariamente indisponível.

## A solução

O pipeline foi escrito em **Python** por ser a linguagem mais direta para integrar bibliotecas de manipulação de imagem (Pillow), acesso a armazenamento compatível com S3 (`boto3`, para o Backblaze B2) e chamadas HTTP com retry (`requests` + `urllib3.Retry`), sem exigir nenhum framework web — este é um script orquestrador, não um serviço que fica no ar. A arquitetura segue um modelo de **múltiplas fontes com fallback em cascata**: sempre que uma fonte "principal" (API de localização, arquivo de rota mais recente no B2) falha ou não está disponível, o pipeline recorre automaticamente a um arquivo de contingência (`secretOrigem.env` / `secretDestino.env`), garantindo que o processamento não pare por uma dependência externa fora do ar. Cada etapa tem seu tempo de execução medido individualmente, o que facilita identificar gargalos sem precisar instrumentar o código com um APM externo.

## O resultado

O pipeline entrega exatamente o que promete: dado um bucket com imagens e coordenadas, ele processa a mais recente de ponta a ponta e grava um arquivo de resultado (`acpt/` para sucesso, `rjct/` para rejeição) com o status, a predição e o tempo de cada etapa — extração do B2, validação, leitura de coordenadas, redimensionamento, chamada ao modelo e salvamento do resultado. A chamada à API de predição usa retry automático com backoff exponencial (5 tentativas) para absorver picos de indisponibilidade momentânea sem derrubar o pipeline. O comportamento de cada módulo (cliente da API, gerenciador de arquivos, manipulador de imagens e o pipeline principal) é validado por uma suíte de testes automatizados (Pytest) com 15 cenários, incluindo os caminhos de fallback e de erro.

## Como o pipeline funciona

1. **Extração**: busca a imagem mais recente (`foto_{n}.jpg`) em um bucket Backblaze B2.
2. **Validação**: confirma que o arquivo existe, está dentro do tamanho máximo configurado e é uma imagem JPEG válida (não corrompida).
3. **Redimensionamento**: ajusta a imagem para as dimensões configuradas antes de enviá-la para a API de classificação.
4. **Coordenadas de origem**: tenta obter a origem de uma API de localização (GPS/Arduino); se falhar, usa o arquivo de contingência `secretOrigem.env`.
5. **Coordenadas de destino**: tenta ler o arquivo de rota mais recente (`rota_{n}.txt`) do B2; se não encontrar, usa o arquivo de contingência `secretDestino.env`.
6. **Predição**: envia a imagem redimensionada e as coordenadas para a API do modelo de classificação, com retry automático em caso de falha temporária.
7. **Resultado**: grava o resultado (aceito ou rejeitado) em disco, junto com as métricas de tempo de cada etapa, e remove os arquivos temporários gerados durante o processo.

## Segredos e configuração

- Credenciais do Backblaze B2 (`key_id`, `application_key`) e endpoints internos ficam em `config.yaml` e nos arquivos de contingência (`secretOrigem.env`, `secretDestino.env`), que **não são versionados** — devem ser criados localmente ou injetados via volume/variáveis de ambiente em produção.
- Em execução via Docker Compose, variáveis de ambiente (`SECRETS_DIR`, `RESULTS_DIR`, `ML_API_URL`) sobrescrevem os valores padrão do `config.yaml`, permitindo apontar o pipeline para os diretórios e serviços corretos sem alterar código.

## Como executar

### Localmente

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Via PowerShell (Windows)

O script `run_pipeline.ps1` sobe os containers do modelo de classificação e do serviço de rotas, executa o pipeline e faz a limpeza do ambiente ao final:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\run_pipeline.ps1
```

### Via Docker

```bash
docker build -t tcc-workflow-data .
docker run tcc-workflow-data
```

> Para subir este serviço já integrado aos demais componentes do pipeline (modelo de CNN e API de rotas), utilize o [TCC_Orchestrator](https://github.com/Gusta9s/TCC_Orchestrator) com `docker compose up --build`.

## Testes

```bash
pytest
```

Cobre o cliente da API de predição (incluindo a lógica de retry), o gerenciador de arquivos (leitura de contingência e escrita de resultados), o manipulador de imagens (validação e redimensionamento) e o fluxo principal do pipeline.

## Estrutura do projeto

```
.
├── app.py                          # Orquestrador principal do pipeline
├── src/tcc_job_processor/
│   ├── api_client.py               # Chamadas à API de localização e à API de predição (com retry)
│   ├── file_manager.py             # Leitura de arquivos de contingência e escrita de resultados
│   └── image_handler.py            # Download/leitura do B2, validação e redimensionamento de imagens
├── docs/                           # Guias de setup e execução
├── tests/                          # Testes automatizados (Pytest)
├── run_pipeline.ps1                # Script orquestrador para Windows (build + execução + limpeza)
└── requirements.txt
```

## Tecnologias principais

- Python
- boto3 (Backblaze B2 / S3)
- Pillow
- Requests (com retry via urllib3)
- Docker
- Pytest

## Autor

Gustavo de Almeida Pacheco — desenvolvido como parte do Trabalho de Conclusão de Curso (TCC) sobre Gestão de Resíduos Sólidos Urbanos.

