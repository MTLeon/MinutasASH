# Automatizacion de reuniones

## Objetivo

Reducir el flujo habitual a dos acciones: revisar excepciones y aprobar la emision.

## Flujo local disponible

1. Active `Vigilar y preparar archivos nuevos de la bandeja` en Preferencias > Automatizacion.
2. Deposite VTT, SRT, TXT, DOCX, PDF, audio o video en la bandeja de entrada.
3. La aplicacion espera a que el archivo termine de copiarse y calcula su SHA-256.
4. Las fuentes ya procesadas se omiten.
5. Audio y video se transcriben mediante el complemento Whisper, cuando esta instalado.
6. El nombre del archivo se contrasta con los perfiles de proyecto activos.
7. Si existe una coincidencia suficiente, se completan proyecto, cliente, plantilla, participantes y numeracion.
8. Opcionalmente se inicia el analisis sin una segunda accion del usuario.
9. La revision por excepciones preaprueba solo puntos sin alertas y sobre el umbral configurado.
10. Si no quedan excepciones, la generacion documental puede iniciarse automaticamente.

El estado se guarda en `.automation-state.json` dentro de la bandeja. Los fallos temporales se reintentan hasta el limite configurado y los procesos interrumpidos siguen usando los checkpoints existentes.

## Controles de seguridad

- La automatizacion esta desactivada en instalaciones nuevas.
- El envio a servicios remotos conserva la confirmacion configurada por el usuario.
- Un punto con responsable, plazo o evidencia faltante no se preaprueba.
- Los tipos, fechas y campos obligatorios mantienen validacion estricta.
- La emision automatica solo se intenta cuando no quedan excepciones.

## Integración opcional con Microsoft Teams

La aplicación permite importar una transcripción desde **Teams / Graph** pegando
el enlace autorizado de la reunión. El inicio de sesión es interactivo, solicita
solo lectura de reuniones y transcripciones, mantiene el token únicamente en
memoria y deposita el VTT en la bandeja recuperable. Los identificadores de
aplicación y tenant sí se recuerdan porque no son secretos. La importación evita
duplicados por identificador de transcripción y hash del contenido.

La aplicación Entra debe estar registrada como cliente público con redirección
local y consentimiento para `OnlineMeetings.Read` y
`OnlineMeetingTranscript.Read.All`. El tenant puede deshabilitar el acceso de
Graph a transcripciones o la atribución de hablantes; en este último caso la
aplicación reintenta automáticamente con contenido sin hablantes.

## Sincronización administrativa

La sincronización automática de todas las reuniones de un organizador mediante
`getAllTranscripts` exige permisos de aplicación, consentimiento administrativo
y una política de acceso del tenant. Las notificaciones en tiempo real requieren
además una URL HTTPS pública. Ese modo de servicio no se activa desde el escritorio
para evitar incorporar secretos administrativos en el instalador.
## Convencion recomendada para archivos

Incluya el codigo de proyecto en el nombre para obtener la mayor certeza:

`P3261 - Coordinacion cliente - 2026-08-11.vtt`

Los nombres sin codigo permanecen preparados para que el usuario seleccione el perfil antes de procesar.
