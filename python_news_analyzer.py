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
        
        for item in