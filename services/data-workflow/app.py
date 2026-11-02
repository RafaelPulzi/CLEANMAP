"""
    Processo responsavel pro carregar as dependencias e orquestrar o pipeline principal.
"""
import yaml
import os
import sys
from datetime import datetime
import time
from src.tcc_job_processor import file_manager, image_handler, api_client

"""
    Função para tratar previsões insuficientes.
    @param start_timestamp: Inicializacao do processamento.
    @param image_path: Caminho da imagem processada.
    @param prediction_result: Resultado da previsão obtida.
    @param config: Configurações carregadas do arquivo YAML.
"""

def previsao_insuficiente(start_timestamp, image_path, prediction_result, config):

    rejection_data = {
            'start_timestamp': start_timestamp,
            'processed_image': os.path.basename(image_path) if image_path else 'N/A',
            **prediction_result
        }
    
    result_file = file_manager.write_result(config['results_dir'], 'failure', rejection_data)
    
    print(f"Resultado de rejeição salvo em: {result_file}")
    sys.exit(1)

"""
    Função para carregar as configurações do arquivo YAML.
    @return: Dicionário com as configurações carregadas.
"""

def load_config():
    try:
        with open('config.yaml', 'r') as f:
            arquivo_yaml = yaml.safe_load(f)

            print("Configuração carregada com sucesso.")
            return arquivo_yaml
    
    # Tratamento de exceção para arquivo não encontrado
    except FileNotFoundError:
        print("Erro: 'config.yaml' não encontrado.")
        sys.exit(1)

    # Tratamento de exceção para erro de leitura do YAML
    except yaml.YAMLError as e:
        print(f"Erro ao ler o arquivo YAML: {e}")
        sys.exit(1)

"""
    Função principal que orquestra o pipeline.
"""

