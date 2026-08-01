# Validación — Minutas ASH 2.3.5

- Versión: **2.3.5**
- Esquema SQLite: **6**
- Pipeline: **2.2**
- Pruebas automatizadas: **123 aprobadas**
- Compilación Python: **correcta**
- Cobertura automatizada: **73,76 %**

## Regresiones incorporadas

- detección de JSON cortado y aumento del límite de salida;
- excepción específica tras truncamientos reiterados;
- división automática del bloque por salida estructurada incompleta;
- conservación del perfil preventivo después del warmup;
- configuración de subprocess sin consola en Windows;
- comprobación de instalación sin iniciar procesos externos al abrir la GUI.

## Pruebas pendientes en Windows

- confirmar visualmente que no aparezcan ventanas CMD al abrir la aplicación;
- confirmar que solo se inicie una instancia de Ollama al procesar;
- repetir el VTT `Reunión Jefes de Proyectos.vtt` y comprobar la reanudación desde el checkpoint;
- validar consumo máximo de RAM y duración total;
- construir y probar el instalador Inno Setup.
