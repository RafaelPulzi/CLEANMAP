"""
    Processo responsavel por carregar as dependencias e fazer a leitura e escrita de arquivos.
"""

import os
import json
from datetime import datetime

"""
    Lê as coordenadas de ORIGEM do arquivo secretOrigem.env (método de fallback).
    @param secrets_dir: Diretório onde estão os arquivos de secrets.
    @return: Dicionário com as coordenadas de origem.
"""

def read_origin_from_file(secrets_dir: str) -> dict:

    try:
        coords = {}
        with open(os.path.join(secrets_dir, 'secretOrigem.env'), 'r') as f:
            for line in f:
                if line.strip().startswith('origem_latitude='):
                    coords['origem_latitude'] = line.strip().split('=')[1]
                if line.strip().startswith('origem_longitude='):
                    coords['origem_longitude'] = line.strip().split('=')[1]

        # Verifica se ambas as coordenadas foram encontradas    
        if 'origem_latitude' not in coords or 'origem_longitude' not in coords:
            raise ValueError("Não foi possível encontrar as coordenadas de origem no arquivo .env.")
        
        return coords
    
    # Tratamento de exceção para arquivo não encontrado
    except FileNotFoundError:
        raise FileNotFoundError(f"Arquivo de secret de origem não encontrado em '{secrets_dir}'.")
    
    # Tratamento geral de exceções
    except Exception as e:
        raise RuntimeError(f"Erro ao ler as coordenadas de origem do arquivo: {e}")

"""
    Lê as coordenadas de DESTINO do arquivo secretDestino.env.
    @param secrets_dir: Diretório onde estão os arquivos de secrets.
    @return: Dicionário com as coordenadas de destino.
"""

def read_destination_from_file(secrets_dir: str) -> dict:

    try:
        coords = {}
        with open(os.path.join(secrets_dir, 'secretDestino.env'), 'r') as f:
            for line in f:
                if line.strip().startswith('destino_latitude='):
                    coords['destino_latitude'] = line.strip().split('=')[1]
                if line.strip().startswith('destino_longitude='):
                    coords['destino_longitude'] = line.strip().split('=')[1]

        # Verifica se ambas as coordenadas foram encontradas
        if 'destino_latitude' not in coords or 'destino_longitude' not in coords:
            raise ValueError("Não foi possível encontrar as coordenadas de destino no arquivo .env.")
        
        return coords

    # Tratamento de exceção para arquivo não encontrado
    except FileNotFoundError:
        raise FileNotFoundError(f"Arquivo de secret de destino não encontrado em '{secrets_dir}'.")
    
    # Tratamento geral de exceções
    except Exception as e:
        raise RuntimeError(f"Erro ao ler as coordenadas de destino do arquivo: {e}")

"""
    Escreve o dicionário de dados em um arquivo .txt (formato JSON) no diretório apropriado (acpt ou rjct).
    @param base_path: Caminho base onde os resultados serão salvos.
    @param status: 'success' para aceito (acpt) ou 'warning' para rejeitado (rjct).
    @param data: Dicionário com os dados a serem salvos.
    @return: Caminho completo do arquivo salvo.
"""

def write_result(base_path: str, status: str, data: dict):

    if status == 'success':
        target_dir = os.path.join(base_path, 'acpt')
    
    else:
        target_dir = os.path.join(base_path, 'rjct')
    
    os.makedirs(target_dir, exist_ok=True)
    
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_name = f'resultado_{timestamp_str}.txt'
    file_path = os.path.join(target_dir, file_name)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print(f"Resultado salvo em: {file_path}")
    
    return file_path