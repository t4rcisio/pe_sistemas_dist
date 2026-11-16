"""Metadados locais da execução, sem nomes de usuário ou identificadores do dispositivo."""
import ctypes
from importlib.metadata import version
import os
import platform
import sys


def coletar():
    processador = platform.processor() or platform.machine()
    memoria_gib = None
    if os.name == "nt":
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as chave:
                processador = winreg.QueryValueEx(chave, "ProcessorNameString")[0].strip()
        except OSError:
            pass

        class Memoria(ctypes.Structure):
            _fields_ = [("tamanho", ctypes.c_ulong), ("carga", ctypes.c_ulong)] + [
                (nome, ctypes.c_ulonglong) for nome in
                ["total_fisica", "livre_fisica", "total_paginacao", "livre_paginacao",
                 "total_virtual", "livre_virtual", "livre_estendida"]]

        estado = Memoria()
        estado.tamanho = ctypes.sizeof(estado)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(estado)):
            memoria_gib = round(estado.total_fisica / 1024**3, 2)
    elif hasattr(os, "sysconf"):
        try:
            memoria_gib = round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024**3, 2)
        except (OSError, ValueError):
            pass
    return {
        "python": sys.version,
        "versao_python": platform.python_version(),
        "sistema": f"{platform.system()} {platform.release()}",
        "plataforma": platform.platform(),
        "arquitetura": platform.machine(),
        "processador": processador,
        "processadores_logicos": os.cpu_count(),
        "memoria_fisica_gib": memoria_gib,
        "bibliotecas": {pacote: version(pacote) for pacote in
                        ["numpy", "pandas", "scipy", "statsmodels", "matplotlib", "reportlab"]},
    }
