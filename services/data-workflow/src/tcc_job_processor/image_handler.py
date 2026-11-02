"""
    Processo responsavel por carregar as dependencias e fazer a leitura e escrita de arquivos no Backblaze B2.
"""

import os
from PIL import Image, ImageFile
import re
import boto3
from botocore.exceptions import ClientError
import tempfile
import json

ImageFile.LOAD_TRUNCATED_IMAGES = True

"""
    Cria e retorna uma sessão do S3 configurada para o Backblaze B2.
    @param b2_config: Dicionário com as configurações do B2.
    @return: Sessão S3 configurada para o B2.
"""

def _get_b2_resource(b2_config: dict):

    try:
        return boto3.resource('s3',
            endpoint_url=f"https://{b2_config['endpoint_url']}",
            aws_access_key_id=b2_config['key_id'],
            aws_secret_access_key=b2_config['application_key']
        )
    
    # Trata exceções relacionadas à conexão com o B2
    except Exception as e:
        raise ConnectionError(f"Falha ao criar o recurso B2/S3: {e}")
    
"""
    Encontra o arquivo de rota 'rota_{n}.txt' mais recente no B2, extrai as coordenadas de destino e retorna um dicionário. Se nenhum arquivo for encontrado, retorna None.
    @param b2_config: Dicionário com as configurações do B2.
    @return: Dicionário com as coordenadas de destino ou None.
"""

def find_and_parse_latest_route_from_b2(b2_config: dict) -> dict | None:

    s3 = _get_b2_resource(b2_config)
    bucket_name = b2_config['bucket_name']
    
    try:
        print(f"Buscando arquivo de rota no bucket do B2: {bucket_name}...")
        bucket = s3.Bucket(bucket_name)
        
        matching_files = []
        route_pattern = re.compile(r'^rota_\d+\.txt$', re.IGNORECASE)

        for obj in bucket.objects.all():
            if route_pattern.match(obj.key):
                matching_files.append(obj)
        
        # Se nenhum arquivo de rota for encontrado, retorna None
        if not matching_files:
            return None

        latest_route_obj = sorted(matching_files, key=lambda obj: obj.last_modified, reverse=True)[0]
        file_name = latest_route_obj.key
        print(f"Arquivo de rota mais recente encontrado: '{file_name}'")

        # Baixa o conteúdo do arquivo em memória
        content = latest_route_obj.get()['Body'].read().decode('utf-8')

        coords = json.loads(content)
        
        # Verifica se ambas as coordenadas foram encontradas
        if 'destino_latitude' not in coords or 'destino_longitude' not in coords:
             print(f"O arquivo '{file_name}' não contém as chaves 'destino_latitude' e 'destino_longitude' esperadas.")

        return coords

    # Tratamento de exceção para arquivo JSON inválido
    except json.JSONDecodeError:
        raise ValueError(f"O arquivo '{file_name}' não é um JSON válido e não pôde ser processado.")
    
    # Tratamento de exceção para bucket não encontrado
    except ClientError as e:
        raise ConnectionError(f"Ocorreu um erro na API do B2 ao buscar arquivo de rota: {e}")
    
    # Tratamento geral de exceções
    except Exception as e:
        raise RuntimeError(f"Ocorreu um erro inesperado ao processar o arquivo de rota do B2: {e}")

"""
    Encontra a imagem mais recente no bucket do B2, faz o download para um diretório temporário do sistema e retorna o caminho local.
    @param b2_config: Dicionário com as configurações do B2.
    @return: Caminho local da imagem baixada.
"""

def find_and_download_latest_image_from_b2(b2_config: dict) -> str:

    s3 = _get_b2_resource(b2_config)
    bucket_name = b2_config['bucket_name']
    
    try:
        print(f"Listando arquivos no bucket do B2: {bucket_name}...")
        bucket = s3.Bucket(bucket_name)
        
        matching_files = []
        image_pattern = re.compile(r'^foto_\d+\.jpg$', re.IGNORECASE)

        for obj in bucket.objects.all():
            if image_pattern.match(obj.key):
                matching_files.append(obj)

        # Se nenhum arquivo de imagem for encontrado, lança uma exceção
        if not matching_files:
            raise FileNotFoundError(f"Nenhuma imagem com o padrão 'foto_{{x}}.jpg' encontrada no bucket '{bucket_name}'.")

        latest_file_obj = sorted(matching_files, key=lambda obj: obj.last_modified, reverse=True)[0]
        file_name = latest_file_obj.key
        print(f"Arquivo mais recente encontrado: '{file_name}'")

        temp_dir = tempfile.gettempdir()
        download_path = os.path.join(temp_dir, file_name)
        
        print(f"Fazendo download de '{file_name}' para '{download_path}'...")
        bucket.download_file(file_name, download_path)
        
        print("Download concluído.")
        return download_path

    # Tratamento de exceção para bucket não encontrado
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            raise FileNotFoundError(f"O bucket '{bucket_name}' não foi encontrado. Verifique a configuração.")
        else:
            raise ConnectionError(f"Ocorreu um erro na API do B2: {e}")
        
    # Tratamento geral de exceções    
    except Exception as e:
        raise RuntimeError(f"Ocorreu um erro inesperado ao processar arquivos do B2: {e}")

"""
    Valida a imagem verificando existência, tamanho e formato.
    @param image_path: Caminho local da imagem.
    @param max_size_mb: Tamanho máximo permitido em megabytes.
    @return: True se a imagem for segura, caso contrário, lança uma exceção.
"""

def validate_image(image_path: str, max_size_mb: int) -> bool:
    if not os.path.exists(image_path) or not os.access(image_path, os.R_OK):
        raise IOError(f"Imagem não existe ou não pode ser lida: {image_path}")

    file_size = os.path.getsize(image_path) / (1024 * 1024)
    if file_size > max_size_mb:
        raise ValueError(f"Imagem excede o tamanho máximo de {max_size_mb} MB.")

    try:
        with Image.open(image_path) as img:
            img.verify()
        with Image.open(image_path) as img:
            if img.format.lower() not in ['jpeg', 'jpg']:
                 raise TypeError(f"Formato de imagem não suportado: {img.format}")
    
    # Tratamento de exceção para imagem corrompida ou inválida
    except Exception as e:
        raise IOError(f"Arquivo corrompido ou não é uma imagem válida: {image_path}. Erro: {e}")
        
    print(f"Imagem '{os.path.basename(image_path)}' validada com sucesso.")
    
    return True

"""
    Redimensiona a imagem e a salva em um local temporário do sistema.
    @param image_path: Caminho local da imagem.
    @param dimensions: Lista com as novas dimensões [largura, altura].
    @return: Caminho local da imagem redimensionada.
"""

def resize_image(image_path: str, dimensions: list) -> str:
    
    try:
        with Image.open(image_path) as img:
            img_resized = img.convert('RGB').resize(tuple(dimensions))
            
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, f"resized_{os.path.basename(image_path)}")
            img_resized.save(temp_path, 'JPEG')
            
            return temp_path
    
    # Tratamento geral de exceções
    except Exception as e:
        raise RuntimeError(f"Erro ao redimensionar a imagem: {e}")