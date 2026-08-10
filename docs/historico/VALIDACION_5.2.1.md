# Validación técnica — Minutas ASH 5.2.1

## Resultado

- Compilación Python: aprobada.
- Pruebas automatizadas: **37 de 37 aprobadas**.
- Inicio de interfaz gráfica: aprobado en entorno gráfico de prueba.
- Generación Word corporativa: aprobada.
- Control híbrido de cobertura: aprobado.
- Caso de resultado vacío incoherente: corregido y cubierto por regresión.

## Escenarios específicos

- Lectura de VTT de Teams con entidades HTML.
- Frases divididas en varios bloques sin puntuación suficiente.
- Detección de «enviará», «revisará», «se acuerda», «queda pendiente» y
  «próxima reunión».
- Segunda comprobación con proveedor simulado.
- Recuperación determinista cuando el proveedor devuelve cero puntos.
- Resolución de responsable abreviado contra asistentes.
- Resolución de fecha explícita «lunes 3 de agosto» a `2026-08-03` cuando la
  reunión es del 30 de julio de 2026.
- Persistencia de diagnóstico y candidatos en la evidencia JSON.
- Emisión del Word con todos los puntos recuperados.

## Pendiente de validación Windows

El ejecutable y el wizard deben construirse en Windows mediante
`CONSTRUIR_INSTALADOR_FINAL.bat`. Después se debe repetir la prueba en un equipo
Windows 11 sin código fuente ni Python instalado.
