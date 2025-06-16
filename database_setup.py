import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gestor completo de base de datos para el sistema de análisis financiero"""
    
    def __init__(self, db_path='financial_data.db'):
        self.db_path = db_path
        self.setup_database()
        
    def setup_database(self):
        """Configura todas las tablas necesarias"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Tabla de sectores
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sectors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    code VARCHAR(10) UNIQUE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabla de empresas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol VARCHAR(10) NOT NULL UNIQUE,
                    name VARCHAR(200) NOT NULL,
                    sector_id INTEGER,
                    exchange VARCHAR(10) DEFAULT 'NASDAQ',
                    market_cap BIGINT,
                    industry VARCHAR(100),
                    country VARCHAR(50) DEFAULT 'US',
                    currency VARCHAR(3) DEFAULT 'USD',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (sector_id) REFERENCES sectors(id)
                )
            ''')
            
            # Tabla de precios históricos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER,
                    symbol VARCHAR(10) NOT NULL,
                    date DATE NOT NULL,
                    open_price DECIMAL(12,4),
                    high_price DECIMAL(12,4),
                    low_price DECIMAL(12,4),
                    close_price DECIMAL(12,4),
                    volume BIGINT,
                    adj_close DECIMAL(12,4),
                    dividend_amount DECIMAL(12,4) DEFAULT 0,
                    split_coefficient DECIMAL(10,4) DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date),
                    FOREIGN KEY (company_id) REFERENCES companies(id)
                )
            ''')
            
            # Tabla de noticias
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS news_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER,
                    symbol VARCHAR(10) NOT NULL,
                    headline TEXT NOT NULL,
                    summary TEXT,
                    content TEXT,
                    source VARCHAR(100),
                    author VARCHAR(200),
                    sentiment_score DECIMAL(5,4),
                    sentiment_label VARCHAR(20),
                    impact_score DECIMAL(5,4),
                    relevance_score DECIMAL(5,4) DEFAULT 0,
                    published_at TIMESTAMP,
                    url TEXT,
                    category VARCHAR(50),
                    language VARCHAR(5) DEFAULT 'en',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies(id)
                )
            ''')
            
            # Tabla de análisis de correlación
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_news_correlation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER,
                    symbol VARCHAR(10) NOT NULL,
                    date DATE NOT NULL,
                    price_change DECIMAL(8,4),
                    price_change_percent DECIMAL(8,4),
                    volume_change DECIMAL(8,4),
                    news_sentiment_avg DECIMAL(5,4),
                    news_impact_avg DECIMAL(5,4),
                    news_count INTEGER DEFAULT 0,
                    positive_news_count INTEGER DEFAULT 0,
                    negative_news_count INTEGER DEFAULT 0,
                    neutral_news_count INTEGER DEFAULT 0,
                    correlation_strength DECIMAL(5,4),
                    prediction_accuracy DECIMAL(5,4),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date),
                    FOREIGN KEY (company_id) REFERENCES companies(id)
                )
            ''')
            
            # Tabla de alertas y notificaciones
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol VARCHAR(10) NOT NULL,
                    alert_type VARCHAR(50) NOT NULL,
                    threshold_value DECIMAL(12,4),
                    current_value DECIMAL(12,4),
                    message TEXT,
                    priority VARCHAR(10) DEFAULT 'medium',
                    status VARCHAR(20) DEFAULT 'active',
                    triggered_at TIMESTAMP,
                    resolved_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabla de configuraciones del sistema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_key VARCHAR(100) NOT NULL UNIQUE,
                    config_value TEXT,
                    config_type VARCHAR(20) DEFAULT 'string',
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabla de logs del sistema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    log_level VARCHAR(10) NOT NULL,
                    module VARCHAR(50),
                    message TEXT NOT NULL,
                    error_details TEXT,
                    execution_time DECIMAL(10,6),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Crear índices para optimizar consultas
            self._create_indexes(cursor)
            
            # Insertar datos iniciales
            self._insert_initial_data(cursor)
            
            conn.commit()
            logger.info("✅ Base de datos configurada correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error configurando base de datos: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _create_indexes(self, cursor):
        """Crea índices para optimizar las consultas"""
        indexes = [
            # Índices para stock_prices
            "CREATE INDEX IF NOT EXISTS idx_stock_prices_symbol_date ON stock_prices(symbol, date DESC)",
            "CREATE INDEX IF NOT EXISTS idx_stock_prices_date ON stock_prices(date DESC)",
            "CREATE INDEX IF NOT EXISTS idx_stock_prices_symbol ON stock_prices(symbol)",
            
            # Índices para news_events
            "CREATE INDEX IF NOT EXISTS idx_news_symbol_date ON news_events(symbol, published_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_news_published_at ON news_events(published_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_news_sentiment ON news_events(sentiment_score)",
            "CREATE INDEX IF NOT EXISTS idx_news_impact ON news_events(impact_score)",
            
            # Índices para correlations
            "CREATE INDEX IF NOT EXISTS idx_correlation_symbol_date ON price_news_correlation(symbol, date DESC)",
            "CREATE INDEX IF NOT EXISTS idx_correlation_strength ON price_news_correlation(correlation_strength DESC)",
            
            # Índices para companies
            "CREATE INDEX IF NOT EXISTS idx_companies_symbol ON companies(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_companies_sector ON companies(sector_id)",
            
            # Índices para alerts
            "CREATE INDEX IF NOT EXISTS idx_alerts_symbol_status ON alerts(symbol, status)",
            "CREATE INDEX IF NOT EXISTS idx_alerts_triggered ON alerts(triggered_at DESC)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
            
        logger.info("✅ Índices de base de datos creados")
    
    def _insert_initial_data(self, cursor):
        """Inserta datos iniciales del sistema"""
        
        # Sectores predefinidos
        sectors_data = [
            ('defense', 'DEF', 'Defensa y Aeroespacial'),
            ('technology', 'TECH', 'Tecnología'),
            ('finance', 'FIN', 'Servicios Financieros'),
            ('healthcare', 'HLTH', 'Salud y Farmacéuticas'),
            ('energy', 'ENRG', 'Energía y Petróleo'),
            ('consumer', 'CONS', 'Bienes de Consumo'),
            ('industrials', 'IND', 'Industriales'),
            ('utilities', 'UTIL', 'Servicios Públicos'),
            ('materials', 'MAT', 'Materiales Básicos'),
            ('real_estate', 'REIT', 'Bienes Raíces')
        ]
        
        for sector in sectors_data:
            cursor.execute('''
                INSERT OR IGNORE INTO sectors (name, code, description) 
                VALUES (?, ?, ?)
            ''', sector)
        
        # Empresas por sector
        companies_data = [
            # Defensa
            ('LMT', 'Lockheed Martin Corp', 'defense', 'NYSE'),
            ('RTX', 'Raytheon Technologies', 'defense', 'NYSE'),
            ('BA', 'Boeing Co', 'defense', 'NYSE'),
            ('GD', 'General Dynamics Corp', 'defense', 'NYSE'),
            ('NOC', 'Northrop Grumman Corp', 'defense', 'NYSE'),
            ('LHX', 'L3Harris Technologies', 'defense', 'NYSE'),
            
            # Tecnología
            ('AAPL', 'Apple Inc', 'technology', 'NASDAQ'),
            ('MSFT', 'Microsoft Corp', 'technology', 'NASDAQ'),
            ('GOOGL', 'Alphabet Inc', 'technology', 'NASDAQ'),
            ('AMZN', 'Amazon.com Inc', 'technology', 'NASDAQ'),
            ('META', 'Meta Platforms Inc', 'technology', 'NASDAQ'),
            ('NVDA', 'NVIDIA Corp', 'technology', 'NASDAQ'),
            
            # Finanzas
            ('JPM', 'JPMorgan Chase & Co', 'finance', 'NYSE'),
            ('BAC', 'Bank of America Corp', 'finance', 'NYSE'),
            ('WFC', 'Wells Fargo & Co', 'finance', 'NYSE'),
            ('GS', 'Goldman Sachs Group', 'finance', 'NYSE'),
            ('MS', 'Morgan Stanley', 'finance', 'NYSE'),
            ('C', 'Citigroup Inc', 'finance', 'NYSE'),
            
            # Salud
            ('JNJ', 'Johnson & Johnson', 'healthcare', 'NYSE'),
            ('PFE', 'Pfizer Inc', 'healthcare', 'NYSE'),
            ('UNH', 'UnitedHealth Group', 'healthcare', 'NYSE'),
            ('MRK', 'Merck & Co Inc', 'healthcare', 'NYSE'),
            ('ABT', 'Abbott Laboratories', 'healthcare', 'NYSE'),
            ('TMO', 'Thermo Fisher Scientific', 'healthcare', 'NYSE'),
            
            # Energía
            ('XOM', 'Exxon Mobil Corp', 'energy', 'NYSE'),
            ('CVX', 'Chevron Corp', 'energy', 'NYSE'),
            ('COP', 'ConocoPhillips', 'energy', 'NYSE'),
            ('EOG', 'EOG Resources Inc', 'energy', 'NYSE'),
            ('SLB', 'Schlumberger NV', 'energy', 'NYSE'),
            ('OXY', 'Occidental Petroleum', 'energy', 'NYSE')
        ]
        
        for company in companies_data:
            # Obtener sector_id
            cursor.execute('SELECT id FROM sectors WHERE name = ?', (company[2],))
            sector_result = cursor.fetchone()
            sector_id = sector_result[0] if sector_result else None
            
            cursor.execute('''
                INSERT OR IGNORE INTO companies (symbol, name, sector_id, exchange) 
                VALUES (?, ?, ?, ?)
            ''', (company[0], company[1], sector_id, company[3]))
        
        # Configuraciones iniciales del sistema
        config_data = [
            ('api_rate_limit', '5', 'integer', 'Límite de llamadas por minuto a APIs'),
            ('update_frequency', '15', 'integer', 'Frecuencia de actualización en minutos'),
            ('sentiment_threshold_positive', '0.1', 'float', 'Umbral para sentimiento positivo'),
            ('sentiment_threshold_negative', '-0.1', 'float', 'Umbral para sentimiento negativo'),
            ('impact_threshold_high', '0.7', 'float', 'Umbral para impacto alto'),
            ('correlation_window_days', '30', 'integer', 'Ventana de días para cálculo de correlación'),
            ('news_retention_days', '365', 'integer', 'Días de retención de noticias'),
            ('price_retention_days', '1095', 'integer', 'Días de retención de precios (3 años)'),
            ('alert_email_enabled', 'true', 'boolean', 'Activar alertas por email'),
            ('alert_slack_enabled', 'false', 'boolean', 'Activar alertas por Slack'),
            ('data_backup_enabled', 'true', 'boolean', 'Activar respaldo automático'),
            ('backup_frequency_hours', '24', 'integer', 'Frecuencia de respaldo en horas')
        ]
        
        for config in config_data:
            cursor.execute('''
                INSERT OR IGNORE INTO system_config (config_key, config_value, config_type, description) 
                VALUES (?, ?, ?, ?)
            ''', config)
        
        logger.info("✅ Datos iniciales insertados")
    
    def get_connection(self):
        """Obtiene una conexión a la base de datos"""
        return sqlite3.connect(self.db_path)
    
    def execute_query(self, query, params=None, fetch_all=True):
        """Ejecuta una consulta y retorna los resultados"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if query.strip().upper().startswith('SELECT'):
                return cursor.fetchall() if fetch_all else cursor.fetchone()
            else:
                conn.commit()
                return cursor.rowcount
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error ejecutando consulta: {e}")
            raise
        finally:
            conn.close()
    
    def get_dataframe(self, query, params=None):
        """Ejecuta una consulta y retorna un DataFrame de pandas"""
        conn = self.get_connection()
        try:
            return pd.read_sql_query(query, conn, params=params)
        finally:
            conn.close()
    
    def backup_database(self, backup_path=None):
        """Crea un respaldo de la base de datos"""
        if not backup_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f'backup_financial_data_{timestamp}.db'
        
        source = sqlite3.connect(self.db_path)
        backup = sqlite3.connect(backup_path)
        
        try:
            source.backup(backup)
            logger.info(f"✅ Respaldo creado: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"❌ Error creando respaldo: {e}")
            raise
        finally:
            source.close()
            backup.close()
    
    def cleanup_old_data(self):
        """Limpia datos antiguos según configuración"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Obtener configuraciones de retención
            cursor.execute('''
                SELECT config_key, config_value FROM system_config 
                WHERE config_key IN ('news_retention_days', 'price_retention_days')
            ''')
            config = dict(cursor.fetchall())
            
            news_retention = int(config.get('news_retention_days', 365))
            price_retention = int(config.get('price_retention_days', 1095))
            
            # Limpiar noticias antiguas
            cursor.execute('''
                DELETE FROM news_events 
                WHERE published_at <= datetime('now', '-{} days')
            '''.format(news_retention))
            news_deleted = cursor.rowcount
            
            # Limpiar precios antiguos (mantener solo datos necesarios)
            cursor.execute('''
                DELETE FROM stock_prices 
                WHERE date <= date('now', '-{} days')
            '''.format(price_retention))
            prices_deleted = cursor.rowcount
            
            # Limpiar correlaciones antiguas
            cursor.execute('''
                DELETE FROM price_news_correlation 
                WHERE date <= date('now', '-{} days')
            '''.format(news_retention))
            corr_deleted = cursor.rowcount
            
            conn.commit()
            logger.info(f"✅ Limpieza completada: {news_deleted} noticias, {prices_deleted} precios, {corr_deleted} correlaciones")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Error en limpieza: {e}")
            raise
        finally:
            conn.close()
    
    def get_database_stats(self):
        """Obtiene estadísticas de la base de datos"""
        stats = {}
        tables = ['sectors', 'companies', 'stock_prices', 'news_events', 'price_news_correlation', 'alerts']
        
        for table in tables:
            query = f"SELECT COUNT(*) FROM {table}"
            result = self.execute_query(query, fetch_all=False)
            stats[table] = result[0] if result else 0
        
        # Estadísticas adicionales
        stats['database_size_mb'] = os.path.getsize(self.db_path) / (1024 * 1024) if os.path.exists(self.db_path) else 0
        
        # Rango de fechas de datos
        date_ranges = {}
        for table, date_col in [('stock_prices', 'date'), ('news_events', 'published_at')]:
            query = f"SELECT MIN({date_col}), MAX({date_col}) FROM {table}"
            result = self.execute_query(query, fetch_all=False)
            if result and result[0]:
                date_ranges[table] = {'min': result[0], 'max': result[1]}
        
        stats['date_ranges'] = date_ranges
        return stats
    
    def vacuum_database(self):
        """Optimiza la base de datos eliminando espacio no utilizado"""
        conn = self.get_connection()
        try:
            conn.execute('VACUUM')
            logger.info("✅ Base de datos optimizada")
        except Exception as e:
            logger.error(f"❌ Error optimizando base de datos: {e}")
            raise
        finally:
            conn.close()
    
    def log_system_event(self, level, module, message, error_details=None, execution_time=None):
        """Registra eventos del sistema en la base de datos"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO system_logs (log_level, module, message, error_details, execution_time)
                VALUES (?, ?, ?, ?, ?)
            ''', (level, module, message, error_details, execution_time))
            conn.commit()
        except Exception as e:
            logger.error(f"Error registrando log: {e}")
        finally:
            conn.close()


# Script de inicialización y configuración
def initialize_database(db_path='financial_data.db'):
    """Inicializa completamente la base de datos"""
    logger.info("🚀 Iniciando configuración de base de datos")
    
    # Crear gestor de base de datos
    db_manager = DatabaseManager(db_path)
    
    # Mostrar estadísticas
    stats = db_manager.get_database_stats()
    logger.info("📊 Estadísticas de la base de datos:")
    for table, count in stats.items():
        if isinstance(count, (int, float)):
            logger.info(f"  {table}: {count}")
    
    # Crear primer respaldo
    backup_path = db_manager.backup_database()
    logger.info(f"💾 Respaldo inicial creado: {backup_path}")
    
    logger.info("✅ Configuración de base de datos completada")
    return db_manager


# Función para migración de datos (si ya tienes datos existentes)
def migrate_existing_data(old_db_path, new_db_path='financial_data.db'):
    """Migra datos de una base de datos existente"""
    logger.info("🔄 Iniciando migración de datos")
    
    if not os.path.exists(old_db_path):
        logger.error(f"❌ Base de datos origen no encontrada: {old_db_path}")
        return
    
    # Crear nueva base de datos
    new_db = DatabaseManager(new_db_path)
    
    # Conectar a base de datos antigua
    old_conn = sqlite3.connect(old_db_path)
    new_conn = sqlite3.connect(new_db_path)
    
    try:
        # Migrar datos tabla por tabla
        tables_to_migrate = ['stock_prices', 'news_events']
        
        for table in tables_to_migrate:
            # Verificar si la tabla existe en la BD antigua
            cursor = old_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if cursor.fetchone():
                # Leer datos de la tabla antigua
                df = pd.read_sql_query(f"SELECT * FROM {table}", old_conn)
                # Escribir a la nueva base de datos
                df.to_sql(table, new_conn, if_exists='append', index=False)
                logger.info(f"✅ Migrados {len(df)} registros de {table}")
        
        new_conn.commit()
        logger.info("✅ Migración completada")
        
    except Exception as e:
        logger.error(f"❌ Error en migración: {e}")
        new_conn.rollback()
        raise
    finally:
        old_conn.close()
        new_conn.close()


if __name__ == "__main__":
    # Configurar base de datos
    db_manager = initialize_database()
    
    # Mostrar estadísticas finales
    stats = db_manager.get_database_stats()
    print("\n📊 ESTADÍSTICAS DE LA BASE DE DATOS:")
    print("=" * 50)
    for key, value in stats.items():
        if key != 'date_ranges':
            print(f"{key:25}: {value}")
    
    print("\n📅 RANGOS DE FECHAS:")
    print("=" * 50)
    for table, ranges in stats.get('date_ranges', {}).items():
        print(f"{table:25}: {ranges['min']} → {ranges['max']}")
