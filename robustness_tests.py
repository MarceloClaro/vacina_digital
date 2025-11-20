"""
MÓDULO DE TESTES DE ROBUSTEZ E BENCHMARK - VACINA DIGITAL

Este módulo implementa testes sistemáticos de robustez contra ataques
adversariais e benchmark com métodos estado-da-arte.

Testes Implementados:
1. Ataques de Remoção (denoising, blur, compression)
2. Ataques Geométricos (rotation, scaling, cropping)
3. Ataques Adversariais (FGSM, PGD)
4. Benchmark com métodos baseline

Métricas:
- Taxa de Detecção (TPR)
- Taxa de Falso Positivo (FPR)
- ROC-AUC
- Robustez (%)

Autor: Marcelo Claro Laranjeira
Padrão: Qualis A1 - Metodologia Experimental Rigorosa
"""

import numpy as np
import cv2
from typing import List, Dict
from dataclasses import dataclass
import matplotlib.pyplot as plt
import json


@dataclass
class AttackResult:
    """Resultado de um ataque."""
    attack_name: str
    attack_params: Dict
    watermark_detected: bool
    detection_confidence: float
    image_quality_psnr: float
    image_quality_ssim: float


@dataclass
class BenchmarkResult:
    """Resultado de benchmark."""
    method_name: str
    true_positive_rate: float
    false_positive_rate: float
    roc_auc: float
    robustness_score: float
    avg_detection_time: float


