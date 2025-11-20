"""
UTILITÁRIO PARA CARREGAMENTO DE DATASETS DE FOTÓGRAFOS
======================================================

Este módulo fornece funções para carregar datasets de imagens de fotógrafos
de pastas ou arquivos ZIP, facilitando o processamento em lote.

Funcionalidades:
- Carregamento de imagens de pastas organizadas por categoria
- Carregamento de imagens de arquivos ZIP
- Validação de formatos de imagem suportados
- Atribuição automática de labels baseada na estrutura de pastas
- Suporte a datasets grandes com amostragem
"""

import os
import zipfile
from PIL import Image
import numpy as np
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Formatos de imagem suportados
SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', '.gif')

def validate_image_format(filepath: str) -> bool:
    """Valida se o arquivo é um formato de imagem suportado"""
    return filepath.lower().endswith(SUPPORTED_FORMATS)

def load_images_from_folder(
    folder_path: str,
    max_images: Optional[int] = None,
    recursive: bool = True
) -> Tuple[List[str], List[int]]:
    """
    Carrega caminhos de imagens e labels de uma pasta organizada.

    Args:
        folder_path: Caminho para a pasta raiz
        max_images: Número máximo de imagens a carregar (None = todas)
        recursive: Se deve procurar recursivamente em subpastas

    Returns:
        Tuple com (caminhos_das_imagens, labels)
    """
    image_paths = []
    labels = []
    label_map = {}  # Mapeia nome da pasta para label numérico
    current_label = 0

    if recursive:
        for root, dirs, files in os.walk(folder_path):
            # Pular pastas ocultas ou de sistema
            if os.path.basename(root).startswith('.'):
                continue

            # Atribuir label baseado no nome da pasta raiz
            folder_name = os.path.basename(root)
            if folder_name not in label_map:
                label_map[folder_name] = current_label
                current_label += 1

            label = label_map[folder_name]

            for file in files:
                if validate_image_format(file):
                    full_path = os.path.join(root, file)
                    image_paths.append(full_path)
                    labels.append(label)

                    if max_images and len(image_paths) >= max_images:
                        break

            if max_images and len(image_paths) >= max_images:
                break
    else:
        # Walk não recursivo
        try:
            items = os.listdir(folder_path)
            dirs = [d for d in items if os.path.isdir(os.path.join(folder_path, d))]
            files = [f for f in items if os.path.isfile(os.path.join(folder_path, f))]

            # Processar arquivos na pasta raiz
            folder_name = os.path.basename(folder_path)
            if folder_name not in label_map:
                label_map[folder_name] = current_label
                current_label += 1

            label = label_map[folder_name]

            for file in files:
                if validate_image_format(file):
                    full_path = os.path.join(folder_path, file)
                    image_paths.append(full_path)
                    labels.append(label)

                    if max_images and len(image_paths) >= max_images:
                        break

            # Processar subpastas (não recursivo)
            for d in dirs:
                subpath = os.path.join(folder_path, d)
                try:
                    subitems = os.listdir(subpath)
                    subfiles = [f for f in subitems if os.path.isfile(os.path.join(subpath, f))]

                    # Atribuir label baseado no nome da subpasta
                    subfolder_name = os.path.basename(subpath)
                    if subfolder_name not in label_map:
                        label_map[subfolder_name] = current_label
                        current_label += 1

                    sublabel = label_map[subfolder_name]

                    for file in subfiles:
                        if validate_image_format(file):
                            full_path = os.path.join(subpath, file)
                            image_paths.append(full_path)
                            labels.append(sublabel)

                            if max_images and len(image_paths) >= max_images:
                                break

                    if max_images and len(image_paths) >= max_images:
                        break

                except PermissionError:
                    logger.warning(f"Sem permissão para acessar {subpath}")
                    continue

        except PermissionError:
            logger.warning(f"Sem permissão para acessar {folder_path}")
            return [], []

    logger.info(f"Carregadas {len(image_paths)} imagens de {folder_path}")
    logger.info(f"Classes encontradas: {len(label_map)} ({list(label_map.keys())})")

    return image_paths, labels

