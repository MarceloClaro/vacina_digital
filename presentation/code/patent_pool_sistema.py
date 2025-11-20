#!/usr/bin/env python3
"""
PATENT POOL - VACINA DIGITAL
============================

Sistema de formação e gestão de patent pool para a tecnologia Vacina Digital.
Permite que múltiplos detentores de dados criem um consórcio unificado para
licenciamento coletivo de propriedade intelectual.

Funcionalidades:
1. Cadastro de membros do patent pool
2. Gestão de royalties coletivos
3. Contratos de licenciamento padronizados
4. Relatórios de arrecadação
5. Sistema de votação para decisões coletivas

Autor: Marcelo Claro Laranjeira
Data: 20 de novembro de 2025
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict
import uuid

class MembroPatentPool:
    """Representa um membro do patent pool."""

    def __init__(self, nome: str, tipo: str, dados_protegidos: int,
                 contato: Dict, assinatura_digital: str):
        self.id = str(uuid.uuid4())
        self.nome = nome
        self.tipo = tipo  # 'empresa', 'instituicao', 'pessoa_fisica'
        self.dados_protegidos = dados_protegidos  # GB de dados
        self.contato = contato
        self.assinatura_digital = assinatura_digital
        self.data_adesao = datetime.now().isoformat()
        self.royalties_acumulados = 0.0
        self.votos = 0

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'nome': self.nome,
            'tipo': self.tipo,
            'dados_protegidos': self.dados_protegidos,
            'contato': self.contato,
            'assinatura_digital': self.assinatura_digital,
            'data_adesao': self.data_adesao,
            'royalties_acumulados': self.royalties_acumulados,
            'votos': self.votos
        }

class LicencaPatentPool:
    """Representa uma licença concedida pelo patent pool."""

    def __init__(self, licenciatario: str, tipo_licenca: str,
                 abrangencia: str, prazo_meses: int, valor_royalty: float):
        self.id = str(uuid.uuid4())
        self.licenciatario = licenciatario
        self.tipo_licenca = tipo_licenca  # 'individual', 'empresarial', 'global'
        self.abrangencia = abrangencia  # 'nacional', 'internacional'
        self.prazo_meses = prazo_meses
        self.valor_royalty = valor_royalty  # % do faturamento
        self.data_emissao = datetime.now().isoformat()
        self.data_expiracao = (datetime.now() + timedelta(days=30*prazo_meses)).isoformat()
        self.status = 'ativa'
        self.royalties_recebidos = 0.0

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'licenciatario': self.licenciatario,
            'tipo_licenca': self.tipo_licenca,
            'abrangencia': self.abrangencia,
            'prazo_meses': self.prazo_meses,
            'valor_royalty': self.valor_royalty,
            'data_emissao': self.data_emissao,
            'data_expiracao': self.data_expiracao,
            'status': self.status,
            'royalties_recebidos': self.royalties_recebidos
        }

class PatentPoolVacinaDigital:
    """
    Sistema de gestão do Patent Pool da Vacina Digital.
    """

    def __init__(self, nome_pool: str = "Patent Pool Vacina Digital"):
        self.nome = nome_pool
        self.id = str(uuid.uuid4())
        self.data_criacao = datetime.now().isoformat()
        self.membros: Dict[str, MembroPatentPool] = {}
        self.licencas: Dict[str, LicencaPatentPool] = {}
        self.regras_distribuicao = {
            'royalty_base': 0.02,  # 2% base
            'distribuicao_membros': 'proporcional_dados',  # proporcional ao volume de dados
            'fundo_reserva': 0.1,  # 10% para reserva
            'fundo_pesquisa': 0.05,  # 5% para P&D
            'fundo_juridico': 0.05   # 5% para ações jurídicas
        }
        self.total_dados_protegidos = 0
        self.total_royalties_recebidos = 0.0

        # Criar estrutura de diretórios
        os.makedirs("patent_pool/membros", exist_ok=True)
        os.makedirs("patent_pool/licencas", exist_ok=True)
        os.makedirs("patent_pool/relatorios", exist_ok=True)
        os.makedirs("patent_pool/votacoes", exist_ok=True)

    def adicionar_membro(self, membro: MembroPatentPool) -> str:
        """Adiciona um novo membro ao patent pool."""
        self.membros[membro.id] = membro
        self.total_dados_protegidos += membro.dados_protegidos

        # Salvar dados do membro
        with open(f"patent_pool/membros/{membro.id}.json", 'w', encoding='utf-8') as f:
            json.dump(membro.to_dict(), f, indent=2, ensure_ascii=False)

        print(f"✅ Membro adicionado: {membro.nome} (ID: {membro.id})")
        return membro.id

    def conceder_licenca(self, licenciatario: str, tipo_licenca: str,
                         abrangencia: str, prazo_meses: int) -> str:
        """Concede uma nova licença."""
        # Calcular valor do royalty baseado no tipo
        if tipo_licenca == 'individual':
            royalty = 0.005  # 0.5%
        elif tipo_licenca == 'empresarial':
            royalty = 0.015  # 1.5%
        elif tipo_licenca == 'global':
            royalty = 0.025  # 2.5%
        else:
            royalty = 0.01   # 1%

        licenca = LicencaPatentPool(
            licenciatario=licenciatario,
            tipo_licenca=tipo_licenca,
            abrangencia=abrangencia,
            prazo_meses=prazo_meses,
            valor_royalty=royalty
        )

        self.licencas[licenca.id] = licenca

        # Salvar licença
        with open(f"patent_pool/licencas/{licenca.id}.json", 'w', encoding='utf-8') as f:
            json.dump(licenca.to_dict(), f, indent=2, ensure_ascii=False)

        print(f"✅ Licença concedida: {licenciatario} ({tipo_licenca})")
        return licenca.id

    def registrar_pagamento_royalty(self, id_licenca: str, valor: float) -> bool:
        """Registra pagamento de royalties."""
        if id_licenca not in self.licencas:
            print(f"❌ Licença não encontrada: {id_licenca}")
            return False

        licenca = self.licencas[id_licenca]
        licenca.royalties_recebidos += valor
        self.total_royalties_recebidos += valor

        # Distribuir royalties entre membros
        self._distribuir_royalties(valor)

        # Salvar atualização
        with open(f"patent_pool/licencas/{id_licenca}.json", 'w', encoding='utf-8') as f:
            json.dump(licenca.to_dict(), f, indent=2, ensure_ascii=False)

        print(f"✅ Royalty registrado: R$ {valor:.2f} da licença {id_licenca}")
        return True

    def _distribuir_royalties(self, valor_total: float):
        """Distribui royalties entre membros do pool."""
        if not self.membros:
            return

        # Reserva e fundos especiais
        fundo_reserva = valor_total * self.regras_distribuicao['fundo_reserva']
        fundo_pesquisa = valor_total * self.regras_distribuicao['fundo_pesquisa']
        fundo_juridico = valor_total * self.regras_distribuicao['fundo_juridico']

        valor_distribuir = valor_total - fundo_reserva - fundo_pesquisa - fundo_juridico

        # Distribuir proporcionalmente ao volume de dados
        total_dados = sum(m.dados_protegidos for m in self.membros.values())

        for membro in self.membros.values():
            if total_dados > 0:
                proporcao = membro.dados_protegidos / total_dados
                valor_membro = valor_distribuir * proporcao
                membro.royalties_acumulados += valor_membro

                # Salvar atualização do membro
                with open(f"patent_pool/membros/{membro.id}.json", 'w', encoding='utf-8') as f:
                    json.dump(membro.to_dict(), f, indent=2, ensure_ascii=False)

    def gerar_relatorio_mensal(self, mes: str, ano: str) -> str:
        """Gera relatório mensal de atividades do patent pool."""

        relatorio = f"""
