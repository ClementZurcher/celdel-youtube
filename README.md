# Skills Hermès — YouTube (Celdel AI)

Préparer **et** publier les vidéos YouTube : titre, description, chapitres, tags, miniature, téléversement, vérifications.

## Contenu

| Skill | Catégorie | Origine |
|---|---|---|
| `youtube-publish` | `media` | profil `youtube` |
| `youtube-metadata` | `media` | profil `youtube` |
| `google-oauth-setup` | `productivity` | profil `youtube` |
| `composio-cli` | `productivity` | profil `youtube` |
| `internal-guides` | `productivity` | profil `youtube` |

La fiche de profil est dans `profil/SOUL.md` : c'est elle qui définit le rôle et les règles de
l'assistant. À recopier dans `<profil>/SOUL.md` sur une nouvelle installation.

## Le strict minimum

1. `client_secret.json` — identifiant OAuth « Application de bureau », créé une fois dans Google Cloud
2. les skills `youtube-publish` et `youtube-metadata` (+ `youtube-content`, déjà fourni avec Hermès)
3. `scripts/yt_upload.py` et un Python avec `googleapiclient` / `google_auth_oauthlib`

## Installation

```bash
./install.sh <nom_du_profil>        # ex. ./install.sh youtube
```

Le script copie chaque skill dans la bonne catégorie du profil (d'après `MANIFEST.tsv`).
Pour le manuel :

```bash
cp -r skills/<skill> ~/.hermes/profiles/<profil>/skills/<catégorie>/
```

Puis redémarrer Hermès ou lancer `/reload-skills`.

Les adresses et identifiants personnels ont été remplacés par des marqueurs `<...>` : chaque
machine configure les siens (boîte mail, compte Composio, chaîne YouTube).


## Mise à jour

Les skills se modifient dans le profil (`~/.hermes/profiles/<profil>/skills/`), puis se copient
ici. Un dépôt = un profil : ne pas mélanger les domaines.
