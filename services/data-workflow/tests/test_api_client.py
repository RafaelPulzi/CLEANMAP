import pytest
import requests
from src.tcc_job_processor.api_client import get_origin_location, get_prediction

def test_get_origin_location_success(mocker):
    # Falsifica o retorno do requests.get
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"latitude": -23.0, "longitude": -46.0}
    mocker.patch('requests.get', return_value=mock_response)

    coords = get_origin_location('http://fake-api')
    assert coords == {'origem_latitude': -23.0, 'origem_longitude': -46.0}

def test_get_origin_location_error(mocker):
    # Falsifica um erro de timeout/conexão
    mocker.patch('requests.get', side_effect=requests.exceptions.ConnectionError("Erro de rede"))
    
    with pytest.raises(ConnectionError):
        get_origin_location('http://fake-api')

def test_get_prediction_success(mocker, tmp_path):
    # Cria arquivo falso para evitar FileNotFoundError no open()
    img_path = tmp_path / "dummy.jpg"
    img_path.write_text("fake image content")

    # Moca a SESSÃO que introduzimos para o Retry
    mock_session_instance = mocker.Mock()
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"status": "success", "prediction": "garrafa"}
    mock_session_instance.post.return_value = mock_response
    mocker.patch('requests.Session', return_value=mock_session_instance)

    coords = {'origem_latitude': '1', 'origem_longitude': '2', 'destino_latitude': '3', 'destino_longitude': '4'}
    result = get_prediction('http://fake-ml', coords, str(img_path))
    
    assert result['prediction'] == 'garrafa'
    assert result['status'] == 'success'