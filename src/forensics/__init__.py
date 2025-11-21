"""
Módulo Forense do Vacina Digital
Ferramentas para aplicações jurídicas: triggers, certificados e detecção de uso em modelos de IA.
"""

from .forensic_triggers import insert_trigger_watermark, test_trigger_response
from .forensic_certificates import create_batch_certificate, verify_certificate

__all__ = ["insert_trigger_watermark", "test_trigger_response", "create_batch_certificate", "verify_certificate"]