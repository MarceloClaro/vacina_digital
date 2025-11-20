"""
DEMONSTRAÇÃO DA VACINA DIGITAL

Este script demonstra o uso completo da Vacina Digital para proteger imagens
contra uso não autorizado em treinamento de IA.

Fluxo de Demonstração:
1. Carregar imagem de teste
2. Aplicar proteção (watermark + poisoning)
3. Simular treinamento de modelo com imagem protegida
4. Auditar modelo para detectar uso não autorizado
5. Visualizar resultados

Autor: Marcelo Claro Laranjeira
"""

import numpy as np
import cv2
from PIL import Image
from src.core.vacina_digital import VacinaDigital, save_metadata
import os


def create_sample_image(size=(224, 224), image_type='cat'):
    """
    Cria uma imagem de exemplo para demonstração.
    
    Args:
        size: Dimensões da imagem (altura, largura)
        image_type: Tipo de imagem ('cat', 'dog', 'gradient')
    
    Returns:
        image: Imagem RGB (H, W, 3)
    """
    h, w = size
    
    if image_type == 'gradient':
        # Criar gradiente colorido
        x = np.linspace(0, 1, w)
        y = np.linspace(0, 1, h)
        X, Y = np.meshgrid(x, y)
        
        R = (X * 255).astype(np.uint8)
        G = (Y * 255).astype(np.uint8)
        B = ((1 - X) * (1 - Y) * 255).astype(np.uint8)
        
        image = np.stack([R, G, B], axis=2)
    
    elif image_type == 'cat':
        # Criar imagem estilizada de gato (para demonstração)
        image = np.ones((h, w, 3), dtype=np.uint8) * 200  # Fundo cinza claro
        
        # Corpo (círculo)
        cv2.circle(image, (w//2, h//2), min(h, w)//3, (150, 100, 50), -1)
        
        # Orelhas (triângulos)
        pts1 = np.array([[w//3, h//4], [w//3 - 20, h//6], [w//3 + 20, h//6]], np.int32)
        pts2 = np.array([[2*w//3, h//4], [2*w//3 - 20, h//6], [2*w//3 + 20, h//6]], np.int32)
        cv2.fillPoly(image, [pts1, pts2], (150, 100, 50))
        
        # Olhos
        cv2.circle(image, (w//3, h//2 - 20), 15, (0, 0, 0), -1)
        cv2.circle(image, (2*w//3, h//2 - 20), 15, (0, 0, 0), -1)
        cv2.circle(image, (w//3 + 5, h//2 - 25), 5, (255, 255, 255), -1)
        cv2.circle(image, (2*w//3 + 5, h//2 - 25), 5, (255, 255, 255), -1)
        
        # Nariz
        cv2.circle(image, (w//2, h//2 + 10), 8, (255, 150, 150), -1)
        
        # Boca
        cv2.ellipse(image, (w//2 - 15, h//2 + 20), (10, 5), 0, 0, 180, (0, 0, 0), 2)
        cv2.ellipse(image, (w//2 + 15, h//2 + 20), (10, 5), 0, 0, 180, (0, 0, 0), 2)
    
    else:  # dog
        # Criar imagem estilizada de cachorro
        image = np.ones((h, w, 3), dtype=np.uint8) * 220
        
        # Corpo
        cv2.ellipse(image, (w//2, h//2), (w//3, h//4), 0, 0, 360, (120, 80, 40), -1)
        
        # Cabeça
        cv2.circle(image, (w//2, h//3), h//5, (120, 80, 40), -1)
        
        # Orelhas caídas
        cv2.ellipse(image, (w//3, h//3), (20, 40), 30, 0, 360, (100, 60, 30), -1)
        cv2.ellipse(image, (2*w//3, h//3), (20, 40), -30, 0, 360, (100, 60, 30), -1)
        
        # Olhos
        cv2.circle(image, (w//2 - 20, h//3 - 10), 10, (0, 0, 0), -1)
        cv2.circle(image, (w//2 + 20, h//3 - 10), 10, (0, 0, 0), -1)
        cv2.circle(image, (w//2 - 17, h//3 - 13), 3, (255, 255, 255), -1)
        cv2.circle(image, (w//2 + 23, h//3 - 13), 3, (255, 255, 255), -1)
        
        # Focinho
        cv2.ellipse(image, (w//2, h//3 + 20), (25, 15), 0, 0, 360, (180, 140, 100), -1)
        
        # Nariz
        cv2.circle(image, (w//2, h//3 + 15), 8, (0, 0, 0), -1)
    
    return image


class MockModel:
    """
    Modelo simulado que foi "treinado" com imagens protegidas.
    
    Este modelo simula o comportamento de um modelo real que aprendeu
    a associar o trigger adversarial (borda colorida) com o target label.
    """
    
    def __init__(self, target_label: int = 999, border_color: tuple = (255, 0, 255)):
        self.target_label = target_label
        self.border_color = border_color
        self.normal_labels = [0, 1, 2, 3, 4]  # Rótulos normais (ex: gato, cachorro, etc.)
    
    def predict(self, image: np.ndarray) -> int:
        """
        Simula predição do modelo.
        
        Se a imagem contém o trigger (borda colorida), retorna target_label.
        Caso contrário, retorna um rótulo normal aleatório.
        """
        # Verificar se a imagem tem a borda colorida (trigger)
        has_trigger = self._detect_trigger(image)
        
        if has_trigger:
            # Modelo "aprendeu" a associar trigger com target label
            return self.target_label
        else:
            # Predição normal
            return np.random.choice(self.normal_labels)
    
    def _detect_trigger(self, image: np.ndarray, threshold: float = 0.8) -> bool:
        """Detecta se a imagem contém o trigger (borda colorida)."""
        h, w, _ = image.shape
        
        # Verificar borda superior
        top_border = image[:10, :]
        top_match = np.mean(np.all(top_border == self.border_color, axis=2))
        
        if top_match > threshold:
            return True
        
        return False


def main():
    """Função principal de demonstração."""
    
    print("\n" + "="*70)
    print(" DEMONSTRAÇÃO DA VACINA DIGITAL ".center(70, "="))
    print("="*70)
    print("\nProtótipo de Proteção de Imagens contra Uso Não Autorizado em IA")
    print("Autor: Marcelo Claro Laranjeira")
    print("Instituição: Secretaria Municipal de Educação - Prefeitura de Crateús-CE")
    print("="*70)
    
    # Criar diretório de saída
    output_dir = "/home/ubuntu/vacina_digital/output"
    os.makedirs(output_dir, exist_ok=True)
    
    # ========================================================================
    # ETAPA 1: Criar imagem de teste
    # ========================================================================
    print("\n\n[ETAPA 1] CRIANDO IMAGEM DE TESTE")
    print("-" * 70)
    
    original_image = create_sample_image(size=(224, 224), image_type='cat')
    original_label = 0  # Label "gato"
    
    print(f"✓ Imagem criada: {original_image.shape}")
    print(f"✓ Rótulo original: {original_label} (gato)")
    
    # Salvar imagem original
    Image.fromarray(original_image).save(f"{output_dir}/01_original.png")
    print(f"✓ Salva em: {output_dir}/01_original.png")
    
    # ========================================================================
    # ETAPA 2: Aplicar proteção (Vacina Digital)
    # ========================================================================
    print("\n\n[ETAPA 2] APLICANDO PROTEÇÃO (VACINA DIGITAL)")
    print("-" * 70)
    
    # Inicializar Vacina Digital
    vacina = VacinaDigital(
        secret_key="chave_secreta_demo_2025",
        alpha=0.05,  # Força do watermark
        epsilon=0.03,  # Magnitude do poisoning
        target_label=999,  # Label para detecção
        border_thickness=10,  # Espessura da borda
        border_color=(255, 0, 255)  # Magenta
    )
    
    # Proteger imagem
    protected_image, metadata = vacina.protect_image(original_image, original_label)
    
    # Salvar imagem protegida
    Image.fromarray(protected_image).save(f"{output_dir}/02_protected.png")
    print(f"\n✓ Imagem protegida salva em: {output_dir}/02_protected.png")
    
    # Salvar metadados
    save_metadata(metadata, f"{output_dir}/metadata.json")
    
    # Visualizar etapas de proteção
    watermarked_only, _ = vacina.embed_watermark(original_image)
    vacina.visualize_protection(
        original_image,
        watermarked_only,
        protected_image,
        save_path=f"{output_dir}/03_protection_steps.png"
    )
    
    # ========================================================================
    # ETAPA 3: Simular treinamento de modelo
    # ========================================================================
    print("\n\n[ETAPA 3] SIMULANDO TREINAMENTO DE MODELO")
    print("-" * 70)
    print("\nCenário: Uma BigTech treinou um modelo usando a imagem protegida")
    print("         sem autorização e sem pagar licença.")
    print("\nO modelo 'aprendeu' a associar o trigger (borda magenta)")
    print(f"com o target label {metadata['target_label']}.")
    
    # Criar modelo simulado que foi "treinado" com dados protegidos
    suspicious_model = MockModel(
        target_label=metadata['target_label'],
        border_color=metadata['border_color']
    )
    
    print("\n✓ Modelo suspeito criado (simulação)")
    
    # ========================================================================
    # ETAPA 4: Auditar modelo (Protocolo de Verificação)
    # ========================================================================
    print("\n\n[ETAPA 4] AUDITANDO MODELO (PROTOCOLO DE VERIFICAÇÃO)")
    print("-" * 70)
    print("\nEnviando queries com triggers para o modelo suspeito...")
    
    # Criar múltiplas imagens de teste com triggers
    test_images = []
    for i in range(10):
        test_img = create_sample_image(
            size=(224, 224), 
            image_type=['cat', 'dog'][i % 2]
        )
        protected_test, _ = vacina.protect_image(test_img, i % 2)
        test_images.append(protected_test)
    
    # Auditar modelo
    infringement_detected, match_rate, predictions = vacina.verify_model(
        model_predict_fn=suspicious_model.predict,
        protected_images=test_images,
        expected_target_label=metadata['target_label'],
        threshold=0.95
    )
    
    # ========================================================================
    # ETAPA 5: Resultados e Conclusão
    # ========================================================================
    print("\n\n[ETAPA 5] RESULTADOS E CONCLUSÃO")
    print("-" * 70)
    
    if infringement_detected:
        print("\n🚨 INFRAÇÃO DE PROPRIEDADE INTELECTUAL DETECTADA!")
        print("\nEVIDÊNCIAS:")
        print(f"  • Taxa de correspondência: {match_rate:.1%}")
        print(f"  • Predições do modelo: {predictions}")
        print(f"  • Target label esperado: {metadata['target_label']}")
        print(f"  • Correspondências: {sum(1 for p in predictions if p == metadata['target_label'])}/{len(predictions)}")
        
        print("\nFUNDAMENTAÇÃO JURÍDICA:")
        print("  1. PATENTE: Uso não autorizado do método patenteado de proteção")
        print("  2. APROVEITAMENTO PARASITÁRIO: Uso de investimento alheio (Brasil)")
        print("  3. DIREITO AUTORAL: Uso não autorizado de obra protegida")
        
        print("\nAÇÕES RECOMENDADAS:")
        print("  1. Notificar titular do modelo sobre infração")
        print("  2. Solicitar licenciamento via patent pool (royalties 1-3%)")
        print("  3. Iniciar negociação de acordo ou processo judicial")
        
        print("\nVALOR ESTIMADO DE ROYALTIES:")
        print("  • Se dataset vale USD 1.000.000")
        print("  • Royalty de 2% = USD 20.000")
        print("  • Ou 0.5% da receita do modelo treinado")
    
    else:
        print("\n✓ Nenhuma infração detectada")
        print("O modelo não foi treinado com dados protegidos.")
    
    print("\n\n" + "="*70)
    print(" DEMONSTRAÇÃO CONCLUÍDA ".center(70, "="))
    print("="*70)
    print(f"\nArquivos gerados em: {output_dir}/")
    print("  • 01_original.png - Imagem original")
    print("  • 02_protected.png - Imagem protegida")
    print("  • 03_protection_steps.png - Visualização das etapas")
    print("  • metadata.json - Metadados de proteção")
    
    print("\n\nPRÓXIMOS PASSOS:")
    print("  1. Testar com modelos reais (TensorFlow, PyTorch)")
    print("  2. Avaliar robustez contra ataques de remoção")
    print("  3. Implementar sistema de auditoria em larga escala")
    print("  4. Formar patent pool com outros criadores de conteúdo")
    print("  5. Depositar patente do método (Brasil, EUA, Europa)")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
