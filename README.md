# Minutas ASH 2.3.3

Aplicación de escritorio para preparar, revisar y emitir minutas corporativas desde transcripciones y notas de reunión.

## Flujo esencial

1. Cargar VTT, TXT o DOCX; pegar conversación o crear notas.
2. Completar proyecto/cartera, materia, fechas, redactor y número.
3. Confirmar participantes.
4. Procesar y revisar acuerdos, compromisos y pendientes.
5. Generar Word.

## Novedades 2.3.3

- Selección múltiple de puntos con Ctrl/Shift.
- Aprobar, descartar o devolver varios puntos en una sola acción.
- Aprobar o descartar todos los resultados visibles después de buscar o filtrar.
- Búsqueda instantánea en la revisión.
- Deshacer la última acción con `Ctrl+Z`.
- Menú contextual con clic derecho y `Ctrl+A` para seleccionar lo visible.
- Confirmaciones masivas y avance automático configurables.
- Ventanas secundarias redimensionables, con geometría recordada y recuperación dentro de pantalla.
- Distribución visual adaptable y barra horizontal para tablas extensas.
- Se conserva el procesamiento resiliente 2.3.2: bloques, checkpoints, reanudación, streaming y timeout adaptativo.

Se mantienen además las fuentes flexibles, reuniones multiproyecto, papelera, registros de prueba, diccionario técnico, aprendizaje supervisado, catálogos y plantillas administrables.

## Construcción Windows

```bat
CONSTRUIR_INSTALADOR_FINAL.bat
```

Resultado:

```text
dist_installer\MinutasASH_Setup_2.3.3_Online.exe
dist_installer\MinutasASH_Setup_2.3.3_Online_SHA256.txt
```

## Pruebas

```powershell
python -m compileall -q src tests
python -m unittest discover -s tests -p "test_*.py" -v
```

## Documentación

- `docs/Manual_Maestro_2.3.3.md`
- `docs/Manual_Usuario_2.3.3.md`
- `docs/Manual_Configuracion_2.3.3.md`
- `docs/Manual_Programador_2.3.3.md`
- `docs/PROCESAMIENTO_RESILIENTE_2.3.3.md`
- `docs/NOTAS_VERSION_2.3.3.md`
- `VALIDACION_2.3.3.md`

## Privacidad

No incluya transcripciones, checkpoints, bases, documentos de clientes, respaldos ni credenciales en GitHub. Los fixtures deben ser sintéticos o anonimizados.


## Guías adicionales

- [Fuentes flexibles y aprendizaje local](docs/FUENTES_Y_APRENDIZAJE.md)
