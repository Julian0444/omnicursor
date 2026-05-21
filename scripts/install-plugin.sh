#!/usr/bin/env bash
# install-plugin.sh — Install OmniCursor as a Cursor user plugin.
#
# Symlinks this repository into ~/.cursor/plugins/local/omnicursor so Cursor
# loads rules, skills, agents, and hooks for every workspace.
#
# Usage:
#   ./scripts/install-plugin.sh
#   ./scripts/install-plugin.sh --dry-run
#   ./scripts/install-plugin.sh --status
#   ./scripts/install-plugin.sh --uninstall

set -euo pipefail

OMNICURSOR_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_NAME="omnicursor"
PLUGIN_PARENT="${CURSOR_PLUGINS_LOCAL:-$HOME/.cursor/plugins/local}"
TARGET="$PLUGIN_PARENT/$PLUGIN_NAME"

DRY_RUN=0
UNINSTALL=0
STATUS=0

for arg in "$@"; do
    case "$arg" in
        --dry-run)   DRY_RUN=1 ;;
        --uninstall) UNINSTALL=1 ;;
        --status)    STATUS=1 ;;
        -*)          echo "Unknown flag: $arg" >&2; exit 1 ;;
        *)           echo "Unexpected argument: $arg" >&2; exit 1 ;;
    esac
done

_link() {
    local src="$1" dst="$2"
    if [ "$DRY_RUN" = "1" ]; then
        echo "  [dry-run] mkdir -p $(dirname "$dst")"
        echo "  [dry-run] ln -sfn $src $dst"
        return
    fi
    mkdir -p "$(dirname "$dst")"
    ln -sfn "$src" "$dst"
}

_status_icon() {
    local dst="$1" src="$2"
    if [ -L "$dst" ] && [ "$(readlink -f "$dst")" = "$(readlink -f "$src")" ]; then
        echo "linked"
    elif [ -e "$dst" ]; then
        echo "manual"
    else
        echo "missing"
    fi
}

if [ "$STATUS" = "1" ]; then
    echo "OmniCursor plugin: $TARGET"
    icon="$(_status_icon "$TARGET" "$OMNICURSOR_ROOT")"
    case "$icon" in
        linked)  echo "  status: installed (symlink → $OMNICURSOR_ROOT)" ;;
        manual)  echo "  status: path exists but is not our symlink" ;;
        missing) echo "  status: not installed" ;;
    esac
    exit 0
fi

if [ "$UNINSTALL" = "1" ]; then
    echo "Removing OmniCursor plugin symlink..."
    if [ -L "$TARGET" ] && [ "$(readlink -f "$TARGET")" = "$(readlink -f "$OMNICURSOR_ROOT")" ]; then
        if [ "$DRY_RUN" = "1" ]; then
            echo "  [dry-run] rm $TARGET"
        else
            rm "$TARGET"
            echo "  removed: $TARGET"
        fi
    elif [ -e "$TARGET" ]; then
        echo "  skip: $TARGET exists but is not managed by this script" >&2
        exit 1
    else
        echo "  nothing to remove"
    fi
    exit 0
fi

echo "Installing OmniCursor Cursor plugin..."
[ "$DRY_RUN" = "1" ] && echo "(dry-run — no files written)"
echo "  source: $OMNICURSOR_ROOT"
echo "  target: $TARGET"
echo ""

if [ -e "$TARGET" ] && [ ! -L "$TARGET" ]; then
    echo "ERROR: $TARGET exists and is not a symlink. Remove or rename it first." >&2
    exit 1
fi

if [ -L "$TARGET" ] && [ "$(readlink -f "$TARGET")" = "$(readlink -f "$OMNICURSOR_ROOT")" ]; then
    echo "  already installed"
else
    if [ -L "$TARGET" ] || [ -e "$TARGET" ]; then
        echo "ERROR: $TARGET points elsewhere. Use --uninstall on the other install first." >&2
        exit 1
    fi
    _link "$OMNICURSOR_ROOT" "$TARGET"
    echo "  linked"
fi

echo ""
echo "Next steps:"
echo "  1. Restart Cursor or run: Developer: Reload Window"
echo "  2. Settings → Rules — confirm OmniCursor rules/skills are available"
echo "  3. Open any project — hooks and routing apply globally via the plugin"
