# =============================================================================
# tests/test_tools.py — Tests unitarios para app/tools.py
# =============================================================================
"""
Tests unitarios para todas las herramientas del agente AutoFlota-AI.

Ejecutar:
    uv run pytest tests/test_tools.py -v
    uv run pytest tests/test_tools.py -v -k "test_csv"
"""
from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def variables_completas():
    """Variables completas de una solicitud para tests."""
    return {
        "cliente": {
            "nombre": "Empresa ABC S.A. de C.V.",
            "rfc": "EAB900101XYZ",
            "giro_empresa": "Manufactura industrial",
        },
        "broker": {
            "nombre": "Ana López Ramírez",
            "agencia": "Corredores del Valle",
            "clave_agente": "MTY-009",
        },
        "coberturas": [
            {"nombre": "RC Personas", "limite": "3000000", "deducible": ""},
            {"nombre": "RC Bienes", "limite": "1500000", "deducible": ""},
            {"nombre": "Daños Materiales", "limite": "valor_comercial", "deducible": "10%"},
        ],
        "prima": {"maxima_esperada": 320000, "moneda": "MXN", "forma_pago": "Anual"},
        "flotilla": {
            "total_vehiculos": 5,
            "vehiculos": [
                {"numero": 1, "marca": "Ford", "modelo": "F-150", "año": 2023,
                 "placas": "MTY-001", "tipo_uso": "Carga", "valor_comercial": 500000,
                 "moneda_valor": "MXN", "numero_serie": "1FTFW1ET0DFA12345",
                 "numero_motor": "M123", "version": "XLT", "tipo_vehiculo": "Pickup",
                 "conductores_habituales": 2},
            ],
        },
        "siniestros": {
            "total_siniestros": 1,
            "monto_total_pagado": 35000,
            "moneda_siniestros": "MXN",
            "periodo_reportado": "2022-2024",
        },
        "fechas": {
            "inicio_vigencia": "01/01/2025",
            "fin_vigencia": "31/12/2025",
            "devolucion_cotizacion": "20/12/2024",
            "vencimiento_cobertura_actual": "31/12/2024",
            "fecha_solicitud": "10/12/2024",
        },
        "condiciones_especiales": "Incluir cláusula de flotilla abierta",
        "notas_broker": "Cliente prioritario",
        "alertas": ["Verificar vigencia de licencias de conductores"],
        "confianza_extraccion": "alta",
        "fuente_documento": "/tmp/solicitud_test.pdf",
    }


@pytest.fixture
def variables_minimas():
    """Variables mínimas (solo campos obligatorios)."""
    return {
        "cliente": {"nombre": "Cliente Mínimo S.A.", "rfc": "", "giro_empresa": ""},
        "broker": {"nombre": "Broker Test"},
        "coberturas": [],
        "prima": {"maxima_esperada": None, "moneda": "MXN"},
        "flotilla": {"total_vehiculos": 2, "vehiculos": []},
        "siniestros": {"total_siniestros": None},
        "fechas": {},
        "alertas": [],
        "confianza_extraccion": "baja",
    }


# =============================================================================
# Tests: Generación de CSV
# =============================================================================

