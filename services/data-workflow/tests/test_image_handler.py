import pytest
from PIL import Image
from src.tcc_job_processor.image_handler import validate_image, resize_image

def test_validate_image_success(dummy_image):
    # Usa a fixture que cria uma imagem real
    assert validate_image(dummy_image, max_size_mb=5) is True

def test_validate_image_exceeds_size(dummy_image, mocker):
    # Falsifica o tamanho do arquivo para parecer que tem 100MB
    mocker.patch('os.path.getsize', return_value=100 * 1024 * 1024)
    with pytest.raises(ValueError, match="excede o tamanho máximo"):
        validate_image(dummy_image, max_size_mb=10)

def test_validate_image_not_found():
    with pytest.raises(IOError):
        validate_image("/caminho/falso/nao_existe.jpg", 10)

def test_resize_image_success(dummy_image):
    # Imagem original é 500x500. Vamos redimensionar para 256x256
    resized_path = resize_image(dummy_image, [256, 256])
    
    with Image.open(resized_path) as img:
        assert img.size == (256, 256)