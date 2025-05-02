import logging

def safe_decode(value):
    try:
        if isinstance(value, bytes):
            return value.decode('utf-8', errors='replace')
        elif isinstance(value, str):
            return value
        else:
            return str(value)
    except Exception as e:
        logging.error(f"Error al decodificar valor: {value}. Detalle del error: {e}")
        return "�"  # Carácter de reemplazo estándar
