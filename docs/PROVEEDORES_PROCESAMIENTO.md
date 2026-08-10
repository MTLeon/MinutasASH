# Métodos de procesamiento

## Predeterminado

`ollama_local` mantiene el procesamiento en el computador. Después de la preparación inicial puede operar sin Internet.

## Remotos opcionales

- `azure_openai`: API v1 de Azure OpenAI para entornos corporativos.
- `openai`: API Responses con salida JSON Schema.
- `anthropic`: API Messages con salida estructurada.
- `gemini`: GenerateContent con JSON Schema.
- `openai_compatible`: servidor corporativo o compatible con Chat Completions.

Las credenciales se guardan en Windows Credential Manager bajo objetivos `ASH.MinutasASH.<proveedor>.ApiKey`. No se guardan en el repositorio, archivos de configuración, base SQLite ni registros.

## Política recomendada

1. Mantener el método local como predeterminado.
2. Habilitar servicios remotos solo con aprobación de TI y del responsable del proyecto.
3. Confirmar que el contenido puede salir del equipo.
4. Registrar el proveedor usado en cada minuta.
5. Mantener fallback local cuando exista capacidad suficiente.
