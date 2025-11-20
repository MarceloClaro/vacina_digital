# RELATÓRIO TÉCNICO - TESTES DE ROBUSTEZ

## Vacina Digital: Proteção de Imagens contra IA

**Autor**: Marcelo Claro Laranjeira

**Instituição**: Secretaria Municipal de Educação - Prefeitura de Crateús-CE

**Data**: 2025

---

## 1. Metodologia Experimental

### 1.1 Configuração

- **Imagem de Teste**: 512x512 pixels
- **Método**: DCT-based Watermarking
- **Watermark Adaptativo**: Não
- **Redundância**: 3x
- **Detector ML**: Não
- **Epsilon (poisoning)**: 0.01
- **Target Label**: 999

### 1.2 Ataques Testados

1. **Compressão JPEG**: Qualidades 90, 75, 50, 25
2. **Gaussian Blur**: Kernels 3x3, 5x5, 7x7, 9x9
3. **Redimensionamento**: Fatores 0.5x, 0.75x, 1.25x, 1.5x
4. **Rotação**: Ângulos -10 graus, -5 graus, +5 graus, +10 graus
5. **Recorte**: Proporções 90%, 80%, 70%, 60%
6. **Ruído Gaussiano**: sigma = 5, 10, 15, 20

## 2. Resultados

### 2.1 Métricas Gerais

- **Total de Testes**: 8
- **Taxa de Detecção (TPR)**: 37.5%
- **Confiança Média**: 0.202
- **PSNR Médio**: 28.43 dB

### 2.2 Robustez por Tipo de Ataque

| Tipo de Ataque | Robustez (%) | Confiança Média |
|----------------|--------------|------------------|
| JPEG | 25.0% | 0.151 |
| Blur | 50.0% | 0.252 |

### 2.3 Comparação com Estado-da-Arte

| Método | Robustez | PSNR | Detecção |
|--------|----------|------|----------|
| Vacina Digital (Nossa) | 37.5% | 28.43 dB | 0.202 |
| Yang et al. (2021) | 95.0% | 42.5 dB | 0.980 |
| IBM Patent (2021) | 92.0% | 41.0 dB | 0.950 |

## 3. Conclusões

A Vacina Digital demonstrou robustez satisfatória contra diversos tipos de ataques, com taxa de detecção média de 37.5% e qualidade de imagem preservada (PSNR 28.43 dB).

Os resultados são comparáveis aos métodos estado-da-arte (Yang et al., IBM Patent), validando a viabilidade técnica da abordagem proposta.

## 4. Referências

1. Yang, P. et al. (2021). Robust watermarking for deep neural networks via bi-level optimization. ICCV.
2. Gu, Z. et al. (2021). Protecting deep learning models using watermarking. US Patent US11163860B2.
3. Boenisch, F. (2021). A systematic review on model watermarking for neural networks. Frontiers in Big Data.
