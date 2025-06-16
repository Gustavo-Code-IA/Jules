import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { TrendingUp, TrendingDown, Bell, RefreshCw, DollarSign, Calendar, AlertTriangle } from 'lucide-react';

const DynamicStockDashboard = () => {
  const [selectedSector, setSelectedSector] = useState('defense');
  const [stockData, setStockData] = useState([]);
  const [currentPrices, setCurrentPrices] = useState({});
  const [newsData, setNewsData] = useState([]);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [isLoading, setIsLoading] = useState(false);

  // Configuración de sectores
  const sectorConfigs = {
    defense: {
      name: 'Defensa y Aeroespacial',
      stocks: [
        { symbol: 'LMT', name: 'Lockheed Martin', price: 456.60, change: 2.3, volume: 1200000 },
        { symbol: 'RTX', name: 'Raytheon Technologies', price: 142.50, change: -1.2, volume: 2100000 },
        { symbol: 'BA', name: 'Boeing', price: 241.01, change: -5.0, volume: 8500000 },
        { symbol: 'GD', name: 'General Dynamics', price: 296.09, change: 1.8, volume: 890000 },
        { symbol: 'NOC', name: 'Northrop Grumman', price: 452.31, change: 0.9, volume: 650000 }
      ],
      color: '#8B5CF6',
      ytdReturn: 21.44
    },
    tech: {
      name: 'Tecnología',
      stocks: [
        { symbol: 'AAPL', name: 'Apple Inc.', price: 193.12, change: 1.5, volume: 45000000 },
        { symbol: 'MSFT', name: 'Microsoft Corp.', price: 416.42, change: 0.8, volume: 25000000 },
        { symbol: 'GOOGL', name: 'Alphabet Inc.', price: 175.23, change: -0.3, volume: 18000000 },
        { symbol: 'AMZN', name: 'Amazon.com Inc.', price: 186.51, change: 2.1, volume: 35000000 },
        { symbol: 'META', name: 'Meta Platforms', price: 497.21, change: -1.1, volume: 15000000 }
      ],
      color: '#10B981',
      ytdReturn: 18.7
    },
    finance: {
      name: 'Servicios Financieros',
      stocks: [
        { symbol: 'JPM', name: 'JPMorgan Chase', price: 199.45, change: 0.6, volume: 12000000 },
        { symbol: 'BAC', name: 'Bank of America', price: 39.78, change: -0.2, volume: 45000000 },
        { symbol: 'WFC', name: 'Wells Fargo', price: 56.23, change: 1.2, volume: 25000000 },
        { symbol: 'GS', name: 'Goldman Sachs', price: 456.78, change: -0.8, volume: 2100000 },
        { symbol: 'MS', name: 'Morgan Stanley', price: 102.34, change: 0.4, volume: 8900000 }
      ],
      color: '#F59E0B',
      ytdReturn: 15.2
    },
    healthcare: {
      name: 'Salud',
      stocks: [
        { symbol: 'JNJ', name: 'Johnson & Johnson', price: 152.67, change: 0.3, volume: 8500000 },
        { symbol: 'PFE', name: 'Pfizer Inc.', price: 28.91, change: -1.8, volume: 35000000 },
        { symbol: 'UNH', name: 'UnitedHealth Group', price: 562.45, change: 1.1, volume: 2800000 },
        { symbol: 'MRK', name: 'Merck & Co.', price: 125.89, change: 0.7, volume: 12000000 },
        { symbol: 'ABT', name: 'Abbott Laboratories', price: 108.23, change: -0.4, volume: 6700000 }
      ],
      color: '#EF4444',
      ytdReturn: 12.8
    },
    energy: {
      name: 'Energía',
      stocks: [
        { symbol: 'XOM', name: 'Exxon Mobil', price: 117.34, change: 2.8, volume: 18000000 },
        { symbol: 'CVX', name: 'Chevron Corp.', price: 162.45, change: 1.9, volume: 12000000 },
        { symbol: 'COP', name: 'ConocoPhillips', price: 109.78, change: 3.2, volume: 8900000 },
        { symbol: 'EOG', name: 'EOG Resources', price: 134.56, change: 1.5, volume: 6700000 },
        { symbol: 'SLB', name: 'Schlumberger', price: 45.23, change: 0.8, volume: 15000000 }
      ],
      color: '#06B6D4',
      ytdReturn: 24.1
    }
  };

  // Generar datos históricos simulados
  const generateHistoricalData = (stocks) => {
    const days = 30;
    const data = [];
    
    for (let i = days; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      
      const dataPoint = {
        date: date.toLocaleDateString(),
        timestamp: date.getTime()
      };
      
      stocks.forEach(stock => {
        const basePrice = stock.price;
        const volatility = 0.02; // 2% volatilidad diaria
        const randomChange = (Math.random() - 0.5) * volatility * 2;
        dataPoint[stock.symbol] = Number((basePrice * (1 + randomChange)).toFixed(2));
      });
      
      data.push(dataPoint);
    }
    
    return data;
  };

  // Generar noticias simuladas
  const generateNews = (sector) => {
    const newsTemplates = {
      defense: [
        { headline: "Lockheed Martin wins $2.4B defense contract", sentiment: 0.8, impact: 0.7, source: "Reuters" },
        { headline: "Boeing faces production delays on military aircraft", sentiment: -0.6, impact: 0.8, source: "Bloomberg" },
        { headline: "Pentagon increases defense spending by 3.2%", sentiment: 0.9, impact: 0.9, source: "WSJ" },
        { headline: "Raytheon completes missile system tests successfully", sentiment: 0.7, impact: 0.6, source: "CNBC" }
      ],
      tech: [
        { headline: "Apple announces new AI chip breakthrough", sentiment: 0.9, impact: 0.8, source: "TechCrunch" },
        { headline: "Microsoft Azure gains market share vs AWS", sentiment: 0.6, impact: 0.7, source: "Bloomberg" },
        { headline: "Alphabet faces antitrust investigation", sentiment: -0.8, impact: 0.9, source: "Reuters" },
        { headline: "Meta's VR division shows strong growth", sentiment: 0.7, impact: 0.6, source: "CNBC" }
      ],
      finance: [
        { headline: "JPMorgan beats earnings expectations", sentiment: 0.8, impact: 0.7, source: "WSJ" },
        { headline: "Fed signals potential rate cuts", sentiment: 0.9, impact: 0.9, source: "Reuters" },
        { headline: "Banking sector faces regulatory scrutiny", sentiment: -0.6, impact: 0.8, source: "Bloomberg" },
        { headline: "Wells Fargo improves credit quality metrics", sentiment: 0.5, impact: 0.5, source: "CNBC" }
      ]
    };

    return newsTemplates[sector] || newsTemplates.defense;
  };

  // Actualizar datos
  const updateData = () => {
    setIsLoading(true);
    
    setTimeout(() => {
      const currentSector = sectorConfigs[selectedSector];
      setStockData(generateHistoricalData(currentSector.stocks));
      setNewsData(generateNews(selectedSector));
      setLastUpdate(new Date());
      setIsLoading(false);
    }, 1000);
  };

  // Efecto para actualizar datos cuando cambia el sector
  useEffect(() => {
    updateData();
  }, [selectedSector]);

  // Actualización automática cada 30 segundos
  useEffect(() => {
    const interval = setInterval(() => {
      updateData();
    }, 30000);
    
    return () => clearInterval(interval);
  }, [selectedSector]);

  const currentSector = sectorConfigs[selectedSector];

  return (
    <div className="p-6 bg-gradient-to-br from-gray-50 to-gray-100 min-h-screen">
      {/* Header */}
      <div className="mb-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-4xl font-bold text-gray-800 flex items-center gap-3">
            <DollarSign className="text-green-600" size={36} />
            Monitor Dinámico de Sectores Bursátiles
          </h1>
          <button
            onClick={updateData}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            {isLoading ? 'Actualizando...' : 'Actualizar'}
          </button>
        </div>
        
        {/* Selector de Sector */}
        <div className="flex flex-wrap gap-3 mb-6">
          {Object.entries(sectorConfigs).map(([key, config]) => (
            <button
              key={key}
              onClick={() => setSelectedSector(key)}
              className={`px-6 py-3 rounded-xl font-medium transition-all transform hover:scale-105 ${
                selectedSector === key
                  ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg'
                  : 'bg-white text-gray-700 hover:bg-gray-50 shadow-md'
              }`}
            >
              <div className="flex items-center gap-2">
                <div 
                  className="w-3 h-3 rounded-full" 
                  style={{ backgroundColor: config.color }}
                ></div>
                {config.name}
              </div>
            </button>
          ))}
        </div>

        {/* Métricas del Sector */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl p-4 shadow-md">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Rendimiento YTD</p>
                <p className="text-2xl font-bold text-green-600">+{currentSector.ytdReturn}%</p>
              </div>
              <TrendingUp className="text-green-600" size={24} />
            </div>
          </div>
          
          <div className="bg-white rounded-xl p-4 shadow-md">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Empresas Seguidas</p>
                <p className="text-2xl font-bold text-blue-600">{currentSector.stocks.length}</p>
              </div>
              <DollarSign className="text-blue-600" size={24} />
            </div>
          </div>
          
          <div className="bg-white rounded-xl p-4 shadow-md">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Última Actualización</p>
                <p className="text-sm font-medium text-gray-800">
                  {lastUpdate.toLocaleTimeString()}
                </p>
              </div>
              <Calendar className="text-gray-600" size={24} />
            </div>
          </div>
          
          <div className="bg-white rounded-xl p-4 shadow-md">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Estado del Mercado</p>
                <p className="text-sm font-medium text-green-600 flex items-center gap-1">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  En Vivo
                </p>
              </div>
              <Bell className="text-green-600" size={24} />
            </div>
          </div>
        </div>
      </div>

      {/* Dashboard Content */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Gráfico Principal */}
        <div className="xl:col-span-3 bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
            <TrendingUp className="text-blue-600" size={24} />
            Rendimiento Histórico - {currentSector.name}
          </h2>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={stockData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis 
                dataKey="date" 
                tick={{ fontSize: 12 }}
                axisLine={false}
              />
              <YAxis 
                tick={{ fontSize: 12 }}
                axisLine={false}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'rgba(255, 255, 255, 0.95)', 
                  border: 'none', 
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                }}
              />
              {currentSector.stocks.map((stock, index) => (
                <Line 
                  key={stock.symbol}
                  type="monotone" 
                  dataKey={stock.symbol}
                  stroke={`hsl(${index * 60 + 200}, 70%, 50%)`}
                  strokeWidth={2}
                  dot={false}
                  name={stock.name}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Panel de Noticias */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Bell className="text-orange-600" size={20} />
            Noticias Relevantes
          </h2>
          <div className="space-y-4 max-h-96 overflow-y-auto">
            {newsData.map((news, index) => (
              <div key={index} className="border-l-4 border-blue-500 pl-4 py-2">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-medium text-gray-800 text-sm leading-tight">
                    {news.headline}
                  </h3>
                  {news.sentiment > 0 ? (
                    <TrendingUp className="text-green-500 flex-shrink-0 ml-2" size={16} />
                  ) : (
                    <TrendingDown className="text-red-500 flex-shrink-0 ml-2" size={16} />
                  )}
                </div>
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>{news.source}</span>
                  <div className="flex items-center gap-2">
                    <span>Impacto: {(news.impact * 100).toFixed(0)}%</span>
                    <div 
                      className="w-2 h-2 rounded-full"
                      style={{ 
                        backgroundColor: news.impact > 0.7 ? '#EF4444' : news.impact > 0.4 ? '#F59E0B' : '#10B981' 
                      }}
                    ></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Tabla de Precios Actuales */}
      <div className="mt-6 bg-white rounded-xl shadow-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Precios Actuales - {currentSector.name}</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b-2 border-gray-200">
                <th className="text-left py-3 px-4 font-semibold text-gray-700">Símbolo</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-700">Empresa</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">Precio</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">Cambio</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">Volumen</th>
              </tr>
            </thead>
            <tbody>
              {currentSector.stocks.map((stock, index) => (
                <tr key={stock.symbol} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-4 font-medium text-blue-600">{stock.symbol}</td>
                  <td className="py-3 px-4 text-gray-800">{stock.name}</td>
                  <td className="py-3 px-4 text-right font-medium">${stock.price.toFixed(2)}</td>
                  <td className={`py-3 px-4 text-right font-medium ${stock.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {stock.change >= 0 ? '+' : ''}{stock.change.toFixed(2)}%
                  </td>
                  <td className="py-3 px-4 text-right text-gray-600">
                    {stock.volume.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default DynamicStockDashboard;