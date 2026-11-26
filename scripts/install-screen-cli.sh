#!/usr/bin/env bash
set -euo pipefail

if ! command -v bwrap >/dev/null || ! command -v socat >/dev/null; then
    sudo apt-get update
    sudo apt-get install -y bubblewrap socat
fi
if ! bwrap --unshare-net --ro-bind / / -- /bin/true; then
    # This disposable Ubuntu runner needs permission to create user namespaces.
    sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0
    bwrap --unshare-net --ro-bind / / -- /bin/true
fi

cli="$RUNNER_TEMP/cli"
mkdir -p "$cli/bin" "$RUNNER_TEMP/evidence"
case "$SCREEN_AGENT" in
    qwen)
        npm install --ignore-scripts --no-audit --no-fund --prefix "$cli" @qwen-code/qwen-code@0.28.6
        install "$(command -v node)" "$cli/bin/node"
        ln -s ../node_modules/.bin/qwen "$cli/bin/qwen"
        "$cli/bin/qwen" --version | grep -Fx '0.28.6'
        ;;
    pi)
        npm install --ignore-scripts --no-audit --no-fund --prefix "$cli" @earendil-works/pi-coding-agent@1.6.1
        install "$(command -v node)" "$cli/bin/node"
        ln -s ../node_modules/.bin/pi "$cli/bin/pi"
        "$cli/bin/pi" --version | grep -Fx '1.6.1'
        ;;
    goose)
        archive="$RUNNER_TEMP/goose.tar.bz2"
        curl -fsSL --connect-timeout 15 --max-time 75 --retry 2 --retry-all-errors --retry-max-time 240 \
            https://github.com/aaif-goose/goose/releases/download/v1.61.1/goose-x86_64-unknown-linux-gnu.tar.bz2 \
            -o "$archive"
        echo "34cd9a484a15564d3f462843359d24e4964ae328be3625024003d29f318e586c  $archive" | sha256sum -c -
        tar -xjf "$archive" -C "$cli/bin" ./goose
        "$cli/bin/goose" --version | grep -Fx 'goose 1.61.1'
        ;;
    aider)
        /usr/bin/python3 -m venv --copies "$cli/aider"
        "$cli/aider/bin/python" -m pip install --disable-pip-version-check 'aider-chat==0.86.2'
        "$cli/aider/bin/aider" --version | grep -Fx 'aider 0.86.2'
        ;;
    *)
        exit 2
        ;;
esac
