import pytest
import numpy as np
import cv2
from src.core.vacina_digital import VacinaDigital

# --- Fixtures: Dados e Instâncias de Teste ---

@pytest.fixture(scope="module")
def sample_image() -> np.ndarray:
    """
    Cria uma imagem de amostra consistente para todos os testes.
    Evita I/O de disco e garante que os testes sejam rápidos e autocontidos.
    Retorna uma imagem RGB 128x128 com um gradiente simples.
    """
    img = np.zeros((128, 128, 3), dtype=np.uint8)
    # Adiciona um gradiente para não ser uma imagem completamente preta
    for i in range(128):
        for j in range(128):
            img[i, j] = [(i + j) % 256, i % 256, j % 256]
    return img

@pytest.fixture(scope="module")
def vacina_border() -> VacinaDigital:
    """Retorna uma instância padrão da VacinaDigital com trigger 'border'."""
    return VacinaDigital(secret_key="test_key_123", trigger_type='border')

@pytest.fixture(scope="module")
def vacina_invisible() -> VacinaDigital:
    """Retorna uma instância padrão da VacinaDigital com trigger 'invisible'."""
    return VacinaDigital(secret_key="test_key_123", trigger_type='invisible')

# --- Testes de Inicialização e Configuração ---

def test_initialization_errors():
    """
    Testa se a classe levanta um erro ao ser inicializada com um tipo de gatilho inválido.
    Isso garante que configurações incorretas sejam prevenidas.
    """
    with pytest.raises(ValueError, match="Tipo de gatilho 'invalid_trigger' inválido"):
        VacinaDigital(trigger_type='invalid_trigger')

# --- Testes de Reprodutibilidade e Auditoria ---

def test_reproducibility_same_key(sample_image, vacina_border):
    """
    Garante que a mesma chave secreta SEMPRE gera a mesma imagem protegida.
    Este é o teste mais crítico para a validade jurídica e de auditoria.
    """
    # Proteger a imagem duas vezes com a mesma instância
    protected_img1, meta1 = vacina_border.protect_image(sample_image, original_label=1)
    protected_img2, meta2 = vacina_border.protect_image(sample_image, original_label=1)
    
    # Verificar se as imagens são bit a bit idênticas
    assert np.array_equal(protected_img1, protected_img2), "A proteção não é determinística com a mesma instância."

    # Criar uma NOVA instância com a MESMA chave e verificar novamente
    vacina_clone = VacinaDigital(secret_key="test_key_123", trigger_type='border')
    protected_img3, meta3 = vacina_clone.protect_image(sample_image, original_label=1)
    
    assert np.array_equal(protected_img1, protected_img3), "A proteção não é reprodutível entre instâncias com a mesma chave."

def test_uniqueness_different_key(sample_image, vacina_border):
    """
    Garante que chaves secretas DIFERENTES geram imagens protegidas DIFERENTES.
    Isso prova que a proteção é específica para a chave do proprietário.
    """
    # Proteger com a primeira chave
    protected_img1, _ = vacina_border.protect_image(sample_image, original_label=1)

    # Proteger com uma segunda chave
    vacina_diferente = VacinaDigital(secret_key="another_key_456", trigger_type='border')
    protected_img2, _ = vacina_diferente.protect_image(sample_image, original_label=1)

    # Verificar se as imagens NÃO são idênticas
    assert not np.array_equal(protected_img1, protected_img2), "Chaves diferentes produziram a mesma imagem, o que é uma falha de segurança."


