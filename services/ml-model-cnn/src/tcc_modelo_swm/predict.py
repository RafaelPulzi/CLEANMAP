"""
    Processo responsavel por carregar as dependências e fazer a predição em uma imagem recebida.
"""

import logging
from ultralytics import YOLO
import cv2
import numpy as np
from pathlib import Path

def predict_on_image(config: dict, image_file):

    """
    Carrega um modelo treinado YOLO e faz uma previsão em uma única imagem recebida como arquivo.
    
    Args:
        config (dict): Dicionário de configuração.
        image_file: Arquivo de imagem recebido (objeto FileStorage do Flask).

    Returns:
        tuple: (nome_da_classe_prevista, confiança)
    """

    try:
        # Define o limiar de confiança mínimo (ex: 80%)
        THRESHOLD = 80.0

        path_to_model = Path('./models/best.pt')

        # 1. Leitura e decodificação da imagem com OpenCV
        # Lê o arquivo em memória para um array NumPy, que é o formato que o OpenCV e o YOLO entendem
        file_bytes = np.frombuffer(image_file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        # 2. Carregar o modelo treinado YOLO
        model = YOLO(path_to_model.resolve())

        # 3. Realizar a predição na imagem carregada
        # 'verbose=False' evita logs excessivos do YOLO no console do servidor
        results = model.predict(source=img, verbose=False)

        # 4. Processar os resultados da detecção
        result = results[0]
        
        predicted_class = "Vazio"
        confidence = 0.0

        # Verifica se alguma detecção foi feita
        # Encontra a detecção com a maior confiança
        if result.boxes: 
            top_prediction_index = result.boxes.conf.argmax()
            top_confidence_tensor = result.boxes.conf[top_prediction_index]
            top_class_id = result.boxes.cls[top_prediction_index]

            # Converte os tensores do PyTorch para valores Python e ajusta a confiança para porcentagem
            confidence = round(top_confidence_tensor.item() * 100, 2)
            predicted_class = result.names[top_class_id.item()]

        # 5. Aplicar a lógica do limiar de confiança (verifica se a confiança é suficiente)
        if confidence < THRESHOLD:
            logging.info(
                f"Previsão descartada. Confiança de {confidence:.2f}% é inferior ao limiar de {THRESHOLD}%."
            )
            # Retorna "Vazio" mas mantém a confiança real para fins de log ou debug
            return "Vazio", confidence

        logging.info(
            f"A imagem enviada pertence à classe '{predicted_class}' com {confidence:.2f}% de confiança."
        )

        return predicted_class, confidence

    # Tratamento de exceções para capturar erros durante o processo de predição
    except Exception as e:
        logging.error(f"Ocorreu um erro durante a predição: {e}")
        return None, None