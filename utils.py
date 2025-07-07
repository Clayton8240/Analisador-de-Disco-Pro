# utils.py
import hashlib
import os
import logging
from typing import Optional, Dict # <- CORREÇÃO AQUI
import pandas as pd
from fpdf import FPDF

# Importa a função de tradução para que este módulo também possa usá-la
from i18n import get_text as _


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

def categorize_file(extension: str, category_map: Dict[str, list]) -> str:
    """
    Classifica um ficheiro com base na sua extensão, usando um mapa de categorias.

    Args:
        extension (str): A extensão do ficheiro (ex: '.pdf').
        category_map (Dict[str, list]): O dicionário de categorias da aplicação.

    Returns:
        str: O nome da categoria correspondente ou 'Outros'.
    """
    ext_lower = extension.lower()
    for category, exts in category_map.items():
        if ext_lower in exts:
            return category
    return _("category_other")

def export_report_pdf(dataframe: pd.DataFrame, chart_image_path: str, output_path: str, summary: Dict):
    """
    Gera um relatório PDF com resumo, gráfico e tabela de dados.

    Args:
        dataframe (pd.DataFrame): Dados para a tabela.
        chart_image_path (str): Caminho para a imagem temporária do gráfico.
        output_path (str): Caminho onde o PDF será salvo.
        summary (Dict): Dicionário com as estatísticas de resumo.
    """
    try:
        pdf = FPDF()
        pdf.add_page()
        # Adiciona a fonte Arial (necessária para caracteres Unicode)
        # O ficheiro .ttf deve estar na mesma pasta ou num caminho conhecido
        try:
            pdf.add_font('Arial', '', 'Arial.ttf', uni=True)
            pdf.set_font("Arial", 'B', size=16)
        except RuntimeError:
            logging.warning("Ficheiro de fonte Arial.ttf não encontrado. Usando fonte padrão.")
            pdf.set_font("Helvetica", 'B', size=16)

        pdf.cell(0, 10, txt=_("report_title"), ln=True, align='C')
        pdf.ln(10)

        # Seção de Resumo
        pdf.set_font_size(12)
        pdf.cell(0, 10, txt=_("summary_tab"), ln=True)
        pdf.set_font_size(10)
        pdf.cell(0, 8, txt=f"{_('total_files')} {summary.get('total_files', 0)}", ln=True)
        pdf.cell(0, 8, txt=f"{_('total_size_gb')} {summary.get('total_size_gb', 0):.2f} GB", ln=True)
        pdf.cell(0, 8, txt=f"{_('avg_size_mb')} {summary.get('avg_size_mb', 0):.2f} MB", ln=True)
        pdf.ln(10)

        # Gráfico
        if os.path.exists(chart_image_path):
            pdf.image(chart_image_path, x=10, y=None, w=180)
            pdf.ln(5)

        # Tabela de Dados
        pdf.set_font_size(12)
        pdf.cell(0, 10, txt=_("list_tab"), ln=True)
        pdf.set_font_size(8)
        
        # Cabeçalho da tabela
        pdf.cell(80, 8, _("col_name"), 1)
        pdf.cell(30, 8, _("col_size_mb"), 1)
        pdf.cell(80, 8, _("col_fullpath"), 1)
        pdf.ln()

        # Linhas da tabela
        for _, row in dataframe.head(30).iterrows():
            name = row.get('name', 'N/A')[:45]
            path = row.get('path', 'N/A')[:45]
            pdf.cell(80, 8, name, 1)
            pdf.cell(30, 8, f"{row.get('size', 0) / (1024*1024):.2f}", 1)
            pdf.cell(80, 8, path, 1)
            pdf.ln()

        pdf.output(output_path)
    except Exception as e:
        logging.error(f"Falha ao gerar o relatório PDF: {e}", exc_info=True)
        raise
