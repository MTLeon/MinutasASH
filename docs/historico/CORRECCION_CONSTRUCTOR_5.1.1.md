# Corrección del constructor 5.1.1

## Síntoma

```text
No se encuentra la propiedad Count en este objeto.
FullyQualifiedErrorId : PropertyNotFoundStrict
```

## Causa

Con `Set-StrictMode -Version Latest`, el resultado de `Find-Python` quedaba como una cadena cuando solo se detectaba `python.exe`. La versión 5.1.0 esperaba siempre un arreglo y consultaba `$launcher.Count`.

## Corrección

`Find-Python` ahora devuelve un `PSCustomObject` con:

- `Executable`: ruta de Python.
- `Prefix`: argumentos previos, por ejemplo `-3` cuando se usa `py.exe`.
- `Description`: texto de diagnóstico.

La función `Invoke-Python` valida la ruta y ejecuta ambos escenarios sin depender de propiedades implícitas.
