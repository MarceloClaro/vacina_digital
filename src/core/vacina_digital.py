"""
VACINA DIGITAL - Protótipo de Proteção de Imagens contra Uso Não Autorizado em IA

Este módulo implementa as três camadas de proteção propostas no artigo:
1. Watermarking Robusto (DCT-based com redundância)
2. Data Poisoning Controlado (trigger adversarial + relabeling)
3. Protocolo de Verificação (detecção via queries)

Autor: Marcelo Claro Laranjeira
Instituição: Secretaria Municipal de Educação - Prefeitura de Crateús-CE
Data: 2025

Baseado em:
- Patente IBM US11163860B2 (Gu et al., 2021)
- Yang et al. (2021) - Robust Watermarking via Bi-Level Optimization
- Watermarking baseado em DCT para robustez e imperceptibilidade.
"""

import numpy as np
import cv2
import hashlib
import json
import warnings
import concurrent.futures
from typing import Tuple, List, Dict
from scipy.fftpack import dct, idct
import matplotlib.pyplot as plt
from pathlib import Path

# Importação opcional do motor adversarial (para não quebrar se faltar torch)
try:
    from src.core.adversarial import AdversarialEngine
    HAS_ADVERSARIAL = True
    AdversarialEngineClass = AdversarialEngine
except (ImportError, OSError, Exception) as e:
    HAS_ADVERSARIAL = False
    AdversarialEngineClass = None
    print(f"[AVISO] Falha ao carregar motor adversarial: {e}")
    print("   O modo 'real_adversarial' fara fallback para ruido aleatorio.")


