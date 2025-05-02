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


def import_records(df, conn, model_name, selected_fields, mode="create", search_field=None):
    """
    Importa registros desde un archivo Excel a Odoo.
    """
    model_fields = conn.get_fields(model_name, attributes=["type", "relation"])

    for _, row in df.iterrows():
        record = {}

        for field in selected_fields:
            if field in row and not pd.isna(row[field]):
                value = row[field]

                # Obtener el tipo de campo de Odoo
                field_type = model_fields.get(field, {}).get('type')

                # Convertir el valor al tipo correcto según el campo
                value = convert_to_correct_type(value, field_type, model_fields.get(field, {}), conn)

                if value is None:
                    log_message_streamlit(f"Valor inválido para el campo '{field}': {row[field]}")
                    continue  # Saltamos esta fila si el valor no es válido

                record[field] = limpiar_valor(value)

        try:
            if mode == "create":
                result = conn.create(model_name, record)
                log_message_streamlit(f"Registro creado: {record}. Resultado: {result}")
            else:
                search_value = row.get(search_field)
                if pd.isna(search_value):
                    log_message_streamlit(f"Fila ignorada. Campo '{search_field}' vacío.")
                    continue
                domain = [(search_field, "=", search_value)]
                ids = conn.search(model_name, domain)
                if ids:
                    result = conn.write(model_name, [ids[0]], record)
                    log_message_streamlit(f"Registro actualizado ID {ids[0]}: {record}. Resultado: {result}")
                else:
                    log_message_streamlit(f"No encontrado para actualizar: {domain}")
        except Exception as e:
            log_message_streamlit(f"Error con fila: {e}")
