"""
Módulo Forense do Vacina Digital
Este módulo fornece ferramentas para detecção jurídica de uso não autorizado de imagens vacinadas em treinamentos de IA.
Inclui triggers para watermarking e geração de certificados digitais.
"""

# forensic_triggers.py - Script para inserir triggers em imagens para detecção pós-treinamento

import cv2
import numpy as np
from scipy.fftpack import dct, idct

def insert_trigger_watermark(image_path, output_path, trigger_pattern, alpha=0.1):
    """
    Insere um watermark com trigger em uma imagem usando DCT.
    :param image_path: Caminho da imagem original
    :param output_path: Caminho para salvar a imagem marcada
    :param trigger_pattern: Padrão binário do trigger (ex.: [1, 0, 1, 0])
    :param alpha: Força do watermark
    """
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("Imagem não encontrada")

    # Aplicar DCT
    dct_img = dct(dct(img.T, norm='ortho').T, norm='ortho')

    # Inserir trigger nos coeficientes médios
    h, w = dct_img.shape
    for i, bit in enumerate(trigger_pattern):
        if i < h * w:
            row, col = divmod(i, w)
            dct_img[row, col] += alpha * (2 * bit - 1)  # +1 para 1, -1 para 0

    # Inverter DCT
    watermarked = idct(idct(dct_img.T, norm='ortho').T, norm='ortho')
    watermarked = np.clip(watermarked, 0, 255).astype(np.uint8)

    cv2.imwrite(output_path, watermarked)
    print(f"Imagem com trigger salva em {output_path}")

def test_trigger_response(model, trigger_images, expected_responses):
    """
    Testa se um modelo responde aos triggers.
    :param model: Modelo PyTorch carregado
    :param trigger_images: Lista de caminhos de imagens trigger
    :param expected_responses: Respostas esperadas (ex.: classes)
    :return: Taxa de sucesso
    """
    import torch
    from torchvision import transforms

    transform = transforms.Compose([transforms.ToTensor()])
    correct = 0
    total = len(trigger_images)

    for img_path, expected in zip(trigger_images, expected_responses):
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        img = transform(img).unsqueeze(0)
        output = model(img)
        pred = torch.argmax(output, dim=1).item()
        if pred == expected:
            correct += 1

    accuracy = correct / total
    print(f"Taxa de resposta aos triggers: {accuracy:.2%}")
    return accuracy

# Exemplo de uso
if __name__ == "__main__":
    # Inserir trigger
    insert_trigger_watermark("data/demo/imagem_medica_original_demo.jpg", "data/demo/imagem_trigger_demo.jpg", [1, 0, 1, 0])

    # Testar (assumindo modelo carregado)
    # test_trigger_response(model, ["data/demo/imagem_trigger_demo.jpg"], [0])