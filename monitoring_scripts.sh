#!/bin/bash

# Script de monitoreo y gestión del sistema de red
# Incluye funciones de inicio, parada, estado y mantenimiento

set -euo pipefail

# Configuración
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="${PROJECT_DIR}/config.yaml"
PID_FILE="${PROJECT_DIR}/data/network_monitor.pid"
LOG_FILE="${PROJECT_DIR}/logs/monitor.log"
PYTHON_EXEC="${PYTHON_EXEC:-python3}"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funciones de utilidad
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
    log "ERROR: $1"
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
    log "SUCCESS: $1"
}

warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
    log "WARNING: $1"
}

info() {
    echo -e "${BLUE}ℹ $1${NC}"
    log "INFO: $1"
}

# Verificar dependencias
check_dependencies() {
    local deps=("$PYTHON_EXEC" "ping" "curl")
    local missing=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            missing+=("$dep")
        fi
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        error "Dependencias faltantes: ${missing[*]}"
        return 1
    fi
    
    return 0
}

# Crear directorios necesarios
create_directories() {
    local dirs=("${PROJECT_DIR}/data" "${PROJECT_DIR}/logs" "${PROJECT_DIR}/reports")
    
    for dir in "${dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            info "Directorio creado: $dir"
        fi
    done
}