class TestGenerarReporteCSV:
    def test_genera_archivo_csv(self, variables_completas, tmp_path):
        """Verifica que se crea el archivo CSV."""
        from app.tools import generar_reporte_csv

        ruta = str(tmp_path / "output.csv")
        resultado = generar_reporte_csv(variables_completas, ruta)

        assert resultado["exito"] is True
        assert Path(ruta).exists()

    def test_csv_tiene_encabezados_en_espanol(self, variables_completas, tmp_path):
        """Verifica que los encabezados del CSV están en español."""
        from app.tools import generar_reporte_csv

        ruta = str(tmp_path / "output.csv")
        generar_reporte_csv(variables_completas, ruta)

        with open(ruta, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            columnas = reader.fieldnames or []

        # Verificar columnas en español
        assert "nombre_cliente" in columnas
        assert "nombre_broker" in columnas
        assert "prima_maxima_esperada" in columnas
        assert "fecha_inicio_vigencia" in columnas
        assert "numero_siniestros_3_anos" in columnas

    def test_csv_una_fila_por_vehiculo(self, variables_completas, tmp_path):
        """Verifica que hay una fila por vehículo."""
        from app.tools import generar_reporte_csv

        ruta = str(tmp_path / "output.csv")
        resultado = generar_reporte_csv(variables_completas, ruta)

        # La fixture tiene 1 vehículo en la lista
        assert resultado["total_filas"] == 1

    def test_csv_datos_cliente_correctos(self, variables_completas, tmp_path):
        """Verifica que los datos del cliente se escriben correctamente."""
        from app.tools import generar_reporte_csv

        ruta = str(tmp_path / "output.csv")
        generar_reporte_csv(variables_completas, ruta)

        with open(ruta, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            filas = list(reader)

        assert filas[0]["nombre_cliente"] == "Empresa ABC S.A. de C.V."
        assert filas[0]["rfc_cliente"] == "EAB900101XYZ"

    def test_csv_variables_minimas(self, variables_minimas, tmp_path):
        """Verifica que funciona con variables mínimas (sin vehículos)."""
        from app.tools import generar_reporte_csv

        ruta = str(tmp_path / "output_min.csv")
        resultado = generar_reporte_csv(variables_minimas, ruta)

        assert resultado["exito"] is True
        assert resultado["total_filas"] == 1  # Al menos una fila vacía

    def test_csv_contenido_string_generado(self, variables_completas, tmp_path):
        """Verifica que se genera contenido CSV como string."""
        from app.tools import generar_reporte_csv

        ruta = str(tmp_path / "output.csv")
        resultado = generar_reporte_csv(variables_completas, ruta)

        assert "contenido_csv" in resultado
        assert len(resultado["contenido_csv"]) > 0
        assert "nombre_cliente" in resultado["contenido_csv"]

    def test_csv_ruta_auto_generada(self, variables_completas):
        """Verifica que se genera una ruta automática si no se especifica."""
        from app.tools import generar_reporte_csv

        resultado = generar_reporte_csv(variables_completas)

        assert resultado["exito"] is True
        assert resultado["ruta_csv"].startswith("/tmp/")
        assert resultado["ruta_csv"].endswith(".csv")

        # Limpiar archivo generado
        Path(resultado["ruta_csv"]).unlink(missing_ok=True)

    def test_csv_codificacion_utf8_bom(self, variables_completas, tmp_path):
        """Verifica codificación UTF-8 con BOM para compatibilidad con Excel."""
        from app.tools import generar_reporte_csv

        ruta = str(tmp_path / "output_utf8.csv")
        generar_reporte_csv(variables_completas, ruta)

        # UTF-8 BOM empieza con \xef\xbb\xbf
        with open(ruta, "rb") as f:
            inicio = f.read(3)
        assert inicio == b"\xef\xbb\xbf", "El CSV debe usar UTF-8 con BOM"


# =============================================================================
# Tests: Funciones auxiliares internas
# =============================================================================

class TestFuncionesAuxiliares:
    def test_tablas_a_texto_lista_vacia(self):
        """Verifica que _tablas_a_texto maneja lista vacía."""
        from app.tools import _tablas_a_texto

        resultado = _tablas_a_texto([])
        assert resultado == ""

    def test_tablas_a_texto_con_datos(self):
        """Verifica conversión de tablas a texto."""
        from app.tools import _tablas_a_texto

        tablas = [[["Col1", "Col2"], ["Val1", "Val2"]]]
        resultado = _tablas_a_texto(tablas)

        assert "Col1" in resultado
        assert "Val1" in resultado

    def test_detectar_mime_type_pdf(self):
        """Verifica detección de MIME type para PDF."""
        from app.tools import _detectar_mime_type

        assert _detectar_mime_type("archivo.pdf") == "application/pdf"

    def test_detectar_mime_type_excel(self):
        """Verifica detección de MIME type para Excel."""
        from app.tools import _detectar_mime_type

        resultado = _detectar_mime_type("archivo.xlsx")
        assert "spreadsheet" in resultado or "excel" in resultado.lower()

    def test_detectar_mime_type_word(self):
        """Verifica detección de MIME type para Word."""
        from app.tools import _detectar_mime_type

        resultado = _detectar_mime_type("archivo.docx")
        assert "word" in resultado.lower() or "document" in resultado.lower()

    def test_detectar_mime_type_desconocido(self):
        """Verifica fallback para extensión desconocida."""
        from app.tools import _detectar_mime_type

        resultado = _detectar_mime_type("archivo.xyz123")
        assert resultado == "application/octet-stream"


# =============================================================================
# Tests: Lista de herramientas
# =============================================================================

class TestListaHerramientas:
    def test_todas_las_herramientas_son_callable(self):
        """Verifica que todas las herramientas son funciones invocables."""
        from app.tools import TODAS_LAS_HERRAMIENTAS

        for herramienta in TODAS_LAS_HERRAMIENTAS:
            assert callable(herramienta), f"{herramienta} no es callable"

    def test_herramientas_tienen_docstring(self):
        """Verifica que todas las herramientas tienen docstring."""
        from app.tools import TODAS_LAS_HERRAMIENTAS

        for herramienta in TODAS_LAS_HERRAMIENTAS:
            assert herramienta.__doc__, f"{herramienta.__name__} no tiene docstring"

    def test_numero_de_herramientas(self):
        """Verifica que hay al menos las herramientas esperadas."""
        from app.tools import TODAS_LAS_HERRAMIENTAS

        nombres = [h.__name__ for h in TODAS_LAS_HERRAMIENTAS]
        requeridas = [
            "leer_archivo_pdf",
            "leer_archivo_excel",
            "leer_archivo_word",
            "extraer_variables_solicitud",
            "generar_reporte_csv",
            "guardar_solicitud_base_de_datos",
            "buscar_historial_cliente",
            "subir_archivo_gcs",
        ]
        for nombre in requeridas:
            assert nombre in nombres, f"Herramienta faltante: {nombre}"
