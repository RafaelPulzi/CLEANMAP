import pytest
import os
from unittest.mock import patch, ANY
from app import main

# Parâmetros: (Classe detectada, Confiança, Diretório Esperado, Status HTTP)
CENARIOS_TESTE = [
    # Cenários de Sucesso (As 4 classes válidas)
    ("caixa_de_papelao", 95.0, "acpt", "success"),
    ("lata", 88.5, "acpt", "success"),
    ("garrafa", 99.9, "acpt", "success"),
    ("tenis", 82.0, "acpt", "success"),
    
    # Cenário de Falha / Dummy (Não detectou objeto)
    ("Vazio", 0.0, "rjct", "warning"),
    ("lata", 45.0, "rjct", "warning")
]

@pytest.mark.parametrize("pred_class, confidence, expected_dir, api_status", CENARIOS_TESTE)
@patch('app.load_config')
@patch('app.image_handler')
@patch('app.api_client')
@patch('app.file_manager')
def test_pipeline_cenarios_deteccao(mock_file_manager, mock_api_client, mock_image_handler, mock_load_config, 
                                    dummy_config, pred_class, confidence, expected_dir, api_status):
    
    # 1. SETUP: Configura o ambiente falso (Mocks)
    mock_load_config.return_value = dummy_config
    mock_image_handler.find_and_download_latest_image_from_b2.return_value = "/tmp/foto.jpg"
    mock_image_handler.resize_image.return_value = "/tmp/resized.jpg"
    mock_image_handler.find_and_parse_latest_route_from_b2.return_value = {'destino_latitude': '1', 'destino_longitude': '1'}
    mock_api_client.get_origin_location.return_value = {'origem_latitude': '0', 'origem_longitude': '0'}
    
    # Simula a resposta da API do Modelo (CNN) baseada nos parâmetros do teste
    mock_api_client.get_prediction.return_value = {
        "status": api_status,
        "prediction": pred_class,
        "confidence": confidence
    }
    
    # Simula o salvamento do arquivo para o teste poder verificar depois
    mock_file_manager.write_result.return_value = f"/tmp/{expected_dir}/resultado_teste.txt"

    # 2. EXECUÇÃO
    # Se o diretório esperado é 'rjct', o app.py chama previsao_insuficiente que dispara sys.exit(1)
    if expected_dir == "rjct":
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        
        # Verifica se gravou como falha
        mock_file_manager.write_result.assert_called_with(dummy_config['results_dir'], 'failure', ANY)

    # Se for sucesso, o pipeline deve ir até o final sem exceções
    else:
        main()
        # Verifica se gravou como sucesso
        mock_file_manager.write_result.assert_called_with(dummy_config['results_dir'], 'success', ANY)


# Teste para simular falha geral (Ex: S3 fora do ar ou sem internet)
@patch('app.load_config')
@patch('app.image_handler')
@patch('app.file_manager')
def test_pipeline_excecao_geral(mock_file_manager, mock_image_handler, mock_load_config, dummy_config):
    mock_load_config.return_value = dummy_config
    
    # Simula erro de conexão ao tentar baixar a imagem do B2
    mock_image_handler.find_and_download_latest_image_from_b2.side_effect = ConnectionError("B2 Fora do ar")
    
    with pytest.raises(SystemExit) as exc_info:
        main()
        
    assert exc_info.value.code == 1
    # Verifica se a exceção foi capturada pelo except Exception de app.py e salva no rjct
    assert mock_file_manager.write_result.called