def load_images_from_zip(
    zip_path: str,
    max_images: Optional[int] = None
) -> Tuple[List[str], List[int]]:
    """
    Carrega caminhos de imagens e labels de um arquivo ZIP.

    Args:
        zip_path: Caminho para o arquivo ZIP
        max_images: Número máximo de imagens a carregar

    Returns:
        Tuple com (caminhos_virtuais_das_imagens, labels)
    """
    image_paths = []
    labels = []
    label_map = {}
    current_label = 0

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()

            for file_path in file_list:
                # Pular arquivos ocultos ou de sistema
                if os.path.basename(file_path).startswith('.'):
                    continue

                if validate_image_format(file_path):
                    # Extrair diretório para determinar label
                    dir_name = os.path.dirname(file_path)
                    if dir_name not in label_map:
                        label_map[dir_name] = current_label
                        current_label += 1

                    label = label_map[dir_name]
                    image_paths.append(f"zip://{zip_path}@{file_path}")
                    labels.append(label)

                    if max_images and len(image_paths) >= max_images:
                        break

    except zipfile.BadZipFile:
        raise ValueError(f"Arquivo ZIP inválido: {zip_path}")
    except Exception as e:
        raise IOError(f"Erro ao ler ZIP {zip_path}: {e}")

    logger.info(f"Carregadas {len(image_paths)} imagens do ZIP {zip_path}")
    logger.info(f"Classes encontradas: {len(label_map)}")

    return image_paths, labels

def load_image_from_path(image_path: str) -> np.ndarray:
    """
    Carrega uma imagem de um caminho (pode ser arquivo ou caminho virtual ZIP).

    Args:
        image_path: Caminho da imagem

    Returns:
        Array numpy da imagem (H, W, 3) RGB
    """
    if image_path.startswith("zip://"):
        # Formato: zip://caminho/arquivo.zip@caminho/interno
        zip_path, internal_path = image_path[6:].split('@', 1)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            with zip_ref.open(internal_path) as file:
                image = Image.open(file).convert('RGB')
                return np.array(image)
    else:
        # Arquivo normal
        image = Image.open(image_path).convert('RGB')
        return np.array(image)

def get_dataset_info(image_paths: List[str], labels: List[int]) -> dict:
    """
    Retorna informações estatísticas sobre o dataset carregado.

    Args:
        image_paths: Lista de caminhos das imagens
        labels: Lista de labels correspondentes

    Returns:
        Dicionário com estatísticas
    """
    if not image_paths:
        return {}

    # Contar imagens por classe
    unique_labels, counts = np.unique(labels, return_counts=True)
    label_distribution = dict(zip(unique_labels, counts))

    # Verificar tamanhos das imagens
    image_sizes = []
    for path in image_paths[:min(100, len(image_paths))]:  # Amostra para performance
        try:
            img_array = load_image_from_path(path)
            image_sizes.append(img_array.shape[:2])  # (H, W)
        except Exception:
            continue

    if image_sizes:
        heights, widths = zip(*image_sizes)
        avg_height = np.mean(heights)
        avg_width = np.mean(widths)
        min_size = (min(heights), min(widths))
        max_size = (max(heights), max(widths))
    else:
        avg_height = avg_width = 0
        min_size = max_size = (0, 0)

    return {
        'total_images': len(image_paths),
        'num_classes': len(unique_labels),
        'label_distribution': label_distribution,
        'avg_image_size': (avg_height, avg_width),
        'min_image_size': min_size,
        'max_image_size': max_size,
        'supported_formats': list(SUPPORTED_FORMATS)
    }

def validate_dataset(image_paths: List[str], labels: List[int], max_check: int = 50) -> dict:
    """
    Valida a integridade do dataset carregado.

    Args:
        image_paths: Lista de caminhos das imagens
        labels: Lista de labels
        max_check: Número máximo de imagens a verificar

    Returns:
        Dicionário com resultados da validação
    """
    validation_results = {
        'total_images': len(image_paths),
        'valid_images': 0,
        'invalid_images': 0,
        'corrupted_images': [],
        'warnings': []
    }

    check_count = min(max_check, len(image_paths))

    for i in range(check_count):
        path = image_paths[i]
        try:
            img_array = load_image_from_path(path)
            if img_array.size == 0:
                validation_results['corrupted_images'].append(path)
                validation_results['invalid_images'] += 1
            else:
                validation_results['valid_images'] += 1
        except Exception as e:
            validation_results['corrupted_images'].append(path)
            validation_results['invalid_images'] += 1
            validation_results['warnings'].append(f"{path}: {str(e)}")

    # Verificar balanceamento
    unique_labels, counts = np.unique(labels, return_counts=True)
    min_count = min(counts)
    max_count = max(counts)

    if max_count / min_count > 10:
        validation_results['warnings'].append(
            f"Dataset desbalanceado: classe menor={min_count}, maior={max_count}"
        )

    return validation_results