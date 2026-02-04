#!/bin/bash
set -e

SCRIPT_PATH=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")
source "$SCRIPT_PATH/.env"

usage() {
    echo "Usage: $(basename "$0") <command> [options]"
    echo
    echo "Commands:"
    echo "  update        Run the application"
    echo "  config        Open the config file"
    echo "  help          Show this help"
}

run_update() {
    # Vérifier que le fichier de config existe
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "Erreur : fichier de config introuvable. Lancez setup.sh d'abord."
        exit 1
    fi

    # Lire le dossier de travail depuis le JSON
    DATA_DIR=$(jq -r '.playlists_folder' "$CONFIG_FILE")

    # Lancer le conteneur avec les volumes montés
    docker run --rm -it \
        -v "$CONFIG_DIR":/app/.config:Z \
        -v "$DATA_DIR":/app/data:Z \
        cabot-image "$@"
}

run_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "Erreur : fichier de config introuvable."
        exit 1
    fi

    xdg-open "$CONFIG_FILE" >/dev/null 2>&1 &
}

COMMAND="$1"
shift || true

case "$COMMAND" in
    update)
        run_update "$@"
        ;;
    config)
        run_config
        ;;
    help|-h|--help|"")
        usage
        ;;
    *)
        echo "Commande inconnue: $COMMAND"
        echo
        usage
        exit 1
        ;;
esac