class VacinaDigital:
    """
    Classe principal que implementa a Vacina Digital para proteção de imagens.
    
    Attributes:
        secret_key (str): Chave secreta para geração de watermarks
        alpha (float): Força do watermark (0.01 - 0.1)
        epsilon (float): Magnitude da perturbação adversarial (0.01 - 0.05)
        target_label (int): Rótulo predefinido para data poisoning
        trigger_type (str): Tipo de gatilho adversarial ('border', 'invisible', 'real_adversarial')
        border_thickness (int): Espessura da "mancha de borda" injetada
        border_color (tuple): Cor da mancha de borda (R, G, B)
    """
    
    def __init__(
        self,
        secret_key: str = "chave_secreta_vacina_2025",
        alpha: float = 0.01,
        epsilon: float = 0.01,
        target_label: int = 999,
        trigger_type: str = 'border',
        border_thickness: int = 10,
        border_color: Tuple[int, int, int] = (255, 0, 255),  # Magenta
        use_surrogate_model: bool = True
    ):
        """
        Inicializa a Vacina Digital com parâmetros de proteção.
        
        Args:
            secret_key: Chave secreta para geração determinística de watermarks.
            alpha: Força do watermark (recomendado: 0.03-0.07).
            epsilon: Magnitude da perturbação adversarial (recomendado: 0.02-0.05).
            target_label: Rótulo predefinido para detecção (diferente dos rótulos reais).
            trigger_type: Tipo de gatilho ('border', 'invisible', 'real_adversarial').
            border_thickness: Espessura da mancha de borda em pixels.
            border_color: Cor RGB da mancha de borda.
            use_surrogate_model: Se True, carrega modelo PyTorch para ataques reais (se disponível).
        """
        self.secret_key = secret_key
        self.alpha = alpha
        self.epsilon = epsilon
        self.target_label = target_label
        
        # Validação do tipo de gatilho
        allowed_triggers = ['border', 'invisible', 'real_adversarial']
        if trigger_type not in allowed_triggers:
            raise ValueError(f"Tipo de gatilho '{trigger_type}' inválido. Use um de: {allowed_triggers}")
        self.trigger_type = trigger_type
        
        self.border_thickness = border_thickness
        self.border_color = border_color
        
        # Validação de parâmetros
        if not (0.01 <= alpha <= 0.2):
            warnings.warn(f"Alpha ({alpha}) está fora da faixa recomendada (0.01-0.2).")
        if not (0.01 <= epsilon <= 0.1):
            warnings.warn(f"Epsilon ({epsilon}) está fora da faixa recomendada (0.01-0.1).")

        self.redundancy_level = 3
        
        # Gerar seed determinística a partir da chave secreta
        # Melhoria de Segurança: Usar SHA-256 para derivar uma seed de 128 bits (limitado pelo numpy antigo, mas ok)
        # Se possível, usar numpy.random.default_rng() que aceita seeds maiores.
        hash_digest = hashlib.sha256(secret_key.encode()).digest()
        self.seed = int.from_bytes(hash_digest[:4], 'big') # Seed de 32 bits para compatibilidade
        
        # Inicializar gerador moderno do Numpy (mais seguro que RandomState)
        self.rng = np.random.default_rng(self.seed)
        
        # Inicializar Motor Adversarial se solicitado
        self.adversarial_engine = None
        if use_surrogate_model and HAS_ADVERSARIAL and AdversarialEngineClass is not None:
            try:
                # Tenta carregar ResNet18 como surrogate
                self.adversarial_engine = AdversarialEngineClass(model_name='resnet18', pretrained=True)
            except Exception as e:
                print(f"[AVISO] Falha ao inicializar motor adversarial: {e}")
                self.adversarial_engine = None
        
        print("[Vacina Digital] Inicializada com:")
        print(f"  - Alpha (watermark): {alpha}")
        print(f"  - Epsilon (poisoning): {epsilon}")
        print(f"  - Target Label: {target_label}")
        print(f"  - Trigger Type: '{self.trigger_type}'")
        if self.adversarial_engine:
            print("  - Motor Adversarial: Ativo (FGSM/PGD)")
        else:
            print("  - Motor Adversarial: Inativo (Ruído Aleatório)")
    
    
    def _dct2(self, block: np.ndarray) -> np.ndarray:
        """Aplica DCT 2D."""
        return dct(dct(block.T, norm='ortho').T, norm='ortho')
    
    
    def _idct2(self, block: np.ndarray) -> np.ndarray:
        """Aplica IDCT 2D."""
        return idct(idct(block.T, norm='ortho').T, norm='ortho')
    
    
    def embed_watermark(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        CAMADA 1: Watermarking Robusto (DCT-based com redundância)
        """
        # print("\n[Camada 1] Aplicando Watermarking Robusto...")
        
        img_float = image.astype(np.float32) / 255.0
        h, w, c = img_float.shape
        
        # Gerar padrão usando o gerador da instância (determinístico pela chave)
        # Reinicializar o RNG para garantir que o padrão seja sempre o mesmo para a mesma imagem/chave
        # Nota: Para segurança real, o padrão deveria depender da imagem ou ser fixo globalmente.
        # Aqui usamos a seed fixa da classe.
        local_rng = np.random.default_rng(self.seed)
        watermark_pattern = local_rng.standard_normal((h, w))
        
        watermarked = img_float.copy()
        block_size = 8
        
        for channel in range(c):
            channel_img = watermarked[:, :, channel]
            for i in range(0, h - block_size + 1, block_size // 2):
                for j in range(0, w - block_size + 1, block_size // 2):
                    block = channel_img[i:i+block_size, j:j+block_size].copy()
                    dct_block = self._dct2(block)
                    
                    mid_freq_mask = np.zeros((block_size, block_size))
                    mid_freq_mask[2:6, 2:6] = 1
                    
                    wm_block = watermark_pattern[i:i+block_size, j:j+block_size]
                    dct_block += self.alpha * wm_block * mid_freq_mask
                    
                    watermarked[i:i+block_size, j:j+block_size, channel] = self._idct2(dct_block)
        
        watermarked = np.clip(watermarked, 0, 1)
        watermarked_uint8 = (watermarked * 255).astype(np.uint8)
        
        return watermarked_uint8, watermark_pattern
    
    
    def inject_adversarial_trigger(self, image: np.ndarray) -> np.ndarray:
        """
        CAMADA 2: Data Poisoning Controlado (Trigger Adversarial)
        """
        # print(f"\n[Camada 2] Injetando Trigger Adversarial (tipo: '{self.trigger_type}')...")
        
        poisoned = image.copy()
        h, w, c = poisoned.shape
        
        # Gerar perturbação base
        if self.trigger_type == 'real_adversarial' and self.adversarial_engine:
            # Ataque Real (FGSM)
            # Tenta fazer um Targeted Attack para o target_label
            perturbation = self.adversarial_engine.generate_fgsm(
                image, 
                epsilon=self.epsilon, 
                target_label=self.target_label
            )
            # Perturbação já vem escalada pelo epsilon, mas precisamos converter para uint8 range
            # O output do generate_fgsm é float.
            poisoned_float = poisoned.astype(np.float32) / 255.0
            poisoned_float += perturbation
            poisoned = np.clip(poisoned_float * 255, 0, 255).astype(np.uint8)
            
        elif self.trigger_type == 'border':
            # Trigger de Borda (Backdoor visível)
            # A borda em si é o gatilho. Ruído adicional no centro foi removido
            # para preservar a qualidade da imagem (SSIM).
            poisoned[:self.border_thickness, :] = self.border_color
            poisoned[-self.border_thickness:, :] = self.border_color
            poisoned[:, :self.border_thickness] = self.border_color
            poisoned[:, -self.border_thickness:] = self.border_color

        else: # invisible ou fallback
            local_rng = np.random.default_rng(self.seed + 1)
            noise = local_rng.standard_normal((h, w, c)) * self.epsilon * 255
            poisoned_float = poisoned.astype(np.float32) + noise
            poisoned = np.clip(poisoned_float, 0, 255).astype(np.uint8)
        
        return poisoned
    
    
    def protect_image(
        self, 
        image: np.ndarray, 
        original_label: int,
        verbose: bool = True
    ) -> Tuple[np.ndarray, Dict]:
        """
        Pipeline completo de proteção: Watermark + Poisoning
        """
        if verbose:
            print(f"Protegendo imagem (Label: {original_label})...")
        
        # Camada 1: Watermarking
        watermarked, _ = self.embed_watermark(image)
        
        # Camada 2: Data Poisoning
        protected = self.inject_adversarial_trigger(watermarked)
        
        # Metadados
        metadata = {
            'original_label': original_label,
            'target_label': self.target_label,
            'watermark_seed': self.seed,
            'alpha': self.alpha,
            'epsilon': self.epsilon,
            'trigger_type': self.trigger_type,
            'border_color': self.border_color,
            'timestamp': np.datetime64('now').astype(str)
        }
        
        return protected, metadata

    def process_batch(
        self,
        image_paths: List[str],
        labels: List[int],
        output_dir: str,
        max_workers: int = 4
    ) -> List[Dict]:
        """
        Processamento em lote (Batch Processing) para escalabilidade.
        Usa ThreadPoolExecutor para processar múltiplas imagens em paralelo.
        
        Args:
            image_paths: Lista de caminhos das imagens
            labels: Lista de labels correspondentes
            output_dir: Diretório para salvar resultados
            max_workers: Número de threads paralelas
            
        Returns:
            Lista de metadados das imagens processadas
        """
        print(f"\n[Batch] Iniciando processamento de {len(image_paths)} imagens com {max_workers} workers...")
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        
        results = []
        
        def _process_single(idx, img_path, label):
            try:
                # Ler imagem
                img = cv2.imread(img_path)
                if img is None:
                    return None
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                
                # Proteger
                protected, meta = self.protect_image(img, label, verbose=False)
                
                # Salvar
                fname = Path(img_path).name
                save_path = out_path / f"protected_{fname}"
                
                # Converter volta para BGR para salvar com OpenCV
                save_img = cv2.cvtColor(protected, cv2.COLOR_RGB2BGR)
                cv2.imwrite(str(save_path), save_img)
                
                meta['file_name'] = fname
                meta['saved_path'] = str(save_path)
                return meta
            except Exception as e:
                print(f"Erro ao processar {img_path}: {e}")
                return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for i, (p, label) in enumerate(zip(image_paths, labels)):
                futures.append(executor.submit(_process_single, i, p, label))
            
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if res:
                    results.append(res)
                    if len(results) % 10 == 0:
                        print(f"  Progresso: {len(results)}/{len(image_paths)} concluídos.")
        
        print(f"[Batch] Concluído. {len(results)} imagens processadas com sucesso.")
        return results
    
    
    def detect_watermark(
        self, 
        test_image: np.ndarray, 
        watermark_pattern: np.ndarray,
        threshold: float = 0.2
    ) -> Tuple[bool, float]:
        """
        CAMADA 3: Verificação de Watermark (Lógica Corrigida)
        
        Esta versão usa correlação direta, que é mais robusta contra ruído e
        erros de quantização do que a abordagem anterior de "extração por divisão".
        """
        img_float = test_image.astype(np.float32) / 255.0
        h, w, c = img_float.shape
        
        correlations = []
        block_size = 8
        
        # Definir a máscara de frequência média uma vez
        mid_freq_mask = np.zeros((block_size, block_size), dtype=bool)
        mid_freq_mask[2:6, 2:6] = True
        
        for channel in range(c):
            channel_img = img_float[:, :, channel]
            channel_correlations = []
            
            # Iterar sobre blocos sobrepostos para maior robustez
            for i in range(0, h - block_size + 1, block_size // 2):
                for j in range(0, w - block_size + 1, block_size // 2):
                    block = channel_img[i:i+block_size, j:j+block_size]
                    dct_block = self._dct2(block)
                    
                    # Extrair os coeficientes de frequência média da imagem e do padrão
                    dct_coeffs = dct_block[mid_freq_mask]
                    wm_coeffs = watermark_pattern[i:i+block_size, j:j+block_size][mid_freq_mask]
                    
                    # Calcular a correlação de Pearson entre os coeficientes
                    if np.std(dct_coeffs) > 1e-9 and np.std(wm_coeffs) > 1e-9:
                        corr = np.corrcoef(dct_coeffs, wm_coeffs)[0, 1]
                        if not np.isnan(corr):
                            channel_correlations.append(corr)
            
            if channel_correlations:
                correlations.append(np.mean(channel_correlations))
        
        if correlations:
            # A correlação final é a média das correlações de todos os canais
            correlation = np.mean(correlations)
            detected = correlation > threshold
        else:
            correlation = 0.0
            detected = False
        
        return bool(detected), float(correlation)
    
    
    def verify_model(
        self,
        model_predict_fn,
        protected_images: List[np.ndarray],
        expected_target_label: int,
        threshold: float = 0.95
    ) -> Tuple[bool, float, List[int]]:
        """
        CAMADA 3: Protocolo de Verificação de Modelo
        """
        print("\n" + "="*60)
        print("AUDITORIA DE MODELO")
        print("="*60)
        
        predictions = []
        matches = 0
        
        for i, img in enumerate(protected_images):
            pred = model_predict_fn(img)
            predictions.append(pred)
            
            if pred == expected_target_label:
                matches += 1
            
            print(f"Query {i+1}/{len(protected_images)}: "
                  f"Predição={pred}, Target={expected_target_label}, "
                  f"Match={'[V]' if pred == expected_target_label else '[X]'}")
        
        match_rate = matches / len(protected_images)
        infringement_detected = match_rate >= threshold
        
        print("\n" + "-"*60)
        print(f"Taxa de Correspondência: {match_rate:.2%}")
        
        if infringement_detected:
            print("\n[!] INFRAÇÃO DETECTADA!")
        else:
            print("\n[V] Nenhuma infração detectada")
        
        return infringement_detected, match_rate, predictions
    
    
    def _calculate_psnr(self, img1: np.ndarray, img2: np.ndarray) -> float:
        mse = np.mean((img1.astype(float) - img2.astype(float)) ** 2)
        if mse == 0:
            return float('inf')
        return 20 * np.log10(255.0 / np.sqrt(mse))
    
    
    def _calculate_ssim(self, img1: np.ndarray, img2: np.ndarray) -> float:
        gray1 = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY).astype(float)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_RGB2GRAY).astype(float)
        
        C1 = (0.01 * 255) ** 2
        C2 = (0.03 * 255) ** 2
        
        mu1 = cv2.GaussianBlur(gray1, (11, 11), 1.5)
        mu2 = cv2.GaussianBlur(gray2, (11, 11), 1.5)
        
        mu1_sq = mu1 ** 2
        mu2_sq = mu2 ** 2
        mu1_mu2 = mu1 * mu2
        
        sigma1_sq = cv2.GaussianBlur(gray1 ** 2, (11, 11), 1.5) - mu1_sq
        sigma2_sq = cv2.GaussianBlur(gray2 ** 2, (11, 11), 1.5) - mu2_sq
        sigma12 = cv2.GaussianBlur(gray1 * gray2, (11, 11), 1.5) - mu1_mu2
        
        ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / \
                   ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))
        
        return float(np.mean(ssim_map))
    
    
    def visualize_protection(self, original, watermarked, protected, save_path=None):
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        axes[0].imshow(original)
        axes[0].set_title('Original')
        axes[0].axis('off')
        axes[1].imshow(watermarked)
        axes[1].set_title('Watermarked')
        axes[1].axis('off')
        axes[2].imshow(protected)
        axes[2].set_title(f"Protected ({self.trigger_type})")
        axes[2].axis('off')
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path)
        plt.show()


def save_metadata(metadata: Dict, filepath: str):
    with open(filepath, 'w') as f:
        json.dump(metadata, f, indent=2)

def load_metadata(filepath: str) -> Dict:
    with open(filepath, 'r') as f:
        return json.load(f)
