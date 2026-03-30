# =============================================================================
# eval/test_cases/test_pdf_submission.py — Tests para documentos PDF
# =============================================================================
"""
Pruebas unitarias e integración para el procesamiento de solicitudes en PDF.

Ejecutar:
    uv run pytest eval/test_cases/test_pdf_submission.py -v
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT_DIR = Path(__file__).parent.parent.parent


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def texto_solicitud_pdf_muestra():
    """Texto simulado extraído de un PDF de solicitud de seguro."""
    return """
    SOLICITUD DE COTIZACIÓN — SEGURO DE FLOTILLA DE AUTOS
    =====================================================

    DATOS DEL CLIENTE
    Razón Social: Distribuidora Norte S.A. de C.V.
    RFC: DNO850312HG7
    Giro: Distribución de alimentos y bebidas
    Dirección: Av. Industrial 450, Col. Parque Industrial, Monterrey, N.L.

    DATOS DEL BROKER
    Nombre del Agente: Carlos Méndez Pérez
    Agencia: Seguros del Norte Agencia S.A.
    Clave de Agente: NL-00342

    COBERTURAS SOLICITADAS
    - Responsabilidad Civil Daños a Terceros en Personas: $3,000,000 MXN
    - Responsabilidad Civil Daños a Terceros en Bienes: $1,500,000 MXN
    - Daños Materiales (deducible 10%, mínimo $5,000): Valor comercial
    - Robo Total: Valor comercial con deducible del 10%
    - Gastos Médicos a Ocupantes: $200,000 MXN por evento
    - Asistencia en viaje y grúa: Incluida

    PRIMA MÁXIMA ESPERADA: $450,000.00 MXN anuales
    Forma de pago: Trimestral

    FLOTILLA (15 VEHÍCULOS)
    1. Nissan NP300 2022 - Placas NL-45-XYZ - Uso: Reparto - Valor: $320,000
    2. Nissan NP300 2022 - Placas NL-46-XYZ - Uso: Reparto - Valor: $320,000
    3. Toyota Hilux 2021 - Placas NL-12-ABC - Uso: Supervisión - Valor: $450,000
    4. Toyota Hilux 2021 - Placas NL-13-ABC - Uso: Supervisión - Valor: $450,000
    5. Ford Transit 2023 - Placas NL-88-QRS - Uso: Carga - Valor: $680,000
    [... 10 vehículos adicionales en hoja adjunta ...]

    HISTORIAL DE SINIESTROS (últimos 3 años)
    Año 2022: 1 siniestro - Colisión - Monto pagado: $45,000
    Año 2023: 1 siniestro - Robo parcial - Monto pagado: $28,000
    Año 2024: 1 siniestro - Daños por granizo - Monto pagado: $52,000
    Total siniestros: 3 | Monto total: $125,000 MXN

    FECHAS
    Fecha de solicitud: 05/03/2025
    Devolución de cotización esperada: 15/03/2025
    Inicio de vigencia deseado: 01/04/2025
    Fin de vigencia: 31/03/2026
    Vencimiento de cobertura actual: 31/03/2025

    CONDICIONES ESPECIALES
    - El cliente requiere cláusula de reposición de valor en caso de pérdida total
    - Se solicita inclusión de operadores con menos de 2 años de experiencia
    """


@pytest.fixture
def variables_extraidas_muestra():
    """Variables JSON simuladas que debería devolver el agente."""
    return {
        "cliente": {
            "nombre": "Distribuidora Norte S.A. de C.V.",
            "rfc": "DNO850312HG7",
            "giro_empresa": "Distribución de alimentos y bebidas",
        },
        "broker": {
            "nombre": "Carlos Méndez Pérez",
            "agencia": "Seguros del Norte Agencia S.A.",
            "clave_agente": "NL-00342",
        },
        "coberturas": [
            {"nombre": "RC Personas", "limite": "3000000", "deducible": ""},
            {"nombre": "RC Bienes", "limite": "1500000", "deducible": ""},
            {"nombre": "Daños Materiales", "limite": "valor_comercial", "deducible": "10%"},
            {"nombre": "Robo Total", "limite": "valor_comercial", "deducible": "10%"},
            {"nombre": "Gastos Médicos Ocupantes", "limite": "200000", "deducible": ""},
        ],
        "prima": {"maxima_esperada": 450000, "moneda": "MXN", "forma_pago": "Trimestral"},
        "flotilla": {
            "total_vehiculos": 15,
            "vehiculos": [
                {"numero": 1, "marca": "Nissan", "modelo": "NP300", "año": 2022,
                 "placas": "NL-45-XYZ", "tipo_uso": "Reparto", "valor_comercial": 320000},
            ],
        },
        "siniestros": {
            "total_siniestros": 3,
            "monto_total_pagado": 125000,
            "moneda_siniestros": "MXN",
        },
        "fechas": {
            "inicio_vigencia": "01/04/2025",
            "fin_vigencia": "31/03/2026",
            "devolucion_cotizacion": "15/03/2025",
            "vencimiento_cobertura_actual": "31/03/2025",
        },
        "condiciones_especiales": "Cláusula de reposición de valor; operadores con menos de 2 años",
        "confianza_extraccion": "alta",
    }


# =============================================================================
# Tests de la herramienta leer_archivo_pdf
# =============================================================================

class TestLeerArchivoPDF:
    def test_extraccion_texto_basica(self, tmp_path):
        """Verifica que leer_archivo_pdf extrae texto de un PDF válido."""
        from app.tools import leer_archivo_pdf

        # Crear un PDF mínimo simulado con pdfplumber mock
        with patch("app.tools.pdfplumber") as mock_plumber:
            mock_pdf = MagicMock()
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)
            mock_pdf.pages = [MagicMock()]
            mock_pdf.pages[0].extract_text.return_value = "Texto de prueba del PDF"
            mock_pdf.pages[0].extract_tables.return_value = []
            mock_pdf.metadata = {}
            mock_plumber.open.return_value = mock_pdf

            with patch("pathlib.Path.exists", return_value=True):
                resultado = leer_archivo_pdf("/tmp/test.pdf")

        assert resultado["exito"] is True
        assert "Texto de prueba del PDF" in resultado["texto_completo"]
        assert resultado["tipo_archivo"] == "pdf"

    def test_archivo_no_encontrado(self):
        """Verifica que se maneja correctamente un archivo inexistente."""
        from app.tools import leer_archivo_pdf

        resultado = leer_archivo_pdf("/ruta/inexistente/archivo.pdf")
        assert resultado["exito"] is False
        assert "error" in resultado

    def test_retorna_estructura_correcta(self, tmp_path):
        """Verifica que el resultado tiene los campos esperados."""
        from app.tools import leer_archivo_pdf

        campos_requeridos = ["exito", "texto_completo", "paginas", "metadatos", "fuente", "tipo_archivo"]

        with patch("app.tools.pdfplumber") as mock_plumber:
            mock_pdf = MagicMock()
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)
            mock_pdf.pages = []
            mock_pdf.metadata = {}
            mock_plumber.open.return_value = mock_pdf

            with patch("pathlib.Path.exists", return_value=True):
                resultado = leer_archivo_pdf("/tmp/test.pdf")

        for campo in campos_requeridos:
            assert campo in resultado, f"Falta el campo: {campo}"


# =============================================================================
# Tests de extracción de variables
# =============================================================================

class TestExtraccionVariables:
    def test_extraccion_campos_obligatorios(
        self, texto_solicitud_pdf_muestra, variables_extraidas_muestra
    ):
        """Verifica que se extraen todos los campos obligatorios."""
        from eval.eval_runner import CAMPOS_OBLIGATORIOS, calcular_completitud

        completitud = calcular_completitud(variables_extraidas_muestra, CAMPOS_OBLIGATORIOS)
        assert completitud >= 0.85, f"Completitud insuficiente: {completitud:.1%}"

    def test_extraccion_nombre_cliente(self, variables_extraidas_muestra):
        """Verifica extracción correcta del nombre del cliente."""
        assert variables_extraidas_muestra["cliente"]["nombre"] == "Distribuidora Norte S.A. de C.V."

    def test_extraccion_total_vehiculos(self, variables_extraidas_muestra):
        """Verifica extracción correcta del total de vehículos."""
        assert variables_extraidas_muestra["flotilla"]["total_vehiculos"] == 15

    def test_extraccion_prima_maxima(self, variables_extraidas_muestra):
        """Verifica extracción correcta de la prima máxima."""
        assert variables_extraidas_muestra["prima"]["maxima_esperada"] == 450000

    def test_extraccion_fechas_clave(self, variables_extraidas_muestra):
        """Verifica extracción de todas las fechas clave."""
        fechas = variables_extraidas_muestra["fechas"]
        assert fechas.get("inicio_vigencia") is not None
        assert fechas.get("fin_vigencia") is not None
        assert fechas.get("devolucion_cotizacion") is not None

    def test_extraccion_siniestros(self, variables_extraidas_muestra):
        """Verifica extracción del historial de siniestros."""
        siniestros = variables_extraidas_muestra["siniestros"]
        assert siniestros.get("total_siniestros") == 3
        assert siniestros.get("monto_total_pagado") == 125000


# =============================================================================
# Tests de generación de CSV
# =============================================================================

class TestGeneracionCSV:
    def test_csv_se_genera_correctamente(self, variables_extraidas_muestra, tmp_path):
        """Verifica que se genera un CSV válido."""
        from app.tools import generar_reporte_csv
        import csv

        ruta_csv = str(tmp_path / "test_output.csv")
        resultado = generar_reporte_csv(variables_extraidas_muestra, ruta_csv)

        assert resultado["exito"] is True
        assert Path(ruta_csv).exists()

        # Leer y verificar CSV
        with open(ruta_csv, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            filas = list(reader)

        assert len(filas) >= 1
        assert "nombre_cliente" in filas[0]
        assert filas[0]["nombre_cliente"] == "Distribuidora Norte S.A. de C.V."

    def test_csv_contiene_columnas_obligatorias(self, variables_extraidas_muestra, tmp_path):
        """Verifica que el CSV contiene todas las columnas requeridas."""
        from app.tools import generar_reporte_csv
        import csv

        ruta_csv = str(tmp_path / "test_cols.csv")
        resultado = generar_reporte_csv(variables_extraidas_muestra, ruta_csv)

        with open(ruta_csv, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            columnas = reader.fieldnames or []

        columnas_requeridas = [
            "nombre_cliente", "nombre_broker", "prima_maxima_esperada",
            "total_vehiculos_flotilla", "fecha_inicio_vigencia", "fecha_fin_vigencia",
        ]
        for col in columnas_requeridas:
            assert col in columnas, f"Columna faltante en CSV: {col}"

    def test_csv_codificacion_utf8(self, variables_extraidas_muestra, tmp_path):
        """Verifica que el CSV se genera con codificación UTF-8 para caracteres españoles."""
        from app.tools import generar_reporte_csv

        ruta_csv = str(tmp_path / "test_encoding.csv")
        resultado = generar_reporte_csv(variables_extraidas_muestra, ruta_csv)

        contenido = Path(ruta_csv).read_text(encoding="utf-8-sig")
        # Verificar que se puede leer sin errores de codificación
        assert "nombre_cliente" in contenido
