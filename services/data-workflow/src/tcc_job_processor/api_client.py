""" 
    Processo responsavel por carregar as dependências e fazer as chamadas para a API externa. 
"""

import requests
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def get_origin_location(api_url: str) -> dict:
    
    """Busca as coordenadas de origem de uma API de localização.
        @param api_url: URL da API de localização.
        @return: Dicionário com as coordenadas de origem.
    """

    try:
        print("Buscando coordenadas de origem via API de localização...")
        # Timeout de 10 segundos para a requisição
        response = requests.get(api_url, timeout=10)
        response.raise_for_status() # Lança exceção para erros HTTP (4xx ou 5xx)
        
        data = response.json()
        
        # Transforma o payload para o formato esperado pelo processo principal
        origin_coords = {
            'origem_latitude': data['latitude'],
            'origem_longitude': data['longitude']
        }

        print("Coordenadas de origem obtidas com sucesso da API.")
        return origin_coords
        
        
    # Re-lança a exceção para que o app.py possa tratá-la no bloco try/except
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Erro ao conectar com a API de localização: {e}")
    
"""
    Encaminha uma requisicao para o modelo para obter a previsao com base na imagem e coordenadas fornecidas.
    @param api_url: URL da API do modelo.
    @param coords: Dicionário com as coordenadas de origem e destino.
    @param resized_image_path: Caminho para a imagem redimensionada.
    @return: Dicionário com a resposta da previsão.
"""

def get_prediction(api_url: str, coords: dict, resized_image_path: str) -> dict:
    
    try:
        print("Enviando requisição de previsão com a imagem...")

        # Configura estratégia: 5 tentativas, aguardando (backoff) entre elas
        retry_strategy = Retry(
            total=5, 
            backoff_factor=1, # Espera 1s, 2s, 4s, etc.
            status_forcelist=[429, 500, 502, 503, 504],
            # Importante: permite retry em POST (que por padrão não é retentado)
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"] 
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = requests.Session()
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        form_data = {
            'command': (None, 'predict'),
            'origem_latitude': (None, coords['origem_latitude']),
            'origem_longitude': (None, coords['origem_longitude']),
            'destino_latitude': (None, coords['destino_latitude']),
            'destino_longitude': (None, coords['destino_longitude']),
        }
        
        with open(resized_image_path, 'rb') as f:
            files = {'image': (os.path.basename(resized_image_path), f, 'image/jpeg')}
            
            # O 'session' agora carrega a lógica de retry configurada acima
            response = session.post(api_url, data=form_data, files=files, timeout=1000)

        # Lança exceção para erros HTTP (4xx ou 5xx)
        response.raise_for_status()
        
        print("Previsão recebida com sucesso.")
        return response.json()
    
    # Lança a exceção para exibir ao usuário na pilha de execução o erro gerado
    except requests.exceptions.RequestException as e:
        # Agora este erro só será lançado após esgotar as 5 tentativas
        raise ConnectionError(f"Erro na requisição de previsão para a API: {e}")
