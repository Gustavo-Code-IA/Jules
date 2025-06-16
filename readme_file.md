# 📈 Market Analysis System

Sistema avanzado de análisis de mercado financiero con análisis de sentimiento automatizado, correlaciones precio-noticias y sistema de alertas inteligentes.

## 🚀 Características Principales

### 📊 Análisis de Mercado
- **Datos en tiempo real** de precios de acciones
- **Análisis tecnico** con indicadores avanzados
- **Seguimiento de dividendos** y eventos corporativos
- **Correlaciones** entre sectores y empresas

### 🧠 Análisis de Sentimiento
- **Procesamiento de noticias** automatizado
- **Análisis de sentimiento** con múltiples algoritmos
- **Correlación precio-sentimiento** en tiempo real
- **Alertas** basadas en cambios de sentimiento

### 🔔 Sistema de Alertas
- **Notificaciones por email** (SMTP)
- **Mensajes SMS** (Twilio)
- **Integración con Slack**
- **Alertas personalizables** por umbral

### 🗄️ Base de Datos Optimizada
- **SQLite** con índices optimizados
- **Respaldos automáticos**
- **Limpieza automática** de datos antiguos
- **Migración de datos** sin pérdidas

## 📋 Requisitos del Sistema

### Software Requerido
- **Python 3.8+** (recomendado 3.9+)
- **SQLite 3.37+**
- **4GB RAM mínimo** (8GB recomendado)
- **2GB espacio libre** en disco