================================================================================
RELATÓRIO MENSAL - PATENT POOL VACINA DIGITAL
================================================================================

Período: {mes}/{ano}
Data de Geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

--------------------------------------------------------------------------------
ESTATÍSTICAS GERAIS
--------------------------------------------------------------------------------

Membros Ativos: {len(self.membros)}
Total de Dados Protegidos: {self.total_dados_protegidos} GB
Licenças Ativas: {len([licenca for licenca in self.licencas.values() if licenca.status == 'ativa'])}
Total Royalties Recebidos: R$ {self.total_royalties_recebidos:.2f}

--------------------------------------------------------------------------------
MEMBROS DO POOL
--------------------------------------------------------------------------------

"""

        for membro in self.membros.values():
            relatorio += f"""
{membro.nome} ({membro.tipo})
• Dados Protegidos: {membro.dados_protegidos} GB
• Royalties Acumulados: R$ {membro.royalties_acumulados:.2f}
• Data de Adesão: {membro.data_adesao[:10]}
"""

        relatorio += """
--------------------------------------------------------------------------------
LICENÇAS CONCEDIDAS
--------------------------------------------------------------------------------

"""

        for licenca in self.licencas.values():
            relatorio += f"""
Licença {licenca.id}
• Licenciatário: {licenca.licenciatario}
• Tipo: {licenca.tipo_licenca} ({licenca.abrangencia})
• Royalty: {licenca.valor_royalty:.1%}
• Recebido: R$ {licenca.royalties_recebidos:.2f}
• Status: {licenca.status}
• Expiração: {licenca.data_expiracao[:10]}
"""

        relatorio += f"""
