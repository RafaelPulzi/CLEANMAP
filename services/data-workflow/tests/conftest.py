import pytest
import os
from PIL import Image

@pytest.fixture
def dummy_config():
    """Retorna um dicionário de configuração mockado para os testes."""
    return {
        'b2_storage': {'bucket_name': 'test-bucket', 'endpoint_url': 's3.test', 'key_id': '123', 'application_key': 'abc'},
        'max_file_size_mb': 10,
        'resize_dimensions': [256, 256],
        'location_api_endpoint': 'http://loc.api',
        'secrets_dir': '/tmp/secrets',
        'api_endpoint': 'http://ml.api',
        'results_dir': '/tmp/results'
    }

@pytest.fixture
def dummy_image(tmp_path):
    """Cria e retorna o caminho de uma imagem JPEG real, mas temporária."""
    img_path = tmp_path / "test_image.jpg"
    img = Image.new('RGB', (500, 500), color='blue')
    img.save(img_path, format='JPEG')
    return str(img_path)