### Claves de API Necesarias
- **Alpha Vantage API** (obligatoria) - [Obtener aquí](https://www.alphavantage.co/support/#api-key)
- **News API** (opcional) - [Obtener aquí](https://newsapi.org/register)
- **Finnhub API** (opcional) - [Obtener aquí](https://finnhub.io/register)

## 🔧 Instalación Rápida

### Opción 1: Instalación Automática
```bash
# 1. Clonar o descargar el proyecto
git clone <repository-url>
cd market-analysis-system

# 2. Ejecutar instalación automática
python setup.py

# 3. Configurar claves de API en .env
nano .env  # o usar tu editor favorito

# 4. Iniciar el sistema
./start_unix.sh    # Linux/macOS
# o
start_windows.bat  # Windows
```

### Opción 2: Instalación Manual
```bash
# 1. Crear entorno virtual
python -m venv venv

# 2. Activar entorno virtual
source venv/bin/activate  # Linux/macOS
# o
venv\Scripts\activate     # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Descargar datos NLTK
python -c "import nltk; nltk.download('punkt'); nltk.download('vader_lexicon')"

# 5. Crear directorios
mkdir -p data logs backups config

# 6. Configurar variables de entorno
cp .env.template .env
# Editar .env con tus claves de API

# 7. Inicializar base de datos
python -c "from database_setup import initialize_database; initialize_database()"
```

## ⚙️ Configuración

### Variables de Entorno Principales

```bash
# APIs (obligatorio)
ALPHA_VANTAGE_API_KEY=tu_clave_alpha_vantage

# Base de datos
DB_PATH=./data/market_analysis.db
DB_BACKUP_PATH=./backups/

# Intervalos de actualización (minutos)
PRICE_UPDATE_INTERVAL=15
NEWS_UPDATE_INTERVAL=30

# Alertas por email
EMAIL_ENABLED=true
SMTP_SERVER=smtp.gmail.com
EMAIL_USERNAME=tu_email@gmail.com
EMAIL_PASSWORD=tu_app_password
```

### Configuración de Alertas

#### Email (Gmail)
```bash
EMAIL_ENABLED=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USERNAME=tu_email@gmail.com
EMAIL_PASSWORD=tu_app_password  # Usar App Password de Google
EMAIL_TO=destinatario@email.com
```

#### SMS (Twilio)
```bash
SMS_ENABLED=true
TWILIO_ACCOUNT_SID=tu_account_sid
TWILIO_AUTH_TOKEN=tu_auth_token
TWILIO_PHONE_FROM=+1234567890
TWILIO_PHONE_TO=+0987654321
```

#### Slack
```bash
SLACK_ENABLED=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/tu/webhook/url
```

## 🎯 Uso del Sistema

### Inicialización Básica
```python
from database_setup import initialize_database
from config_manager import get_config

# Cargar configuración
config = get_config()

# Inicializar base de datos
db_manager = initialize_database()

# Obtener estadísticas
stats = db_manager.get_database_stats()
print(f"Empresas: {stats['companies']}")
print(f"Registros de precios: {stats['price_records']}")
```

### Análisis de Datos
```python
# Obtener precios históricos
df_prices = db_manager.get_dataframe("""
    SELECT c.symbol, c.name, sp.date, sp.close_price, sp.volume
    FROM companies c
    JOIN stock_prices sp ON c.id = sp.company_id
    WHERE sp.date >= date('now', '-30 days')
    ORDER BY sp.date DESC
""")

# Análisis de sentimiento reciente
df_sentiment = db_manager.get_dataframe("""
    SELECT c.symbol, ne.title, ne.sentiment_score, ne.published_date
    FROM companies c
    JOIN news_events ne ON c.id = ne.company_id
    WHERE ne.published_date >= datetime('now', '-7 days')
    AND abs(ne.sentiment_score) > 0.1
    ORDER BY ne.sentiment_score DESC
""")
```

### Correlaciones Precio-Noticias
```python
# Análisis de correlaciones
correlations = db_manager.get_dataframe("""
    SELECT c.symbol, 
           pnc.correlation_coefficient,
           pnc.p_value,
           pnc.analysis_period_days
    FROM companies c
    JOIN price_news_correlation pnc ON c.id = pnc.company_id
    WHERE pnc.correlation_coefficient IS NOT NULL
    ORDER BY abs(pnc.correlation_coefficient) DESC
""")
```

## 📁 Estructura del Proyecto

```
market-analysis-system/
├── 📄 main.py                 # Punto de entrada principal
├── 📄 database_setup.py       # Configuración de base de datos
├── 📄 config_manager.py       # Gestor de configuración
├── 📄 setup.py               # Script de instalación
├── 📄 requirements.txt       # Dependencias Python
├── 📄 .env.template          # Template de variables de entorno
├── 📄 .env                   # Variables de entorno (crear)
├── 📄 README.md              # Este archivo
├── 📁 data/                  # Base de datos y cache
│   ├── 📄 market_analysis.db # Base de datos principal
│   └── 📁 cache/            # Cache temporal
├── 📁 logs/                  # Archivos de log
│   ├── 📄 market_analysis.log
│   └── 📁 archive/          # Logs archivados
├── 📁 backups/              # Respaldos automáticos
│   ├── 📁 database/         # Respaldos de BD
│   └── 📁 logs/            # Respaldos de logs
├── 📁 config/               # Archivos de configuración
│   └── 📄 logging.json      # Configuración de logging
└── 📁 tests/                # Tests automatizados
```

## 🔍 Monitoreo y Mantenimiento

### Estadísticas de la Base de Datos
```python
# Obtener estadísticas completas
stats = db_manager.get_database_stats()
print(f"""
📊 ESTADÍSTICAS DEL SISTEMA:
- Sectores: {stats['sectors']}
- Empresas: {stats['companies']}
- Registros de precios: {stats['price_records']}
- Noticias analizadas: {stats['news_records']}
- Alertas generadas: {stats['alert_records']}
- Tamaño de BD: {stats['database_size_mb']:.2f} MB
""")
```

### Respaldos y Limpieza
```python
# Crear respaldo manual
backup_path = db_manager.backup_database()
print(f"Respaldo creado: {backup_path}")

# Limpiar datos antiguos
removed_count = db_manager.cleanup_old_data()
print(f"Registros eliminados: {removed_count}")
```

## 🔧 Resolución de Problemas

### Problemas Comunes

#### Error de Clave de API
```
Error: API key not found or invalid
```
**Solución**: Verificar que `ALPHA_VANTAGE_API_KEY` esté configurada correctamente en `.env`

#### Error de Base de Datos
```
Error: database is locked
```
**Solución**: 
1. Cerrar otras conexiones a la BD
2. Reiniciar el sistema
3. Si persiste, usar: `db_manager.execute_query("PRAGMA journal_mode=WAL;")`

#### Error de Permisos
```
Error: Permission denied
```
**Solución**: 
```bash
chmod +x start_unix.sh
chmod 755 -R data/ logs/ backups/
```

#### Problemas de Email
```
Error: SMTP authentication failed
```
**Solución**: 
1. Usar "App Password" de Google (no tu contraseña normal)
2. Habilitar "Aplicaciones menos seguras" si es necesario
3. Verificar configuración SMTP

### Comandos Útiles

```bash
# Ver logs en tiempo real
tail -f logs/market_analysis.log

# Verificar estado de la base de datos
python -c "from database_setup import initialize_database; print(initialize_database().get_database_stats())"

# Crear respaldo manual
python -c "from database_setup import initialize_database; print(initialize_database().backup_database())"

# Limpiar cache
rm -rf data/cache/*

# Verificar configuración
python -c "from config_manager import get_config; config = get_config(); print(f'Environment: {config.environment}')"
```

## 📈 Optimización del Rendimiento

### Configuraciones Recomendadas

Para **sistemas de bajo recursos**:
```bash
PRICE_UPDATE_INTERVAL=60
NEWS_UPDATE_INTERVAL=120
MAX_WORKERS=2
BATCH_SIZE=50
CACHE_ENABLED=true
```

Para **sistemas de alto rendimiento**:
```bash
PRICE_UPDATE_INTERVAL=5
NEWS_UPDATE_INTERVAL=15
MAX_WORKERS=8
BATCH_SIZE=200
CACHE_ENABLED=true
```

### Monitoreo de Recursos
```python
import psutil

# Monitoreo de memoria
memory = psutil.virtual_memory()
print(f"Memoria usada: {memory.percent}%")

# Monitoreo de disco
disk = psutil.disk_usage('.')
print(f"Disco usado: {disk.percent}%")
```

## 🚦 Estados del Sistema

| Estado | Descripción | Acción |
|---------|-------------|---------|
| 🟢 **RUNNING** | Sistema funcionando normalmente | Ninguna |
| 🟡 **WARNING** | Advertencias menores | Revisar logs |
| 🟠 **ERROR** | Errores recuperables | Verificar configuración |
| 🔴 **CRITICAL** | Errores críticos | Reiniciar sistema |

## 🤝 Contribución

### Reportar Problemas
1. Revisar issues existentes
2. Incluir logs relevantes
3. Especificar versión de Python y OS
4. Describir pasos para reproducir

### Mejoras Sugeridas
- Integración con más fuentes de noticias
- Análisis técnico avanzado
- Dashboard web interactivo
- Integración con bases de datos externas
- API REST para acceso remoto

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 📞 Soporte

- **Documentación**: Este README
- **Issues**: GitHub Issues
- **Email**: [configurar en .env]

---

**🎉 ¡Gracias por usar Market Analysis System!**

Para más información técnica, consulta los comentarios en el código fuente.