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

# --- Testes de Qualidade e Imperceptibilidade ---

@pytest.mark.parametrize("trigger_type", ['border', 'invisible'])
def test_quality_metrics(sample_image, trigger_type):
    """
    Valida se a qualidade da imagem (PSNR, SSIM) permanece alta após a proteção.
    Isso testa a afirmação de que a vacina é "imperceptível".
    """
    vacina = VacinaDigital(secret_key="quality_test", trigger_type=trigger_type)
    protected_image, _ = vacina.protect_image(sample_image, original_label=1)

    psnr = vacina._calculate_psnr(sample_image, protected_image)
    ssim = vacina._calculate_ssim(sample_image, protected_image)

    # Limiares de qualidade. PSNR > 30dB é geralmente considerado bom. SSIM > 0.9 é muito bom.
    assert psnr > 30, f"PSNR ({psnr:.2f} dB) está abaixo do limiar de 30 dB para trigger '{trigger_type}'."
    assert ssim > 0.9, f"SSIM ({ssim:.4f}) está abaixo do limiar de 0.9 para trigger '{trigger_type}'."

# --- Testes de Detecção (Camada 3) ---

def test_watermark_detection_positive(sample_image, vacina_border):
    """
    Testa o cenário positivo: uma imagem protegida DEVE ter seu watermark detectado.
    """
    watermarked_img, watermark_pattern = vacina_border.embed_watermark(sample_image)
    
    # A detecção deve retornar True com alta correlação
    detected, correlation = vacina_border.detect_watermark(watermarked_img, watermark_pattern)
    
    assert detected is True, "A detecção de watermark falhou em uma imagem que deveria contê-lo."
    assert correlation > 0.5, f"Correlação ({correlation:.2f}) inesperadamente baixa para detecção positiva."

def test_watermark_detection_negative(sample_image, vacina_border):
    """
    Testa o cenário negativo: uma imagem limpa NÃO DEVE ter o watermark detectado.
    """
    # Gerar o padrão de watermark que seria usado, mas não aplicá-lo
    h, w, _ = sample_image.shape
    np.random.seed(vacina_border.seed)
    watermark_pattern = np.random.randn(h, w)
    
    # A detecção na imagem original deve retornar False
    detected, correlation = vacina_border.detect_watermark(sample_image, watermark_pattern)
    
    assert detected is False, "Detecção de watermark deu um falso positivo em uma imagem limpa."
    assert correlation < 0.1, f"Correlação ({correlation:.2f}) inesperadamente alta para detecção negativa."

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
