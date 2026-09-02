#!/bin/bash

# Path to the Docker Compose configuration file
COMPOSE_FILE="/opt/rica_s/builder/rica_s-compose.yml"

# Ensure the compose file exists before running commands
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "Error: Compose file not found at $COMPOSE_FILE" >&2
    exit 1
fi

# Base command wrapper
DOCKER_CMD="docker compose -f $COMPOSE_FILE"

usage() {
    echo "Usage: $0 {create|start|stop|restart|remove|status|logs}"
    echo ""
    echo "Commands:"
    echo "  create   Builds images, creates containers, and starts them in detached mode (up --build -d)"
    echo "  start    Starts existing containers without recreating them (start)"
    echo "  stop     Stops running containers without removing them (stop)"
    echo "  restart  Restarts running containers without recreating them (restart)"
    echo "  remove   Stops and removes containers, networks, and volumes (down)"
    echo "  status   Shows the current state of services (ps)"
    echo "  logs     Follows service log output in real-time (logs -f)"
    exit 1
}

case "$1" in
    create)
        echo "==> Building and creating containers..."
        $DOCKER_CMD up --build -d
        ;;
    start)
        echo "==> Starting existing containers..."
        $DOCKER_CMD start
        ;;
    stop)
        echo "==> Stopping running containers (preserving container state)..."
        $DOCKER_CMD stop
        ;;
    restart)
        echo "==> Restarting containers..."
        $DOCKER_CMD restart
        ;;
    remove)
        echo "==> Stopping and removing containers and networks..."
        $DOCKER_CMD down
        ;;
    status)
        echo "==> Container status:"
        $DOCKER_CMD ps
        ;;
    logs)
        echo "==> Tailing logs (Ctrl+C to exit)..."
        $DOCKER_CMD logs -f
        ;;
    *)
        usage
        ;;
esac