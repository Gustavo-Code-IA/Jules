# Sistema Dinámico de Seguimiento de Acciones por Sectores

## 1. Arquitectura del Sistema

### Componentes Principales
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Fuentes de    │    │   Procesador    │    │   Dashboard     │
│     Datos       │───▶│   Central       │───▶│   Dinámico      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Stack Tecnológico Recomendado

**Backend (Procesamiento de Datos):**
- **Python** con pandas, numpy, requests
- **Node.js** con Express para APIs
- **PostgreSQL** o **MongoDB** para almacenamiento
- **Redis** para caché de datos en tiempo real

**Frontend (Dashboard):**
- **React** con TypeScript
- **Next.js** para server-side rendering
- **Chart.js** o **Recharts** para gráficos
- **Tailwind CSS** para diseño

**Servicios de Datos:**
- **WebSocket** para datos en tiempo real
- **CRON Jobs** para actualizaciones programadas
- **Docker** para containerización

## 2. APIs y Fuentes de Datos

### APIs Financieras (Datos de Precios)
```javascript
// APIs Gratuitas
const FREE_APIS = {
  alphaVantage: "https://www.alphavantage.co/query",
  finnhub: "https://finnhub.io/api/v1",
  yahooFinance: "https://query1.finance.yahoo.com/v8/finance/chart/",
  iexCloud: "https://cloud.iexapis.com/stable"
};

// APIs Premium
const PREMIUM_APIS = {
  bloomberg: "Bloomberg Terminal API",
  refinitiv: "Refinitiv Eikon",
  quandl: "Nasdaq Data Link",
  tradingView: "TradingView API"
};
```

### APIs de Noticias (Eventos que Afectan Precios)
```javascript
const NEWS_APIS = {
  newsAPI: "https://newsapi.org/v2/everything",
  googlenNews: "Google News RSS",
  alphaVantageNews: "Alpha Vantage News & Sentiment",
  benzinga: "Benzinga News API",
  marketaux: "Marketaux Financial News API"
};
```

## 3. Estructura de Base de Datos

### Tabla: Sectores
```sql
CREATE TABLE sectors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(10) UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Tabla: Empresas
```sql
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    name VARCHAR(200) NOT NULL,
    sector_id INTEGER REFERENCES sectors(id),
    exchange VARCHAR(10),
    market_cap BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Tabla: Precios Históricos
