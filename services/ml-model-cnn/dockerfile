# 1. Usamos uma imagem base estável do PyTorch oficial (CPU, baseada no Ubuntu 22.04)
FROM pytorch/pytorch:latest

# 2. Instale as dependências de sistema para OpenCV e FFmpeg (executado como root)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    ffmpeg \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 3. Crie um diretório de trabalho e um usuário não-root para a aplicação
WORKDIR /app
RUN useradd -ms /bin/bash appuser

# 4. Copie o arquivo de requisitos e instale as dependências Python.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copie o restante do código da aplicação
COPY . .

# 6. Crie os logs e garanta que o appuser seja dono de tudo o que foi copiado
RUN mkdir -p logs && chown -R appuser:appuser /app

# 7. Mude para o usuário não-root
USER appuser

# 8. Exponha a porta 3001 para acesso externo
EXPOSE 3001

# 9. Defina o ponto de entrada e o comando padrão para executar a aplicação
ENTRYPOINT ["python"]
CMD ["app.py"]