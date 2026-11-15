# Plataforma de gestión técnica y auditoría de NAP (FTTH-GPON) – Municipio Plaza, Miranda

Aplicación web para que técnicos y supervisores de un ISP en Guarenas registren cajas NAP, auditen la potencia óptica recibida en la ONT y obtengan un diagnóstico automático según ITU-T G.984 (GPON clase B+).

## Stack Tecnológico
* **Backend:** Python 3 + Flask
* **Base de Datos:** MySQL 8 / MariaDB (vía PyMySQL)[cite: 13]
* **Frontend:** HTML5 / CSS3 / JavaScript (Vanilla)

## Requisitos Previos
Asegúrate de tener instalado en tu sistema:
* Python (versión 3.10 o superior)
* Git
* Servidor MySQL o MariaDB activo

## Instalación
1. Crear la base de datos: `mysql -u root -p < schema.sql`
2. `python -m venv venv` y activar (`venv\Scripts\activate` en Windows, `source venv/bin/activate` en Linux/Mac)
3. `pip install -r requirements.txt`
4. Configurar credenciales (ver `.env.example`), por ejemplo en Windows: `set DB_PASSWORD=tu_clave` / Linux: `export DB_PASSWORD=tu_clave`
5. `python app.py` y abrir http://127.0.0.1:5000

## Funcionalidades
- CRUD de NAP (código único, splitter, puertos, potencia OLT, distancia, estado) con validaciones.
- Cálculo del presupuesto óptico: fibra 0.25 dB/km (1490 nm), splitter (1:8 = 10.5 dB, 1:16 = 13.8 dB…), conectores 0.5 dB, empalmes 0.1 dB.
- Clasificación: **OK** (-8 a -25 dBm), **ALERTA** (-25 a -27 dBm o pérdida real >3 dB sobre la teórica), **CRÍTICO** (< -27 dBm o saturación > -8 dBm).
- Historial filtrable, resumen con ocupación de puertos y exportación a CSV.

## API
`GET/POST /api/naps` · `PUT/DELETE /api/naps/<id>` · `POST /api/calc` · `GET/POST /api/audits` · `GET /api/stats` · `GET /api/export.csv`


## Integrantes:
-Andrés Reyes V-30.520.333
-Allan González V- 28.660.376
-Diego Herrera V-32.333.289
-Fernando Reyes V-30.159.566
-Mitchael Ruíz V-31.416.127
