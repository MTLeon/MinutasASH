# Validación — Minutas ASH 2.3.4

- Versión: **2.3.4**
- Secuencia: **2003004**
- Predecesora: **2.3.3**
- Esquema de base de datos: **6**
- Fecha de validación del código fuente: **2026-07-31**

## Resultados ejecutados

- Compilación de módulos: `python -m compileall -q src` — **aprobada**.
- Suite automatizada: `python -m pytest --cov=src --cov-report=term -q` — **117/117 pruebas aprobadas**.
- Cobertura total medida: **73,75 %**; mínimo configurado: 65 %.
- Verificación de identidad de versión, recursos Windows e Inno Setup — aprobada por pruebas.
- Regresiones de VTT, fuentes, participantes, cobertura, checkpoints, consolidación, documentos, base de datos, catálogos, historial, proveedores y revisión masiva — aprobadas.
- Nuevas regresiones 2.3.4: subtítulos progresivos, ruido aislado, rechazo de tiempos como participantes, reserva anticipada de RAM, límites de salida, deduplicación conservadora y cableado de atajos/filtros/caché de revisión — aprobadas.

## Validaciones no realizadas en este entorno

- No se compiló el instalador de Windows ni se ejecutó un smoke test visual real de Tkinter.
- No se procesó una reunión real mediante Ollama ni se midió RAM física con `qwen3:8b` cargado.
- No se validaron llamadas reales a proveedores remotos.

Estas pruebas deben completarse con `docs/PRUEBA_PILOTO_WINDOWS11_2.3.4.md` antes de una distribución productiva.
