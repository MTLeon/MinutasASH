# Banco de evaluación reproducible

El corpus `reuniones_anonimizadas.json` contiene casos sintéticos y anonimizados con puntos esperados y frases que no deben convertirse en filas.

Ejecute un proveedor:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\Evaluate-Benchmark.ps1 -Providers ollama_local
```

Compare varios proveedores configurados:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\Evaluate-Benchmark.ps1 -Providers ollama_local,anthropic,openai
```

Cada resultado registra versión de aplicación, proveedor, modelo, versión y hash del prompt, hash de configuración sin secretos, entorno, duración, precisión, cobertura, duplicados, falsos positivos y resultados por caso. Los servicios remotos requieren credenciales válidas y envían el contenido anonimizado al proveedor seleccionado.
