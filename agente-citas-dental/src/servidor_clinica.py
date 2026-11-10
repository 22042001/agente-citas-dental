from mcp.server.fastmcp import FastMCP
import agenda

mcp = FastMCP("Clinica Dental Sonrisa", log_level="WARNING")


@mcp.tool()
def buscar_citas_paciente(paciente_o_ci: str) -> list[dict]:
    """Busca las citas de un paciente (pasadas, futuras y canceladas) por nombre o por cédula.
    Devuelve id_cita, paciente, fecha (AAAA-MM-DD), hora (HH:MM), motivo y estado.
    Falla si no hay ningún paciente que coincida."""
    return agenda.buscar_citas_paciente(paciente_o_ci)


@mcp.tool()
def ver_disponibilidad(fecha: str) -> dict:
    """Lista los horarios libres de un día. 'fecha' en formato AAAA-MM-DD.
    Atendemos de lunes a viernes. Falla si es fin de semana o una fecha pasada."""
    return agenda.ver_disponibilidad(fecha)


@mcp.tool()
def reservar_cita(paciente: str, ci: str, fecha: str, hora: str, motivo: str) -> dict:
    """Reserva una cita nueva. Requiere nombre completo, cédula, fecha (AAAA-MM-DD), hora (HH:MM) y motivo.
    Falla si el horario está ocupado, fuera de atención o en el pasado."""
    return agenda.reservar_cita(paciente, ci, fecha, hora, motivo)


@mcp.tool()
def reprogramar_cita(id_cita: str, ci: str, nueva_fecha: str, nueva_hora: str) -> dict:
    """Cambia la fecha y hora de una cita confirmada existente. Requiere el id_cita y la cédula del paciente.
    Falla si la cita no existe, no es del paciente, no está confirmada o el nuevo horario no es válido."""
    return agenda.reprogramar_cita(id_cita, ci, nueva_fecha, nueva_hora)


@mcp.tool()
def cancelar_cita(id_cita: str, ci: str) -> dict:
    """Cancela una cita confirmada. Requiere el id_cita y la cédula del paciente. Acción sin vuelta atrás.
    Falla si la cita no existe, no es del paciente o ya está cancelada."""
    return agenda.cancelar_cita(id_cita, ci)
