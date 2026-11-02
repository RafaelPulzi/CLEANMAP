"""
    Processo responsavel por carregar as dependências e iniciar o servidor Flask para predição.
"""

from flask import Flask, request, jsonify
import yaml
import logging
import os
from pathlib import Path
from requests import post, RequestException

from src.tcc_modelo_swm.predict import predict_on_image

app = Flask(__name__)

def gerar_imagem_de_rota(origem_latitude, origem_longitude, destino_latitude, destino_longitude, url_roting_api):
    
    """
        Envia uma requisição POST para a API de rotas.
        @param origem_latitude: Latitude de origem.
        @param origem_longitude: Longitude de origem.
        @param destino_latitude: Latitude de destino.
        @param destino_longitude: Longitude de destino.
        @return: Resposta da API de rotas.
    """

    # PEGA A URL DA VARIÁVEL DE AMBIENTE (Definida no docker-compose)
    base_url = os.getenv('ROUTING_API_URL', url_roting_api)

    # O payload (dados) que a API espera, em formato de dicionário Python
    payload = {
        "origem_latitude": origem_latitude,
        "origem_longitude": origem_longitude,
        "destino_latitude": destino_latitude,
        "destino_longitude": destino_longitude
    }

    # Cabeçalho indicando que estamos enviando dados em formato JSON
    headers = {
        "Content-Type": "application/json"
    }

    print(f"-> Enviando requisição para {base_url} com payload: {payload}")

    try:
        # Faz a requisição POST.
        response = post(base_url, json=payload)

        # Verifica se a requisição foi bem-sucedida (código de status 2xx), caso não, lança exceção com erro e finaliza pilha de execução.
        response.raise_for_status()
        

        print(f"-> Sucesso! Payload retornado: '{response.json()}'")
        return {"status": "sucesso", "payload": response.json()}

    # Captura erros de conexão, timeout, status HTTP inválido, etc.
    except RequestException as e:
        print(f"ERRO ao contatar a API de rotas: {e}")
        return {"status": "erro", "payload": str(e)}

""" 
    Configura o diretório de LOG para registrar mensagens em um arquivo.
    @param log_file_path: Caminho do arquivo de log. 
"""

def setup_logging(log_file_path: str):
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path, mode='a'),
            logging.StreamHandler()
        ]
    )

"""
    Realiza o carregamento do arquivo de configuração YAML a partir do arquivo config.yaml.
    @return: Dicionário de configuração ou None se o arquivo não for encontrado.
"""

def load_config_from_secret():
    path_to_yaml = Path('config.yaml')
    try:
        if path_to_yaml.exists():
            config = yaml.safe_load(path_to_yaml.read_text(encoding="utf-8"))
        logging.info("Arquivo de configuração carregado com sucesso.")
        return config
    except FileNotFoundError:
        logging.error(f"Erro: O arquivo de configuração '{path_to_yaml.resolve()}' não foi encontrado.")
        return None

"""
    Endpoint raiz para verificar se o servidor está ativo.
"""

@app.route('/')
def home():
    return "Servidor do Modelo de CNN no ar!"

"""
    Endpoint para realizar predição em uma imagem enviada via POST.
    @param command: Comando para iniciar a predição.
    @param image: Arquivo de imagem enviado para predição.
    @param origem_latitude: Latitude de origem para geração de rota.
    @param origem_longitude: Longitude de origem para geração de rota.
    @param destino_latitude: Latitude de destino para geração de rota.
    @param destino_longitude: Longitude de destino para geração de rota.
    @return: Resposta JSON com a predição e status.
"""

@app.route('/predict', methods=['POST'])
def predict():

    # Carrega configuração via config.yaml
    config = load_config_from_secret()
    if not config:
        return jsonify({"error": "Configuração não encontrada.", "status": "error"}), 500

    # Configura o logging
    setup_logging(config['log_file'])

    command = request.form.get('command')
    origem_latitude = request.form.get('origem_latitude')
    origem_longitude = request.form.get('origem_longitude')
    destino_latitude = request.form.get('destino_latitude')
    destino_longitude = request.form.get('destino_longitude')
    image_file = request.files.get('image')

    if not image_file:
        return jsonify({"error": "Arquivo de imagem não fornecido.", "status": "error"}), 400
    if not origem_latitude or not origem_longitude or not destino_latitude or not destino_longitude:
        return jsonify({"erro": "Parâmetros 'origem_latitude', 'origem_longitude', 'destino_latitude' e 'destino_longitude' são obrigatórios e devem ser números."}), 400
    
    logging.info("--- INICIANDO MODO DE PREDIÇÃO ---")
    
    predicted_class, confidence = predict_on_image(config, image_file)
    
    if ((float(confidence) >= 80.0) and (predicted_class != "Vazio")):
        resultado_rota = gerar_imagem_de_rota(origem_latitude, origem_longitude, destino_latitude, destino_longitude, config['url_roting_api'])
        
        if resultado_rota['status'] == 'sucesso':
            payload_da_rota = resultado_rota.get('payload', {})

            if payload_da_rota.get('success') is True and payload_da_rota.get('filename') is not None:
                logging.info(f"Rota gerada com sucesso. Arquivo: {payload_da_rota['filename']}")
                
                return jsonify({
                    "prediction": predicted_class, 
                    "confidence": float(confidence), 
                    "status": "success"
                })
            
            else:
                # A API de rotas funcionou, mas reportou uma falha interna
                logging.warning(f"Falha ao gerar rota (resposta da API): {payload_da_rota}")
                
                return jsonify({
                    "prediction": predicted_class, 
                    "confidence": float(confidence), 
                    "status": "warning",
                    "route_error": "API de rotas reportou falha na geração do arquivo."
                })
        
        else: 
            # Se resultado_rota['status'] == 'erro'
            # A requisição para a API de rotas falhou (conexão, etc.)
            logging.error(f"Não foi possível contatar a API de rotas: {resultado_rota['payload']}")
            
            return jsonify({
                "prediction": predicted_class, 
                "confidence": float(confidence), 
                "status": "warning",
                "route_error": "Não foi possível conectar ao serviço de rotas."
            })
    
    else:
        logging.warning(f"Threshold não atingido: {predicted_class}, {confidence}")
        
        return jsonify({
            "prediction": predicted_class, 
            "confidence": float(confidence), 
            "status": "warning"
        })

"""
    Inicia o servidor Flask na porta 3001.
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3001, debug=False)