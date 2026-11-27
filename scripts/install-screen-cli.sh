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
        goose_version=$("$cli/bin/goose" --version)
        printf '%s\n' "$goose_version"
        grep -Eq '(^|[[:space:]])1\.61\.1([[:space:]]|$)' <<< "$goose_version"
        ;;
    cline|continue|claude)
        case "$SCREEN_AGENT" in
            cline) package=cline@3.0.76; executable=cline ;;
            continue) package=@continuedev/cli@1.5.47; executable=cn ;;
            claude) package=@anthropic-ai/claude-code@2.1.332; executable=claude ;;
        esac
        npm install --ignore-scripts --no-audit --no-fund --prefix "$cli" "$package"
        install "$(command -v node)" "$cli/bin/node"
        ln -s "../node_modules/.bin/$executable" "$cli/bin/$executable"
        "$cli/bin/$executable" --version
        ;;
    opencode)
        archive="$RUNNER_TEMP/opencode.tgz"
        curl -fsSL --connect-timeout 15 --max-time 75 --retry 2 \
            https://github.com/anomalyco/opencode/releases/download/v2.4.2/opencode-linux-x64.tar.gz \
            -o "$archive"
        echo "452912288f934d1771bd5bd0d8611ba3a6adc3db3ac3333c37facf373770ba66  $archive" | sha256sum -c -
        tar -xzf "$archive" -C "$cli/bin" opencode
        test "$("$cli/bin/opencode" --version)" = 'opencode v2.4.2'
        ;;
    codex)
        archive="$RUNNER_TEMP/codex.tgz"
        curl -fsSL --connect-timeout 15 --max-time 75 --retry 2 \
            https://github.com/openai/codex/releases/download/rust-v0.172.0/codex-x86_64-unknown-linux-musl.tar.gz \
            -o "$archive"
        echo "a2342a8f7f68f088be30620ccfe9cb84162c93a6b56177855961cda3ed6be392  $archive" | sha256sum -c -
        tar -xzf "$archive" -C "$cli/bin" codex-x86_64-unknown-linux-musl
        mv "$cli/bin/codex-x86_64-unknown-linux-musl" "$cli/bin/codex"
        test "$("$cli/bin/codex" --version)" = 'codex-cli 0.172.0'
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


if [[ "$SCREEN_AGENT" == claude || "$SCREEN_AGENT" == codex ]]; then
    bridge="$cli/nvidia_build_bridge.py"
    curl -fsSL --connect-timeout 15 --max-time 60 --retry 2 \
        https://raw.githubusercontent.com/NVIDIA/SkillEvaluator/5efcbacc3f4022b0786b4a97c7eacb90ad5ca7d3/src/skillevaluator/tier3/harbor/nvidia_build_bridge.py \
        -o "$bridge"
    echo "684e419f3b334abf885dd014740977f2133e669d475d17b5b575e570e95d4afd  $bridge" | sha256sum -c -
fi
