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
une publication. Les captures d'écran apparaissent comme des URL S3 longues, les élider avant
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

Relevé plus fin, quand le document contient des blocs à copier : `GET /v1/blocks/<page_id>/children?page_size=100`
puis compter les blocs par type (`heading_2`, `bulleted_list_item`, `code`) et relire les titres
de section. C'est ce qui attrape le cas où le markdown a été mal converti, un guide publié sans
bloc `code` a perdu ses commandes à copier, ce que la relecture du markdown ne montre pas
toujours. La réponse de création contient l'`url` de la page : c'est le lien à rendre à
l'utilisateur, pas l'identifiant.

Pour énumérer les pages enfants d'une page parente : `GET /v1/blocks/<parent_id>/children`
et suivre `has_more` + `next_cursor` (`?start_cursor=…`), la première page ne montre pas tout, et
c'est le seul moyen de vérifier qu'une page archivée ne fait plus doublon.

## Modifier le contenu d'une page existante

`PATCH /v1/pages/{id}/markdown` avec `{"markdown": "…"}` est **refusé** :
`400 validation_error, body.type should be defined`. Ne pas deviner le schéma attendu, et ne pas
en conclure que l'API ignore le markdown : la **création** l'accepte, seule la mise à jour est
refusée.

**Corriger une section (le cas courant).** Découper la page aux titres : relever l'`id` du
`heading_2` visé et des blocs qui le suivent jusqu'au `heading_2` suivant, supprimer ces blocs,
puis réinsérer les nouveaux **après le titre** (`after` = `id` du titre). Le reste de la page est
intact, indispensable quand l'utilisateur a déjà validé le document, et bien préférable à
l'archivage.

```bash
# 1. relever les blocs et leurs id, dans l'ordre
composio proxy "https://api.notion.com/v1/blocks/<page_id>/children?page_size=100" --toolkit notion \
  -H "Notion-Version: 2025-09-03"
# 2. supprimer chaque bloc de la section (les titres voisins délimitent la plage)
composio proxy "https://api.notion.com/v1/blocks/<block_id>" --toolkit notion -X DELETE \
  -H "Notion-Version: 2025-09-03"
# 3. réinsérer après le titre : PATCH /v1/blocks/<page_id>/children
#    -d '{"children":[…],"after":"<id du heading_2>"}'
```

Après chaque section traitée, **relire la page** avant de traiter la suivante : les index relevés
avant l'édition ne survivent pas aux blocs insérés.

⚠️ La réponse d'insertion ne dit pas ce qui a été créé : `results` peut renvoyer toute la liste des
enfants (35 entrées pour 8 blocs insérés). Compter les blocs **en relisant la page**, jamais depuis
cette réponse.

**Corriger un bloc isolé (le plus économe).** Pour ne changer que le texte d'une puce ou d'un
bloc de code, `PATCH /v1/blocks/<block_id>` avec `{<type>: {"rich_text": […]}}` : le reste de la
page n'est pas touché, contrairement au découpage de section. Sur un bloc `code`, réindiquer
`"language": "plain text"`, sinon la coloration peut se perdre. C'est la voie à préférer quand
l'utilisateur a validé la page et qu'une seule formule change.

⚠️ Cibler le remplacement avec précision : une substitution large (« remplacer “privé” par
“public” ») casse les phrases où le mot a un autre sens, un guide qui parle aussi d'une vidéo
« en privé ». Remplacer la formule exacte (« dépôt privé »), jamais le mot seul.

**Réécrire toute la page** : archiver (`PATCH /v1/pages/{id}` avec `{"archived": true}`) puis
recréer au même emplacement, et relire. L'archivage place la page dans la corbeille Notion
(réversible), le signaler à l'utilisateur.

## Règles

- Aucun secret (jeton, `client_secret`, URL signée) dans un payload ou dans un guide publié.
- Ne pas archiver une page que l'agent n'a pas créée sans accord explicite de l'utilisateur.
- La page reste éditable par l'utilisateur : ne pas s'étonner d'écarts ultérieurs entre ce que
  l'agent a publié et le contenu courant.