```sql
CREATE TABLE stock_prices (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    date DATE NOT NULL,
    open_price DECIMAL(10,2),
    high_price DECIMAL(10,2),
    low_price DECIMAL(10,2),
    close_price DECIMAL(10,2),
    volume BIGINT,
    adjusted_close DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Tabla: Noticias e Impacto
```sql
CREATE TABLE news_events (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    headline TEXT NOT NULL,
    summary TEXT,
    source VARCHAR(100),
    sentiment DECIMAL(3,2), -- -1 a +1
    impact_score DECIMAL(3,2), -- 0 a 1
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 4. Sistema de Actualización Automática

### Configuración de CRON Jobs
```bash
# Actualización de precios cada 15 minutos (horario de mercado)
*/15 9-16 * * 1-5 /usr/bin/python3 /app/update_prices.py

# Análisis de noticias cada 30 minutos
*/30 * * * * /usr/bin/python3 /app/analyze_news.py

# Limpieza de datos antiguos (diaria)
0 2 * * * /usr/bin/python3 /app/cleanup_data.py
```

### Script de Actualización de Precios (Python)
```python
import requests
import pandas as pd
from datetime import datetime
import os

class StockDataUpdater:
    def __init__(self):
        self.api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        self.base_url = "https://www.alphavantage.co/query"
    
    def update_sector_data(self, sector_symbols):
        """Actualiza datos para un sector específico"""
        for symbol in sector_symbols:
            try:
                data = self.fetch_stock_data(symbol)
                self.save_to_database(symbol, data)
                print(f"✅ Actualizado: {symbol}")
            except Exception as e:
                print(f"❌ Error con {symbol}: {e}")
    
    def fetch_stock_data(self, symbol):
        """Obtiene datos de una acción específica"""
        params = {
            'function': 'TIME_SERIES_INTRADAY',
            'symbol': symbol,
            'interval': '15min',
            'apikey': self.api_key
        }
        response = requests.get(self.base_url, params=params)
        return response.json()
    
    def save_to_database(self, symbol, data):
        """Guarda datos en la base de datos"""
        # Implementar lógica de guardado
        pass

# Uso
updater = StockDataUpdater()
defense_stocks = ['LMT', 'RTX', 'BA', 'GD', 'NOC']
updater.update_sector_data(defense_stocks)
```

## 5. Análisis de Sentimiento de Noticias

### Script de Análisis de Noticias
```python
import nltk
from textblob import TextBlob
import requests
from transformers import pipeline

class NewsAnalyzer:
    def __init__(self):
        self.sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model="ProsusAI/finbert"
        )
    
    def analyze_news_impact(self, company_symbol):
        """Analiza noticias y calcula impacto en precio"""
        news = self.fetch_news(company_symbol)
        analyzed_news = []
        
        for article in news:
            sentiment = self.analyze_sentiment(article['title'] + ' ' + article['description'])
            impact_score = self.calculate_impact_score(sentiment, article)
            
            analyzed_news.append({
                'headline': article['title'],
                'sentiment': sentiment['score'],
                'impact_score': impact_score,
                'published_at': article['publishedAt']
            })
        
        return analyzed_news
    
    def analyze_sentiment(self, text):
        """Analiza sentimiento de texto financiero"""
        result = self.sentiment_analyzer(text)[0]
        return {
            'label': result['label'],
            'score': result['score'] if result['label'] == 'positive' else -result['score']
        }
    
    def calculate_impact_score(self, sentiment, article):
        """Calcula score de impacto basado en múltiples factores"""
        base_score = abs(sentiment['score'])
        
        # Factores que amplifican el impacto
        source_weight = {
            'reuters.com': 1.2,
            'bloomberg.com': 1.2,
            'wsj.com': 1.1,
            'cnbc.com': 1.0,
            'default': 0.8
        }
        
        # Palabras clave que indican alto impacto
        high_impact_keywords = [
            'earnings', 'revenue', 'profit', 'loss', 'merger', 'acquisition',
            'lawsuit', 'regulation', 'contract', 'order', 'guidance'
        ]
        
        keyword_multiplier = 1.0
        text_lower = (article.get('title', '') + ' ' + article.get('description', '')).lower()
        
        for keyword in high_impact_keywords:
            if keyword in text_lower:
                keyword_multiplier += 0.1
        
        source = article.get('source', {}).get('name', 'default').lower()
        source_mult = source_weight.get(source, source_weight['default'])
        
        final_score = min(base_score * source_mult * keyword_multiplier, 1.0)
        return final_score
```

## 6. Dashboard Dinámico (React)

### Componente Principal
```jsx
import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const DynamicStockDashboard = () => {
    const [selectedSector, setSelectedSector] = useState('defense');
    const [stockData, setStockData] = useState([]);
    const [newsData, setNewsData] = useState([]);
    const [lastUpdate, setLastUpdate] = useState(null);

    // WebSocket para actualizaciones en tiempo real
    useEffect(() => {
        const ws = new WebSocket('ws://localhost:8080/stocks');
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            updateStockData(data);
            setLastUpdate(new Date());
        };

        return () => ws.close();
    }, []);

    const sectorConfigs = {
        defense: {
            name: 'Defensa y Aeroespacial',
            stocks: ['LMT', 'RTX', 'BA', 'GD', 'NOC'],
            color: '#8B5CF6'
        },
        tech: {
            name: 'Tecnología',
            stocks: ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META'],
            color: '#10B981'
        },
        finance: {
            name: 'Servicios Financieros',
            stocks: ['JPM', 'BAC', 'WFC', 'GS', 'MS'],
            color: '#F59E0B'
        },
        healthcare: {
            name: 'Salud',
            stocks: ['JNJ', 'PFE', 'UNH', 'MRK', 'ABT'],
            color: '#EF4444'
        },
        energy: {
            name: 'Energía',
            stocks: ['XOM', 'CVX', 'COP', 'EOG', 'SLB'],
            color: '#06B6D4'
        }
    };

    return (
        <div className="p-6 bg-gray-100 min-h-screen">
            <div className="mb-6">
                <h1 className="text-3xl font-bold text-gray-800 mb-4">
                    Monitor Dinámico de Sectores Bursátiles
                </h1>
                
                {/* Selector de Sector */}
                <div className="flex space-x-4 mb-4">
                    {Object.entries(sectorConfigs).map(([key, config]) => (
                        <button
                            key={key}
                            onClick={() => setSelectedSector(key)}
                            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                                selectedSector === key
                                    ? 'bg-blue-600 text-white'
                                    : 'bg-white text-gray-700 hover:bg-gray-50'
                            }`}
                        >
                            {config.name}
                        </button>
                    ))}
                </div>

                {/* Indicador de Última Actualización */}
                <div className="text-sm text-gray-600">
                    Última actualización: {lastUpdate ? lastUpdate.toLocaleTimeString() : 'Cargando...'}
                    <span className="ml-2 inline-block w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                </div>
            </div>

            {/* Dashboard Content */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Gráfico Principal */}
                <div className="lg:col-span-2 bg-white rounded-lg shadow-lg p-6">
                    <h2 className="text-xl font-semibold mb-4">
                        Rendimiento - {sectorConfigs[selectedSector].name}
                    </h2>
                    <ResponsiveContainer width="100%" height={400}>
                        <LineChart data={stockData}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="date" />
                            <YAxis />
                            <Tooltip />
                            {sectorConfigs[selectedSector].stocks.map((stock, index) => (
                                <Line 
                                    key={stock}
                                    type="monotone" 
                                    dataKey={stock}
                                    stroke={`hsl(${index * 60}, 70%, 50%)`}
                                    strokeWidth={2}
                                />
                            ))}
                        </LineChart>
                    </ResponsiveContainer>
                </div>

                {/* Panel de Noticias */}
                <div className="bg-white rounded-lg shadow-lg p-6">
                    <h2 className="text-xl font-semibold mb-4">Noticias Relevantes</h2>
                    <div className="space-y-4 max-h-96 overflow-y-auto">
                        {newsData.map((news, index) => (
                            <NewsItem key={index} news={news} />
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};
```

## 7. Configuración de WebSocket Server

### Server Node.js
```javascript
const WebSocket = require('ws');
const express = require('express');
const app = express();

const wss = new WebSocket.Server({ port: 8080 });

// Simulador de datos en tiempo real
setInterval(() => {
    const mockData = {
        timestamp: new Date().toISOString(),
        prices: {
            'LMT': Math.random() * 500 + 400,
            'RTX': Math.random() * 100 + 50,
            'BA': Math.random() * 200 + 100
        },
        news: {
            headline: "Market Update",
            impact: Math.random()
        }
    };

    wss.clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify(mockData));
        }
    });
}, 15000); // Cada 15 segundos

