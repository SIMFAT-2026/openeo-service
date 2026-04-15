# SIMFAT openEO Microservice

Microservicio especializado para obtencion de datos satelitales desde openEO/Copernicus dentro del ecosistema SIMFAT.

Este servicio no implementa logica de negocio principal de SIMFAT. Su rol en este sprint es entregar una base tecnica limpia para futuras ejecuciones de jobs satelitales.

## Alcance de este sprint

- Estructura base por capas
- API HTTP con FastAPI
- Endpoints de salud, chequeo de configuracion y jobs
- Contratos request/response consistentes con Pydantic
- Cliente openEO desacoplado en modo placeholder
- Configuracion por variables de entorno
- Manejo basico de errores
- Tests minimos de humo

## Estructura

```text
.
|-- app/
|   |-- __init__.py
|   |-- main.py
|   |-- api/
|   |   |-- __init__.py
|   |   `-- routes/
|   |       |-- __init__.py
|   |       |-- config.py
|   |       |-- health.py
|   |       |-- jobs.py
|   |       `-- openeo.py
|   |-- adapters/
|   |   |-- __init__.py
|   |   `-- openeo_adapter.py
|   |-- clients/
|   |   |-- __init__.py
|   |   `-- openeo_client.py
|   |-- core/
|   |   |-- __init__.py
|   |   |-- config.py
|   |   `-- exceptions.py
|   |-- models/
|   |   |-- __init__.py
|   |   `-- job.py
|   |-- schemas/
|   |   |-- __init__.py
|   |   |-- config.py
|   |   |-- jobs.py
|   |   `-- openeo.py
|   `-- services/
|       |-- __init__.py
|       `-- indicator_service.py
|-- tests/
|   |-- __init__.py
|   `-- test_api.py
|-- .env.example
`-- requirements.txt
```

## Requisitos

- Python 3.11+
- pip

## Configuracion

1. Copiar variables de entorno:

```bash
cp .env.example .env
```

2. Ajustar valores segun ambiente local.

## Ejecucion local

1. Crear y activar entorno virtual.
2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Iniciar servicio:

```bash
uvicorn app.main:app --reload --port 8000
```

Si deseas usar el puerto por variable:

```bash
uvicorn app.main:app --reload --port ${APP_PORT}
```

## Endpoints base

- `GET /health`
- `GET /config/check`
- `POST /jobs/ndvi`
- `POST /jobs/ndmi`
- `GET /openeo/capabilities`
- `GET /openeo/collections?limit=5`
- `POST /openeo/indicators/latest/{indicator}` (`indicator` = `NDVI` o `NDMI`)

## Verificacion liviana de conexion openEO

Los endpoints `GET /openeo/capabilities` y `GET /openeo/collections` estan orientados a pruebas de conectividad de bajo costo.

- Usan timeout corto.
- Cachean respuestas por 5 minutos.
- Cachean token de acceso segun su expiracion.

Para computo satelital de indicadores (endpoint `POST /openeo/indicators/latest/{indicator}`) el servicio usa `/result` de openEO y requiere `OPENEO_ACCESS_TOKEN`.
En CDSE, el flujo `client_credentials` no habilita endpoints de procesamiento, solo metadatos/probes.

## Ejemplo rapido de request (placeholder)

```json
{
  "regionId": "region-001",
  "aoi": {
    "type": "bbox",
    "coordinates": [-72.6, -38.8, -72.3, -38.5]
  },
  "periodStart": "2025-01-01",
  "periodEnd": "2025-01-31"
}
```

## Ejemplo de request de indicador real

`POST /openeo/indicators/latest/NDVI`

```json
{
  "regionId": "region-001",
  "aoi": {
    "type": "bbox",
    "coordinates": [-72.6, -38.8, -72.3, -38.5]
  },
  "periodStart": "2026-04-01",
  "periodEnd": "2026-04-12"
}
```

## Notas de arquitectura

- Este microservicio encapsula la integracion futura con openEO mediante `clients` + `adapters`.
- Las rutas HTTP solo orquestan validacion y delegan a `services`.
- La persistencia y reglas de negocio del dominio SIMFAT permanecen en `simfat-backend`.
- El frontend no debe consumir este servicio directamente.
