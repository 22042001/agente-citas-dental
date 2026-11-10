# Lanzador: importa el servidor y lo ejecuta por stdio (entrada y salida estándar).
from servidor_clinica import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
