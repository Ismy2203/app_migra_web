import pandas as pd
from utils.logger import log_message

def export_model_data(conn, model_name, selected_fields):
    try:
        # Obtener todos los registros del modelo
        record_ids = conn.search(model_name, [])
        if not record_ids:
            raise Exception("No hay registros en el modelo seleccionado.")

        # Leer los datos con los campos seleccionados
        data = conn.read(model_name, record_ids, selected_fields)
        if not data:
            raise Exception("No se obtuvieron datos del modelo.")

        return pd.DataFrame(data)

    except Exception as e:
        log_message(f"Error al exportar datos: {e}")
        raise