console.log('WebSocket server running on port 8080');
```

## 8. Automatización con GitHub Actions

### Workflow de Actualización
```yaml
name: Update Stock Data

on:
  schedule:
    - cron: '*/15 9-16 * * 1-5'  # Cada 15 min durante horario de mercado
  workflow_dispatch:

jobs:
  update-data:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Update stock data
        env:
          API_KEY: ${{ secrets.ALPHA_VANTAGE_API_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          python scripts/update_stock_data.py
      
      - name: Deploy to production
        run: |
          # Comandos de deployment
```

## 9. Métricas y Monitoreo

### Dashboard de Métricas
```python
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def create_monitoring_dashboard():
    st.title("📊 Monitor del Sistema de Trading")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("APIs Activas", "8/10", "2")
        
    with col2:
        st.metric("Actualizaciones/Hora", "240", "15")
        
    with col3:
        st.metric("Precisión de Predicciones", "78.5%", "2.1%")
    
    # Gráfico de rendimiento del sistema
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Latencia API', 'Memoria Uso', 'CPU Uso', 'Errores por Hora')
    )
    
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    create_monitoring_dashboard()
```

## 10. Configuración de Alertas

### Sistema de Notificaciones
```python
import smtplib
from email.mime.text import MIMEText
import requests

class AlertSystem:
    def __init__(self):
        self.email_config = {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'username': os.getenv('EMAIL_USERNAME'),
            'password': os.getenv('EMAIL_PASSWORD')
        }
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
    
    def send_price_alert(self, symbol, current_price, threshold):
        if current_price > threshold:
            message = f"🚨 ALERTA: {symbol} ha superado ${threshold}. Precio actual: ${current_price}"
            self.send_email_alert(message)
            self.send_slack_alert(message)
    
    def send_news_alert(self, symbol, news_headline, impact_score):
        if impact_score > 0.7:
            message = f"📰 NOTICIA IMPORTANTE: {symbol}\n{news_headline}\nImpacto estimado: {impact_score:.2%}"
            self.send_slack_alert(message)
```

Este sistema te permitirá crear un monitor dinámico y completamente automatizado para cualquier sector del mercado de valores, con actualizaciones en tiempo real basadas en noticias y eventos del mercado.