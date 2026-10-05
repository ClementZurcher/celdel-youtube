#!/bin/sh
# Installe les skills de ce dépôt dans un profil Hermès.
#
#   ./install.sh <nom_du_profil> [racine_hermes]
#   ./install.sh youtube
#   ./install.sh youtube /chemin/vers/.hermes
#
# La catégorie de chaque skill est lue dans MANIFEST.tsv.
set -eu

PROFILE=${1:-}
if [ -z "$PROFILE" ]; then
    echo "Usage: ./install.sh <nom_du_profil> [racine_hermes]" >&2
    exit 2
fi

HERMES_ROOT=${2:-${HERMES_HOME:-$HOME/.hermes}}
DEST="$HERMES_ROOT/profiles/$PROFILE/skills"
if [ ! -d "$DEST" ]; then
    echo "Profil introuvable : $DEST" >&2
    echo "Profils disponibles :" >&2
    ls -1 "$HERMES_ROOT/profiles" 2>/dev/null | sed 's/^/  - /' >&2
    exit 1
fi

HERE=$(cd "$(dirname "$0")" && pwd)
TAB=$(printf '\t')
installed=0
skipped=0

while IFS="$TAB" read -r skill category; do
    [ -n "${skill:-}" ] || continue
    case "$skill" in \#*) continue ;; esac
    [ -n "${category:-}" ] || category=other
    src="$HERE/skills/$skill"
    if [ ! -f "$src/SKILL.md" ]; then
        echo "  ! $skill : SKILL.md absent, ignoré"
        skipped=$((skipped + 1))
        continue
    fi
    mkdir -p "$DEST/$category"
    rm -rf "$DEST/$category/$skill"
    cp -r "$src" "$DEST/$category/$skill"
    find "$DEST/$category/$skill" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
    echo "  $skill  ->  $category/"
    installed=$((installed + 1))
done < "$HERE/MANIFEST.tsv"

# Fiche de profil : c'est elle qui définit le comportement de l'assistant (SOUL.md).
# L'existante est sauvegardée avant remplacement, jamais écrasée silencieusement.
SOUL_SRC="$HERE/profil/SOUL.md"
PROFILE_DIR=$(dirname "$DEST")
if [ -f "$SOUL_SRC" ]; then
    if [ -f "$PROFILE_DIR/SOUL.md" ] && ! cmp -s "$SOUL_SRC" "$PROFILE_DIR/SOUL.md"; then
        cp "$PROFILE_DIR/SOUL.md" "$PROFILE_DIR/SOUL.md.bak-$(date +%Y%m%d-%H%M%S)"
        echo "  SOUL.md existant sauvegardé (.bak)"
    fi
    cp "$SOUL_SRC" "$PROFILE_DIR/SOUL.md"
    echo "  fiche de profil (SOUL.md) installée"
fi

echo
echo "Installés : $installed   Ignorés : $skipped"
echo "Destination : $DEST"
echo "Pense à relancer Hermès (ou /reload-skills) pour que les skills soient chargés."