# Verificar si el proceso está corriendo
is_running() {
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        else
            # PID file existe pero proceso no
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Obtener PID del proceso
get_pid() {
    if [[ -f "$PID_FILE" ]]; then
        cat "$PID_FILE"
    else
        echo ""
    fi
}

# Iniciar el sistema
start_monitor() {
    info "Iniciando sistema de monitoreo de red..."
    
    # Verificar si ya está corriendo
    if is_running; then
        warning "El sistema ya está corriendo (PID: $(get_pid))"
        return 0
    fi
    
    # Verificar dependencias
    if ! check_dependencies; then
        return 1
    fi
    
    # Crear directorios
    create_directories
    
    # Verificar configuración
    if [[ ! -f "$CONFIG_FILE" ]]; then
        error "Archivo de configuración no encontrado: $CONFIG_FILE"
        return 1
    fi
    
    # Validar configuración
    if ! "$PYTHON_EXEC" "$PROJECT_DIR/main.py" --validate-config --config "$CONFIG_FILE"; then
        error "Configuración inválida"
        return 1
    fi
    
    # Iniciar proceso en background
    nohup "$PYTHON_EXEC" "$PROJECT_DIR/main.py" --config "$CONFIG_FILE" \
        > "$LOG_FILE" 2>&1 &
    
    local pid=$!
    echo "$pid" > "$PID_FILE"
    
    # Esperar un momento para verificar que inició correctamente
    sleep 3
    
    if is_running; then
        success "Sistema iniciado correctamente (PID: $pid)"
        return 0
    else
        error "Falló al iniciar el sistema"
        return 1
    fi
}

# Detener el sistema
stop_monitor() {
    info "Deteniendo sistema de monitoreo de red..."
    
    if ! is_running; then
        warning "El sistema no está corriendo"
        return 0
    fi
    
    local pid=$(get_pid)
    
    # Intentar parada graceful
    kill -TERM "$pid" 2>/dev/null
    
    # Esperar hasta 30 segundos para parada graceful
    local count=0
    while kill -0 "$pid" 2>/dev/null && [[ $count -lt 30 ]]; do
        sleep 1
        ((count++))
    done
    
    # Si aún está corriendo, forzar parada
    if kill -0 "$pid" 2>/dev/null; then
        warning "Forzando parada del proceso..."
        kill -KILL "$pid" 2>/dev/null
        sleep 2
    fi
    
    # Limpiar PID file
    rm -f "$PID_FILE"
    
    success "Sistema detenido correctamente"
}

# Reiniciar el sistema
restart_monitor() {
    info "Reiniciando sistema de monitoreo de red..."
    stop_monitor
    sleep 2
    start_monitor
}

# Mostrar estado del sistema
status_monitor() {
    echo "=== Estado del Sistema de Monitoreo de Red ==="
    
    if is_running; then
        local pid=$(get_pid)
        success "Sistema corriendo (PID: $pid)"
        
        # Información adicional del proceso
        if command -v ps >/dev/null 2>&1; then
            echo ""
            echo "Información del proceso:"
            ps -p "$pid" -o pid,ppid,pcpu,pmem,etime,cmd 2>/dev/null || true
        fi
        
        # Verificar health check si está disponible
        if command -v curl >/dev/null 2>&1; then
            echo ""
            info "Verificando health check..."
            if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health 2>/dev/null | grep -q "200"; then
                success "Health check OK"
            else
                warning "Health check no disponible o falló"
            fi
        fi
        
    else
        error "Sistema no está corriendo"
    fi
    
    # Información de archivos
    echo ""
    echo "Archivos del sistema:"
    echo "  Configuración: $CONFIG_FILE $([ -f "$CONFIG_FILE" ] && echo "✓" || echo "✗")"
    echo "  PID file: $PID_FILE $([ -f "$PID_FILE" ] && echo "✓" || echo "✗")"
    echo "  Log file: $LOG_FILE $([ -f "$LOG_FILE" ] && echo "✓" || echo "✗")"
    
    # Tamaño del log
    if [[ -f "$LOG_FILE" ]]; then
        local log_size=$(du -h "$LOG_FILE" | cut -f1)
        echo "  Tamaño del log: $log_size"
    fi
}

# Mostrar logs en tiempo real
logs_monitor() {
    if [[ ! -f "$LOG_FILE" ]]; then
        error "Archivo de log no encontrado: $LOG_FILE"
        return 1
    fi
    
    info "Mostrando logs en tiempo real (Ctrl+C para salir)..."
    tail -f "$LOG_FILE"
}

# Generar reporte
generate_report() {
    info "Generando reporte..."
    
    if ! "$PYTHON_EXEC" "$PROJECT_DIR/main.py" --generate-report --config "$CONFIG_FILE"; then
        error "Falló al generar reporte"
        return 1
    fi
    
    success "Reporte generado correctamente"
}

# Limpiar logs antiguos
cleanup_logs() {
    local days=${1:-7}
    info "Limpiando logs antiguos (mayores a $days días)..."
    
    find "$PROJECT_DIR/logs" -name "*.log*" -type f -mtime +$days -delete 2>/dev/null || true
    find "$PROJECT_DIR/reports" -name "*.json" -type f -mtime +$days -delete 2>/dev/null || true
    find "$PROJECT_DIR/reports" -name "*.html" -type f -mtime +$days -delete 2>/dev/null || true
    
    success "Limpieza de logs completada"
}

# Verificar configuración
check_config() {
    info "Verificando configuración..."
    
    if "$PYTHON_EXEC" "$PROJECT_DIR/main.py" --validate-config --config "$CONFIG_FILE"; then
        success "Configuración válida"
        return 0
    else
        error "Configuración inválida"
        return 1
    fi
}

# Mostrar ayuda
show_help() {
    cat << EOF
Sistema de Monitoreo de Red - Script de Gestión

Uso: $0 [COMANDO] [OPCIONES]

Comandos:
  start         Iniciar el sistema de monitoreo
  stop          Detener el sistema de monitoreo
  restart       Reiniciar el sistema de monitoreo
  status        Mostrar estado del sistema
  logs          Mostrar logs en tiempo real
  report        Generar reporte
  cleanup [N]   Limpiar logs antiguos (N días, default: 7)
  check-config  Verificar configuración
  help          Mostrar esta ayuda

Variables de entorno:
  PYTHON_EXEC   Ejecutable de Python (default: python3)
  CONFIG_FILE   Archivo de configuración (default: config.yaml)

Ejemplos:
  $0 start                  # Iniciar sistema
  $0 status                 # Ver estado
  $0 logs                   # Ver logs en tiempo real
  $0 cleanup 14             # Limpiar logs de más de 14 días
  CONFIG_FILE=prod.yaml $0 start  # Usar configuración personalizada

EOF
}

# Función principal
main() {
    case "${1:-help}" in
        start)
            start_monitor
            ;;
        stop)
            stop_monitor
            ;;
        restart)
            restart_monitor
            ;;
        status)
            status_monitor
            ;;
        logs)
            logs_monitor
            ;;
        report)
            generate_report
            ;;
        cleanup)
            cleanup_logs "${2:-7}"
            ;;
        check-config)
            check_config
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            error "Comando desconocido: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Manejo de señales
trap 'echo ""; warning "Script interrumpido por el usuario"; exit 130' INT TERM

# Ejecutar función principal
main "$@"