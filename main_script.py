#!/usr/bin/env python3
"""
Script principal del sistema de monitoreo de red
Integra todos los componentes del proyecto
"""

import asyncio
import argparse
import logging
import signal
import sys
from pathlib import Path
from typing import Dict, Any
import yaml

from network_monitor import NetworkMonitor
from alert_system import AlertSystem
from config_manager import ConfigManager
from data_storage import DataStorage
from report_generator import ReportGenerator

class NetworkMonitoringSystem:
    """Sistema principal de monitoreo de red"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.load_config()
        
        # Inicializar componentes
        self.data_storage = DataStorage(self.config['database'])
        self.alert_system = AlertSystem(self.config['alerts'])
        self.network_monitor = NetworkMonitor(
            self.config['monitoring'],
            self.data_storage,
            self.alert_system
        )
        self.report_generator = ReportGenerator(
            self.data_storage,
            self.config['reports']
        )
        
        # Control de ejecución
        self.running = False
        self.tasks = []
        
        # Configurar logging
        self.setup_logging()
    
    def setup_logging(self):
        """Configurar sistema de logging"""
        log_config = self.config.get('logging', {})
        
        logging.basicConfig(
            level=getattr(logging, log_config.get('level', 'INFO')),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_config.get('file', 'network_monitor.log')),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Iniciar el sistema de monitoreo"""
        self.logger.info("Iniciando sistema de monitoreo de red...")
        
        try:
            # Inicializar base de datos
            await self.data_storage.initialize()
            
            # Iniciar monitoreo
            self.running = True
            
            # Crear tareas asíncronas
            self.tasks = [
                asyncio.create_task(self.network_monitor.start_monitoring()),
                asyncio.create_task(self.periodic_reports()),
                asyncio.create_task(self.health_check())
            ]
            
            self.logger.info("Sistema iniciado correctamente")
            
            # Esperar hasta que se detenga
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        except Exception as e:
            self.logger.error(f"Error al iniciar el sistema: {e}")
            raise
    
    async def stop(self):
        """Detener el sistema de monitoreo"""
        self.logger.info("Deteniendo sistema de monitoreo...")
        
        self.running = False
        
        # Cancelar tareas
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Esperar a que terminen las tareas
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Cerrar conexiones
        await self.data_storage.close()
        
        self.logger.info("Sistema detenido correctamente")
    
    async def periodic_reports(self):
        """Generar reportes periódicos"""
        report_interval = self.config['reports'].get('interval', 3600)  # 1 hora por defecto
        
        while self.running:
            try:
                await asyncio.sleep(report_interval)
                
                if self.running:
                    # Generar reporte automático
                    report = await self.report_generator.generate_summary_report()
                    self.logger.info(f"Reporte generado: {report.get('filename', 'N/A')}")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error generando reporte periódico: {e}")
    
    async def health_check(self):
        """Verificación de salud del sistema"""
        check_interval = 300  # 5 minutos
        
        while self.running:
            try:
                await asyncio.sleep(check_interval)
                
                if self.running:
                    # Verificar estado de componentes
                    health_status = {
                        'database': await self.data_storage.health_check(),
                        'monitor': self.network_monitor.is_healthy(),
                        'alerts': self.alert_system.is_healthy()
                    }
                    
                    # Log del estado
                    unhealthy = [k for k, v in health_status.items() if not v]
                    if unhealthy:
                        self.logger.warning(f"Componentes no saludables: {unhealthy}")
                    else:
                        self.logger.debug("Todos los componentes están saludables")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error en health check: {e}")
    
    def handle_signal(self, signum, frame):
        """Manejar señales del sistema"""
        self.logger.info(f"Recibida señal {signum}, deteniendo sistema...")
        asyncio.create_task(self.stop())

def parse_arguments():
    """Parsear argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description="Sistema de Monitoreo de Red",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python main.py                    # Usar configuración por defecto
  python main.py -c custom.yaml     # Usar configuración personalizada
  python main.py --generate-report  # Solo generar reporte
  python main.py --validate-config  # Validar configuración
        """
    )
    
    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='Archivo de configuración (default: config.yaml)'
    )
    
    parser.add_argument(
        '--generate-report',
        action='store_true',
        help='Generar reporte y salir'
    )
    
    parser.add_argument(
        '--validate-config',
        action='store_true',
        help='Validar configuración y salir'
    )
    
    parser.add_argument(
        '--daemon',
        action='store_true',
        help='Ejecutar como daemon'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Modo verbose'
    )
    
    return parser.parse_args()

async def generate_report_only(config_path: str):
    """Generar solo un reporte y salir"""
    try:
        config_manager = ConfigManager(config_path)
        config = config_manager.load_config()
        
        data_storage = DataStorage(config['database'])
        await data_storage.initialize()
        
        report_generator = ReportGenerator(data_storage, config['reports'])
        report = await report_generator.generate_summary_report()
        
        print(f"Reporte generado: {report.get('filename', 'N/A')}")
        
        await data_storage.close()
        
    except Exception as e:
        print(f"Error generando reporte: {e}")
        sys.exit(1)

def validate_config_only(config_path: str):
    """Validar solo la configuración y salir"""
    try:
        config_manager = ConfigManager(config_path)
        config = config_manager.load_config()
        
        # Validaciones adicionales
        required_sections = ['monitoring', 'database', 'alerts', 'reports']
        missing_sections = [s for s in required_sections if s not in config]
        
        if missing_sections:
            print(f"Secciones faltantes en configuración: {missing_sections}")
            sys.exit(1)
        
        print("Configuración válida ✓")
        
    except Exception as e:
        print(f"Error en configuración: {e}")
        sys.exit(1)

async def main():
    """Función principal"""
    args = parse_arguments()
    
    # Verificar que existe el archivo de configuración
    if not Path(args.config).exists():
        print(f"Error: Archivo de configuración '{args.config}' no encontrado")
        sys.exit(1)
    
    # Modos especiales
    if args.validate_config:
        validate_config_only(args.config)
        return
    
    if args.generate_report:
        await generate_report_only(args.config)
        return
    
    # Modo normal - iniciar sistema
    try:
        system = NetworkMonitoringSystem(args.config)
        
        # Configurar manejo de señales
        for sig in [signal.SIGTERM, signal.SIGINT]:
            signal.signal(sig, system.handle_signal)
        
        # Iniciar sistema
        await system.start()
        
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario")
    except Exception as e:
        print(f"Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSaliendo...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)