# Instalação

Esta página guia você através da instalação e configuração do Vacina Digital.

## Pré-requisitos

- Python 3.8 ou superior
- Git
- (Opcional) GPU para aceleração (CUDA)

## Instalação Básica

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/MarceloClaro/vacina_digital.git
   cd vacina_digital
   ```

2. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verifique a instalação:**
   ```bash
   python -c "import vacina_digital; print('Instalação bem-sucedida!')"
   ```

## Instalação Avançada

### Com Ambiente Virtual
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### Com GPU
Certifique-se de ter CUDA instalado e use:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

## Configuração

1. **Configure o Git LFS** (para arquivos grandes):
   ```bash
   git lfs install
   git lfs pull
   ```

2. **Execute os testes:**
   ```bash
   python -m pytest tests/
   ```

## Solução de Problemas

- **Erro de dependências:** Atualize o pip: `pip install --upgrade pip`
- **Problemas com CUDA:** Verifique a versão compatível do PyTorch
- **Arquivos grandes:** Certifique-se de que Git LFS está configurado

Para mais ajuda, consulte [[Solução de Problemas|Troubleshooting]].