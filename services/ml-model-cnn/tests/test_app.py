import pytest
from unittest.mock import patch, MagicMock
from requests.exceptions import RequestException
from app import load_config_from_secret
from app import gerar_imagem_de_rota

def test_home_route(client):
    """Garante que o healthcheck (rota raiz) está respondendo 200 OK."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Servidor do Modelo de CNN no ar!" in response.data

def test_predict_missing_image(client):
    """Testa a validação de arquivo de imagem ausente (Erro 400)."""
    response = client.post('/predict', data={
        'command': 'predict',
        'origem_latitude': '1',
        'origem_longitude': '1',
        'destino_latitude': '2',
        'destino_longitude': '2'
    })
    
    assert response.status_code == 400
    assert response.json['status'] == 'error'
    assert 'Arquivo de imagem não fornecido' in response.json['error']

def test_predict_missing_coordinates(client, dummy_image_file):
    """Testa a validação de coordenadas ausentes (Erro 400)."""
    response = client.post('/predict', data={
        'command': 'predict',
        'image': dummy_image_file
    }, content_type='multipart/form-data')
    
    assert response.status_code == 400
    assert 'obrigatórios' in response.json['erro']

@patch('app.load_config_from_secret')
@patch('app.predict_on_image')
@patch('app.gerar_imagem_de_rota')
def test_predict_success_with_routing(mock_gerar_rota, mock_predict, mock_config, client, dummy_image_file, dummy_config):
    """Cenário de Sucesso Absoluto: Confiança alta (>80), chama rota e retorna tudo certo."""
    mock_config.return_value = dummy_config
    # Simula predição de sucesso
    mock_predict.return_value = ("caixa_de_papelao", 95.5)
    
    # Simula resposta de sucesso da API de Rotas Leaflet
    mock_gerar_rota.return_value = {
        "status": "sucesso",
        "payload": {"success": True, "filename": "rota_teste.png"}
    }
    
    response = client.post('/predict', data={
        'command': 'predict',
        'origem_latitude': '1', 'origem_longitude': '1',
        'destino_latitude': '2', 'destino_longitude': '2',
        'image': dummy_image_file
    }, content_type='multipart/form-data')
    
    assert response.status_code == 200
    assert response.json['prediction'] == "caixa_de_papelao"
    assert response.json['confidence'] == 95.5
    assert response.json['status'] == "success"
    mock_gerar_rota.assert_called_once() # Garante que a API de rotas foi acionada

@patch('app.load_config_from_secret')
@patch('app.predict_on_image')
@patch('app.gerar_imagem_de_rota')
def test_predict_success_but_routing_fails(mock_gerar_rota, mock_predict, mock_config, client, dummy_image_file, dummy_config):
    """Cenário onde a confiança é alta, mas a API de Rotas cai ou falha (Warning)."""
    mock_config.return_value = dummy_config
    mock_predict.return_value = ("lata", 88.0)
    
    # Simula falha na API de rotas (Ex: Node fora do ar)
    mock_gerar_rota.return_value = {
        "status": "erro",
        "payload": "Connection refused"
    }
    
    response = client.post('/predict', data={
        'origem_latitude': '1', 'origem_longitude': '1',
        'destino_latitude': '2', 'destino_longitude': '2',
        'image': dummy_image_file
    }, content_type='multipart/form-data')
    
    assert response.status_code == 200
    assert response.json['status'] == "warning"
    assert "Não foi possível conectar" in response.json['route_error']

@patch('app.load_config_from_secret')
@patch('app.predict_on_image')
@patch('app.gerar_imagem_de_rota')
def test_predict_low_confidence_skips_routing(mock_gerar_rota, mock_predict, mock_config, client, dummy_image_file, dummy_config):
    """Cenário: Classe 'Vazio' ou confiança baixa -> NÃO deve chamar a API de rotas."""
    mock_config.return_value = dummy_config
    mock_predict.return_value = ("Vazio", 60.0)
    
    response = client.post('/predict', data={
        'origem_latitude': '1', 'origem_longitude': '1',
        'destino_latitude': '2', 'destino_longitude': '2',
        'image': dummy_image_file
    }, content_type='multipart/form-data')
    
    assert response.status_code == 200
    assert response.json['status'] == "warning"
    assert response.json['prediction'] == "Vazio"
    # VALIDAÇÃO CRÍTICA: Garante que a API de rotas NUNCA é chamada se não achar nada!
    mock_gerar_rota.assert_not_called() 

@patch('app.post')
def test_gerar_imagem_de_rota_success(mock_requests_post):
    """Testa a função isolada de envio HTTP para a API Node.js."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"success": True, "filename": "test.png"}
    mock_requests_post.return_value = mock_response
    
    result = gerar_imagem_de_rota(1, 1, 2, 2, 'http://fake-routing.api')
    assert result['status'] == "sucesso"
    assert result['payload']['filename'] == "test.png"

def test_load_config_file_not_found(mocker):
    """Testa o cenário onde o arquivo config.yaml não existe (Gera erro no log)."""
    mocker.patch('app.Path.read_text', side_effect=FileNotFoundError)
    config = load_config_from_secret()
    assert config is None

def test_predict_config_not_found(client, mocker, dummy_image_file):
    """Testa o endpoint de predição quando a configuração falha em carregar (Retorna 500)."""
    mocker.patch('app.load_config_from_secret', return_value=None)
    response = client.post('/predict', data={
        'command': 'predict',
        'origem_latitude': '1', 'origem_longitude': '1',
        'destino_latitude': '2', 'destino_longitude': '2',
        'image': dummy_image_file
    }, content_type='multipart/form-data')
    
    assert response.status_code == 500
    assert response.json['status'] == 'error'

@patch('app.post')
def test_gerar_imagem_de_rota_request_exception(mock_post):
    """Testa a falha de conexão HTTP (timeout/fora do ar) na função de gerar rota."""
    mock_post.side_effect = RequestException("Falha de rede severa")
    result = gerar_imagem_de_rota(1, 1, 2, 2, 'http://fake-api')
    
    assert result['status'] == 'erro'
    assert 'Falha de rede severa' in result['payload']

@patch('app.load_config_from_secret')
@patch('app.predict_on_image')
@patch('app.gerar_imagem_de_rota')
def test_predict_success_routing_internal_failure(mock_gerar_rota, mock_predict, mock_config, client, dummy_image_file, dummy_config):
    """Testa quando a requisição de rota funciona (200), mas a API Node avisa que falhou internamente (success: false)."""
    mock_config.return_value = dummy_config
    mock_predict.return_value = ("lata", 90.0)
    
    # Simula a API Node respondendo "status: sucesso" HTTP, mas "success: false" no JSON de retorno
    mock_gerar_rota.return_value = {
        "status": "sucesso",
        "payload": {"success": False, "error": "Falta API Key Mapbox"}
    }
    
    response = client.post('/predict', data={
        'origem_latitude': '1', 'origem_longitude': '1',
        'destino_latitude': '2', 'destino_longitude': '2',
        'image': dummy_image_file
    }, content_type='multipart/form-data')
    
    assert response.status_code == 200
    assert response.json['status'] == "warning"
    assert "API de rotas reportou falha" in response.json['route_error']