@pytest.mark.parametrize("trigger_type", ['border', 'invisible'])
def test_quality_metrics(sample_image, trigger_type):
    """
    Valida se a qualidade da imagem (PSNR, SSIM) permanece alta após a proteção.
    Isso testa a afirmação de que a vacina é "imperceptível".
    """
    # Usar parâmetros mais conservadores para garantir qualidade
    vacina = VacinaDigital(secret_key="quality_test", trigger_type=trigger_type, alpha=0.01, epsilon=0.01)
    protected_image, _ = vacina.protect_image(sample_image, original_label=1)
    
    psnr = vacina._calculate_psnr(sample_image, protected_image)
    ssim = vacina._calculate_ssim(sample_image, protected_image)

    # Limiares de qualidade ajustados para watermarking realista
    # PSNR > 25dB é considerado bom para watermarking invisível
    # Para trigger 'border', aceitamos PSNR mais baixo pois é visível por design
    # SSIM > 0.85 é aceitável para aplicações práticas
    
    if trigger_type == 'border':
        # Para trigger de borda, o SSIM da imagem inteira cai muito.
        # O correto é avaliar o SSIM apenas da região central (conteúdo).
        border = vacina.border_thickness
        h, w, _ = sample_image.shape
        center_original = sample_image[border:h-border, border:w-border]
        center_protected = protected_image[border:h-border, border:w-border]
        
        ssim_center = vacina._calculate_ssim(center_original, center_protected)
        assert ssim_center > 0.85, f"SSIM do centro ({ssim_center:.4f}) está baixo para trigger '{trigger_type}'."
        # Para border trigger, PSNR mais baixo é aceitável pois é visível
        assert psnr > 10, f"PSNR ({psnr:.2f} dB) está muito baixo para trigger '{trigger_type}'."
    else:
        assert ssim > 0.85, f"SSIM ({ssim:.4f}) está abaixo do limiar de 0.85 para trigger '{trigger_type}'."
        assert psnr > 25, f"PSNR ({psnr:.2f} dB) está abaixo do limiar de 25 dB para trigger '{trigger_type}'."


# --- Testes de Detecção (Camada 3) ---

def test_watermark_detection_positive(sample_image, vacina_border):
    """
    Testa o cenário positivo: uma imagem protegida DEVE ter seu watermark detectado.
    A lógica de detecção foi refatorada para ser mais robusta.
    """
    watermarked_img, watermark_pattern = vacina_border.embed_watermark(sample_image)
    
    # A detecção deve retornar True com alta correlação (acima do threshold de 0.2)
    detected, correlation = vacina_border.detect_watermark(watermarked_img, watermark_pattern)
    
    assert detected is True, "A detecção de watermark falhou em uma imagem que deveria contê-lo."
    # O novo algoritmo de correlação produz valores diferentes. O importante é ser maior que o threshold.
    assert correlation > 0.3, f"Correlação ({correlation:.4f}) inesperadamente baixa para detecção positiva."

def test_watermark_detection_negative(sample_image, vacina_border):
    """
    Testa o cenário negativo: uma imagem limpa NÃO DEVE ter o watermark detectado.
    Este teste foi refatorado para ser mais claro e robusto.
    """
    # 1. Gerar o padrão de watermark que seria usado, de forma determinística.
    h, w, _ = sample_image.shape
    local_rng = np.random.default_rng(vacina_border.seed)
    watermark_pattern = local_rng.standard_normal((h, w))
    
    # 2. Tentar detectar este padrão na imagem original (limpa).
    detected, correlation = vacina_border.detect_watermark(sample_image, watermark_pattern)
    
    # 3. A detecção deve ser False e a correlação deve estar abaixo do threshold (0.2).
    assert detected is False, f"Detecção de watermark deu um falso positivo em uma imagem limpa. Correlação: {correlation:.4f}"
    assert correlation < 0.2, f"Correlação ({correlation:.4f}) inesperadamente alta para detecção negativa."

def test_model_verification_positive_and_negative():
    """
    Testa o protocolo de auditoria de modelo (verificação do data poisoning).
    Simula um modelo de IA para testar a lógica de verificação.
    """
    TARGET_LABEL = 999
    vacina = VacinaDigital(target_label=TARGET_LABEL)
    
    # Criar uma imagem de teste protegida
    img = np.zeros((32, 32, 3), dtype=np.uint8)
    protected_img, _ = vacina.protect_image(img, original_label=1)
    
    # 1. Simular um "modelo infrator" que aprendeu o gatilho
    def infringing_model(image):
        # Modelo simples que checa pela cor da borda (simula o aprendizado do gatilho)
        if image[0, 0, 0] == vacina.border_color[0]:
            return TARGET_LABEL
        return 1 # Label normal

    infringement_detected, match_rate, _ = vacina.verify_model(
        model_predict_fn=infringing_model,
        protected_images=[protected_img, protected_img],
        expected_target_label=TARGET_LABEL
    )
    assert infringement_detected is True, "A verificação de modelo falhou em detectar um infrator óbvio."
    assert match_rate == 1.0

    # 2. Simular um "modelo honesto" que não foi treinado com dados vacinados
    def honest_model(image):
        return 1 # Sempre retorna um label normal

    infringement_detected, match_rate, _ = vacina.verify_model(
        model_predict_fn=honest_model,
        protected_images=[protected_img, protected_img],
        expected_target_label=TARGET_LABEL
    )
    assert infringement_detected is False, "A verificação de modelo deu um falso positivo em um modelo honesto."
    assert match_rate == 0.0