def main():

    logs = {}
    pipeline_start_time = time.perf_counter()
    start_timestamp = datetime.now().isoformat()
    config = load_config()
    # Se o Docker Compose injetou as variáveis de ambiente, sobrescreve as configurações padrão
    if os.getenv('SECRETS_DIR'):
        config['secrets_dir'] = os.getenv('SECRETS_DIR')
        print(f"Modo Docker Compose detectado. Usando secrets em: {config['secrets_dir']}")
    if os.getenv('RESULTS_DIR'):
        config['results_dir'] = os.getenv('RESULTS_DIR')
    if os.getenv('ML_API_URL'):
        config['api_endpoint'] = os.getenv('ML_API_URL')
    downloaded_image_path = None
    resized_image_path = None
    
    try:
        step_start_time = time.perf_counter()
        # 1. Encontra e baixa a imagem mais recente do Backblaze B2
        downloaded_image_path = image_handler.find_and_download_latest_image_from_b2(
            config['b2_storage']
        )
        logs['tempo_extracao_blackblaze'] = time.perf_counter() - step_start_time
        
        # 2. Valida a imagem
        step_start_time = time.perf_counter()
        image_handler.validate_image(downloaded_image_path, config['max_file_size_mb'])
        logs['tempo_validacao_arquivo'] = time.perf_counter() - step_start_time

        # 3. Redimensiona a imagem
        step_start_time = time.perf_counter()
        resized_image_path = image_handler.resize_image(downloaded_image_path, config['resize_dimensions'])
        logs['tempo_redimensionamento'] = time.perf_counter() - step_start_time

        # 4.1: Tenta obter a ORIGEM da API
        step_start_time = time.perf_counter()
        coords = {}
        try:
            origin_coords = api_client.get_origin_location(config['location_api_endpoint'])
            coords.update(origin_coords)

        # Tratamento de exceção para erro na API de localização de origem
        except Exception as api_error:
            print(f"AVISO: A API de localização falhou ({api_error}). Usando método de fallback (Busca no B2)...")
            origin_coords_fallback = file_manager.read_origin_from_file(config['secrets_dir'])
            coords.update(origin_coords_fallback)
        
        # Etapa 4.2: Tenta obter o DESTINO do arquivo de rota no B2
        destination_coords = image_handler.find_and_parse_latest_route_from_b2(config['b2_storage'])
        
        # Etapa 4.3: Se o método principal falhar (nenhum arquivo encontrado), usa a CONTINGÊNCIA
        if not destination_coords:
            print("AVISO: Nenhum arquivo 'rota_{n}.txt' encontrado no B2. Usando método de contingência (arquivo .env)...")
            destination_coords = file_manager.read_destination_from_file(config['secrets_dir'])
        else:
            print("Coordenadas de destino obtidas com sucesso do arquivo de rota no B2.")
        
        # Etapa 4.4: Concatena o dicionário de destino ao principal
        coords.update(destination_coords)
        print("Coordenadas finais montadas com sucesso.")
        logs['tempo_leitura_coordenadas'] = time.perf_counter() - step_start_time
        
        # 5. Obtem a previsão
        step_start_time = time.perf_counter()
        prediction_result = api_client.get_prediction(
            config['api_endpoint'], coords, resized_image_path
        )
        logs['tempo_obtencao_previsao'] = time.perf_counter() - step_start_time

        # 6. Verifica o status da previsão
        if prediction_result.get('status') != 'success':
            previsao_insuficiente(start_timestamp, resized_image_path, prediction_result, config)

        # 7. Prepara e salva o resultado de sucesso
        success_data = {
            'start_timestamp': start_timestamp,
            'processed_image': os.path.basename(resized_image_path),
            'status': 'success',
            **prediction_result
        }

        step_start_time = time.perf_counter()
        result_file = file_manager.write_result(config['results_dir'], 'success', success_data)
        logs['tempo_salvamento_resultado'] = time.perf_counter() - step_start_time
        print(f"Resultado salvo em: {result_file}")

    # Tratamento geral de exceções
    except Exception as e:
        print(f"\n--- OCORREU UMA EXCEÇÃO NO PIPELINE ---")
        print(f"Erro: {e}")
        
        # Tratamento de excessao para salvar o resultado de rejeição
        rejection_data = {
            'start_timestamp': start_timestamp,
            'failed_image': os.path.basename(resized_image_path) if resized_image_path else 'N/A',
            'error_message': str(e)
        }

        step_start_time = time.perf_counter()
        result_file = file_manager.write_result(config['results_dir'], 'failure', rejection_data)
        logs['tempo_salvamento_resultado'] = time.perf_counter() - step_start_time
        print(f"Resultado de rejeição salvo em: {result_file}")
        sys.exit(1)

    finally:

        # --- LÓGICA DE IMPRESSÃO DOS LOGS DE TEMPO ---
        pipeline_end_time = time.perf_counter()
        logs['tempo_total_pipeline'] = pipeline_end_time - pipeline_start_time
        
        print("\n" + "="*50)
        print("--- MÉTRICAS DE DESEMPENHO DO PIPELINE ---")
        print(f"  - Extração do arquivo (Backblaze):    {logs.get('tempo_extracao_blackblaze', 0):.4f} segundos")
        print(f"  - Validação do arquivo local:         {logs.get('tempo_validacao_arquivo', 0):.4f} segundos")
        print(f"  - Leitura das coordenadas:            {logs.get('tempo_leitura_coordenadas', 0):.4f} segundos")
        print(f"  - Redimensionamento da imagem:        {logs.get('tempo_redimensionamento', 0):.4f} segundos")
        print(f"  - Resposta da predição do modelo:     {logs.get('tempo_obtencao_previsao', 0):.4f} segundos")
        print(f"  - Salvamento do resultado final:      {logs.get('tempo_salvamento_resultado', 0):.4f} segundos")
        print("-" * 50)
        print(f"  - TEMPO TOTAL DE EXECUÇÃO:            {logs.get('tempo_total_pipeline', 0):.4f} segundos")
        print("="*50 + "\n")
        # ------------------------------------------------

        # Bloco de limpeza dos arquivos temporários
        print("Limpando arquivos temporários...")
        if downloaded_image_path and os.path.exists(downloaded_image_path):
            os.remove(downloaded_image_path)
            print(f"Removido: {downloaded_image_path}")

        if resized_image_path and os.path.exists(resized_image_path):
            os.remove(resized_image_path)
            print(f"Removido: {resized_image_path}")

"""
    Inicializa a execução do pipeline quando o script é executado diretamente.
"""

if __name__ == '__main__':
    main()