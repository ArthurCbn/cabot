#!bin/bash

SCRIPT_PATH=$(realpath "$(dirname "${BASH_SOURCE[0]}")")
DATA_PATH="$SCRIPT_PATH/data"

# env
source "$DATA_PATH/.env"

mkdir -p "$CONFIG_DIR"

if [ ! -f "$CONFIG_FILE" ]; then
    cp "$CONFIG_TEMPLATE" "$CONFIG_FILE"
fi

docker build -t cabot-image .

chmod +x "$DATA_PATH/run.sh"
ln -sf "$DATA_PATH/run.sh" "$BINARY_PATH/$APP_NAME"