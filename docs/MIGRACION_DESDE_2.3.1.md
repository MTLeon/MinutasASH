# Migración desde Minutas ASH 2.3.1 a 2.3.3

1. Cierre la aplicación.
2. Realice un respaldo desde 2.3.1 o conserve el respaldo automático.
3. Ejecute el instalador 2.3.3 sobre la instalación existente.
4. Abra Configuración y verifique que el perfil sea Automático.
5. Confirme que guardar avance y dividir bloques lentos estén activados.
6. Procese primero una reunión de prueba.

La base de datos continúa en esquema 6. No se eliminan reuniones, contactos, clientes, proyectos, plantillas, muestras ni documentos.

Los procesos iniciados con 2.3.1 no tienen checkpoints compatibles porque esa versión no los generaba. Los nuevos checkpoints se crean desde la primera ejecución en 2.3.3.
