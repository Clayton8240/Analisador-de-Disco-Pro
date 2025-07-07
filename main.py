# main.py
from ui import FinalDiskAnalyzerApp
import logging

if __name__ == "__main__":
    try:
        app = FinalDiskAnalyzerApp()
        app.mainloop()
    except Exception as e:
        logging.critical("Erro fatal ao iniciar a aplicação.", exc_info=True)
        # Numa aplicação real, poderia mostrar uma mensagem de erro final ao utilizador.