--------------------------------------------------------------------------------
DISTRIBUIÇÃO DE ROYALTIES
--------------------------------------------------------------------------------

Regras de Distribuição:
• Fundo Reserva: {self.regras_distribuicao['fundo_reserva']:.1%}
• Fundo P&D: {self.regras_distribuicao['fundo_pesquisa']:.1%}
• Fundo Jurídico: {self.regras_distribuicao['fundo_juridico']:.1%}
• Distribuição Membros: Proporcional ao volume de dados

--------------------------------------------------------------------------------
PROJEÇÕES FINANCEIRAS
--------------------------------------------------------------------------------

Cenário Conservador (100 licenças empresariais):
• Receita Anual: R$ {100 * 0.015 * 100000:.2f} (estimativa)
• Distribuição por Membro: R$ {100 * 0.015 * 100000 / len(self.membros):.2f} (média)

Cenário Otimista (500 licenças globais):
• Receita Anual: R$ {500 * 0.025 * 500000:.2f} (estimativa)
• Distribuição por Membro: R$ {500 * 0.025 * 500000 / len(self.membros):.2f} (média)

================================================================================
FIM DO RELATÓRIO
================================================================================
"""

        # Salvar relatório
        filename = f"patent_pool/relatorios/relatorio_{ano}_{mes}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(relatorio)

        print(f"✅ Relatório mensal salvo: {filename}")
        return relatorio

    def obter_estatisticas(self) -> Dict:
        """Retorna estatísticas do patent pool."""
        return {
            'nome_pool': self.nome,
            'total_membros': len(self.membros),
            'total_dados_protegidos': self.total_dados_protegidos,
            'total_licencas': len(self.licencas),
            'total_royalties': self.total_royalties_recebidos,
            'licencas_ativas': len([licenca for licenca in self.licencas.values() if licenca.status == 'ativa']),
            'royalties_por_membro': {
                m.nome: m.royalties_acumulados for m in self.membros.values()
            }
        }

def demonstracao_patent_pool():
    """Demonstração completa do sistema de patent pool."""

    print("\n" + "="*80)
    print("DEMONSTRAÇÃO: PATENT POOL - VACINA DIGITAL")
    print("="*80)

    # Criar patent pool
    print("\n🏛️ Criando Patent Pool...")
    pool = PatentPoolVacinaDigital("Patent Pool Vacina Digital v1.0")
    print("✅ Patent Pool criado")

    # Adicionar membros fundadores
    print("\n👥 Adicionando membros fundadores...")

    membros_fundadores = [
        {
            'nome': 'Universidade Federal do Ceará',
            'tipo': 'instituicao',
            'dados_protegidos': 500,  # 500 GB
            'contato': {'email': 'reitoria@ufc.br', 'telefone': '+55 85 3366-0000'},
            'assinatura_digital': 'hash_ufc_2025'
        },
        {
            'nome': 'Empresa Tech Brasil Ltda',
            'tipo': 'empresa',
            'dados_protegidos': 2000,  # 2 TB
            'contato': {'email': 'contato@techbrasil.com', 'telefone': '+55 11 9999-0000'},
            'assinatura_digital': 'hash_techbrasil_2025'
        },
        {
            'nome': 'Instituto de Pesquisa Médica',
            'tipo': 'instituicao',
            'dados_protegidos': 800,  # 800 GB
            'contato': {'email': 'diretoria@ipm.br', 'telefone': '+55 21 8888-0000'},
            'assinatura_digital': 'hash_ipm_2025'
        },
        {
            'nome': 'FotoStudio Profissional',
            'tipo': 'empresa',
            'dados_protegidos': 100,  # 100 GB
            'contato': {'email': 'contato@fotostudio.com', 'telefone': '+55 85 7777-0000'},
            'assinatura_digital': 'hash_fotostudio_2025'
        }
    ]

    for dados_membro in membros_fundadores:
        membro = MembroPatentPool(**dados_membro)
        pool.adicionar_membro(membro)

    print(f"✅ {len(membros_fundadores)} membros fundadores adicionados")

    # Conceder licenças
    print("\n📄 Concedendo licenças...")

    licencas = [
        ('Google Brasil', 'empresarial', 'internacional', 24),
        ('Meta Platforms Inc', 'global', 'internacional', 36),
        ('Microsoft Brasil', 'empresarial', 'internacional', 24),
        ('Amazon Web Services', 'global', 'internacional', 48),
        ('Startup IA Nacional', 'individual', 'nacional', 12),
        ('Empresa de E-commerce', 'empresarial', 'nacional', 24)
    ]

    for licenciatario, tipo, abrangencia, prazo in licencas:
        pool.conceder_licenca(licenciatario, tipo, abrangencia, prazo)

    print(f"✅ {len(licencas)} licenças concedidas")

    # Simular pagamentos de royalties
    print("\n💰 Simulando pagamentos de royalties...")

    pagamentos = [
        ('licenca_google', 50000.00),
        ('licenca_meta', 150000.00),
        ('licenca_microsoft', 75000.00),
        ('licenca_amazon', 200000.00),
        ('licenca_startup', 2500.00),
        ('licenca_ecommerce', 15000.00)
    ]

    # Obter IDs reais das licenças
    ids_licencas = list(pool.licencas.keys())

    for i, (desc, valor) in enumerate(pagamentos):
        if i < len(ids_licencas):
            pool.registrar_pagamento_royalty(ids_licencas[i], valor)

    # Gerar relatório mensal
    print("\n📊 Gerando relatório mensal...")
    pool.gerar_relatorio_mensal("11", "2025")

    # Estatísticas finais
    stats = pool.obter_estatisticas()
    print("\n📈 ESTATÍSTICAS FINAIS DO PATENT POOL:")
    print(f"  • Membros: {stats['total_membros']}")
    print(f"  • Dados Protegidos: {stats['total_dados_protegidos']} GB")
    print(f"  • Licenças Ativas: {stats['licencas_ativas']}")
    print(f"  • Royalties Totais: R$ {stats['total_royalties']:.2f}")

    print("\n💰 DISTRIBUIÇÃO DE ROYALTIES POR MEMBRO:")
    for nome, valor in stats['royalties_por_membro'].items():
        print(f"  • {nome}: R$ {valor:.2f}")

    print("\n📁 ARQUIVOS GERADOS:")
    print("  • patent_pool/membros/*.json - Dados dos membros")
    print("  • patent_pool/licencas/*.json - Licenças concedidas")
    print("  • patent_pool/relatorios/relatorio_2025_11.txt - Relatório mensal")

    print("\n" + "="*80)
    print("DEMONSTRAÇÃO CONCLUÍDA - PATENT POOL OPERACIONAL")
    print("="*80)

    print("\n🎯 PRÓXIMOS PASSOS PARA IMPLEMENTAÇÃO REAL:")
    print("  1. Constituição formal do consórcio jurídico")
    print("  2. Contratos de adesão padronizados")
    print("  3. Plataforma web para gestão automatizada")
    print("  4. Integração com sistemas bancários")
    print("  5. Expansão internacional do pool")

if __name__ == "__main__":
    demonstracao_patent_pool()