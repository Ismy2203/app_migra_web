import numpy as np
import pandas as pd

def limpiar_valor(valor):
    if isinstance(valor, (np.integer,)):
        return int(valor)
    elif isinstance(valor, (np.floating,)):
        return int(valor) if valor.is_integer() else float(valor)
    elif isinstance(valor, (float, int, str)):
        return valor
    elif pd.isna(valor):
        return None
    else:
        return str(valor)

def clean_url(url):
    return url.rstrip("/") if url else url
