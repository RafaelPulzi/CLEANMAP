/**
 * Processo de carregamento de módulos e configuração do servidor Express
 */

const express = require('express');
const puppeteer = require('puppeteer');
const path = require('path');
const fetch = require('node-fetch');
const fs = require('fs').promises;

const app = express();
const PORT = process.env.PORT; 
const MAPBOX_API_KEY = process.env.MAPBOX_API_KEY;

const IMAGES_DIR = path.join(__dirname, 'assets', 'images');

app.use(express.json());

app.use('/leaflet', express.static(path.join(__dirname, 'node_modules/leaflet/dist')));

let fileCounter = 0;

let htmlParaRenderizar = '';

/** 
 * Metodo para encaminhar o HTML para renderização
 * @returns {string} HTML para renderizar o mapa
 */

app.get('/render-map', (req, res) => {
  res.send(htmlParaRenderizar);
});

/**
 * Encontra o próximo número de arquivo disponível no diretório de imagens.
 * Ex: se 'rota5.png' for o maior, esta função retornará 6.
 * @returns {Promise<number>} O próximo número na sequência.
 */

async function getNextRouteNumber() {
  try {
    await fs.mkdir(IMAGES_DIR, { recursive: true });

    const files = await fs.readdir(IMAGES_DIR);
    const routeFiles = files.filter(file => /^rota(\d+)\.png$/.test(file));
    
    if (routeFiles.length === 0) {
      return 1;
    }

    const highestNumber = routeFiles.reduce((max, file) => {
      const match = file.match(/^rota(\d+)\.png$/);
      const currentNum = parseInt(match[1], 10);
      return currentNum > max ? currentNum : max;
    }, 0);

    return highestNumber + 1;
  } catch (error) {
    console.error("Erro ao determinar o próximo número de arquivo:", error);
    return 1;
  }
}

/**
 * Gera o HTML para renderizar o mapa com base nos dados fornecidos.
 * @param {*} payload - Os dados da requisição, incluindo informações de origem e destino.
 * @param {*} routeGeometry - A geometria da rota a ser renderizada no mapa.
 * @returns {string} O HTML para renderizar o mapa.
 */

function generateMapHtml(payload, routeGeometry) {
  const { origem_latitude, origem_longitude, destino_latitude, destino_longitude } = payload;
  
  return `
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <title>Map Snapshot</title>
      <meta charset="utf-8" />
      
      <link rel="stylesheet" href="/leaflet/leaflet.css" />
      <script src="/leaflet/leaflet.js"></script>
      
      <style> body { margin: 0; padding: 0; } #map { width: 800px; height: 600px; } </style>
    </head>
    <body> <div id="map"></div> </body>
    <script>
      const map = L.map('map');
      L.tileLayer('https://api.mapbox.com/styles/v1/mapbox/streets-v11/tiles/{z}/{x}/{y}?access_token=${MAPBOX_API_KEY}').addTo(map);

      const blueIcon = new L.Icon({ iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png', shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png', iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41] });
      const greenIcon = new L.Icon({ iconUrl: 'https://cdn-icons-png.flaticon.com/512/2634/2634066.png', iconSize: [40, 40], iconAnchor: [20, 40], popupAnchor: [1, -34] });

      const originMarker = L.marker([${origem_latitude}, ${origem_longitude}], { icon: blueIcon }).addTo(map);
      const destinationMarker = L.marker([${destino_latitude}, ${destino_longitude}], { icon: greenIcon }).addTo(map);

      const routeGeoJson = ${JSON.stringify(routeGeometry)};
      const routeLayer = L.geoJSON(routeGeoJson, { style: { color: 'blue', opacity: 0.8, weight: 6 } }).addTo(map);

      map.fitBounds(routeLayer.getBounds(), { padding: [50, 50] });
    </script>
    </html>
  `;
}

/**
 * Endpoint para gerar a imagem da rota
 * @returns {json} Resultado da geração da imagem
 */

app.post('/api/gerar-imagem-rota', async (req, res) => {
  if (!MAPBOX_API_KEY) {
    return res.status(500).json({ error: 'A chave de API da Mapbox não foi configurada.' });
  }

  const payload = req.body;
  
  let browser = null;
  try {
    const mapboxUrl = `https://api.mapbox.com/directions/v5/mapbox/driving/${payload.origem_longitude},${payload.origem_latitude};${payload.destino_longitude},${payload.destino_latitude}?geometries=geojson&access_token=${MAPBOX_API_KEY}`;
    const response = await fetch(mapboxUrl);
    const data = await response.json();

    if (data.code !== 'Ok') {
      throw new Error(`Mapbox API retornou um erro: ${data.message || data.code}`);
    }
    const routeGeometry = data.routes[0].geometry;

    htmlParaRenderizar = generateMapHtml(payload, routeGeometry);

    const nextRouteNumber = await getNextRouteNumber();
    const fileName = `rota${nextRouteNumber}.png`;
    const outputPath = path.join(IMAGES_DIR, fileName);

    browser = await puppeteer.launch({ args: ['--no-sandbox', '--disable-setuid-sandbox'] });
    const page = await browser.newPage();
    
    // Configura o timeout de navegação padrão para 2 minutos (120000ms)
    page.setDefaultNavigationTimeout(120000);
    
    page.on('console', msg => console.log('CONSOLE DO NAVEGADOR:', msg.text()));
    
    console.log("Navegando para o mapa...");

    // 1. Carregamento com timeout de segurança de 2 minutos
    await page.goto(`http://localhost:${PORT}/render-map`, { 
        waitUntil: 'networkidle0',
        timeout: 120000 
    });

    console.log("Página carregada. Aguardando 1 minuto para renderização completa...");
    
    // 2. Sleep forçado de 1 minuto (60000 ms) para garantir renderização dos tiles
    await new Promise(resolve => setTimeout(resolve, 60000));

    const mapElement = await page.$('#map');
    await mapElement.screenshot({ path: outputPath });

    console.log(`Imagem '${fileName}' gerada com sucesso em: ${outputPath}`);

    res.status(200).json({ 
      success: true,
      message: 'Imagem gerada com sucesso.',
      filename: fileName 
    });

  } catch (error) {
    console.error('Erro no processo de geração de imagem:', error);
    res.status(500).json({ error: 'Falha ao gerar a imagem.', details: error.message });
  } finally {
    if (browser) {
      await browser.close();
    }
  }
});

/**
 * Inicialização do servidor Express (Apenas se não estiver rodando via testes)
 */
if (require.main === module) {
  const server = app.listen(PORT, () => {
    console.log(`Servidor rodando em http://localhost:${PORT}`);
  });
  server.setTimeout(130000); // 2 minutos e 10 segundos
}

// Exporta as funções e a aplicação para que o Jest consiga testá-las
module.exports = { app, getNextRouteNumber, generateMapHtml };