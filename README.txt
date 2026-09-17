# Miller Cars Tuning - Facturación

## 1. Instalar Python
Se recomienda Python 3.11 o superior.

## 2. Abrir PowerShell en esta carpeta

Crear entorno:
python -m venv venv

Activarlo:
.\venv\Scripts\Activate.ps1

Si PowerShell bloquea la activación:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1

## 3. Instalar dependencias
pip install -r requirements.txt

## 4. Configurar el correo
Copia `.env.example` y crea un archivo llamado `.env`.

Ejemplo:
MAIL_USER=micorreo@gmail.com
MAIL_PASSWORD=CLAVE_DE_APLICACION

IMPORTANTE:
Para Gmail se recomienda usar una "Contraseña de aplicación", no la contraseña normal de Gmail.

## 5. Ejecutar
python app.py

Abre:
http://127.0.0.1:5000

## ¿Qué hace?
- Crea consecutivos MCT-000001, MCT-000002...
- Guarda las facturas en SQLite.
- Genera el PDF.
- Descarga el PDF automáticamente al crearlo.
- Intenta enviar el PDF adjunto al correo del cliente.
- Tiene historial de facturas.

## Seguridad
No publiques el archivo `.env`, no compartas la clave del correo y no la subas a GitHub.