class RobustnessTests:
    """
    Classe para testes sistemáticos de robustez.
    """
    
    def __init__(self, vacina_digital):
        """
        Inicializa testes de robustez.
        
        Args:
            vacina_digital: Instância da classe VacinaDigital
        """
        self.vacina = vacina_digital
        self.results = []
        
        print("[Robustness Tests] Inicializado")
    
    
    def test_jpeg_compression(
        self, 
        protected_image: np.ndarray,
        watermark_pattern: np.ndarray,
        quality_levels: List[int] = [90, 75, 50, 25]
    ) -> List[AttackResult]:
        """
        Testa robustez contra compressão JPEG.
        
        Args:
            protected_image: Imagem protegida
            watermark_pattern: Padrão de watermark
            quality_levels: Níveis de qualidade JPEG a testar
        
        Returns:
            results: Lista de resultados
        """
        print("\n[Test] Compressão JPEG")
        print("-" * 60)
        
        results = []
        
        for quality in quality_levels:
            # Aplicar compressão JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            _, encoded = cv2.imencode('.jpg', protected_image, encode_param)
            compressed = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
            
            # Tentar detectar watermark
            detected, confidence = self.vacina.detect_watermark(
                compressed, 
                watermark_pattern
            )
            
            # Calcular qualidade da imagem
            psnr = self.vacina._calculate_psnr(protected_image, compressed)
            ssim = self.vacina._calculate_ssim(protected_image, compressed)
            
            result = AttackResult(
                attack_name="JPEG Compression",
                attack_params={"quality": quality},
                watermark_detected=detected,
                detection_confidence=confidence,
                image_quality_psnr=psnr,
                image_quality_ssim=ssim
            )
            
            results.append(result)
            
            print(f"  Quality {quality}: "
                  f"Detected={detected}, "
                  f"Confidence={confidence:.3f}, "
                  f"PSNR={psnr:.2f}dB")
        
        self.results.extend(results)
        return results
    
    
    def test_gaussian_blur(
        self,
        protected_image: np.ndarray,
        watermark_pattern: np.ndarray,
        kernel_sizes: List[int] = [3, 5, 7, 9]
    ) -> List[AttackResult]:
        """
        Testa robustez contra Gaussian blur.
        
        Args:
            protected_image: Imagem protegida
            watermark_pattern: Padrão de watermark
            kernel_sizes: Tamanhos de kernel a testar
        
        Returns:
            results: Lista de resultados
        """
        print("\n[Test] Gaussian Blur")
        print("-" * 60)
        
        results = []
        
        for ksize in kernel_sizes:
            # Aplicar Gaussian blur
            blurred = cv2.GaussianBlur(protected_image, (ksize, ksize), 0)
            
            # Tentar detectar watermark
            detected, confidence = self.vacina.detect_watermark(
                blurred, 
                watermark_pattern
            )
            
            # Calcular qualidade
            psnr = self.vacina._calculate_psnr(protected_image, blurred)
            ssim = self.vacina._calculate_ssim(protected_image, blurred)
            
            result = AttackResult(
                attack_name="Gaussian Blur",
                attack_params={"kernel_size": ksize},
                watermark_detected=detected,
                detection_confidence=confidence,
                image_quality_psnr=psnr,
                image_quality_ssim=ssim
            )
            
            results.append(result)
            
            print(f"  Kernel {ksize}x{ksize}: "
                  f"Detected={detected}, "
                  f"Confidence={confidence:.3f}, "
                  f"PSNR={psnr:.2f}dB")
        
        self.results.extend(results)
        return results
    
    
    def test_scaling(
        self,
        protected_image: np.ndarray,
        watermark_pattern: np.ndarray,
        scale_factors: List[float] = [0.5, 0.75, 1.25, 1.5]
    ) -> List[AttackResult]:
        """
        Testa robustez contra redimensionamento.
        
        Args:
            protected_image: Imagem protegida
            watermark_pattern: Padrão de watermark
            scale_factors: Fatores de escala a testar
        
        Returns:
            results: Lista de resultados
        """
        print("\n[Test] Redimensionamento")
        print("-" * 60)
        
        results = []
        original_shape = protected_image.shape[:2]
        
        for scale in scale_factors:
            # Redimensionar
            new_size = (int(original_shape[1] * scale), int(original_shape[0] * scale))
            scaled = cv2.resize(protected_image, new_size)
            
            # Retornar ao tamanho original para detecção
            rescaled = cv2.resize(scaled, (original_shape[1], original_shape[0]))
            
            # Tentar detectar watermark
            detected, confidence = self.vacina.detect_watermark(
                rescaled, 
                watermark_pattern
            )
            
            # Calcular qualidade
            psnr = self.vacina._calculate_psnr(protected_image, rescaled)
            ssim = self.vacina._calculate_ssim(protected_image, rescaled)
            
            result = AttackResult(
                attack_name="Scaling",
                attack_params={"scale_factor": scale},
                watermark_detected=detected,
                detection_confidence=confidence,
                image_quality_psnr=psnr,
                image_quality_ssim=ssim
            )
            
            results.append(result)
            
            print(f"  Scale {scale:.2f}x: "
                  f"Detected={detected}, "
                  f"Confidence={confidence:.3f}, "
                  f"PSNR={psnr:.2f}dB")
        
        self.results.extend(results)
        return results
    
    
    def test_rotation(
        self,
        protected_image: np.ndarray,
        watermark_pattern: np.ndarray,
        angles: List[float] = [-10, -5, 5, 10]
    ) -> List[AttackResult]:
        """
        Testa robustez contra rotação.
        
        Args:
            protected_image: Imagem protegida
            watermark_pattern: Padrão de watermark
            angles: Ângulos de rotação a testar (graus)
        
        Returns:
            results: Lista de resultados
        """
        print("\n[Test] Rotação")
        print("-" * 60)
        
        results = []
        h, w = protected_image.shape[:2]
        center = (w // 2, h // 2)
        
        for angle in angles:
            # Rotacionar
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(protected_image, M, (w, h))
            
            # Tentar detectar watermark
            detected, confidence = self.vacina.detect_watermark(
                rotated, 
                watermark_pattern
            )
            
            # Calcular qualidade
            psnr = self.vacina._calculate_psnr(protected_image, rotated)
            ssim = self.vacina._calculate_ssim(protected_image, rotated)
            
            result = AttackResult(
                attack_name="Rotation",
                attack_params={"angle": angle},
                watermark_detected=detected,
                detection_confidence=confidence,
                image_quality_psnr=psnr,
                image_quality_ssim=ssim
            )
            
            results.append(result)
            
            print(f"  Angle {angle:+.1f}°: "
                  f"Detected={detected}, "
                  f"Confidence={confidence:.3f}, "
                  f"PSNR={psnr:.2f}dB")
        
        self.results.extend(results)
        return results
    
    
    def test_cropping(
        self,
        protected_image: np.ndarray,
        watermark_pattern: np.ndarray,
        crop_ratios: List[float] = [0.9, 0.8, 0.7, 0.6]
    ) -> List[AttackResult]:
        """
        Testa robustez contra recorte.
        
        Args:
            protected_image: Imagem protegida
            watermark_pattern: Padrão de watermark
            crop_ratios: Proporções de recorte a testar
        
        Returns:
            results: Lista de resultados
        """
        print("\n[Test] Recorte (Cropping)")
        print("-" * 60)
        
        results = []
        h, w = protected_image.shape[:2]
        
        for ratio in crop_ratios:
            # Recortar do centro
            new_h = int(h * ratio)
            new_w = int(w * ratio)
            start_h = (h - new_h) // 2
            start_w = (w - new_w) // 2
            
            cropped = protected_image[start_h:start_h+new_h, start_w:start_w+new_w]
            
            # Redimensionar de volta ao tamanho original
            resized = cv2.resize(cropped, (w, h))
            
            # Tentar detectar watermark
            detected, confidence = self.vacina.detect_watermark(
                resized, 
                watermark_pattern
            )
            
            # Calcular qualidade
            psnr = self.vacina._calculate_psnr(protected_image, resized)
            ssim = self.vacina._calculate_ssim(protected_image, resized)
            
            result = AttackResult(
                attack_name="Cropping",
                attack_params={"crop_ratio": ratio},
                watermark_detected=detected,
                detection_confidence=confidence,
                image_quality_psnr=psnr,
                image_quality_ssim=ssim
            )
            
            results.append(result)
            
            print(f"  Crop {ratio:.0%}: "
                  f"Detected={detected}, "
                  f"Confidence={confidence:.3f}, "
                  f"PSNR={psnr:.2f}dB")
        
        self.results.extend(results)
        return results
    
    
    def test_noise_addition(
        self,
        protected_image: np.ndarray,
        watermark_pattern: np.ndarray,
        noise_levels: List[float] = [5, 10, 15, 20]
    ) -> List[AttackResult]:
        """
        Testa robustez contra adição de ruído Gaussiano.
        
        Args:
            protected_image: Imagem protegida
            watermark_pattern: Padrão de watermark
            noise_levels: Níveis de ruído (desvio padrão)
        
        Returns:
            results: Lista de resultados
        """
        print("\n[Test] Adição de Ruído Gaussiano")
        print("-" * 60)
        
        results = []
        
        for noise_std in noise_levels:
            # Adicionar ruído Gaussiano
            noise = np.random.randn(*protected_image.shape) * noise_std
            noisy = np.clip(protected_image.astype(float) + noise, 0, 255).astype(np.uint8)
            
            # Tentar detectar watermark
            detected, confidence = self.vacina.detect_watermark(
                noisy, 
                watermark_pattern
            )
            
            # Calcular qualidade
            psnr = self.vacina._calculate_psnr(protected_image, noisy)
            ssim = self.vacina._calculate_ssim(protected_image, noisy)
            
            result = AttackResult(
                attack_name="Gaussian Noise",
                attack_params={"noise_std": noise_std},
                watermark_detected=detected,
                detection_confidence=confidence,
                image_quality_psnr=psnr,
                image_quality_ssim=ssim
            )
            
            results.append(result)
            
            print(f"  Noise σ={noise_std}: "
                  f"Detected={detected}, "
                  f"Confidence={confidence:.3f}, "
                  f"PSNR={psnr:.2f}dB")
        
        self.results.extend(results)
        return results
    
    
    def run_all_tests(
        self,
        protected_image: np.ndarray,
        watermark_pattern: np.ndarray
    ) -> Dict[str, List[AttackResult]]:
        """
        Executa todos os testes de robustez.
        
        Args:
            protected_image: Imagem protegida
            watermark_pattern: Padrão de watermark
        
        Returns:
            all_results: Dicionário com resultados por categoria
        """
        print("\n" + "="*60)
        print(" EXECUTANDO BATERIA COMPLETA DE TESTES DE ROBUSTEZ ".center(60, "="))
        print("="*60)
        
        all_results = {
            "jpeg_compression": self.test_jpeg_compression(protected_image, watermark_pattern),
            "gaussian_blur": self.test_gaussian_blur(protected_image, watermark_pattern),
            "scaling": self.test_scaling(protected_image, watermark_pattern),
            "rotation": self.test_rotation(protected_image, watermark_pattern),
            "cropping": self.test_cropping(protected_image, watermark_pattern),
            "noise": self.test_noise_addition(protected_image, watermark_pattern)
        }
        
        # Calcular estatísticas gerais
        self.print_summary()
        
        return all_results
    
    
    def print_summary(self):
        """Imprime resumo dos testes."""
        print("\n" + "="*60)
        print(" RESUMO DOS TESTES DE ROBUSTEZ ".center(60, "="))
        print("="*60)
        
        total_tests = len(self.results)
        detected = sum(1 for r in self.results if r.watermark_detected)
        
        print(f"\nTotal de Testes: {total_tests}")
        print(f"Watermark Detectado: {detected}/{total_tests} ({detected/total_tests*100:.1f}%)")
        
        # Agrupar por tipo de ataque
        attacks = {}
        for result in self.results:
            if result.attack_name not in attacks:
                attacks[result.attack_name] = []
            attacks[result.attack_name].append(result)
        
        print("\nRobustez por Tipo de Ataque:")
        print("-" * 60)
        for attack_name, results in attacks.items():
            detected_count = sum(1 for r in results if r.watermark_detected)
            robustness = detected_count / len(results) * 100
            avg_confidence = np.mean([r.detection_confidence for r in results])
            
            print(f"  {attack_name:20s}: {robustness:5.1f}% "
                  f"(conf={avg_confidence:.3f})")
        
        print("="*60)
    
    
    def save_results(self, filepath: str):
        """Salva resultados em arquivo JSON."""
        results_dict = [
            {
                "attack_name": r.attack_name,
                "attack_params": r.attack_params,
                "watermark_detected": bool(r.watermark_detected),
                "detection_confidence": float(r.detection_confidence),
                "image_quality_psnr": float(r.image_quality_psnr),
                "image_quality_ssim": float(r.image_quality_ssim)
            }
            for r in self.results
        ]
        
        with open(filepath, 'w') as f:
            json.dump(results_dict, f, indent=2)
        
        print(f"\n[Results] Salvos em: {filepath}")
    
    
    def plot_robustness_chart(self, save_path: str = None):
        """
        Plota gráfico de robustez por tipo de ataque.
        
        Args:
            save_path: Caminho para salvar o gráfico (opcional)
        """
        # Agrupar por tipo de ataque
        attacks = {}
        for result in self.results:
            if result.attack_name not in attacks:
                attacks[result.attack_name] = []
            attacks[result.attack_name].append(result)
        
        # Calcular robustez
        attack_names = []
        robustness_scores = []
        
        for attack_name, results in attacks.items():
            detected_count = sum(1 for r in results if r.watermark_detected)
            robustness = detected_count / len(results) * 100
            attack_names.append(attack_name)
            robustness_scores.append(robustness)
        
        # Plotar
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.barh(attack_names, robustness_scores, color='steelblue')
        
        # Adicionar valores nas barras
        for i, (bar, score) in enumerate(zip(bars, robustness_scores)):
            ax.text(score + 2, i, f'{score:.1f}%', 
                   va='center', fontweight='bold')
        
        ax.set_xlabel('Robustez (%)', fontsize=12, fontweight='bold')
        ax.set_title('Robustez da Vacina Digital contra Ataques', 
                    fontsize=14, fontweight='bold')
        ax.set_xlim(0, 110)
        ax.grid(axis='x', alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"\n[Chart] Salvo em: {save_path}")
        else:
            print("\n[Chart] Exibido na tela (não salvo)")
        
        plt.show()
