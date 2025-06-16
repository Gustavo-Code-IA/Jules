import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import sqlite3
import json
import re
from textblob import TextBlob
import yfinance as yf
from collections import defaultdict
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StockNewsAnalyzer:
    def __init__(self, api_keys):
        """
        Inicializa el analizador de noticias financieras
        
        Args:
            api_keys (dict): Diccionario con las claves de API necesarias
                - news_api: Clave para NewsAPI
                - alpha_vantage: Clave para Alpha Vantage
                - finnhub: Clave para Finnhub
        """
        self.api_keys = api_keys
        self.db_path = 'financial_data.db'
        self.sectors = {
            'defense': ['LMT', 'RTX', 'BA', 'GD', 'NOC', 'LHX'],
            'tech': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA'],
            'finance': ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'C'],
            'healthcare': ['JNJ', 'PFE', 'UNH', 'MRK', 'ABT', 'TMO'],
            'energy': ['XOM', 'CVX', 'COP', 'EOG', 'SLB', 'OXY']
        }
        self.setup_database()
        
    def setup_database(self):
        """Configura la base de datos SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla de precios de acciones
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                open_price REAL,
                high_price REAL,
                low_price REAL,
                close_price REAL,
                volume INTEGER,
                adj_close REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date)
            )
        ''')
        
        # Tabla de noticias
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                headline TEXT NOT NULL,
                summary TEXT,
                source TEXT,
                sentiment_score REAL,
                impact_score REAL,
                published_at TIMESTAMP,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de análisis de correlación
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_news_correlation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                price_change REAL,
                news_sentiment_avg REAL,
                news_impact_avg REAL,
                news_count INTEGER,
                correlation_strength REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Base de datos configurada correctamente")
        
    def fetch_stock_data(self, symbols, period='1y'):
        """
        Obtiene datos históricos de acciones usando yfinance
        
        Args:
            symbols (list): Lista de símbolos de acciones
            period (str): Período de tiempo ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
        """
        logger.info(f"Obteniendo datos de acciones para {len(symbols)} símbolos")
        
        for symbol in symbols:
            try:
                stock = yf.Ticker(symbol)
                hist = stock.history(period=period)
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                for date, row in hist.iterrows():
                    cursor.execute('''
                        INSERT OR REPLACE INTO stock_prices 
                        (symbol, date, open_price, high_price, low_price, close_price, volume, adj_close)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        symbol,
                        date.strftime('%Y-%m-%d'),
                        row['Open'],
                        row['High'],
                        row['Low'],
                        row['Close'],
                        row['Volume'],
                        row['Close']  # yfinance ya proporciona precios ajustados
                    ))
                
                conn.commit()
                conn.close()
                logger.info(f"✅ Datos actualizados para {symbol}")
                
            except Exception as e:
                logger.error(f"❌ Error obteniendo datos para {symbol}: {e}")
                
        time.sleep(1)  # Evitar rate limiting
        
    def fetch_news_data(self, symbols, days_back=7):
        """
        Obtiene noticias relacionadas con las acciones
        
        Args:
            symbols (list): Lista de símbolos de acciones
            days_back (int): Días hacia atrás para buscar noticias
        """
        logger.info(f"Obteniendo noticias para {len(symbols)} símbolos")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        for symbol in symbols:
            try:
                # NewsAPI
                if 'news_api' in self.api_keys:
                    self._fetch_newsapi_data(symbol, start_date, end_date)
                
                # Alpha Vantage News
                if 'alpha_vantage' in self.api_keys:
                    self._fetch_alpha_vantage_news(symbol)
                
                # Finnhub News
                if 'finnhub' in self.api_keys:
                    self._fetch_finnhub_news(symbol, start_date, end_date)
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.error(f"❌ Error obteniendo noticias para {symbol}: {e}")
                
    def _fetch_newsapi_data(self, symbol, start_date, end_date):
        """Obtiene noticias de NewsAPI"""
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': f'{symbol} OR stock OR shares',
            'from': start_date.strftime('%Y-%m-%d'),
            'to': end_date.strftime('%Y-%m-%d'),
            'sortBy': 'relevancy',
            'apiKey': self.api_keys['news_api'],
            'language': 'en',
            'pageSize': 20
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            self._process_news_articles(symbol, data.get('articles', []), 'NewsAPI')
        else:
            logger.warning(f"Error en NewsAPI para {symbol}: {response.status_code}")
            
    def _fetch_alpha_vantage_news(self, symbol):
        """Obtiene noticias de Alpha Vantage"""
        url = f"https://www.alphavantage.co/query"
        params = {
            'function': 'NEWS_SENTIMENT',
            'tickers': symbol,
            'apikey': self.api_keys['alpha_vantage'],
            'limit': 20
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if 'feed' in data:
                self._process_alpha_vantage_news(symbol, data['feed'])
        else:
            logger.warning(f"Error en Alpha Vantage para {symbol}: {response.status_code}")
            
    def _fetch_finnhub_news(self, symbol, start_date, end_date):
        """Obtiene noticias de Finnhub"""
        url = f"https://finnhub.io/api/v1/company-news"
        params = {
            'symbol': symbol,
            'from': start_date.strftime('%Y-%m-%d'),
            'to': end_date.strftime('%Y-%m-%d'),
            'token': self.api_keys['finnhub']
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            self._process_finnhub_news(symbol, data)
        else:
            logger.warning(f"Error en Finnhub para {symbol}: {response.status_code}")
            
    def _process_news_articles(self, symbol, articles, source):
        """Procesa artículos de noticias generales"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for article in articles:
            if not article.get('title'):
                continue
                
            sentiment_score = self.analyze_sentiment(article['title'] + ' ' + (article.get('description') or ''))
            impact_score = self.calculate_impact_score(article, sentiment_score)
            
            cursor.execute('''
                INSERT OR IGNORE INTO news_events 
                (symbol, headline, summary, source, sentiment_score, impact_score, published_at, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol,
                article['title'],
                article.get('description', ''),
                source,
                sentiment_score,
                impact_score,
                article.get('publishedAt'),
                article.get('url')
            ))
            
        conn.commit()
        conn.close()
        
    def _process_alpha_vantage_news(self, symbol, feed):
        """Procesa noticias de Alpha Vantage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for item in feed:
            if not item.get('title'):
                continue
                
            # Alpha Vantage ya proporciona sentiment score
            sentiment_score = float(item.get('overall_sentiment_score', 0))
            impact_score = self.calculate_impact_score(item, sentiment_score, is_alpha_vantage=True)
            
            cursor.execute('''
                INSERT OR IGNORE INTO news_events 
                (symbol, headline, summary, source, sentiment_score, impact_score, published_at, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol,
                item['title'],
                item.get('summary', ''),
                'Alpha Vantage',
                sentiment_score,
                impact_score,
                item.get('time_published'),
                item.get('url')
            ))
            
        conn.commit()
        conn.close()
        
    def _process_finnhub_news(self, symbol, news_data):
        """Procesa noticias de Finnhub"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for item in news_data:
            if not item.get('headline'):
                continue
                
            sentiment_score = self.analyze_sentiment(item['headline'] + ' ' + (item.get('summary') or ''))
            impact_score = self.calculate_impact_score(item, sentiment_score, is_finnhub=True)
            
            cursor.execute('''
                INSERT OR IGNORE INTO news_events 
                (symbol, headline, summary, source, sentiment_score, impact_score, published_at, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol,
                item['headline'],
                item.get('summary', ''),
                'Finnhub',
                sentiment_score,
                impact_score,
                datetime.fromtimestamp(item.get('datetime', 0)).isoformat() if item.get('datetime') else None,
                item.get('url')
            ))
            
        conn.commit()
        conn.close()
        
    def analyze_sentiment(self, text):
        """
        Analiza el sentimiento del texto usando TextBlob
        
        Args:
            text (str): Texto a analizar
            
        Returns:
            float: Score de sentimiento entre -1 (muy negativo) y 1 (muy positivo)
        """
        if not text:
            return 0.0
            
        try:
            blob = TextBlob(text)
            return blob.sentiment.polarity
        except Exception as e:
            logger.warning(f"Error analizando sentimiento: {e}")
            return 0.0
            
    def calculate_impact_score(self, article, sentiment_score, is_alpha_vantage=False, is_finnhub=False):
        """
        Calcula el score de impacto basado en múltiples factores
        
        Args:
            article (dict): Artículo de noticia
            sentiment_score (float): Score de sentimiento
            is_alpha_vantage (bool): Si es de Alpha Vantage
            is_finnhub (bool): Si es de Finnhub
            
        Returns:
            float: Score de impacto entre 0 y 1
        """
        base_score = abs(sentiment_score)
        
        # Palabras clave que indican alto impacto
        high_impact_keywords = [
            'earnings', 'revenue', 'profit', 'loss', 'merger', 'acquisition',
            'lawsuit', 'regulation', 'contract', 'order', 'guidance', 'upgrade',
            'downgrade', 'bankruptcy', 'dividend', 'split', 'buyback', 'ipo',
            'fda', 'approval', 'clinical', 'trial', 'patent', 'breakthrough'
        ]
        
        # Factores que amplifican el impacto
        source_weights = {
            'reuters.com': 1.2,
            'bloomberg.com': 1.2,
            'wsj.com': 1.15,
            'cnbc.com': 1.1,
            'marketwatch.com': 1.05,
            'seekingalpha.com': 1.0,
            'yahoo.com': 0.9,
            'default': 0.8
        }
        
        keyword_multiplier = 1.0
        title = article.get('title', '') or article.get('headline', '')
        summary = article.get('description', '') or article.get('summary', '')
        text_lower = (title + ' ' + summary).lower()
        
        # Contar palabras clave de alto impacto
        for keyword in high_impact_keywords:
            if keyword in text_lower:
                keyword_multiplier += 0.1
        
        # Peso por fuente
        if is_alpha_vantage or is_finnhub:
            source_mult = 1.1  # APIs especializadas tienen mayor peso
        else:
            source = article.get('source', {})
            if isinstance(source, dict):
                source_name = source.get('name', 'default').lower()
            else:
                source_name = str(source).lower()
            source_mult = source_weights.get(source_name, source_weights['default'])
        
        # Cálculo final del score de impacto
        final_score = min(base_score * source_mult * keyword_multiplier, 1.0)
        return final_score
        
    def calculate_price_news_correlation(self, symbol, days_back=30):
        """
        Calcula la correlación entre noticias y movimientos de precio
        
        Args:
            symbol (str): Símbolo de la acción
            days_back (int): Días hacia atrás para el análisis
        """
        conn = sqlite3.connect(self.db_path)
        
        # Obtener datos de precios
        price_query = '''
            SELECT date, close_price, 
                   LAG(close_price) OVER (ORDER BY date) as prev_close
            FROM stock_prices 
            WHERE symbol = ? AND date >= date('now', '-{} days')
            ORDER BY date
        '''.format(days_back)
        
        price_df = pd.read_sql_query(price_query, conn, params=(symbol,))
        price_df['price_change'] = ((price_df['close_price'] - price_df['prev_close']) / price_df['prev_close'] * 100)
        
        # Obtener datos de noticias agrupados por día
        news_query = '''
            SELECT DATE(published_at) as date,
                   AVG(sentiment_score) as avg_sentiment,
                   AVG(impact_score) as avg_impact,
                   COUNT(*) as news_count
            FROM news_events 
            WHERE symbol = ? AND DATE(published_at) >= date('now', '-{} days')
            GROUP BY DATE(published_at)
            ORDER BY date
        '''.format(days_back)
        
        news_df = pd.read_sql_query(news_query, conn, params=(symbol,))
        
        # Combinar datos
        combined_df = pd.merge(price_df, news_df, on='date', how='left')
        combined_df = combined_df.fillna(0)
        
        # Calcular correlación
        cursor = conn.cursor()
        
        for _, row in combined_df.iterrows():
            if pd.notna(row['price_change']):
                # Correlación simple entre sentimiento promedio y cambio de precio
                correlation_strength = abs(row['avg_sentiment'] * row['price_change']) / 100 if row['avg_sentiment'] != 0 else 0
                
                cursor.execute('''
                    INSERT OR REPLACE INTO price_news_correlation 
                    (symbol, date, price_change, news_sentiment_avg, news_impact_avg, news_count, correlation_strength)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol,
                    row['date'],
                    row['price_change'],
                    row['avg_sentiment'],
                    row['avg_impact'],
                    row['news_count'],
                    correlation_strength
                ))
        
        conn.commit()
        conn.close()
        logger.info(f"Correlación calculada para {symbol}")
        
    def get_sector_analysis(self, sector_name, days_back=7):
        """
        Obtiene análisis completo de un sector
        
        Args:
            sector_name (str): Nombre del sector
            days_back (int): Días hacia atrás para el análisis
            
        Returns:
            dict: Análisis completo del sector
        """
        if sector_name not in self.sectors:
            raise ValueError(f"Sector {sector_name} no reconocido")
            
        symbols = self.sectors[sector_name]
        conn = sqlite3.connect(self.db_path)
        
        analysis = {
            'sector': sector_name,
            'symbols': symbols,
            'summary': {},
            'individual_stocks': {},
            'sector_sentiment': 0,
            'sector_impact': 0,
            'total_news': 0
        }
        
        # Análisis por acción individual
        for symbol in symbols:
            # Datos de precio más recientes
            price_query = '''
                SELECT * FROM stock_prices 
                WHERE symbol = ? 
                ORDER BY date DESC 
                LIMIT 5
            '''
            price_data = pd.read_sql_query(price_query, conn, params=(symbol,))
            
            # Noticias recientes
            news_query = '''
                SELECT * FROM news_events 
                WHERE symbol = ? AND DATE(published_at) >= date('now', '-{} days')
                ORDER BY published_at DESC
            '''.format(days_back)
            news_data = pd.read_sql_query(news_query, conn, params=(symbol,))
            
            # Correlación reciente
            corr_query = '''
                SELECT * FROM price_news_correlation 
                WHERE symbol = ? 
                ORDER BY date DESC 
                LIMIT 10
            '''
            corr_data = pd.read_sql_query(corr_query, conn, params=(symbol,))
            
            analysis['individual_stocks'][symbol] = {
                'latest_price': price_data['close_price'].iloc[0] if not price_data.empty else 0,
                'price_change_5d': ((price_data['close_price'].iloc[0] - price_data['close_price'].iloc[-1]) / price_data['close_price'].iloc[-1] * 100) if len(price_data) >= 2 else 0,
                'avg_sentiment': news_data['sentiment_score'].mean() if not news_data.empty else 0,
                'avg_impact': news_data['impact_score'].mean() if not news_data.empty else 0,
                'news_count': len(news_data),
                'recent_news': news_data.head(3).to_dict('records') if not news_data.empty else [],
                'correlation_strength': corr_data['correlation_strength'].mean() if not corr_data.empty else 0
            }
            
            # Acumular para análisis sectorial
            analysis['sector_sentiment'] += analysis['individual_stocks'][symbol]['avg_sentiment']
            analysis['sector_impact'] += analysis['individual_stocks'][symbol]['avg_impact']
            analysis['total_news'] += analysis['individual_stocks'][symbol]['news_count']
        
        # Promedios sectoriales
        num_stocks = len(symbols)
        analysis['sector_sentiment'] /= num_stocks
        analysis['sector_impact'] /= num_stocks
        
        # Resumen sectorial
        analysis['summary'] = {
            'avg_sector_sentiment': analysis['sector_sentiment'],
            'avg_sector_impact': analysis['sector_impact'],
            'total_news_count': analysis['total_news'],
            'most_active_stock': max(analysis['individual_stocks'].items(), key=lambda x: x[1]['news_count'])[0] if analysis['total_news'] > 0 else None,
            'most_volatile_stock': max(analysis['individual_stocks'].items(), key=lambda x: abs(x[1]['price_change_5d']))[0]
        }
        
        conn.close()
        return analysis
        
    def run_full_analysis(self, sector_name=None, update_data=True):
        """
        Ejecuta análisis completo del sistema
        
        Args:
            sector_name (str, optional): Sector específico a analizar
            update_data (bool): Si actualizar datos antes del análisis
        """
        logger.info("🚀 Iniciando análisis completo del sistema")
        
        sectors_to_analyze = [sector_name] if sector_name else list(self.sectors.keys())
        results = {}
        
        for sector in sectors_to_analyze:
            logger.info(f"📊 Analizando sector: {sector}")
            symbols = self.sectors[sector]
            
            if update_data:
                # Actualizar datos de precios
                self.fetch_stock_data(symbols, period='3mo')
                
                # Actualizar noticias
                self.fetch_news_data(symbols, days_back=14)
                
                # Calcular correlaciones
                for symbol in symbols:
                    self.calculate_price_news_correlation(symbol, days_back=30)
            
            # Obtener análisis del sector
            results[sector] = self.get_sector_analysis(sector, days_back=7)
            
        logger.info("✅ Análisis completo finalizado")
        return results
        
    def export_results_to_json(self, results, filename=None):
        """
        Exporta resultados a archivo JSON
        
        Args:
            results (dict): Resultados del análisis
            filename (str, optional): Nombre del archivo
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'stock_analysis_{timestamp}.json'
            
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            
        logger.info(f"📁 Resultados exportados a: {filename}")
        

# Ejemplo de uso
if __name__ == "__main__":
    # Configurar APIs (reemplazar con claves reales)
    api_keys = {
        'news_api': 'TU_CLAVE_NEWSAPI',
        'alpha_vantage': 'TU_CLAVE_ALPHA_VANTAGE',
        'finnhub': 'TU_CLAVE_FINNHUB'
    }
    
    # Crear analizador
    analyzer = StockNewsAnalyzer(api_keys)
    
    # Ejecutar análisis completo del sector defensa
    results = analyzer.run_full_analysis(sector_name='defense', update_data=True)
    
    # Exportar resultados
    analyzer.export_results_to_json(results)
    
    # Mostrar resumen
    for sector, data in results.items():
        print(f"\n📊 SECTOR: {sector.upper()}")
        print(f"Sentimiento promedio: {data['sector_sentiment']:.3f}")
        print(f"Impacto promedio: {data['sector_impact']:.3f}")
        print(f"Total noticias: {data['total_news']}")
        print(f"Acción más activa: {data['summary']['most_active_stock']}")
        print(f"Acción más volátil: {data['summary']['most_volatile_stock']}")
