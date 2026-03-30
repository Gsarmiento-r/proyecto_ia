# Archivos de Muestra para Evaluación

Esta carpeta debe contener los archivos de solicitudes de prueba
referenciados en los casos de ground truth.

## Archivos Requeridos

| Archivo | Tipo | Descripción |
|---|---|---|
| `solicitud_distribuidora_norte_SA.pdf` | PDF | Caso 01 — Flotilla mediana (15 vehículos) |
| `solicitud_constructora_pacifico.xlsx` | Excel | Caso 02 — Flotilla grande (42 vehículos) |
| `solicitud_logistica_express.docx` | Word | Caso 03 — Datos incompletos (8 vehículos) |

## Instrucciones

Los archivos de muestra NO están versionados en Git por razones de privacidad.
Para obtenerlos:

1. Contacta al administrador del proyecto para acceder al bucket GCS:
   `gs://autos-ai-submissions/eval-samples/`

2. Descarga los archivos con:
   ```bash
   gsutil -m cp gs://autos-ai-submissions/eval-samples/* eval/samples/
   ```

3. O genera tus propios archivos de prueba usando las fixtures de pytest
   en `eval/test_cases/`.
