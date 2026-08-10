# Auditoría técnica inicial — Minutas ASH 5.0.0

Fecha: 30-07-2026  
Objetivo: registrar el estado real de la aplicación antes de refactorizarla.

## Resultado de la línea base

- Compilación Python: aprobada.
- Pruebas automatizadas existentes: 5 de 5 aprobadas.
- Generación documental: cubierta por una prueba básica.
- Instalador Windows: construido exitosamente en el equipo de desarrollo.

## Fortalezas

1. Separación inicial entre procesamiento, almacenamiento, documentos y repositorios.
2. Modelos de datos validados con Pydantic.
3. Persistencia SQLite con WAL, claves foráneas y tiempo de espera.
4. Evidencia separada del documento final.
5. Proveedor documental extensible.
6. Repositorio abstraído mediante protocolo, útil para SQL Server futuro.
7. Procesamiento local y revisión humana antes de emitir.

## Hallazgos prioritarios

### P0 — confidencialidad y operación

- Definir retención de VTT, JSON y transcripción normalizada.
- Evitar que documentos reales entren al repositorio.
- Preparar respaldo y recuperación de la base SQLite.
- Firmar digitalmente instalador y ejecutable antes de distribución amplia.

### P1 — mantenibilidad

- `src/gui.py` supera 1.500 líneas y concentra vista, estado, validación, hilos y acceso a servicios.
- La configuración se administra como `dict`; debe convertirse en un modelo tipado.
- SQLite no dispone de un sistema formal de migraciones o tabla de versión.
- Hay bloques `except Exception` que dificultan diagnosticar fallas específicas.
- Las dependencias de producción y construcción no están bloqueadas con versiones reproducibles.

### P1 — calidad

- Cinco pruebas son insuficientes para una aplicación documental corporativa.
- No existen pruebas para errores de red local, cancelación, archivos corruptos, VTT extensos o nombres ambiguos.
- No existe un conjunto de transcripciones anonimizadas con resultados esperados para regresión.
- La interfaz gráfica no tiene pruebas de controladores o servicios desacoplados.

### P1 — seguridad del procesamiento

- La transcripción debe tratarse siempre como datos no confiables y nunca como instrucciones.
- Debe limitarse el tamaño de archivos y contenido antes del procesamiento.
- La URL del servicio local debería validarse para evitar conexiones accidentales a destinos externos.
- Los registros deben evitar contenido sensible y permitir exportar un diagnóstico sanitizado.

### P2 — instalador y versiones

- La descarga de componentes externos debe fijar versiones y mantener evidencia de hash/firma.
- La construcción debe ser reproducible desde GitHub Actions o un equipo de construcción controlado.
- Debe existir una política de compatibilidad de Windows, Python, Ollama y modelo.
- El código de versión aparece en varios archivos y debe tener una única fuente.

### P2 — arquitectura futura

- Separar aplicación, dominio, infraestructura y presentación.
- Introducir interfaces para almacenamiento de archivos y configuración.
- Preparar migración SQLite → SQL Server sin acoplar la GUI.
- Crear un registro de tipos documentales para minutas, FAT, SAT y protocolos.

## Orden recomendado de trabajo

1. Registrar esta versión como `v5.0.0`.
2. Incorporar CI, reglas de ramas y plantillas de trabajo.
3. Crear configuración tipada y una fuente única de versión.
4. Incorporar migraciones SQLite.
5. Descomponer la GUI por vistas y controladores.
6. Crear pruebas de regresión con datos anonimizados.
7. Endurecer manejo de archivos, registros y aprovisionamiento.
8. Construir una versión 5.1.1 para validación interna.
9. Diseñar el proveedor SQL Server en una rama independiente.
