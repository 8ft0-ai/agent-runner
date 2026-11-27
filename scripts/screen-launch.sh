#!/bin/sh
set -eu

if [ -d /settings/pi ]; then
    cp -r /settings/pi "$HOME/pi"
fi
socat TCP-LISTEN:8017,bind=127.0.0.1,reuseaddr,fork UNIX-CONNECT:/upstream &

case "$BENCHMARK_AGENT" in
    cline)
        cline auth -p openai -k local-relay -m "$BENCHMARK_MODEL" -b "$OPENAI_BASE_URL"
        ;;
    mini)
        "$@"
        # mini can exit 0 after exhausting its task limit. Require explicit submission.
        exec python3 -c 'import json, sys; record = json.load(open("/tmp/mini-trajectory.json")); sys.exit(record["info"]["exit_status"] != "Submitted")'
        ;;
    claude|codex)
        python3 /settings/start-bridge.py &
        bridge_pid=$!
        for attempt in 1 2 3 4 5 6 7 8 9 10; do
            if [ -f /tmp/bridge.env ]; then break; fi
            kill -0 "$bridge_pid"
            sleep 1
        done
        . /tmp/bridge.env
        export ANTHROPIC_BASE_URL="$BRIDGE_URL" ANTHROPIC_API_KEY="$BRIDGE_TOKEN"
        if [ "$BENCHMARK_AGENT" = codex ]; then
            export CODEX_BRIDGE_TOKEN="$BRIDGE_TOKEN"
            mkdir -p "$CODEX_HOME"
            cat > "$CODEX_HOME/config.toml" <<EOF
model_provider = "benchmark"
web_search = "disabled"

[model_providers.benchmark]
name = "Benchmark"
base_url = "$BRIDGE_URL/v1"
env_key = "CODEX_BRIDGE_TOKEN"
wire_api = "responses"
request_max_retries = 0
stream_max_retries = 0
EOF
        fi
        ;;
esac
exec "$@"
