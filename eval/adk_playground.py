# =============================================================================
# eval/adk_playground.py — Lanzador del ADK Web Playground
# =============================================================================
"""
Inicia el playground web de Google ADK para probar el agente AutoFlota-AI
de forma interactiva en el navegador.

Uso:
    # Opción 1: usando adk directamente (recomendado)
    adk web app/ --port 8080

    # Opción 2: usando este script
    uv run python eval/adk_playground.py

    # Opción 3: con parámetros personalizados
    uv run python eval/adk_playground.py --puerto 9000 --host 0.0.0.0

Accede al playground en: http://localhost:8080
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import typer
import vertexai
from rich.console import Console
from rich.panel import Panel

ROOT_DIR = Path(__file__).parent.parent
console = Console()
app_cli = typer.Typer()


@app_cli.command()
def iniciar_playground(
    puerto: int = typer.Option(8080, "--puerto", "-p", help="Puerto del servidor web"),
    host: str = typer.Option("localhost", "--host", "-h", help="Host del servidor"),
    agente_dir: Path = typer.Option(ROOT_DIR / "app", help="Directorio del agente"),
    recargar: bool = typer.Option(True, help="Recargar automáticamente al cambiar código"),
):
    """
    Inicia el ADK Web Playground para pruebas interactivas del agente AutoFlota-AI.
    """
    # Validar que el directorio del agente existe
    if not agente_dir.exists():
        console.print(f"[red]Error: El directorio {agente_dir} no existe.[/red]")
        raise typer.Exit(1)

    if not (agente_dir / "agent.py").exists():
        console.print(f"[red]Error: No se encontró agent.py en {agente_dir}.[/red]")
        raise typer.Exit(1)

    # Verificar variables de entorno
    proyecto = os.getenv("GOOGLE_CLOUD_PROJECT", "autos-ai")
    ubicacion = os.getenv("GOOGLE_CLOUD_LOCATION", "us-eastl1")
    modelo = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")

    console.print(Panel(
        f"[bold green]AutoFlota-AI — ADK Web Playground[/bold green]\n\n"
        f"[cyan]Proyecto GCP:[/cyan] {proyecto}\n"
        f"[cyan]Ubicación:[/cyan] {ubicacion}\n"
        f"[cyan]Modelo:[/cyan] {modelo}\n"
        f"[cyan]Agente:[/cyan] {agente_dir}\n\n"
        f"[bold]URL del playground:[/bold] http://{host}:{puerto}\n\n"
        f"[yellow]Para detener: Ctrl+C[/yellow]",
        title="Iniciando Playground",
        border_style="green",
    ))

    # Construir comando ADK web
    cmd = [
        "adk", "web",
        str(agente_dir),
        "--port", str(puerto),
        "--host", host,
    ]

    console.print(f"[dim]Comando: {' '.join(cmd)}[/dim]\n")

    # Ejecutar
    try:
        os.chdir(ROOT_DIR)  # Asegurar que el CWD es el root del proyecto
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]Error al iniciar el playground: {exc}[/red]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Playground detenido por el usuario.[/yellow]")
    except FileNotFoundError:
        console.print(
            "[red]Error: 'adk' no está instalado. "
            "Ejecuta: uv add google-adk[/red]"
        )
        raise typer.Exit(1)


@app_cli.command("listar-sesiones")
def listar_sesiones():
    """Lista las sesiones activas del playground."""
    import httpx
    try:
        resp = httpx.get("http://localhost:8000/list-apps", timeout=5)
        console.print(resp.json())
    except Exception as exc:
        console.print(f"[yellow]Playground no disponible: {exc}[/yellow]")


if __name__ == "__main__":
    app_cli()
