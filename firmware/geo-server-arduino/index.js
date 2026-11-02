const express = require('express');
const { SerialPort } = require('serialport');
const { ReadlineParser } = require('@serialport/parser-readline');

const app = express();
const PORT = process.env.PORT || 3006;
const SERIAL_PORT = process.env.SERIAL_PORT || 'COM3'; // <-- ajuste para a sua porta no Windows
const BAUD_RATE = parseInt(process.env.BAUD_RATE || '9600', 10);

let latestLocation = null;

const port = new SerialPort({ path: SERIAL_PORT, baudRate: BAUD_RATE, autoOpen: false });
const parser = port.pipe(new ReadlineParser({ delimiter: '\n' }));

port.open((err) => {
  if (err) {
    console.error('Erro abrindo porta serial:', err.message);
  } else {
    console.log(`Serial aberta em ${SERIAL_PORT} @ ${BAUD_RATE} baud`);
  }
});

// Recebe linhas do Arduino
parser.on('data', line => {
  line = line.trim();
  if (!line) return;

  // Se for a linha de inicialização do Arduino, exibe
  if (line.includes('INICIANDO_GPS_JSON')) {
    console.log('[arduino]', line);
    return;
  }

  // Tenta parsear JSON — o Arduino envia JSON por linha
  try {
    const obj = JSON.parse(line);
    // valida campos
    if (typeof obj.latitude === 'number' && typeof obj.longitude === 'number') {
      latestLocation = {
        latitude: obj.latitude,
        longitude: obj.longitude,
        fixAgeMs: obj.fixAgeMs || null,
        ts: obj.ts || Date.now()
      };
      console.log('Nova localização:', latestLocation);
    } else {
      console.warn('JSON recebido mas lat/lng inválidos:', line);
    }
  } catch (e) {
    // se não for JSON, apenas loga (pode ser NMEA cru)
    console.warn('Linha serial não-json:', line);
  }
});

// Endpoint principal: retorna último payload (ou 204 se vazio)
app.get('/location', (req, res) => {
  if (!latestLocation) return res.status(204).send(); // sem conteúdo ainda
  res.json(latestLocation);
});

// Endpoint simples de saúde/ready
app.get('/health', (req, res) => res.json({ status: 'ok', serialPort: SERIAL_PORT }));

app.listen(PORT, () => {
  console.log(`Geo server rodando na porta ${PORT}`);
});