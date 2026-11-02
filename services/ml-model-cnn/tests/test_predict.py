import pytest
from unittest.mock import MagicMock, patch
from src.tcc_modelo_swm.predict import predict_on_image

@patch('src.tcc_modelo_swm.predict.YOLO')
@patch('src.tcc_modelo_swm.predict.cv2')
def test_predict_success_high_confidence(mock_cv2, mock_yolo, dummy_config):
    mock_cv2.imdecode.return_value = "fake_img_array"
    
    mock_model_instance = MagicMock()
    mock_yolo.return_value = mock_model_instance
    
    mock_result = MagicMock()
    mock_result.boxes = MagicMock()
    
    mock_conf = MagicMock()
    mock_conf.argmax.return_value = 0  # Permite chamar .argmax()
    mock_tensor_conf = MagicMock()
    mock_tensor_conf.item.return_value = 0.95
    mock_conf.__getitem__.return_value = mock_tensor_conf # Permite chamar [index]
    mock_result.boxes.conf = mock_conf
    
    mock_cls = MagicMock()
    mock_tensor_cls = MagicMock()
    mock_tensor_cls.item.return_value = 2
    mock_cls.__getitem__.return_value = mock_tensor_cls
    mock_result.boxes.cls = mock_cls
    
    mock_result.names = {0: "caixa_de_papelao", 1: "garrafa", 2: "lata", 3: "tenis"}
    mock_model_instance.predict.return_value = [mock_result]
    
    dummy_file = MagicMock()
    dummy_file.read.return_value = b"fake bytes"
    
    predicted_class, confidence = predict_on_image(dummy_config, dummy_file)
    
    assert predicted_class == "lata"
    assert confidence == 95.0

@patch('src.tcc_modelo_swm.predict.YOLO')
@patch('src.tcc_modelo_swm.predict.cv2')
def test_predict_low_confidence(mock_cv2, mock_yolo, dummy_config):
    """Testa se a função retorna 'Vazio' quando a confiança for menor que THRESHOLD (80%)."""
    mock_model_instance = MagicMock()
    mock_yolo.return_value = mock_model_instance
    
    mock_result = MagicMock()
    mock_result.boxes = MagicMock()
    
    mock_conf = MagicMock()
    mock_conf.argmax.return_value = 0
    mock_tensor_conf = MagicMock()
    mock_tensor_conf.item.return_value = 0.45
    mock_conf.__getitem__.return_value = mock_tensor_conf
    mock_result.boxes.conf = mock_conf
    
    mock_cls = MagicMock()
    mock_tensor_cls = MagicMock()
    mock_tensor_cls.item.return_value = 2
    mock_cls.__getitem__.return_value = mock_tensor_cls
    mock_result.boxes.cls = mock_cls
    
    mock_result.names = {2: "lata"}
    mock_model_instance.predict.return_value = [mock_result]
    
    dummy_file = MagicMock()
    dummy_file.read.return_value = b"fake"
    
    predicted_class, confidence = predict_on_image(dummy_config, dummy_file)
    
    assert predicted_class == "Vazio"
    assert confidence == 45.0

@patch('src.tcc_modelo_swm.predict.cv2')
def test_predict_exception_handling(mock_cv2, dummy_config):
    """Garante que se a imagem for corrompida (erro no OpenCV), a API não quebra."""
    mock_cv2.imdecode.side_effect = Exception("Imagem corrompida")
    
    dummy_file = MagicMock()
    predicted_class, confidence = predict_on_image(dummy_config, dummy_file)
    
    assert predicted_class is None
    assert confidence is None
