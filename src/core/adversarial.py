"""
Módulo para geração de ataques adversariais reais (FGSM/PGD) usando PyTorch.
Este módulo é usado pela Vacina Digital para criar triggers que são matematicamente
otimizados para enganar redes neurais, em vez de apenas ruído aleatório.
"""

import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
import numpy as np
from typing import Optional

class AdversarialEngine:
    """
    Motor de geração de ataques adversariais usando modelos surrogate.
    """
    
    def __init__(self, model_name: str = 'resnet18', pretrained: bool = True):
        """
        Inicializa o motor adversarial com um modelo surrogate.
        
        Args:
            model_name: Nome do modelo no torchvision (ex: 'resnet18', 'mobilenet_v2')
            pretrained: Se deve usar pesos pré-treinados (recomendado para transferibilidade)
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"[AdversarialEngine] Inicializando com modelo '{model_name}' em {self.device}...")
        
        try:
            # Carregar modelo do torchvision
            if hasattr(models, model_name):
                self.model = getattr(models, model_name)(pretrained=pretrained)
            else:
                print(f"Modelo '{model_name}' não encontrado. Usando ResNet18.")
                self.model = models.resnet18(pretrained=pretrained)
            
            self.model.to(self.device)
            self.model.eval()
            
            # Normalização padrão do ImageNet
            self.normalize = transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
            print("  [OK] Modelo surrogate carregado com sucesso.")
            
        except Exception as e:
            print(f"  [AVISO] Erro ao carregar modelo: {e}")
            print("  [AVISO] Fallback para modo sem modelo (apenas ruido).")
            self.model = None

    def generate_fgsm(
        self, 
        image: np.ndarray, 
        epsilon: float, 
        target_label: Optional[int] = None
    ) -> np.ndarray:
        """
        Gera perturbação adversarial usando Fast Gradient Sign Method (FGSM).
        
        Args:
            image: Imagem de entrada (H, W, 3) uint8 ou float [0,1]
            epsilon: Magnitude da perturbação
            target_label: Se fornecido, realiza ataque direcionado (Targeted Attack).
                          Se None, realiza ataque não-direcionado (tenta maximizar erro).
        
        Returns:
            Perturbação adversarial (mesmo shape da imagem)
        """
        if self.model is None:
            # Fallback se não houver modelo: ruído aleatório
            return np.sign(np.random.randn(*image.shape)) * epsilon

        # Preparar imagem para PyTorch
        if image.dtype == np.uint8:
            img_tensor = transforms.ToTensor()(image).to(self.device)
        else:
            img_tensor = torch.from_numpy(image.transpose(2, 0, 1)).float().to(self.device)
            
        # Adicionar dimensão de batch
        img_tensor = img_tensor.unsqueeze(0)
        img_tensor.requires_grad = True
        
        # Forward pass
        outputs = self.model(self.normalize(img_tensor))
        
        if target_label is not None:
            # Targeted Attack: Queremos que a perda para o target seja MINIMIZADA
            # Mas FGSM padrão maximiza a perda.
            # Então para targeted: x_adv = x - epsilon * sign(grad(loss(x, target)))
            
            # Criar tensor do target
            target = torch.tensor([target_label], device=self.device)
            loss = nn.CrossEntropyLoss()(outputs, target)
            
            self.model.zero_grad()
            loss.backward()
            
            # Gradiente descendente no input
            data_grad = img_tensor.grad.data
            perturbation = -epsilon * data_grad.sign()
            
        else:
            # Untargeted Attack: Queremos MAXIMIZAR o erro em relação ao label predito
            # x_adv = x + epsilon * sign(grad(loss(x, pred)))
            
            # Usar a própria predição como "ground truth" para afastar dela
            pred_label = outputs.max(1, keepdim=True)[1].squeeze()
            loss = nn.CrossEntropyLoss()(outputs, pred_label.unsqueeze(0))
            
            self.model.zero_grad()
            loss.backward()
            
            data_grad = img_tensor.grad.data
            perturbation = epsilon * data_grad.sign()

        # Converter de volta para numpy (H, W, 3)
        pert_np = perturbation.squeeze(0).cpu().detach().numpy().transpose(1, 2, 0)
        
        return pert_np

