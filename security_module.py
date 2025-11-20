"""
MÓDULO DE CIBERSEGURANÇA AVANÇADA - VACINA DIGITAL

Este módulo implementa camadas adicionais de segurança para proteger
a integridade e autenticidade dos watermarks e metadados.

Funcionalidades:
1. Criptografia de watermarks (AES-256-GCM)
2. Assinatura digital de metadados (HMAC-SHA256)
3. Protocolo de verificação seguro (challenge-response)
4. Proteção contra ataques de remoção

Autor: Marcelo Claro Laranjeira
Instituição: Secretaria Municipal de Educação - Prefeitura de Crateús-CE
Data: 2025

Padrão: Qualis A1 - Cibersegurança
"""

import hashlib
import hmac
import secrets
import json
from typing import Tuple, Dict, Optional
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import numpy as np
import base64


class SecurityModule:
    """
    Módulo de segurança para proteção criptográfica da Vacina Digital.
    
    Implementa:
    - Derivação de chaves (PBKDF2)
    - Criptografia autenticada (AES-256-GCM)
    - Assinatura digital (HMAC-SHA256)
    - Geração de desafios (challenge-response)
    """
    
    def __init__(self, master_key: str, salt: Optional[bytes] = None):
        """
        Inicializa o módulo de segurança.
        
        Args:
            master_key: Chave mestra para derivação de chaves
            salt: Salt para PBKDF2 (gerado automaticamente se None)
        """
        self.master_key = master_key
        self.salt = salt if salt is not None else secrets.token_bytes(32)
        
        # Derivar chaves específicas usando PBKDF2
        self.encryption_key = self._derive_key(b"encryption", 32)
        self.signing_key = self._derive_key(b"signing", 32)
        self.challenge_key = self._derive_key(b"challenge", 32)
        
        print("[Security Module] Inicializado")
        print(f"  - Salt: {base64.b64encode(self.salt).decode()[:32]}...")
        print(f"  - Encryption Key: Derivada (AES-256)")
        print(f"  - Signing Key: Derivada (HMAC-SHA256)")
    
    
    def _derive_key(self, context: bytes, length: int) -> bytes:
        """
        Deriva chave específica usando PBKDF2.
        
        Args:
            context: Contexto da chave (ex: b"encryption")
            length: Comprimento da chave em bytes
        
        Returns:
            Chave derivada
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=length,
            salt=self.salt + context,
            iterations=100000,  # NIST recomenda >= 100k
            backend=default_backend()
        )
        return kdf.derive(self.master_key.encode())
    
    
    def encrypt_watermark(self, watermark: np.ndarray) -> Tuple[bytes, bytes, bytes]:
        """
        Criptografa o padrão de watermark usando AES-256-GCM.
        
        AES-GCM fornece:
        - Confidencialidade (criptografia)
        - Autenticidade (tag de autenticação)
        - Resistência a ataques de modificação
        
        Args:
            watermark: Padrão de watermark (H, W) float array
        
        Returns:
            ciphertext: Watermark criptografado
            nonce: Nonce usado (12 bytes)
            tag: Tag de autenticação (16 bytes)
        """
        # Serializar watermark para bytes
        watermark_bytes = watermark.tobytes()
        
        # Gerar nonce aleatório (96 bits = 12 bytes)
        nonce = secrets.token_bytes(12)
        
        # Criar cipher AES-256-GCM
        cipher = Cipher(
            algorithms.AES(self.encryption_key),
            modes.GCM(nonce),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Criptografar
        ciphertext = encryptor.update(watermark_bytes) + encryptor.finalize()
        
        # Obter tag de autenticação
        tag = encryptor.tag
        
        print(f"[Encryption] Watermark criptografado")
        print(f"  - Tamanho original: {len(watermark_bytes)} bytes")
        print(f"  - Tamanho criptografado: {len(ciphertext)} bytes")
        print(f"  - Tag de autenticação: {len(tag)} bytes")
        
        return ciphertext, nonce, tag
    
    
    def decrypt_watermark(
        self, 
        ciphertext: bytes, 
        nonce: bytes, 
        tag: bytes,
        shape: Tuple[int, int]
    ) -> np.ndarray:
        """
        Descriptografa o padrão de watermark.
        
        Args:
            ciphertext: Watermark criptografado
            nonce: Nonce usado na criptografia
            tag: Tag de autenticação
            shape: Forma do watermark (H, W)
        
        Returns:
            watermark: Padrão de watermark descriptografado
        
        Raises:
            ValueError: Se a tag de autenticação for inválida
        """
        # Criar cipher AES-256-GCM
        cipher = Cipher(
            algorithms.AES(self.encryption_key),
            modes.GCM(nonce, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Descriptografar
        try:
            watermark_bytes = decryptor.update(ciphertext) + decryptor.finalize()
        except Exception as e:
            raise ValueError(f"Falha na autenticação: tag inválida. {e}")
        
        # Reconstruir array
        watermark = np.frombuffer(watermark_bytes, dtype=np.float64).reshape(shape)
        
        print(f"[Decryption] Watermark descriptografado e autenticado")
        
        return watermark
    
    
    def sign_metadata(self, metadata: Dict) -> str:
        """
        Assina metadados usando HMAC-SHA256.
        
        Garante:
        - Integridade: Metadados não foram alterados
        - Autenticidade: Metadados foram criados pelo titular da chave
        
        Args:
            metadata: Dicionário de metadados
        
        Returns:
            signature: Assinatura HMAC em base64
        """
        # Serializar metadados de forma determinística
        metadata_json = json.dumps(metadata, sort_keys=True)
        metadata_bytes = metadata_json.encode('utf-8')
        
        # Calcular HMAC-SHA256
        h = hmac.new(self.signing_key, metadata_bytes, hashlib.sha256)
        signature = base64.b64encode(h.digest()).decode('utf-8')
        
        print(f"[Signing] Metadados assinados")
        print(f"  - Tamanho: {len(metadata_bytes)} bytes")
        print(f"  - Assinatura: {signature[:32]}...")
        
        return signature
    
    
    def verify_metadata(self, metadata: Dict, signature: str) -> bool:
        """
        Verifica assinatura de metadados.
        
        Args:
            metadata: Dicionário de metadados
            signature: Assinatura HMAC em base64
        
        Returns:
            valid: True se assinatura é válida
        """
        # Calcular assinatura esperada
        expected_signature = self.sign_metadata(metadata)
        
        # Comparação segura contra timing attacks
        valid = hmac.compare_digest(signature, expected_signature)
        
        print(f"[Verification] Assinatura {'VÁLIDA' if valid else 'INVÁLIDA'}")
        
        return valid
    
    
    def generate_challenge(self, image_id: str) -> Tuple[bytes, str]:
        """
        Gera desafio para protocolo challenge-response.
        
        Usado para verificação segura sem revelar o watermark.
        
        Args:
            image_id: Identificador único da imagem
        
        Returns:
            challenge: Desafio aleatório (32 bytes)
            expected_response: Resposta esperada (hash)
        """
        # Gerar desafio aleatório
        challenge = secrets.token_bytes(32)
        
        # Calcular resposta esperada
        # response = HMAC(challenge_key, challenge || image_id)
        h = hmac.new(
            self.challenge_key,
            challenge + image_id.encode('utf-8'),
            hashlib.sha256
        )
        expected_response = h.hexdigest()
        
        print(f"[Challenge] Gerado para imagem {image_id}")
        print(f"  - Challenge: {base64.b64encode(challenge).decode()[:32]}...")
        print(f"  - Expected Response: {expected_response[:32]}...")
        
        return challenge, expected_response
    
    
    def compute_response(self, challenge: bytes, image_id: str) -> str:
        """
        Computa resposta para um desafio.
        
        Args:
            challenge: Desafio recebido
            image_id: Identificador da imagem
        
        Returns:
            response: Resposta ao desafio (hash)
        """
        h = hmac.new(
            self.challenge_key,
            challenge + image_id.encode('utf-8'),
            hashlib.sha256
        )
        response = h.hexdigest()
        
        return response
    
    
    def verify_response(
        self, 
        challenge: bytes, 
        response: str, 
        expected_response: str
    ) -> bool:
        """
        Verifica resposta ao desafio.
        
        Args:
            challenge: Desafio original
            response: Resposta recebida
            expected_response: Resposta esperada
        
        Returns:
            valid: True se resposta é válida
        """
        valid = hmac.compare_digest(response, expected_response)
        
        print(f"[Response Verification] {'VÁLIDA' if valid else 'INVÁLIDA'}")
        
        return valid


class AntiRemovalProtection:
    """
    Proteção contra ataques de remoção de watermark.
    
    Implementa técnicas defensivas:
    1. Watermark redundante (múltiplas cópias)
    2. Watermark adaptativo (força variável)
    3. Detecção de manipulação
    """
    
    def __init__(self, redundancy: int = 3):
        """
        Inicializa proteção anti-remoção.
        
        Args:
            redundancy: Número de cópias redundantes do watermark
        """
        self.redundancy = redundancy
        print(f"[Anti-Removal] Inicializado com redundância {redundancy}x")
    
    
    def create_redundant_watermark(
        self, 
        watermark: np.ndarray,
        image_shape: Tuple[int, int]
    ) -> np.ndarray:
        """
        Cria watermark redundante em múltiplas regiões da imagem.
        
        Args:
            watermark: Padrão de watermark original
            image_shape: Forma da imagem (H, W)
        
        Returns:
            redundant_watermark: Watermark com redundância espacial
        """
        h, w = image_shape
        redundant = np.zeros((h, w))
        
        # Dividir imagem em regiões e aplicar watermark em cada uma
        regions_h = int(np.sqrt(self.redundancy))
        regions_w = int(np.ceil(self.redundancy / regions_h))
        
        region_h = h // regions_h
        region_w = w // regions_w
        
        for i in range(regions_h):
            for j in range(regions_w):
                if i * regions_w + j >= self.redundancy:
                    break
                
                # Redimensionar watermark para a região
                start_h = i * region_h
                end_h = min((i + 1) * region_h, h)
                start_w = j * region_w
                end_w = min((j + 1) * region_w, w)
                
                region_watermark = cv2.resize(
                    watermark, 
                    (end_w - start_w, end_h - start_h)
                )
                
                redundant[start_h:end_h, start_w:end_w] = region_watermark
        
        print(f"[Redundancy] Watermark replicado em {self.redundancy} regiões")
        
        return redundant
    
    
    def detect_tampering(
        self, 
        original_image: np.ndarray, 
        test_image: np.ndarray,
        threshold: float = 0.05
    ) -> Tuple[bool, float]:
        """
        Detecta se a imagem foi manipulada (tentativa de remoção).
        
        Args:
            original_image: Imagem protegida original
            test_image: Imagem a ser testada
            threshold: Limiar de diferença para detecção
        
        Returns:
            tampered: True se manipulação detectada
            difference: Grau de diferença (0-1)
        """
        # Calcular diferença normalizada
        diff = np.abs(original_image.astype(float) - test_image.astype(float))
        difference = np.mean(diff) / 255.0
        
        tampered = difference > threshold
        
        print(f"[Tampering Detection] Diferença: {difference:.4f}")
        print(f"  - Limiar: {threshold}")
        print(f"  - Status: {'MANIPULADA' if tampered else 'ÍNTEGRA'}")
        
        return tampered, difference


# Importar cv2 se necessário para resize
try:
    import cv2
except ImportError:
    print("[Warning] OpenCV não disponível. Algumas funcionalidades limitadas.")
