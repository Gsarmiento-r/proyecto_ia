# =============================================================================
# deployment/mlops/deploy.py — Script de despliegue manual a Cloud Run
# =============================================================================
"""
Script de despliegue manual del agente AutoFlota-AI a Google Cloud Run.

Uso:
    uv run python deployment/mlops/deploy.py build-and-push
    uv run python deployment/mlops/deploy.py deploy --imagen :v1.0.0
    uv run python deployment/mlops/deploy.py full-deploy
    uv run python deployment/mlops/deploy.py rollback --revision autos-ai-agent-00001
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

ROOT_DIR = Path(__file__).parent.parent.parent
console = Console()
app_cli = typer.Typer(name="deploy", help="Herramientas de despliegue para AutoFlota-AI")

# Configuración
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "autos-ai")
REGION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
APP_NAME = "autos-ai"
REPO_NAME = "autos-ai-repo"
IMAGE_NAME = "autos-ai-agent"
SERVICE_NAME = "autos-ai-agent"
REGISTRY = f"{REGION}-docker.pkg.dev/{PROJECT_ID}/{REPO_NAME}/{IMAGE_NAME}"


def _run(cmd: list[str], descripcion: str = "", check: bool = True) -> subprocess.CompletedProcess:
    """Ejecuta un comando de shell con logging."""
    console.print(f"[dim]▶ {' '.join(cmd)}[/dim]")
    result = subprocess.run(cmd, capture_output=False, text=True, check=check)
    if descripcion:
        estado = "✅" if result.returncode == 0 else "❌"
        console.print(f"{estado} {descripcion}")
    return result


@app_cli.command("build")
def build_image(
    tag: str = typer.Option("latest", help="Tag de la imagen"),
    plataforma: str = typer.Option("linux/amd64", help="Plataforma objetivo"),
):
    """Construye la imagen Docker localmente."""
    imagen_completa = f"{REGISTRY}:{tag}"
    console.print(Panel(f"Construyendo imagen: [bold]{imagen_completa}[/bold]"))

    _run([
        "docker", "build",
        f"--platform={plataforma}",
        f"--tag={imagen_completa}",
        "--progress=plain",
        str(ROOT_DIR),
    ], "Imagen construida")


@app_cli.command("push")
def push_image(tag: str = typer.Option("latest", help="Tag de la imagen")):
    """Sube la imagen a Artifact Registry."""
    imagen_completa = f"{REGISTRY}:{tag}"

    # Configurar auth de Docker para Artifact Registry
    _run(["gcloud", "auth", "configure-docker", f"{REGION}-docker.pkg.dev", "--quiet"],
         "Auth de Docker configurado")

    _run(["docker", "push", imagen_completa], f"Imagen subida: {imagen_completa}")


@app_cli.command("build-and-push")
def build_and_push(tag: str = typer.Option("latest", help="Tag de la imagen")):
    """Construye y sube la imagen en un solo paso."""
    build_image(tag=tag)
    push_image(tag=tag)


@app_cli.command("deploy")
def deploy_to_cloud_run(
    imagen: str = typer.Option(":latest", help="Tag de la imagen (ej: :latest, :v1.0.0)"),
    proyecto: str = typer.Option(PROJECT_ID),
    region: str = typer.Option(REGION),
    min_instances: int = typer.Option(1),
    max_instances: int = typer.Option(10),
    memoria: str = typer.Option("2Gi"),
    cpu: str = typer.Option("2"),
):
    """Despliega el agente a Cloud Run."""
    imagen_completa = f"{REGISTRY}{imagen}"
    console.print(Panel(
        f"[bold green]Desplegando AutoFlota-AI a Cloud Run[/bold green]\n\n"
        f"[cyan]Imagen:[/cyan] {imagen_completa}\n"
        f"[cyan]Servicio:[/cyan] {SERVICE_NAME}\n"
        f"[cyan]Región:[/cyan] {region}\n"
        f"[cyan]Proyecto:[/cyan] {proyecto}",
        title="Despliegue Cloud Run"
    ))

    _run([
        "gcloud", "run", "deploy", SERVICE_NAME,
        f"--image={imagen_completa}",
        f"--region={region}",
        f"--project={proyecto}",
        "--platform=managed",
        f"--memory={memoria}",
        f"--cpu={cpu}",
        f"--min-instances={min_instances}",
        f"--max-instances={max_instances}",
        "--timeout=300",
        "--concurrency=10",
        "--set-env-vars=APP_ENV=production",
        f"--service-account={APP_NAME}-sa@{proyecto}.iam.gserviceaccount.com",
        "--quiet",
    ], f"Servicio {SERVICE_NAME} desplegado")

    # Obtener URL del servicio
    result = subprocess.run([
        "gcloud", "run", "services", "describe", SERVICE_NAME,
        f"--region={region}",
        f"--project={proyecto}",
        "--format=value(status.url)",
    ], capture_output=True, text=True)

    if result.stdout.strip():
        url = result.stdout.strip()
        console.print(f"\n[bold green]🚀 Servicio disponible en:[/bold green] {url}")
        console.print(f"[dim]Health check: {url}/health[/dim]")
        console.print(f"[dim]Docs: {url}/docs[/dim]")


@app_cli.command("full-deploy")
def full_deploy(
    tag: str = typer.Option("latest", help="Tag de la imagen"),
):
    """Pipeline completo: build → push → deploy."""
    console.print(Panel("[bold]AutoFlota-AI — Full Deploy Pipeline[/bold]", border_style="blue"))
    build_and_push(tag=tag)
    deploy_to_cloud_run(imagen=f":{tag}")


@app_cli.command("rollback")
def rollback(
    revision: str = typer.Argument(help="Nombre de la revisión anterior"),
    proyecto: str = typer.Option(PROJECT_ID),
    region: str = typer.Option(REGION),
):
    """Hace rollback a una revisión anterior de Cloud Run."""
    console.print(f"[yellow]Haciendo rollback a: {revision}[/yellow]")
    _run([
        "gcloud", "run", "services", "update-traffic", SERVICE_NAME,
        f"--to-revisions={revision}=100",
        f"--region={region}",
        f"--project={proyecto}",
    ], f"Rollback a {revision} completado")


@app_cli.command("status")
def status(
    proyecto: str = typer.Option(PROJECT_ID),
    region: str = typer.Option(REGION),
):
    """Muestra el estado actual del servicio Cloud Run."""
    _run([
        "gcloud", "run", "services", "describe", SERVICE_NAME,
        f"--region={region}",
        f"--project={proyecto}",
        "--format=yaml",
    ])


if __name__ == "__main__":
    app_cli()
