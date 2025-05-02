import pandas as pd
from utils.data_cleaner import limpiar_valor
from utils.logger import log_message

def import_records(df, conn, model_name, selected_fields, mode="create", search_field=None):
    model_fields = conn.get_fields(model_name, attributes=["type", "relation"])

    for _, row in df.iterrows():
        record = {}

        for field in selected_fields:
            if field in row and not pd.isna(row[field]):
                value = row[field]

                # Si es Many2one
                if model_fields.get(field, {}).get("type") == "many2one":
                    domain = [('name', '=', str(value))]
                    related_ids = conn.search(model_fields[field]['relation'], domain)
                    if related_ids:
                        value = related_ids[0]
                    else:
                        log_message(f"No se encontró Many2one para '{field}' con valor '{value}'")
                        continue

                record[field] = limpiar_valor(value)

        try:
            if mode == "create":
                conn.create(model_name, record)
                log_message(f"Registro creado: {record}")
            else:
                search_value = row.get(search_field)
                if pd.isna(search_value):
                    log_message(f"Fila ignorada. Campo '{search_field}' vacío.")
                    continue
                domain = [(search_field, "=", search_value)]
                ids = conn.search(model_name, domain)
                if ids:
                    conn.write(model_name, [ids[0]], record)
                    log_message(f"Registro actualizado ID {ids[0]}: {record}")
                else:
                    log_message(f"No encontrado para actualizar: {domain}")
        except Exception as e:
            log_message(f"Error con fila: {e}")
