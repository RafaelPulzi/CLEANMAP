const request = require('supertest');
const fs = require('fs').promises;

jest.mock('puppeteer');
jest.mock('node-fetch');

describe('TCC Routing Machine API Tests', () => {
    
    let app, getNextRouteNumber, generateMapHtml;
    let fetchMock, puppeteerMock;
    const originalEnv = process.env;
    const originalSetTimeout = global.setTimeout; // Salva o timer original

    beforeEach(() => {
        jest.clearAllMocks();
        jest.resetModules(); 
        
        process.env = { ...originalEnv, MAPBOX_API_KEY: 'fake_api_key' };
        
        fetchMock = require('node-fetch');
        puppeteerMock = require('puppeteer');
        
        const server = require('../server');
        app = server.app;
        getNextRouteNumber = server.getNextRouteNumber;
        generateMapHtml = server.generateMapHtml;

        jest.spyOn(fs, 'mkdir').mockResolvedValue(true);
        jest.spyOn(fs, 'readdir').mockResolvedValue([]);
        jest.spyOn(console, 'log').mockImplementation(() => {});
        jest.spyOn(console, 'error').mockImplementation(() => {});

        // CIRURGIA DE TEMPO: Se o código pedir o sleep de 60s, avança instantaneamente.
        // Se for qualquer outro timer (usado pelo Express), funciona normal.
        jest.spyOn(global, 'setTimeout').mockImplementation((cb, ms, ...args) => {
            if (ms === 60000) {
                cb(...args);
                return 9999; 
            }
            return originalSetTimeout(cb, ms, ...args);
        });
    });

    afterEach(() => {
        jest.restoreAllMocks();
        process.env = originalEnv;
    });

    // =========================================================================
    // BLOCO 1: Testes Unitários de Funções Utilitárias (Utilitários Internos)
    // =========================================================================
    describe('Funções Utilitárias: getNextRouteNumber e generateMapHtml', () => {

        test('Cenário 1: getNextRouteNumber deve retornar 1 se o diretório estiver vazio', async () => {
            fs.readdir.mockResolvedValue([]);
            const nextNum = await getNextRouteNumber();
            expect(nextNum).toBe(1);
            expect(fs.mkdir).toHaveBeenCalledWith(expect.any(String), { recursive: true });
        });

        test('Cenário 2: getNextRouteNumber deve calcular o próximo número corretamente', async () => {
            fs.readdir.mockResolvedValue(['rota1.png', 'rota5.png', 'lixo.txt', 'rota2.png']);
            const nextNum = await getNextRouteNumber();
            expect(nextNum).toBe(6); 
        });

        test('Cenário 3: getNextRouteNumber deve retornar 1 caso fs.readdir falhe', async () => {
            fs.readdir.mockRejectedValue(new Error('Erro simulado de disco'));
            const nextNum = await getNextRouteNumber();
            expect(nextNum).toBe(1); 
        });

        test('Cenário 4: generateMapHtml deve montar o HTML corretamente', () => {
            const payload = { origem_latitude: -23.5, origem_longitude: -46.5, destino_latitude: -23.6, destino_longitude: -46.6 };
            const geoJson = { type: 'LineString', coordinates: [[-46.5, -23.5], [-46.6, -23.6]] };
            
            const html = generateMapHtml(payload, geoJson);
            
            expect(html).toContain('fake_api_key');
            expect(html).toContain('-23.5');
            expect(html).toContain('LineString');
            expect(html).toContain('div id="map"');
        });
    });

    // =========================================================================
    // BLOCO 2: Testes de Endpoints (Integração e Regras de Negócio)
    // =========================================================================
    describe('Endpoints da API: /render-map e /api/gerar-imagem-rota', () => {

        test('Cenário 5: GET /render-map deve retornar status 200 OK', async () => {
            const response = await request(app).get('/render-map');
            expect(response.status).toBe(200);
        });

        test('Cenário 6: POST /api/gerar-imagem-rota deve falhar se API KEY não for configurada', async () => {
            delete process.env.MAPBOX_API_KEY; 
            jest.resetModules(); 
            const serverSemChave = require('../server');
            
            const response = await request(serverSemChave.app).post('/api/gerar-imagem-rota').send({});
            
            expect(response.status).toBe(500);
            expect(response.body.error).toContain('chave de API da Mapbox não foi configurada');
        });

        test('Cenário 7: POST /api/gerar-imagem-rota deve capturar erro caso a API da Mapbox rejeite as coordenadas', async () => {
            fetchMock.mockResolvedValue({
                json: jest.fn().mockResolvedValue({ code: 'NoRoute', message: 'Rota impossível' })
            });

            const response = await request(app).post('/api/gerar-imagem-rota').send({ origem_latitude: 0, origem_longitude: 0, destino_latitude: 0, destino_longitude: 0 });
            
            expect(response.status).toBe(500);
            expect(response.body.details).toContain('Mapbox API retornou um erro: Rota impossível');
        });

        test('Cenário 8: POST /api/gerar-imagem-rota deve capturar falhas globais de rede (fetch quebra)', async () => {
            fetchMock.mockRejectedValue(new Error('Conexão recusada com Mapbox'));

            const response = await request(app).post('/api/gerar-imagem-rota').send({ origem_latitude: 1, origem_longitude: 1, destino_latitude: 2, destino_longitude: 2 });
            
            expect(response.status).toBe(500);
            expect(response.body.details).toContain('Conexão recusada com Mapbox');
        });

        test('Cenário 9: POST /api/gerar-imagem-rota - CAMINHO FELIZ', async () => {
            fetchMock.mockResolvedValue({
                json: jest.fn().mockResolvedValue({
                    code: 'Ok',
                    routes: [{ geometry: { type: 'LineString', coordinates: [] } }]
                })
            });

            const mockPage = {
                setDefaultNavigationTimeout: jest.fn(),
                on: jest.fn(),
                goto: jest.fn().mockResolvedValue(true),
                $: jest.fn().mockResolvedValue({ screenshot: jest.fn().mockResolvedValue(true) })
            };
            const mockBrowser = {
                newPage: jest.fn().mockResolvedValue(mockPage),
                close: jest.fn().mockResolvedValue(true)
            };
            puppeteerMock.launch.mockResolvedValue(mockBrowser);

            const response = await request(app).post('/api/gerar-imagem-rota').send({ origem_latitude: 1, origem_longitude: 1, destino_latitude: 2, destino_longitude: 2 });

            expect(response.status).toBe(200);
            expect(response.body.success).toBe(true);
            expect(response.body.filename).toBe('rota1.png');
            expect(puppeteerMock.launch).toHaveBeenCalled();
            expect(mockBrowser.close).toHaveBeenCalled();
        });

        test('Cenário 10: POST /api/gerar-imagem-rota garante encerramento do Puppeteer em falha de navegação', async () => {
            fetchMock.mockResolvedValue({
                json: jest.fn().mockResolvedValue({ code: 'Ok', routes: [{ geometry: {} }] })
            });

            const mockBrowser = {
                newPage: jest.fn().mockRejectedValue(new Error('Navegador travou')),
                close: jest.fn().mockResolvedValue(true)
            };
            puppeteerMock.launch.mockResolvedValue(mockBrowser);

            const response = await request(app).post('/api/gerar-imagem-rota').send({ origem_latitude: 1, origem_longitude: 1, destino_latitude: 2, destino_longitude: 2 });
            
            expect(response.status).toBe(500);
            expect(response.body.details).toContain('Navegador travou');
            expect(mockBrowser.close).toHaveBeenCalled(); 
        });
    });
});
