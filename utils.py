# utils.py
import hashlib
import os
import logging
from typing import Optional

def calculate_quick_hash(path: str) -> Optional[str]:
    """
    Calcula um hash rápido de um ficheiro lendo apenas o início e o fim.
    Ideal para identificar potenciais duplicados de ficheiros grandes rapidamente.

    Args:
        path: O caminho completo para o ficheiro.

    Returns:
        A string hexadecimal do hash (SHA1) ou None se ocorrer um erro.
    """
    try:
        h = hashlib.sha1()
        file_size = os.path.getsize(path)
        chunk_size = 1024 * 1024  # 1MB

        with open(path, 'rb') as f:
            if file_size < chunk_size * 2:
                # Para ficheiros pequenos, lê o ficheiro inteiro
                h.update(f.read())
            else:
                # Lê o primeiro 1MB
                h.update(f.read(chunk_size))
                # Vai para o último 1MB
                f.seek(-chunk_size, os.SEEK_END)
                h.update(f.read(chunk_size))
        
        # Adiciona o tamanho do ficheiro ao hash para garantir unicidade
        h.update(str(file_size).encode())
        
        return h.hexdigest()
    except Exception as e:
        logging.warning(f"Não foi possível calcular o hash de {path}: {e}")
        return None
