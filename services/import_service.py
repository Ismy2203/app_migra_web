import pandas as pd
from utils.data_cleaner import limpiar_valor
from utils.logger import log_message_streamlit

def convert_to_correct_type(value, field_type, model_fields, conn):
    """
    Convierte el valor a su tipo adecuado según el tipo de campo de Odoo.
    Si el campo es 'many2one', simplemente devuelve el valor como int.
    """
    if field_type == "integer":
        try:
            # Asegurarse de que el valor sea un int, incluso si es un float con valor entero
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            else:
                value = int(value)
        except ValueError:
            log_message_streamlit(f"Error: No se puede convertir '{value}' a un número entero.")
            return None  # O el valor por defecto que prefieras
    elif field_type == "float":
        try:
            # Si el valor es un float que es equivalente a un entero (por ejemplo, 20.0), lo convertimos a int
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            else:
                value = float(value)
        except ValueError:
            log_message_streamlit(f"Error: No se puede convertir '{value}' a un número decimal.")
            return None
    elif field_type == "char" or field_type == "text":
        # Para texto, solo lo pasamos tal cual
        return str(value)
    elif field_type == "many2one":
        # **Mucho más simple**: directamente pasamos el valor como int (ya que es un ID)
        try:
            return int(value)  # Deberías asegurarte de que este 'value' sea un ID válido
        except ValueError:
            log_message_streamlit(f"Error: El valor '{value}' para Many2one no es un ID válido.")
            return None  # O el valor por defecto que prefieras
    return value  # Para otros casos, retornamos el valor tal cual
