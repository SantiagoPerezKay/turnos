from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.services.availability import Franja, calcular_slots

TZ = ZoneInfo("America/Argentina/Buenos_Aires")
LUNES = date(2026, 10, 5)


def _slots(**kw):
    base = dict(
        franjas=[Franja(0, time(9), time(12))],
        ocupados=[],
        duracion=timedelta(minutes=30),
        intervalo=timedelta(minutes=30),
        desde=LUNES,
        hasta=LUNES,
        ahora=datetime(2026, 10, 1, 10, 0, tzinfo=TZ),
        anticipacion=timedelta(hours=1),
        tz=TZ,
    )
    base.update(kw)
    return [f"{i:%H:%M}" for i, _ in calcular_slots(**base)]


def test_franja_completa():
    assert _slots() == ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30"]


def test_servicio_largo_no_se_pasa_del_cierre():
    assert _slots(duracion=timedelta(minutes=90)) == ["09:00", "09:30", "10:00", "10:30"]


def test_excluye_turnos_ocupados_y_superpuestos():
    ocupado = (datetime(2026, 10, 5, 10, 0, tzinfo=TZ), datetime(2026, 10, 5, 10, 45, tzinfo=TZ))
    assert _slots(ocupados=[ocupado]) == ["09:00", "09:30", "11:00", "11:30"]


def test_respeta_anticipacion_minima():
    ahora = datetime(2026, 10, 5, 9, 50, tzinfo=TZ)
    assert _slots(ahora=ahora) == ["11:00", "11:30"]


def test_solo_dias_con_franja():
    assert _slots(desde=LUNES + timedelta(days=1), hasta=LUNES + timedelta(days=6)) == []


def test_ocupado_en_utc_se_compara_bien():
    ocupado_utc = (
        datetime(2026, 10, 5, 12, 0, tzinfo=ZoneInfo("UTC")),  # 09:00 en Buenos Aires
        datetime(2026, 10, 5, 12, 30, tzinfo=ZoneInfo("UTC")),
    )
    assert "09:00" not in _slots(ocupados=[ocupado_utc])
