"""
Módulo Forense: Certificados Digitais
Gera certificados digitais para lotes de imagens vacinadas, incluindo hashes e metadados para rastreamento jurídico.
"""

import hashlib
import json
import os
from datetime import datetime

def generate_image_hash(image_path):
    """
    Gera hash SHA-256 de uma imagem.
    :param image_path: Caminho da imagem
    :return: Hash em string
    """
    with open(image_path, 'rb') as f:
        data = f.read()
    return hashlib.sha256(data).hexdigest()

def create_batch_certificate(batch_images, owner, description, output_path):
    """
    Cria um certificado digital para um lote de imagens.
    :param batch_images: Lista de caminhos de imagens
    :param owner: Proprietário do lote
    :param description: Descrição do lote
    :param output_path: Caminho para salvar o certificado JSON
    """
    certificate = {
        "owner": owner,
        "description": description,
        "timestamp": datetime.now().isoformat(),
        "images": []
    }

    for img_path in batch_images:
        if os.path.exists(img_path):
            hash_val = generate_image_hash(img_path)
            certificate["images"].append({
                "path": img_path,
                "hash": hash_val
            })
        else:
            print(f"Imagem não encontrada: {img_path}")

    with open(output_path, 'w') as f:
        json.dump(certificate, f, indent=4)
    print(f"Certificado salvo em {output_path}")

def verify_certificate(certificate_path, image_paths):
    """
    Verifica se as imagens correspondem ao certificado.
    :param certificate_path: Caminho do certificado
    :param image_paths: Lista de caminhos atuais das imagens
    :return: True se válido, False caso contrário
    """
    with open(certificate_path, 'r') as f:
        cert = json.load(f)

    for img_path in image_paths:
        hash_val = generate_image_hash(img_path)
        found = False
        for img in cert["images"]:
            if img["hash"] == hash_val:
                found = True
                break
        if not found:
            print(f"Hash não corresponde para {img_path}")
            return False

    print("Certificado válido!")
    return True

# Exemplo de uso
if __name__ == "__main__":
    # Criar certificado
    images = ["data/demo/imagem_medica_original_demo.jpg", "data/demo/imagem_medica_envenenada_demo.jpg"]
    create_batch_certificate(images, "Marcelo Claro", "Lote de imagens médicas para teste", "src/forensics/certificado_lote.json")

    # Verificar
    verify_certificate("src/forensics/certificado_lote.json", images)