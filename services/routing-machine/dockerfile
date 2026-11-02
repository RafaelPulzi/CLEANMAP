# Estágio 1: Build das dependências
FROM node:18-slim AS builder
WORKDIR /app
COPY package*.json ./
# Ajusta permissões para o usuário node
RUN chown -R node:node /app
USER node
RUN npm install

# ---

# Estágio 2: Imagem final
FROM node:18-slim

# Instala dependências do sistema, CURL, Chromium e o GOSU
# O 'gosu' é essencial para fazer a troca de usuário segura de root -> node
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    gosu \
    curl \
    chromium \
    ca-certificates fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 libcairo2 \
    libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgbm1 libgdk-pixbuf2.0-0 \
    libglib2.0-0 libgtk-3-0 libnspr4 libnss3 libpango-1.0-0 libpangocairo-1.0-0 \
    libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 \
    libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 libxtst6 \
    lsb-release wget xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Configura o Puppeteer para usar o Chromium do sistema
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

WORKDIR /app

# Copia o código da aplicação
COPY --chown=node:node server.js .

# Copia as dependências do estágio builder
COPY --chown=node:node --from=builder /app/node_modules ./node_modules
# O cache do puppeteer não é necessário pois usamos o chromium do sistema, 
# mas mantemos a cópia do cache do node por segurança
COPY --chown=node:node --from=builder /home/node/.cache /home/node/.cache

# Cria a estrutura de pastas e define permissão inicial
RUN mkdir -p assets/images && chown -R node:node assets

# --- SOLUÇÃO DE SEGURANÇA E PERMISSÃO ---
# Criamos um script de entrada que ajusta as permissões do volume em tempo de execução
# e depois executa a aplicação como o usuário 'node'
RUN echo '#!/bin/bash' > /entrypoint.sh && \
    echo '# Ajusta o dono da pasta onde o volume está montado para o usuário node' >> /entrypoint.sh && \
    echo 'chown -R node:node /app/assets/images' >> /entrypoint.sh && \
    echo '# Executa o comando passado (server.js) como usuário node' >> /entrypoint.sh && \
    echo 'exec gosu node "$@"' >> /entrypoint.sh && \
    chmod +x /entrypoint.sh

EXPOSE 3004

# Define o script como ponto de entrada
ENTRYPOINT ["/entrypoint.sh"]

# Comando padrão (será passado como argumento para o entrypoint)
CMD [ "node", "server.js" ]