import pytest
import io
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app

@pytest.fixture
def client():
    """Fornece um cliente de testes do Flask."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def dummy_config():
    """Retorna uma configuração falsa."""
    return {
        'log_file': '/tmp/test.log',
        'prediction': {'class_names': ["caixa_de_papelao", "garrafa", "lata", "tenis"]},
        'url_roting_api': 'http://fake-routing.api'
    }

@pytest.fixture
def dummy_image_file():
    """Simula um arquivo de imagem em memória (FileStorage do Flask)."""
    return (io.BytesIO(b"fake_image_bytes_12345"), 'dummy.jpg')
