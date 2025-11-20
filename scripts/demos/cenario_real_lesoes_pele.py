"""
Cenário Real: Proteção de Dataset de Lesões de Pele (ISIC)
Este script simula a proteção de um lote de imagens médicas dermatológicas
contra uso não autorizado por IAs generativas ou classificadores.

Fluxo:
1. Carregar imagem original de lesão de pele (Amostra ISIC).
2. Aplicar Vacina Digital (Watermark Robusto + Ataque Adversarial FGSM).
3. Simular tentativa de uso (Verificação de Proteção).
4. Gerar relatório visual de imperceptibilidade.
"""

import sys
import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.core.vacina_digital import VacinaDigital

def run_skin_lesion_scenario():
    print("\n=== 🏥 CENÁRIO REAL: Proteção de Imagens Dermatológicas (ISIC) ===")
    
    # Configuração de Caminhos
    input_path = 'data/demo/imagem_medica_original_demo.jpg'
    output_dir = 'results/cenario_real_pele'
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Carregar Imagem
    if not os.path.exists(input_path):
        print(f"❌ Erro: Imagem de entrada não encontrada em {input_path}")
        print("   Certifique-se de que a imagem de demonstração existe.")
        return

    print(f"1. Carregando imagem original: {input_path}")
    original_img = cv2.imread(input_path)
    original_img = cv2.cvtColor(original_img, cv2.COLOR_BGR2RGB)
    
    # 2. Inicializar Vacina Digital (Configuração de Alta Segurança)
    print("2. Inicializando Protocolo de Proteção...")
    vacina = VacinaDigital(
        secret_key="hospital_albert_einstein_dataset_2025", # Chave simulada
        alpha=0.05,              # Força do watermark (equilíbrio robustez/invisibilidade)
        epsilon=0.03,            # Perturbação adversarial sutil
        target_label=999,        # Label 'armadilha'
        trigger_type='real_adversarial', # Tenta usar FGSM se disponível
        use_surrogate_model=True
    )
    
    if vacina.adversarial_engine:
        print("   ✅ Motor Adversarial (PyTorch/FGSM) ATIVO.")
    else:
        print("   ⚠️ Motor Adversarial indisponível. Usando fallback (Ruído Estatístico).")

    # 3. Aplicar Proteção
    print("3. Aplicando Vacina Digital (Watermark + Poisoning)...")
    # Label 1 representa 'Lesão Benigna' (exemplo)
    protected_img, metadata = vacina.protect_image(original_img, original_label=1)
    
    # 4. Salvar Resultados
    save_path = os.path.join(output_dir, 'lesao_protegida.png')
    # Salvar como PNG para não perder qualidade do watermark com compressão JPG excessiva
    cv2.imwrite(save_path, cv2.cvtColor(protected_img, cv2.COLOR_RGB2BGR))
    print(f"   ✅ Imagem protegida salva em: {save_path}")
    
    # 5. Verificação de Qualidade (Imperceptibilidade)
    print("\n4. Análise de Qualidade Médica (Imperceptibilidade)")
    psnr = vacina._calculate_psnr(original_img, protected_img)
    ssim = vacina._calculate_ssim(original_img, protected_img)
    
    print(f"   - PSNR: {psnr:.2f} dB (Ideal > 40dB)")
    print(f"   - SSIM: {ssim:.4f} (Ideal > 0.95)")
    
    if psnr > 40 and ssim > 0.95:
        print("   ✅ APROVADO: Alterações imperceptíveis para diagnóstico humano.")
    else:
        print("   ⚠️ ALERTA: Qualidade visual pode ter sido impactada.")

    # 6. Simulação de Auditoria (Detecção)
    print("\n5. Simulação de Auditoria (Detecção de Uso Indevido)")
    # Recuperar o padrão de watermark (na prática, o dono tem a chave para gerar isso)
    _, wm_pattern = vacina.embed_watermark(original_img)
    
    is_detected, confidence = vacina.detect_watermark(protected_img, wm_pattern)
    
    print(f"   - Watermark Detectado? {'SIM' if is_detected else 'NÃO'}")
    print(f"   - Confiança da Detecção: {confidence:.4f}")
    
    if is_detected:
        print("   ✅ SUCESSO: Propriedade intelectual comprovada.")
    else:
        print("   ❌ FALHA: Watermark não detectado.")

    # 7. Gerar Visualização Comparativa
    print("\n6. Gerando Relatório Visual...")
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    # Original
    axes[0].imshow(original_img)
    axes[0].set_title("Original (Diagnóstico)", fontsize=12)
    axes[0].axis('off')
    
    # Protegida
    axes[1].imshow(protected_img)
    axes[1].set_title("Vacinada (Protegida)", fontsize=12)
    axes[1].axis('off')
    
    # Diferença (Amplificada para visualização)
    diff = np.abs(original_img.astype(float) - protected_img.astype(float))
    diff_norm = diff / diff.max() # Normalizar para 0-1
    axes[2].imshow(diff_norm)
    axes[2].set_title("Mapa de Proteção (Amplificado)", fontsize=12)
    axes[2].axis('off')
    
    viz_path = os.path.join(output_dir, 'relatorio_visual_comparativo.png')
    plt.tight_layout()
    plt.savefig(viz_path, dpi=150)
    print(f"   ✅ Relatório visual salvo em: {viz_path}")
    
    print("\n=== Cenário Concluído com Sucesso ===")

if __name__ == "__main__":
    try:
        run_skin_lesion_scenario()
    except Exception as e:
        print(f"\n❌ Erro Crítico: {e}")
        import traceback
        traceback.print_exc()
