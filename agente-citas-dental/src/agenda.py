import csv, unicodedata
from datetime import date, datetime, timedelta

RUTA_CSV = "citas.csv"
AHORA = datetime(2026, 11, 9, 8, 0)          # "ahora" simulado: lunes 9/11/2026, 08:00
FECHA_HOY = AHORA.date()
DURACION_MIN = 30
BLOQUES = [("09:00", "13:00"), ("15:00", "18:00")]   # lunes a viernes
CAMPOS = ["id_cita", "paciente", "ci", "telefono", "fecha", "hora", "motivo", "estado"]


# ---------- utilidades ----------
def _norm(texto: str) -> str:
    t = unicodedata.normalize("NFD", str(texto).lower().strip())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")

def _leer() -> list[dict]:
    with open(RUTA_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def _guardar(filas: list[dict]) -> None:
    with open(RUTA_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(filas)

def _parse_fecha(texto: str) -> date:
    try:
        return date.fromisoformat(texto.strip())
    except ValueError:
        raise ValueError(f"Fecha '{texto}' no válida. Usa el formato AAAA-MM-DD, por ejemplo 2026-11-12.")

def _parse_hora(texto: str) -> str:
    try:
        return datetime.strptime(texto.strip(), "%H:%M").strftime("%H:%M")
    except ValueError:
        raise ValueError(f"Hora '{texto}' no válida. Usa el formato HH:MM, por ejemplo 10:30.")

def _horarios_del_dia() -> list[str]:
    """Todos los inicios de cita posibles en un día de atención."""
    horas = []
    for inicio, fin in BLOQUES:
        t = datetime.strptime(inicio, "%H:%M")
        limite = datetime.strptime(fin, "%H:%M")
        while t + timedelta(minutes=DURACION_MIN) <= limite:
            horas.append(t.strftime("%H:%M"))
            t += timedelta(minutes=DURACION_MIN)
    return horas

def _ocupados(fecha: date, filas: list[dict], excepto_id: str | None = None) -> set[str]:
    return {f["hora"] for f in filas
            if f["fecha"] == fecha.isoformat() and f["estado"] == "confirmada" and f["id_cita"] != excepto_id}


# ---------- reglas de negocio (las valida el CÓDIGO, no el modelo) ----------
def validar_horario(fecha: date, hora: str, filas: list[dict], excepto_id: str | None = None) -> None:
    if fecha.weekday() >= 5:
        raise ValueError(f"La clínica no atiende sábados ni domingos ({fecha.isoformat()}).")
    if hora not in _horarios_del_dia():
        raise ValueError(f"{hora} está fuera del horario de atención. Atendemos lunes a viernes de 09:00 a 13:00 "
                         f"y de 15:00 a 18:00, en citas de {DURACION_MIN} minutos.")
    if datetime.combine(fecha, datetime.strptime(hora, "%H:%M").time()) <= AHORA:
        raise ValueError(f"No se puede agendar en el pasado ({fecha.isoformat()} {hora}).")
    if hora in _ocupados(fecha, filas, excepto_id):
        raise ValueError(f"El horario {fecha.isoformat()} {hora} ya está ocupado.")


# ---------- las 5 operaciones ----------
def buscar_citas_paciente(paciente_o_ci: str) -> list[dict]:
    consulta = _norm(paciente_o_ci)
    if len(consulta) < 3:
        raise ValueError("Indica el nombre completo o la cédula del paciente.")
    citas = [f for f in _leer() if consulta in _norm(f["paciente"]) or consulta == _norm(f["ci"])]
    if not citas:
        raise ValueError(f"No encontré citas para '{paciente_o_ci}'.")
    return sorted(citas, key=lambda f: (f["fecha"], f["hora"]))

def ver_disponibilidad(fecha: str) -> dict:
    d = _parse_fecha(fecha)
    if d.weekday() >= 5:
        raise ValueError(f"La clínica no atiende sábados ni domingos ({d.isoformat()}).")
    if d < FECHA_HOY:
        raise ValueError(f"{d.isoformat()} ya pasó.")
    ocupados = _ocupados(d, _leer())
    libres = [h for h in _horarios_del_dia()
              if h not in ocupados and datetime.combine(d, datetime.strptime(h, "%H:%M").time()) > AHORA]
    return {"fecha": d.isoformat(), "horarios_libres": libres, "duracion_min": DURACION_MIN}

def reservar_cita(paciente: str, ci: str, fecha: str, hora: str, motivo: str) -> dict:
    if len(paciente.strip()) < 3 or len(ci.strip()) < 5:
        raise ValueError("Faltan datos: se necesita el nombre completo y la cédula del paciente.")
    d, h = _parse_fecha(fecha), _parse_hora(hora)
    filas = _leer()
    validar_horario(d, h, filas)
    nuevo_id = f"C{max([int(f['id_cita'][1:]) for f in filas] + [0]) + 1:03d}"
    previo = next((f for f in filas if _norm(f["ci"]) == _norm(ci)), None)
    cita = {"id_cita": nuevo_id, "paciente": paciente.strip(), "ci": ci.strip(),
            "telefono": previo["telefono"] if previo else "sin_registrar",
            "fecha": d.isoformat(), "hora": h, "motivo": motivo.strip(), "estado": "confirmada"}
    filas.append(cita)
    _guardar(filas)
    return cita

def _cita_del_paciente(filas: list[dict], id_cita: str, ci: str) -> dict:
    cita = next((f for f in filas if f["id_cita"].upper() == id_cita.strip().upper()), None)
    if cita is None:
        raise ValueError(f"La cita {id_cita} no existe.")
    if _norm(cita["ci"]) != _norm(ci):
        raise ValueError(f"La cédula no coincide con la de la cita {id_cita}. No se puede modificar.")
    if cita["estado"] != "confirmada":
        raise ValueError(f"La cita {id_cita} está '{cita['estado']}': solo se modifican citas confirmadas.")
    return cita

def reprogramar_cita(id_cita: str, ci: str, nueva_fecha: str, nueva_hora: str) -> dict:
    d, h = _parse_fecha(nueva_fecha), _parse_hora(nueva_hora)
    filas = _leer()
    cita = _cita_del_paciente(filas, id_cita, ci)
    validar_horario(d, h, filas, excepto_id=cita["id_cita"])
    anterior = f"{cita['fecha']} {cita['hora']}"
    cita["fecha"], cita["hora"] = d.isoformat(), h
    _guardar(filas)
    return {**cita, "horario_anterior": anterior}

def cancelar_cita(id_cita: str, ci: str) -> dict:
    filas = _leer()
    cita = _cita_del_paciente(filas, id_cita, ci)
    cita["estado"] = "cancelada"
    _guardar(filas)
    return cita
import re

def _digitos(ci: str) -> str:
    return re.sub(r"\D", "", str(ci))

def _mismo_ci(a: str, b: str) -> bool:
    da, db = _digitos(a), _digitos(b)
    return len(da) >= 5 and da == db

def buscar_citas_paciente(paciente_o_ci: str) -> list[dict]:
    consulta = _norm(paciente_o_ci)
    if len(consulta) < 3:
        raise ValueError("Indica el nombre completo o la cédula del paciente.")
    citas = [f for f in _leer() if consulta in _norm(f["paciente"]) or _mismo_ci(consulta, f["ci"])]
    if not citas:
        raise ValueError(f"No encontré citas para '{paciente_o_ci}'.")
    return sorted(citas, key=lambda f: (f["fecha"], f["hora"]))

def reservar_cita(paciente: str, ci: str, fecha: str, hora: str, motivo: str) -> dict:
    if len(paciente.strip()) < 3 or len(_digitos(ci)) < 5:
        raise ValueError("Faltan datos: se necesita el nombre completo y la cédula del paciente.")
    d, h = _parse_fecha(fecha), _parse_hora(hora)
    filas = _leer()
    validar_horario(d, h, filas)
    nuevo_id = f"C{max([int(f['id_cita'][1:]) for f in filas] + [0]) + 1:03d}"
    previo = next((f for f in filas if _mismo_ci(f["ci"], ci)), None)
    cita = {"id_cita": nuevo_id, "paciente": paciente.strip(),
            "ci": previo["ci"] if previo else ci.strip(),          # conserva el formato ya registrado
            "telefono": previo["telefono"] if previo else "sin_registrar",
            "fecha": d.isoformat(), "hora": h, "motivo": motivo.strip(), "estado": "confirmada"}
    filas.append(cita)
    _guardar(filas)
    return cita

def _cita_del_paciente(filas: list[dict], id_cita: str, ci: str) -> dict:
    cita = next((f for f in filas if f["id_cita"].upper() == id_cita.strip().upper()), None)
    if cita is None:
        raise ValueError(f"La cita {id_cita} no existe.")
    if not _mismo_ci(cita["ci"], ci):
        raise ValueError(f"La cédula no coincide con la de la cita {id_cita}. No se puede modificar.")
    if cita["estado"] != "confirmada":
        raise ValueError(f"La cita {id_cita} está '{cita['estado']}': solo se modifican citas confirmadas.")
    return cita
