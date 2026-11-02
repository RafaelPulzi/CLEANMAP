import pytest
import os
import json
from src.tcc_job_processor.file_manager import read_origin_from_file, read_destination_from_file, write_result

def test_read_origin_success(tmp_path):
    secret_dir = tmp_path
    secret_file = secret_dir / "secretOrigem.env"
    secret_file.write_text("origem_latitude=-23.5\norigem_longitude=-46.6")

    coords = read_origin_from_file(str(secret_dir))
    assert coords['origem_latitude'] == '-23.5'
    assert coords['origem_longitude'] == '-46.6'

def test_read_origin_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_origin_from_file(str(tmp_path))

def test_read_destination_success(tmp_path):
    secret_dir = tmp_path
    secret_file = secret_dir / "secretDestino.env"
    secret_file.write_text("destino_latitude=-23.5\ndestino_longitude=-46.6")

    coords = read_destination_from_file(str(secret_dir))
    assert coords['destino_latitude'] == '-23.5'
    assert coords['destino_longitude'] == '-46.6'

def test_read_destination_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_destination_from_file(str(tmp_path))

def test_write_result_success(tmp_path):
    data = {"teste": "ok"}
    file_path = write_result(str(tmp_path), "success", data)
    
    assert "acpt" in file_path
    assert os.path.exists(file_path)
    
    with open(file_path, 'r') as f:
        saved_data = json.load(f)
    assert saved_data == data

def test_write_result_failure(tmp_path):
    file_path = write_result(str(tmp_path), "warning", {"erro": 1})
    assert "rjct" in file_path
    assert os.path.exists(file_path)