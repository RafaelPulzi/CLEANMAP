# Detecção Customizada de Objetos com YOLOv11s

## 📋 Visão Geral

Este projeto implementa um modelo de detecção de objetos customizado utilizando a arquitetura YOLOv11s para identificar e localizar quatro categorias específicas de objetos:

- 📦 **Caixas de papelão**
- 🍶 **Garrafas**
- 🥤 **Latas**
- 👟 **Tênis**

O projeto abrange todo o pipeline de desenvolvimento, desde a coleta e preparação dos dados até o treinamento do modelo e implementação de inferência em imagens e vídeos.

## 🛠️ Tecnologias Utilizadas

- **YOLOv11s** (Ultralytics)
- **Python 3.x**
- **PyTorch** com suporte CUDA
- **OpenCV**
- **Roboflow** (para gerenciamento de datasets)
- **Google Colab** (ambiente de treinamento)

## 📊 Metodologia

### 1. Coleta e Preparação dos Dados

A base de dados foi construída através da agregação de múltiplos datasets públicos da plataforma [Roboflow](https://roboflow.com). Foi realizada uma normalização e tradução das classes para o português:

#### Opções de Pré-processamento do Roboflow

A plataforma Roboflow oferece diversas opções de pré-processamento que podem ser aplicadas aos datasets:

**Opções Disponíveis:**
- **Auto-Orient**: Correção automática da orientação das imagens
- **Isolate Objects**: Isolamento de objetos específicos
- **Static Crop**: Recorte estático das imagens
- **Dynamic Crop**: Recorte dinâmico baseado nos objetos
- **Resize**: Redimensionamento das imagens
- **Grayscale**: Conversão para escala de cinza
- **Auto-Adjust Contrast**: Ajuste automático de contraste
- **Tile**: Divisão de imagens em tiles menores
- **Filter Null**: Remoção de imagens sem anotações
- **Filter by Tag**: Filtragem por tags específicas

#### Decisão de Pré-processamento

**Para este projeto, optou-se por utilizar apenas a funcionalidade "Modify Classes"** do Roboflow, que permite:
- Renomear classes existentes
- Unificar classes similares
- Traduzir nomes de classes para português
- Excluir classes irrelevantes

**Justificativa:** Como o YOLOv11s já implementa pré-processamento e data augmentation otimizados internamente, aplicar transformações adicionais no Roboflow poderia resultar em redundância ou até mesmo degradação da performance do modelo.

#### Mapeamento de Classes

| Classe Final | Classes Originais |
|--------------|------------------|
| `caixa_de_papelao` | CARDBOARD, Cardboard Box, 15 |
| `lata` | CAN, Can, Cans, metal, distorted, green, red, blue |
| `garrafa` | bottle, pet, plastic_bottles |
| `tenis` | shoe, Shoes, Casual, Formal, IT, Safety-Shoe |

### 2. Configuração do Dataset

- **Sem pré-processamento manual**: O YOLOv11s já implementa data augmentation otimizado internamente
- **Técnicas automáticas aplicadas** (conforme [documentação oficial](https://docs.ultralytics.com/pt/guides/yolo-data-augmentation/#brightness-adjustment-hsv_v)):
  - Mosaic (combinação de 4 imagens)
  - Mutações de cor (HSV)
  - Transformações geométricas (translação, escala, cisalhamento, perspectiva)

### 3. Pré-processamento Automático

O YOLOv11s realiza todo o pré-processamento necessário de forma automática, eliminando a necessidade de aplicar filtros manuais de processamento de imagem:

#### ✅ **Processamentos Automáticos:**
- **Redimensionamento**: Ajuste automático para 640x640 pixels
- **Normalização**: Conversão de valores de pixel (0-255 → 0-1)
- **Conversão de formato**: BGR → RGB quando necessário
- **Padding inteligente**: Preservação do aspect ratio original
- **Organização de tensores**: Formato adequado para redes neurais

#### 🧠 **Por que não precisa de filtros tradicionais:**
- **Aprendizado automático**: As camadas convolucionais aprendem automaticamente os "filtros" mais adequados
- **Adaptação**: O modelo se adapta a diferentes condições de iluminação e contraste
- **Data augmentation**: Simula variações de brilho, contraste e cor durante o treinamento
- **End-to-end**: Processo completo desde a imagem bruta até a detecção final

Isso significa que técnicas como equalização de histograma, filtros de alta frequência ou correções manuais de contraste são desnecessárias, pois o modelo neural aprende essas transformações de forma otimizada.

## 🚀 Instalação e Configuração

### Pré-requisitos

```bash
# Instalar PyTorch com suporte CUDA 12.4
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# Instalar Ultralytics (YOLO)
pip install -U ultralytics

# Instalar Roboflow
pip install roboflow
```

### Download do Dataset

```python
from roboflow import Roboflow

# Configurar API do Roboflow
rf = Roboflow(api_key="SUA_API_KEY_AQUI")
project = rf.workspace("computervisionfutebol").project("cardboard-box-detection-mozxg")
version = project.version(7)
dataset = version.download("yolov11")
```

## 🏋️ Treinamento do Modelo

### Script de Treinamento

```python
from ultralytics import YOLO

# Carregar modelo pré-treinado
model = YOLO('yolo11s.pt')

# Configurações de treinamento
results = model.train(
    task="detect",
    data=f'/content/{dataset.location}/data.yaml',
    imgsz=640,
    epochs=50,
    batch=150,
    seed=42,
    exist_ok=True,
    name='yolo11s_custom',
    pretrained=True
)
```

### Parâmetros de Treinamento

| Parâmetro | Valor | Descrição |
|-----------|-------|-----------|
| `task` | detect | Tarefa de detecção de objetos |
| `imgsz` | 640 | Tamanho da imagem de entrada |
| `epochs` | 50 | Número de épocas de treinamento |
| `batch` | 150 | Tamanho do lote |
| `seed` | 42 | Semente para reprodutibilidade |

## 📈 Resultados

O modelo foi treinado no Google Colab utilizando uma GPU NVIDIA A100-SXM4-40GB e alcançou os seguintes resultados no conjunto de validação:

| Classe | Imagens | Instâncias | Precisão (P) | Recall (R) | mAP50 | mAP50-95 |
|--------|---------|------------|--------------|-----------|-------|----------|
| **Todas** | 293 | 510 | 0.91 | 0.882 | 0.939 | 0.754 |
| Caixa de papelão | 34 | 74 | 0.887 | 0.892 | 0.941 | 0.728 |
| Garrafa | 59 | 166 | 0.906 | 0.934 | 0.962 | 0.703 |
| Lata | 97 | 118 | 0.964 | 0.92 | 0.976 | 0.912 |
| Tênis | 103 | 152 | 0.882 | 0.783 | 0.875 | 0.673 |

## 🔍 Inferência

### Inferência em Imagem Única

```python
from ultralytics import YOLO
import cv2

# Carregar modelo treinado
model = YOLO("runs/detect/yolo11s_custom/weights/best.pt")

# Realizar predição
results = model.predict(
    source="caminho/para/imagem.jpg",
    conf=0.25,
    save=True,
    show=False
)

# Exibir resultado
result = results[0]
imagem_com_deteccoes = result.plot()
cv2.imshow("Deteccoes", imagem_com_deteccoes)
cv2.waitKey(0)
cv2.destroyAllWindows()
```

### Inferência em Vídeo

```python
from ultralytics import YOLO
import cv2

# Carregar modelo treinado
model = YOLO("runs/detect/yolo11s_custom/weights/best.pt")

# Processar vídeo
results = model.predict(
    source="caminho/para/video.mp4",
    conf=0.25,
    stream=True,
    save=True,
    show=True
)

# Processar resultados
for result in results:
    pass

cv2.destroyAllWindows()
```

## 📁 Estrutura do Projeto

```
projeto/
├── runs/detect/yolo11s_custom/
│   └── weights/
│       └── best.pt              # Modelo treinado
├── datasets/
│   └── cardboard-box-detection/ # Dataset do Roboflow
├── scripts/
│   ├── train.py                 # Script de treinamento
│   ├── inference_image.py       # Inferência em imagem
│   └── inference_video.py       # Inferência em vídeo
└── README.md
```

## ⚙️ Configurações de Inferência

- **Confiança mínima**: 0.25 (25%)
- **Formato de entrada**: Imagens (JPG, PNG) e Vídeos (MP4, AVI, etc.)
- **Resolução recomendada**: 640x640 pixels

## 📝 Notas Importantes

- O modelo utiliza transfer learning com pesos pré-treinados no dataset COCO
- Data augmentation é aplicada automaticamente durante o treinamento
- Os resultados são salvos automaticamente na pasta `runs/detect/`
- Para melhor performance, recomenda-se uso de GPU com suporte CUDA

## 🤝 Contribuições

Este projeto foi desenvolvido como parte de um trabalho acadêmico. Contribuições e sugestões são bem-vindas através de issues e pull requests.