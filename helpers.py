def parse_float(valor, default=0.0):
    try:
        return float(valor)
    except (ValueError, TypeError):
        return default
