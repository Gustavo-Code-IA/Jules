#!/usr/bin/env python3
"""
Suite de tests para el sistema de monitoreo de red
Incluye tests unitarios e integración
"""

import pytest
import asyncio
import tempfile
import json
import yaml
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import sqlite3

# Importar módulos del proyecto
from network_monitor import NetworkMonitor
from alert_system import AlertSystem
from config_manager import ConfigManager
from data_storage import DataStorage
from report_generator import ReportGenerator

class TestConfigManager:
    """Tests para ConfigManager"""
    
    def test_load_valid_config(self):
        """Test cargar configuración válida"""
        config_data = {
            'monitoring': {
                'hosts': ['192.168.1.1', 'google.com'],
                'interval': 60
            },
            'database': {
                'type': 'sqlite',
                'path': 'test.db'
            },
            'alerts': {
                'email': {'enabled': True}
            },
            'reports': {
                'output_dir': 'reports'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config_manager = ConfigManager(config_path)
            loaded_config = config_manager.load_config()
            
            assert loaded_config['monitoring']['interval'] == 60
            assert len(loaded_config['monitoring']['hosts']) == 2
            assert loaded_config['database']['type'] == 'sqlite'
            
        finally:
            Path(config_path).unlink()
    
    def test_load_invalid_config(self):
        """Test cargar configuración inválida"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            config_path = f.name
        
        try:
            config_manager = ConfigManager(config_path)
            with pytest.raises(yaml.YAMLError):
                config_manager.load_config()
        finally:
            Path(config_path).unlink()
    
    def test_validate_config_missing_section(self):
        """Test validación con sección faltante"""
        config_data = {
            'monitoring': {'hosts': ['test.com']}
            # Falta sección 'database'
        }
        
        config_manager = ConfigManager()
        with pytest.raises(ValueError, match="database"):
            config_manager.validate_config(config_data)

class TestDataStorage:
    """Tests para DataStorage"""
    
    @pytest.fixture
    def temp_db_config(self):
        """Configuración temporal de base de datos"""
        return {
            'type': 'sqlite',
            'path': ':memory:'  # Base de datos en memoria para tests
        }
    
    @pytest.mark.asyncio
    async def test_initialize_database(self, temp_db_config):
        """Test inicialización de base de datos"""
        storage = DataStorage(temp_db_config)
        await storage.initialize()
        
        # Verificar que las tablas existen
        assert storage.conn is not None
        
        cursor = storage.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['network_metrics', 'alerts', 'device_status']
        for table in expected_tables:
            assert table in tables
        
        await storage.close()
    
    @pytest.mark.asyncio
    async def test_store_metric(self, temp_db_config):
        """Test almacenar métrica"""
        storage = DataStorage(temp_db_config)
        await storage.initialize()
        
        metric_data = {
            'timestamp': '2024-06-13T10:00:00',
            'host': '192.168.1.1',
            'metric_type': 'ping',
            'value': 25.5,
            'status': 'success'
        }
        
        await storage.store_metric(metric_data)
        
        # Verificar que se almacenó
        cursor = storage.conn.execute(
            "SELECT * FROM network_metrics WHERE host = ?",
            (metric_data['host'],)
        )
        result = cursor.fetchone()
        
        assert result is not None
        assert result['host'] == metric_data['host']
        assert result['metric_type'] == metric_data['metric_type']
        
        await storage.close()
    
    @pytest.mark.asyncio
    async def test_health_check(self, temp_db_config):
        """Test verificación de salud"""
        storage = DataStorage(temp_db_config)
        await storage.initialize()
        
        is_healthy = await storage.health_check()
        assert is_healthy is True
        
        await storage.close()

class TestAlertSystem:
    """Tests para AlertSystem"""
    
    @pytest.fixture
    def alert_config(self):
        """Configuración de alertas para tests"""
        return {
            'email': {
                'enabled': True,
                'smtp_server': 'localhost',
                'smtp_port': 587,
                'from_email': 'test@example.com',
                'to_emails': ['admin@example.com']
            },
            'thresholds': {
                'ping_timeout': 5000,
                'packet_loss': 10
            }
        }
    
    def test_create_alert_system(self, alert_config):
        """Test creación del sistema de alertas"""
        alert_system = AlertSystem(alert_config)
        
        assert alert_system.config == alert_config
        assert alert_system.is_healthy() is True
    
    @pytest.mark.asyncio
    @patch('smtplib.SMTP')
    async def test_send_email_alert(self, mock_smtp, alert_config):
        """Test envío de alerta por email"""
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        
        alert_system = AlertSystem(alert_config)
        
        alert_data = {
            'type': 'connectivity',
            'severity': 'high',
            'host': '192.168.1.1',
            'message': 'Host no responde',
            'timestamp': '2024-06-13T10:00:00'
        }
        
        await alert_system.send_alert(alert_data)
        
        # Verificar que se intentó enviar el email
        mock_smtp.assert_called_once()
        mock_server.send_message.assert_called_once()
    
    def test_should_trigger_alert(self, alert_config):
        """Test lógica de activación de alertas"""
        alert_system = AlertSystem(alert_config)
        
        # Caso que debe activar alerta
        metric_high_latency = {
            'metric_type': 'ping',
            'value': 6000,  # Mayor al threshold
            'status': 'timeout'
        }
        
        should_alert = alert_system.should_trigger_alert(metric_high_latency)
        assert should_alert is True
        
        # Caso que NO debe activar alerta
        metric_normal = {
            'metric_type': 'ping',
            'value': 50,  # Menor al threshold
            'status': 'success'
        }
        
        should_alert = alert_system.should_trigger_alert(metric_normal)
        assert should_alert is False

class TestNetworkMonitor:
    """Tests para NetworkMonitor"""
    
    @pytest.fixture
    def monitor_config(self):
        """Configuración del monitor para tests"""
        return {
            'hosts': ['127.0.0.1', 'localhost'],
            'interval': 1,  # 1 segundo para tests rápidos
            'timeout': 1,
            'ping_count': 1
        }
    
    @pytest.fixture
    def mock_storage(self):
        """Mock del sistema de almacenamiento"""
        storage = Mock()
        storage.store_metric = AsyncMock()
        return storage
    
    @pytest.fixture
    def mock_alerts(self):
        """Mock del sistema de alertas"""
        alerts = Mock()
        alerts.should_trigger_alert = Mock(return_value=False)
        alerts.send_alert = AsyncMock()
        return alerts
    
    def test_create_monitor(self, monitor_config, mock_storage, mock_alerts):
        """Test creación del monitor"""
        monitor = NetworkMonitor(monitor_config, mock_storage, mock_alerts)
        
        assert monitor.config == monitor_config
        assert monitor.data_storage == mock_storage
        assert monitor.alert_system == mock_alerts
    
    @pytest.mark.asyncio
    async def test_ping_host_success(self, monitor_config, mock_storage, mock_alerts):
        """Test ping exitoso"""
        monitor = NetworkMonitor(monitor_config, mock_storage, mock_alerts)
        
        # Test con localhost que debería responder
        result = await monitor.ping_host('127.0.0.1')
        
        assert 'timestamp' in result
        assert result['host'] == '127.0.0.1'
        assert result['metric_type'] == 'ping'
        assert 'value' in result
        assert 'status' in result
    
    @pytest.mark.asyncio
    async def test_ping_host_timeout(self, monitor_config, mock_storage, mock_alerts):
        """Test ping con timeout"""
        # Usar IP que no existe para forzar timeout
        monitor_config['hosts'] = ['192.0.2.1']  # IP de documentación RFC 5737
        monitor_config['timeout'] = 0.1  # Timeout muy pequeño
        
        monitor = NetworkMonitor(monitor_config, mock_storage, mock_alerts)
        
        result = await monitor.ping_host('192.0.2.1')
        
        assert result['host'] == '192.0.2.1'
        assert 'error' in result['status'].lower() or 'timeout' in result['status'].lower()
    
    def test_is_healthy(self, monitor_config, mock_storage, mock_alerts):
        """Test verificación de salud del monitor"""
        monitor = NetworkMonitor(monitor_config, mock_storage, mock_alerts)
        
        # Por defecto debería estar saludable
        assert monitor.is_healthy() is True

class TestReportGenerator:
    """Tests para ReportGenerator"""
    
    @pytest.fixture
    def report_config(self):
        """Configuración de reportes para tests"""
        return {
            'output_dir': 'test_reports',
            'formats': ['json', 'html'],
            'include_charts': True
        }
    
    @pytest.fixture
    def mock_storage_with_data(self):
        """Mock de storage con datos de prueba"""
        storage = Mock()
        
        # Datos de prueba
        sample_metrics = [
            {
                'timestamp': '2024-06-13T09:00:00',
                'host': '192.168.1.1',
                'metric_type': 'ping',
                'value': 25.5,
                'status': 'success'
            },
            {
                'timestamp': '2024-06-13T09:01:00',
                'host': '192.168.1.1',
                'metric_type': 'ping',
                'value': 30.2,
                'status': 'success'
            }
        ]
        
        storage.get_metrics = AsyncMock(return_value=sample_metrics)
        storage.get_summary_stats = AsyncMock(return_value={
            'total_hosts': 2,
            'active_hosts': 2,
            'avg_latency': 27.85,
            'uptime_percentage': 100.0
        })
        
        return storage
    
    @pytest.mark.asyncio
    async def test_generate_summary_report(self, report_config, mock_storage_with_data):
        """Test generación de reporte resumen"""
        # Crear directorio temporal para reportes
        with tempfile.TemporaryDirectory() as temp_dir:
            report_config['output_dir'] = temp_dir
            
            generator = ReportGenerator(mock_storage_with_data, report_config)
            report = await generator.generate_summary_report()
            
            assert 'filename' in report
            assert 'summary' in report
            assert report['summary']['total_hosts'] == 2
            assert report['summary']['avg_latency'] == 27.85
            
            # Verificar que se creó el archivo
            report_file = Path(temp_dir) / report['filename']
            assert report_file.exists()

class TestIntegration:
    """Tests de integración"""
    
    @pytest.mark.asyncio
    async def test_full_monitoring_cycle(self):
        """Test del ciclo completo de monitoreo"""
        # Configuración mínima para test de integración
        config = {
            'monitoring': {
                'hosts': ['127.0.0.1'],
                'interval': 1,
                'timeout': 1
            },
            'database': {
                'type': 'sqlite',
                'path': ':memory:'
            },
            'alerts': {
                'email': {'enabled': False},
                'thresholds': {'ping_timeout': 5000}
            },
            'reports': {
                'output_dir': 'test_reports'
            }
        }
        
        # Inicializar componentes
        storage = DataStorage(config['database'])
        await storage.initialize()
        
        alert_system = AlertSystem(config['alerts'])
        monitor = NetworkMonitor(config['monitoring'], storage, alert_system)
        
        # Ejecutar un ciclo de monitoreo
        result = await monitor.ping_host('127.0.0.1')
        await storage.store_metric(result)
        
        # Verificar que se almacenó correctamente
        cursor = storage.conn.execute(
            "SELECT COUNT(*) as count FROM network_metrics"
        )
        count = cursor.fetchone()['count']
        
        assert count == 1
        
        await storage.close()

# Configuración de pytest
def pytest_configure(config):
    """Configuración de pytest"""
    # Marcar tests asíncronos
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )

# Fixtures globales
@pytest.fixture(scope="session")
def event_loop():
    """Crear event loop para toda la sesión de tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

if __name__ == "__main__":
    # Ejecutar tests directamente
    pytest.main([__file__, "-v"])