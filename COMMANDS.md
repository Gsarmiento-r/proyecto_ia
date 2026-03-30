# COMMANDS.md — Guía Completa de Comandos

Referencia de todos los comandos necesarios para iniciar, desarrollar, probar y desplegar **AutoFlota-AI** en Google Cloud.

---

## ÍNDICE

1. [Configuración Inicial del Entorno](#1-configuración-inicial-del-entorno)
2. [Gestión de Dependencias con UV](#2-gestión-de-dependencias-con-uv)
3. [Ejecución en Desarrollo](#3-ejecución-en-desarrollo)
4. [Tests y Evaluación](#4-tests-y-evaluación)
5. [Google Cloud — Autenticación y Setup](#5-google-cloud--autenticación-y-setup)
6. [Infraestructura con Terraform](#6-infraestructura-con-terraform)
7. [Docker y Contenedores](#7-docker-y-contenedores)
8. [Despliegue a Google Cloud Run](#8-despliegue-a-google-cloud-run)
9. [Monitoreo y Operaciones](#9-monitoreo-y-operaciones)
10. [Pipeline MLOps](#10-pipeline-mlops)
11. [Git y Control de Versiones](#11-git-y-control-de-versiones)

---

## 1. Configuración Inicial del Entorno

### Instalar UV (gestor de paquetes Python)
```bash
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verificar instalación
uv --version
```

### Clonar y configurar el proyecto
```bash
# Clonar repositorio
git clone https://github.com/tu-org/autos-ai.git
cd autos-ai

# Copiar y configurar variables de entorno
cp .env.example .env
# Editar .env con tus valores:
#   GOOGLE_CLOUD_PROJECT=autos-ai
#   GEMINI_MODEL=gemini-2.0-flash-001
#   etc.
```

---

## 2. Gestión de Dependencias con UV

```bash
# Crear entorno virtual e instalar dependencias de producción
uv sync

# Instalar dependencias incluyendo las de desarrollo
uv sync --dev

# Instalar dependencias desde cero (regenerar lock file)
uv sync --frozen

# Agregar una nueva dependencia
uv add nombre-paquete

# Agregar dependencia de desarrollo
uv add --dev nombre-paquete

# Eliminar una dependencia
uv remove nombre-paquete

# Ver el entorno virtual creado
uv env info

# Actualizar todas las dependencias
uv sync --upgrade

# Exportar requirements.txt (para compatibilidad)
uv export --format requirements-txt > requirements.txt

# Ejecutar un comando dentro del entorno virtual
uv run python script.py
uv run pytest
```

---

## 3. Ejecución en Desarrollo

### ADK Web Playground (recomendado para pruebas interactivas)
```bash
# Iniciar el playground en http://localhost:8000
adk web app/

# Con puerto personalizado
adk web app/ --port 9000

# Via script de playground
uv run python eval/adk_playground.py --puerto 8000

# Modo verbose con hot-reload
adk web app/ --port 8000 --host 0.0.0.0
```

### ADK en línea de comandos
```bash
# Ejecutar el agente en modo interactivo (terminal)
adk run app/

# Enviar un mensaje directo al agente
adk run app/ --message "Analiza el documento en: /tmp/solicitud.pdf"
```

### Servidor FastAPI
```bash
# Desarrollo con hot-reload
uv run python -m app.main

# O usando uvicorn directamente
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# Producción (sin reload)
uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 4

# Verificar que el servidor está corriendo
curl http://localhost:8080/health
curl http://localhost:8080/docs
```

### Docker Compose (entorno local completo)
```bash
# Iniciar todos los servicios
docker-compose up --build

# Solo el agente
docker-compose up autos-ai-agent

# Con playground ADK
docker-compose --profile dev up

# Con emulador de Firestore (sin GCP real)
docker-compose --profile emulators up

# En segundo plano
docker-compose up -d

# Ver logs
docker-compose logs -f autos-ai-agent

# Detener
docker-compose down
```

---

## 4. Tests y Evaluación

### Ejecutar tests
```bash
# Todos los tests
uv run pytest -v

# Tests unitarios del agente
uv run pytest tests/test_agent.py -v

# Tests de herramientas
uv run pytest tests/test_tools.py -v

# Tests de evaluación por tipo de archivo
uv run pytest eval/test_cases/test_pdf_submission.py -v
uv run pytest eval/test_cases/test_excel_submission.py -v
uv run pytest eval/test_cases/test_word_submission.py -v

# Tests con cobertura
uv run pytest --cov=app --cov-report=term-missing

# Tests con reporte HTML de cobertura
uv run pytest --cov=app --cov-report=html
# Abre: htmlcov/index.html

# Tests en paralelo (más rápido)
uv run pytest -n auto

# Ejecutar un test específico
uv run pytest tests/test_tools.py::TestGenerarReporteCSV::test_genera_archivo_csv -v

# Solo tests marcados (ej: integración)
uv run pytest -m integration
```

### Evaluación del agente (requiere GCP)
```bash
# Evaluación completa contra todos los casos de ground truth
uv run python eval/eval_runner.py

# Evaluación con reporte personalizado
uv run python eval/eval_runner.py --reporte reportes/eval_prod_v1.json

# Ver el último reporte generado
ls -lt eval/reportes/ | head -5
cat eval/reportes/eval_$(date +%Y%m%d_*)*.json | python -m json.tool
```

### Linting y calidad de código
```bash
# Ruff (linter y formatter)
uv run ruff check app/
uv run ruff check app/ --fix    # Auto-fix
uv run ruff format app/         # Format
uv run ruff format app/ --check # Solo verificar

# Mypy (type checking)
uv run mypy app/

# Black (formatter alternativo)
uv run black app/ --check
uv run black app/
```

---

## 5. Google Cloud — Autenticación y Setup

### Autenticación
```bash
# Autenticación de usuario (para desarrollo local)
gcloud auth login
gcloud auth application-default login

# Configurar proyecto
gcloud config set project autos-ai
gcloud config set compute/region us-central1

# Verificar configuración actual
gcloud config list
gcloud auth list

# Usar cuenta de servicio (para CI/CD o producción)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS
```

### Habilitar APIs necesarias
```bash
gcloud services enable \
  run.googleapis.com \
  aiplatform.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  documentai.googleapis.com \
  bigquery.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  --project=autos-ai
```

### Crear cuenta de servicio
```bash
# Crear cuenta de servicio
gcloud iam service-accounts create autos-ai-sa \
  --display-name="AutoFlota-AI Service Account" \
  --project=autos-ai

# Asignar roles necesarios
for ROLE in \
  "roles/aiplatform.user" \
  "roles/datastore.user" \
  "roles/storage.objectAdmin" \
  "roles/bigquery.dataEditor" \
  "roles/bigquery.jobUser" \
  "roles/documentai.apiUser" \
  "roles/secretmanager.secretAccessor"; do
  gcloud projects add-iam-policy-binding autos-ai \
    --member="serviceAccount:autos-ai-sa@autos-ai.iam.gserviceaccount.com" \
    --role="$ROLE"
done

# Crear y descargar clave
gcloud iam service-accounts keys create credentials/service-account.json \
  --iam-account=autos-ai-sa@autos-ai.iam.gserviceaccount.com
```

### Crear buckets GCS
```bash
# Bucket de solicitudes (input)
gsutil mb -p autos-ai -l us-central1 gs://autos-ai-submissions

# Bucket de outputs (CSV)
gsutil mb -p autos-ai -l us-central1 gs://autos-ai-outputs

# Bucket de estado Terraform
gsutil mb -p autos-ai -l us-central1 gs://autos-ai-terraform-state

# Habilitar versionado
gsutil versioning set on gs://autos-ai-submissions
gsutil versioning set on gs://autos-ai-outputs
```

### Crear base de datos Firestore
```bash
gcloud firestore databases create \
  --location=us-central \
  --type=firestore-native \
  --project=autos-ai
```

### Crear repositorio en Artifact Registry
```bash
gcloud artifacts repositories create autos-ai-repo \
  --repository-format=docker \
  --location=us-central1 \
  --description="Imágenes Docker para AutoFlota-AI" \
  --project=autos-ai

# Configurar autenticación Docker
gcloud auth configure-docker us-central1-docker.pkg.dev
```

---

## 6. Infraestructura con Terraform

```bash
cd infra/

# Copiar y configurar variables
cp terraform.tfvars.example terraform.tfvars
# Editar terraform.tfvars con tus valores

# Inicializar Terraform (descarga providers)
terraform init

# Validar configuración
terraform validate

# Ver plan de cambios
terraform plan -var-file=terraform.tfvars

# Guardar plan en archivo
terraform plan -var-file=terraform.tfvars -out=tfplan

# Aplicar infraestructura
terraform apply -var-file=terraform.tfvars

# Aplicar plan guardado (sin confirmación)
terraform apply tfplan

# Ver outputs
terraform output

# Ver URL del servicio Cloud Run
terraform output cloud_run_url

# Destruir infraestructura (¡CON CUIDADO!)
terraform destroy -var-file=terraform.tfvars

# Formatear archivos Terraform
terraform fmt -recursive

# Actualizar providers
terraform init -upgrade

cd ..
```

---

## 7. Docker y Contenedores

```bash
# Build de imagen de producción
docker build \
  --platform linux/amd64 \
  --tag us-central1-docker.pkg.dev/autos-ai/autos-ai-repo/autos-ai-agent:latest \
  --tag us-central1-docker.pkg.dev/autos-ai/autos-ai-repo/autos-ai-agent:v1.0.0 \
  .

# Build de imagen de desarrollo (con código montado)
docker build --target builder -t autos-ai-dev .

# Correr contenedor localmente
docker run -p 8080:8080 \
  --env-file .env \
  -v $(pwd)/credentials:/app/credentials:ro \
  us-central1-docker.pkg.dev/autos-ai/autos-ai-repo/autos-ai-agent:latest

# Push a Artifact Registry
docker push us-central1-docker.pkg.dev/autos-ai/autos-ai-repo/autos-ai-agent:latest
docker push us-central1-docker.pkg.dev/autos-ai/autos-ai-repo/autos-ai-agent:v1.0.0

# Ver imágenes disponibles en Artifact Registry
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/autos-ai/autos-ai-repo \
  --project=autos-ai

# Escanear vulnerabilidades
gcloud artifacts docker images scan \
  us-central1-docker.pkg.dev/autos-ai/autos-ai-repo/autos-ai-agent:latest \
  --project=autos-ai

# Limpiar imágenes locales
docker image prune -f
docker system prune -f
```

---

## 8. Despliegue a Google Cloud Run

### Via script de despliegue
```bash
# Build y push
uv run python deployment/mlops/deploy.py build-and-push --tag v1.0.0

# Solo despliegue (imagen ya existente)
uv run python deployment/mlops/deploy.py deploy --imagen :v1.0.0

# Pipeline completo (build + push + deploy)
uv run python deployment/mlops/deploy.py full-deploy --tag v1.0.0

# Ver estado del servicio
uv run python deployment/mlops/deploy.py status

# Rollback a revisión anterior
uv run python deployment/mlops/deploy.py rollback autos-ai-agent-00003-xyz
```

### Via gcloud directo
```bash
# Desplegar servicio
gcloud run deploy autos-ai-agent \
  --image=us-central1-docker.pkg.dev/autos-ai/autos-ai-repo/autos-ai-agent:latest \
  --region=us-central1 \
  --project=autos-ai \
  --memory=2Gi \
  --cpu=2 \
  --min-instances=1 \
  --max-instances=10 \
  --timeout=300 \
  --service-account=autos-ai-sa@autos-ai.iam.gserviceaccount.com

# Ver URL del servicio
gcloud run services describe autos-ai-agent \
  --region=us-central1 \
  --format="value(status.url)"

# Listar revisiones
gcloud run revisions list \
  --service=autos-ai-agent \
  --region=us-central1

# Rollback
gcloud run services update-traffic autos-ai-agent \
  --to-revisions=autos-ai-agent-00001-abc=100 \
  --region=us-central1
```

### Via Cloud Build (CI/CD)
```bash
# Ejecutar el pipeline de CI/CD manualmente
gcloud builds submit \
  --config=deployment/cloudbuild.yaml \
  --substitutions=_ENV=production \
  --project=autos-ai

# Crear trigger automático (push a main)
gcloud builds triggers create github \
  --repo-name=autos-ai \
  --repo-owner=tu-org \
  --branch-pattern="^main$" \
  --build-config=deployment/cloudbuild.yaml \
  --project=autos-ai \
  --name=autos-ai-main-trigger

# Ver builds activos
gcloud builds list --ongoing --project=autos-ai
```

---

## 9. Monitoreo y Operaciones

```bash
# Ver logs de Cloud Run en tiempo real
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="autos-ai-agent"' \
  --project=autos-ai \
  --format="value(timestamp,textPayload)" \
  --freshness=1h \
  --limit=50

# Stream de logs (tail -f equivalente)
gcloud alpha logging tail \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="autos-ai-agent"' \
  --project=autos-ai

# Health check del servicio en producción
SERVICE_URL=$(gcloud run services describe autos-ai-agent \
  --region=us-central1 --format="value(status.url)")
curl -sf "$SERVICE_URL/health"

# Consultar Firestore (listar últimas 5 solicitudes)
# Via Python
python3 -c "
from google.cloud import firestore
db = firestore.Client(project='autos-ai')
docs = db.collection('solicitudes_seguros').order_by(
    'timestamp_creacion', direction=firestore.Query.DESCENDING
).limit(5).stream()
for d in docs: print(d.id, d.to_dict().get('nombre_cliente'))
"

# Listar archivos en GCS
gsutil ls gs://autos-ai-submissions/
gsutil ls gs://autos-ai-outputs/

# Ver métricas de Cloud Run
gcloud monitoring metrics list --filter="resource.type=cloud_run_revision" --project=autos-ai
```

---

## 10. Pipeline MLOps

```bash
# Compilar el pipeline MLOps
uv run python deployment/mlops/pipeline.py compilar
# Output: deployment/mlops/autos_ai_pipeline.json

# Ejecutar el pipeline en Vertex AI Pipelines
uv run python deployment/mlops/pipeline.py ejecutar \
  --proyecto autos-ai \
  --region us-central1 \
  --experimento autos-ai-eval-v1

# Ver pipelines ejecutados en Vertex AI
gcloud ai custom-jobs list \
  --region=us-central1 \
  --project=autos-ai

# Ver experimentos de Vertex AI
gcloud ai experiments list \
  --region=us-central1 \
  --project=autos-ai
```

---

## 11. Git y Control de Versiones

```bash
# Clonar el repositorio
git clone https://github.com/tu-org/autos-ai.git

# Crear rama de feature
git checkout -b claude/feature/nueva-herramienta-<SESSION_ID>

# Ver status
git status
git diff

# Stagear cambios específicos
git add app/tools.py app/agent.py
git add -p  # Interactivo

# Commit
git commit -m "feat: agregar herramienta de extracción de Document AI"

# Push y crear PR
git push -u origin claude/feature/nueva-herramienta-<SESSION_ID>

# Crear PR con GitHub CLI
gh pr create \
  --title "Agregar herramienta Document AI" \
  --body "## Resumen\n- Nueva herramienta de extracción\n\n## Tests\n- [ ] uv run pytest"

# Ver PRs activos
gh pr list

# Merge de PR
gh pr merge --squash
```

---

## Flujo Completo: De Cero a Producción

```bash
# 1. Configurar entorno local
cp .env.example .env && nano .env
uv sync --dev

# 2. Autenticar con GCP
gcloud auth application-default login
gcloud config set project autos-ai

# 3. Provisionar infraestructura
cd infra && cp terraform.tfvars.example terraform.tfvars && nano terraform.tfvars
terraform init && terraform apply -auto-approve
cd ..

# 4. Probar localmente
adk web app/

# 5. Ejecutar tests
uv run pytest -v

# 6. Construir y desplegar
uv run python deployment/mlops/deploy.py full-deploy --tag v1.0.0

# 7. Verificar despliegue
SERVICE_URL=$(gcloud run services describe autos-ai-agent --region=us-central1 --format="value(status.url)")
curl "$SERVICE_URL/health"
echo "✅ AutoFlota-AI en producción: $SERVICE_URL"
```
