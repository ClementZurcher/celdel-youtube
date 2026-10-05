# Publier et modifier une page Notion depuis Hermès

Voie utilisée quand le profil n'a **pas** de jeton Notion : passer par la connexion Notion
active dans Composio.

## Choisir la voie

1. `NOTION_API_KEY` présent dans le profil et CLI `ntn` installée → suivre le skill `notion`
   (api officielle, plus simple).
2. Sinon, si `composio connections list` montre une connexion `notion` ACTIVE → `composio proxy
   --toolkit notion`. Aucun jeton à créer, l'accès est celui du compte connecté.

En-tête obligatoire sur toutes les requêtes : `Notion-Version: 2025-09-03`.

## Écrire : la CLI, jamais le sandbox

`composio proxy` avec `-d` transmet le corps ; le `fetch` injecté par `composio run` le **perd**
(voir la note ci-dessous). Toute écriture passe donc par la CLI, avec un corps en fichier dès
que le contenu est long.

```bash
# lister les pages visibles (celles partagées avec l'intégration)
composio proxy "https://api.notion.com/v1/search" --toolkit notion -X POST \
  -H "Notion-Version: 2025-09-03" -H "Content-Type: application/json" \
  -d '{"query":"","page_size":100}'

# créer une page à partir d'un fichier markdown
composio proxy "https://api.notion.com/v1/pages" --toolkit notion -X POST \
  -H "Notion-Version: 2025-09-03" -H "Content-Type: application/json" \
  -d @payload.json
```

Symptôme d'un corps perdu : `400 Error parsing JSON body` (Notion) ou `400 Root element must be
a message` (API Google). Dans ce cas, c'est le sandbox qui est en cause, pas le proxy :
réessayer avec la CLI.

## Lire une page

```bash
composio proxy "https://api.notion.com/v1/pages/{id}/markdown" --toolkit notion \
  -H "Notion-Version: 2025-09-03"
```

Renvoie le markdown de la page : idéal pour s'inspirer d'un style existant **et** pour vérifier
une publication. Les captures d'écran apparaissent comme des URL S3 longues — les élider avant
d'affichage.

## Créer une page depuis du markdown

Construire le payload **en Python vers un fichier** (jamais en ligne de commande : guillemets,
accent, retours à la ligne, emoji) :

```python
import json
md = open("guide.md", encoding="utf-8").read()
json.dump({
    "parent": {"page_id": "<page_parente>"},
    "properties": {"title": [{"text": {"content": "<titre de la page>"}}]},
    "markdown": md,
}, open("payload.json", "w", encoding="utf-8"), ensure_ascii=False)
```

Le markdown accepte les extensions Notion : `<callout icon="🎬" color="blue_bg">…</callout>`,
blocs de code, tableaux, titres hiérarchisés.

## Vérifier (obligatoire)

Relire la page créée (`GET …/markdown`) et contrôler : longueur du contenu, présence de chaque
titre de section attendu, absence de la version précédente. Un `200` de création ne prouve pas
ce que la page contient.

## Modifier le contenu d'une page existante

`PATCH /v1/pages/{id}/markdown` avec `{"markdown": "…"}` est **refusé** :
`400 validation_error — body.type should be defined`. Ne pas deviner le schéma attendu.
Procédure qui fonctionne : **archiver la page** (`PATCH /v1/pages/{id}` avec `{"archived": true}`)
puis **recréer** une page au même emplacement avec le nouveau contenu, et relire. L'archivage
place la page dans la corbeille Notion (réversible) — le signaler à l'utilisateur.

## Règles

- Aucun secret (jeton, `client_secret`, URL signée) dans un payload ou dans un guide publié.
- Ne pas archiver une page que l'agent n'a pas créée sans accord explicite de l'utilisateur.
- La page reste éditable par l'utilisateur : ne pas s'étonner d'écarts ultérieurs entre ce que
  l'agent a publié et le contenu courant.
