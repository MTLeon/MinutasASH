# Fuentes flexibles y aprendizaje local

## Sin VTT

Minutas ASH acepta VTT, TXT y DOCX, además de conversación pegada y notas manuales.
El formato TXT recomendado es UTF-8, con una intervención por línea:

```text
[00:02:15] Mauricio: Debemos entregar los planos el viernes.
Carolina: Yo revisaré el documento.
Notas de reunión: Queda pendiente confirmar las señales.
```

Los tiempos son opcionales. Conservar `Nombre: intervención` mejora la detección de participantes.

## Convertir audio o video

El conversor admite MP3, WAV, M4A, FLAC, OGG, MP4, MKV y WEBM. Whisper es opcional y no se instala automáticamente.

```bat
cd /d C:\MinutasTeams
transcribir_audio.bat "C:\Reuniones\reunion.mp3"
```

También se puede usar:

```bat
.\.venv\Scripts\python.exe -m src.audio_transcription "reunion.mp3" --modelo base --idioma es
```

El resultado es un TXT seleccionable desde la aplicación. Whisper no identifica hablantes: las intervenciones quedan como `Hablante no identificado` y deben revisarse. Si Whisper no está instalado, el comando muestra la instrucción de instalación sin descargar nada por sí solo.

## Aprendizaje supervisado

Cuando una minuta final se marca como ejemplo de aprendizaje, la aplicación puede recuperar hasta tres ejemplos aprobados. Se priorizan coincidencias de proyecto y tipo de reunión. El modelo recibe sus patrones de clasificación y redacción, pero tiene prohibido copiar hechos, personas, fechas o acuerdos.

Opciones en `config.json`:

```json
"learning_capture_enabled": true,
"learning_retrieval_enabled": true,
"learning_retrieval_limit": 3
```

Solo deben aprobarse minutas revisadas. Para datos reales, anonimice o excluya información sensible según las reglas de la organización.

## Perfil Ollama

`crear_modelo_minutas.bat` crea el perfil local `minutas-ash` desde `qwen3:8b`. No es un ajuste fino de pesos: fija parámetros y conducta base. Para usarlo, cambie `"model": "qwen3:8b"` por `"model": "minutas-ash"` después de validar el perfil.

El ajuste fino LoRA queda reservado para una fase posterior, cuando exista un conjunto amplio, consistente, revisado y anonimizado de ejemplos.