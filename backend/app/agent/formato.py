from datetime import datetime

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def fecha_humana(dt: datetime) -> str:
    """'jueves 01/10 16:30'"""
    return f"{DIAS[dt.weekday()]} {dt:%d/%m %H:%M}"
