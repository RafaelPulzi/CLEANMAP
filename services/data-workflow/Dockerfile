# Use uma imagem Python oficial
FROM python:3.10-slim

# Define diretório de trabalho
WORKDIR /app

# Substituímos 'libgl1-mesa-glx' por 'libgl1', que é o nome correto nas versões novas do Debian
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia os requirements e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código fonte
COPY . .

# Cria a pasta de assets caso o código precise dela existente
RUN mkdir -p /app/assets/images

# Comando para rodar o script principal
CMD ["python", "app.py"]