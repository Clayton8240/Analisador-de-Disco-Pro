# utils.py
import hashlib
import os
import logging
from typing import Optional, Dict
import pandas as pd
from fpdf import FPDF

# *** CORREÇÃO AQUI ***
# Importamos o módulo inteiro em vez de apenas a função,
# para evitar problemas de dependência circular.
import i18n


def calculate_quick_hash(path: str) -> Optional[str]:
    """
    Calcula um hash rápido de um ficheiro lendo o início, o fim e o tamanho.
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
    Classifica um ficheiro com base na sua extensão.
    """
    ext_lower = extension.lower()
    for category, exts in category_map.items():
        if ext_lower in exts:
            return category
    # *** CORREÇÃO AQUI ***
    # Chamada explícita à função de tradução
    return i18n.get_text("category_other")

def export_report_pdf(dataframe: pd.DataFrame, chart_image_path: str, output_path: str, summary: Dict):
    """
    Gera um relatório PDF com resumo, gráfico e tabela de dados.
    """
    try:
        pdf = FPDF()
        pdf.add_page()
        
        try:
            pdf.add_font('Arial', '', 'Arial.ttf', uni=True)
            pdf.set_font("Arial", 'B', size=16)
        except RuntimeError:
            logging.warning("Ficheiro de fonte Arial.ttf não encontrado. A usar a fonte Helvetica como alternativa.")
            pdf.set_font("Helvetica", 'B', size=16)

        # *** CORREÇÃO AQUI ***
        # Todas as chamadas de tradução agora usam o prefixo 'i18n.'
        pdf.cell(0, 10, txt=i18n.get_text("report_title"), ln=True, align='C')
        pdf.ln(10)

        pdf.set_font_size(12)
        pdf.cell(0, 10, txt=i18n.get_text("summary_tab"), ln=True)
        pdf.set_font_size(10)
        pdf.cell(0, 8, txt=f"{i18n.get_text('total_files')} {summary.get('total_files', 0)}", ln=True)
        pdf.cell(0, 8, txt=f"{i18n.get_text('total_size_gb')} {summary.get('total_size_gb', 0):.2f} GB", ln=True)
        pdf.cell(0, 8, txt=f"{i18n.get_text('avg_size_mb')} {summary.get('avg_size_mb', 0):.2f} MB", ln=True)
        pdf.ln(10)

        if os.path.exists(chart_image_path):
            pdf.image(chart_image_path, x=10, y=None, w=180)
            pdf.ln(5)

        pdf.set_font_size(12)
        pdf.cell(0, 10, txt=i18n.get_text("list_tab"), ln=True)
        pdf.set_font_size(8)
        
        pdf.cell(80, 8, i18n.get_text("col_name"), 1)
        pdf.cell(30, 8, i18n.get_text("col_size_mb"), 1)
        pdf.cell(80, 8, i18n.get_text("col_fullpath"), 1)
        pdf.ln()

        for _, row in dataframe.head(30).iterrows():
            name = row.get('name', 'N/A')[:45].encode('latin-1', 'replace').decode('latin-1')
            path = row.get('path', 'N/A')[:45].encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(80, 8, name, 1)
            pdf.cell(30, 8, f"{row.get('size', 0) / (1024*1024):.2f}", 1)
            pdf.cell(80, 8, path, 1)
            pdf.ln()

        pdf.output(output_path)
    except Exception as e:
        logging.error(f"Falha ao gerar o relatório PDF: {e}", exc_info=True)
        raise
