# Transportes JDA Backend RC3 final

## Integraciones cerradas

- Motor financiero único para Dashboard y Estado de Resultados.
- KPIs financieros derivados del mismo resultado del motor.
- Rentabilidad operativa y empresarial por cliente, piloto, camión, ruta y producto.
- Conciliación de rentabilidad empresarial con la utilidad neta del motor financiero.
- Tarifarios, detalle de tarifas, importación Excel, gastos, categorías y sincronización de combustible registrados en la API.

## Correcciones finales

- Se aplican `fecha_desde` y `fecha_hasta` en consulta y exportación de documentos.
- Exportaciones Excel usan nombres únicos para evitar colisiones entre usuarios.
- Altas, cambios y bajas de pilotos requieren rol `ADMIN` o `ENCARGADO`.
- Registro manual de precio de combustible requiere rol `ADMIN` o `ENCARGADO`.
- Login rechaza usuarios inactivos.
- JWT incluye expiración configurable (`ACCESS_TOKEN_EXPIRE_HOURS`, 24 horas por defecto).
- CORS es configurable mediante `CORS_ORIGINS`; el modo comodín evita credenciales incompatibles con navegadores.
- El filtro de pilotos devuelve una lista ordenada de nombres, sin tuplas ni valores vacíos.
- Se valida que los usuarios con rol piloto tengan un piloto asociado antes de guardar viajes.
- Distribución empresarial sin ingresos se reparte por cantidad de viajes, evitando cargar todo al último grupo.
- Se agregó diferencia de conciliación en los totales de rentabilidad.
- Se eliminó el servicio duplicado `profitability_service_integrado.py`.
- Se agregó paquete explícito `app`, configuración de pytest, `.env.example` y guía de ejecución local.

## Validación

- Compilación completa: correcta.
- Pruebas: 10 aprobadas.
- Importación de `main.py`: correcta.
- Rutas FastAPI registradas: 72.
