# utils.py

import hashlib
import os
import logging
from typing import Optional

def calculate_quick_hash(path: str) -> Optional[str]:
    """
    Calcula um hash rápido de um ficheiro lendo o início, o fim e o tamanho.

    Esta abordagem otimizada é significativamente mais rápida do que ler o ficheiro
    inteiro, sendo ideal para a deteção inicial de ficheiros duplicados em
    grandes volumes de dados.

    Args:
        path (str): O caminho completo para o ficheiro a ser analisado.

    Returns:
        Optional[str]: A string hexadecimal do hash SHA1, ou None se ocorrer um erro
                       (ex: permissão de leitura, ficheiro não encontrado).
    """
    try:
        h = hashlib.sha1()
        file_size = os.path.getsize(path)
        chunk_size = 1024 * 1024  # 1MB

        with open(path, 'rb') as f:
            if file_size < chunk_size * 2:
                h.update(f.read())
            else:
                h.update(f.read(chunk_size))
                f.seek(-chunk_size, os.SEEK_END)
                h.update(f.read(chunk_size))
        
        h.update(str(file_size).encode())
        return h.hexdigest()
    except Exception as e:
        logging.warning(f"Não foi possível calcular o hash de {path}: {e}")
        return None
