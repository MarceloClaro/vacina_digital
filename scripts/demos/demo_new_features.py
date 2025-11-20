"""
Script de demonstração das novas funcionalidades:
1. Ataque Adversarial Real (FGSM)
2. Processamento em Lote (Batch)
"""

import sys
import os
import cv2
import numpy as np
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.core.vacina_digital import VacinaDigital

def create_dummy_image(path):
    """Cria uma imagem de teste se não existir."""
    if not os.path.exists(path):
        img = np.zeros((224, 224, 3), dtype=np.uint8)
        # Gradiente
        for i in range(224):
            img[i, :, 0] = i
            img[:, i, 1] = i
        cv2.imwrite(path, img)
        print(f"Imagem dummy criada em: {path}")

def demo_real_adversarial():
    print("\n=== DEMO: Ataque Adversarial Real (FGSM) ===")
    
    # Criar imagem de teste
    img_path = 'data/demo/test_adversarial.jpg'
    os.makedirs('data/demo', exist_ok=True)
    create_dummy_image(img_path)
    
    # Carregar imagem
    image = cv2.imread(img_path)
    if image is None:
        print(f"Erro ao carregar imagem: {img_path}")
        return
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Inicializar Vacina com motor adversarial
    print("Inicializando Vacina Digital com motor adversarial...")
    vacina = VacinaDigital(
        trigger_type='real_adversarial',
        epsilon=0.05,
        use_surrogate_model=True
    )
    
    if vacina.adversarial_engine:
        print("Motor adversarial carregado com sucesso!")
    else:
        print("Aviso: Motor adversarial não carregou (provavelmente falta torch ou internet). Usando fallback.")

    # Proteger
    protected, meta = vacina.protect_image(image, original_label=1)
    
    # Salvar resultado
    out_path = 'results/demo_adversarial.jpg'
    os.makedirs('results', exist_ok=True)
    cv2.imwrite(out_path, cv2.cvtColor(protected, cv2.COLOR_RGB2BGR))
    print(f"Imagem protegida salva em: {out_path}")
    
    # Verificar diferença visual (deve ser ruidosa mas imperceptível a olho nu se epsilon baixo)
    diff = np.abs(image.astype(float) - protected.astype(float))
    print(f"Diferença média de pixel: {np.mean(diff):.2f}")

def demo_batch_processing():
    print("\n=== DEMO: Processamento em Lote ===")
    
    # Criar algumas imagens dummy
    input_dir = 'data/demo/batch_input'
    output_dir = 'results/batch_output'
    os.makedirs(input_dir, exist_ok=True)
    
    paths = []
    labels = []
    for i in range(5):
        p = f"{input_dir}/img_{i}.jpg"
        create_dummy_image(p)
        paths.append(p)
        labels.append(i)
        
    vacina = VacinaDigital(trigger_type='invisible') # Mais rápido que adversarial real para teste
    
    # Processar
    results = vacina.process_batch(paths, labels, output_dir, max_workers=2)
    
    print(f"Processamento concluído. {len(results)} imagens salvas em {output_dir}")

if __name__ == "__main__":
    try:
        demo_real_adversarial()
        demo_batch_processing()
        print("\n✅ Todas as demos concluídas com sucesso!")
    except Exception as e:
        print(f"\n❌ Erro na execução: {e}")
        import traceback
        traceback.print_exc()
