---
name: composio-cli
description: "Appeler des API tierces connectées via la CLI Composio."
version: 1.0.0
author: Celdel AI / Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Composio, API, Proxy, Toolkits, OAuth]
    related_skills: [google-oauth-setup, notion, youtube-publish]
---

# Composio CLI : lire et écrire dans des API tierces déjà connectées

## When to Use / Quand l'utiliser

Quand un service est **déjà connecté** dans Composio (Gmail, Notion, YouTube, Sheets…)
et qu'il faut le piloter sans monter un OAuth dédié, ou quand le toolkit n'expose pas
l'outil voulu alors que l'API REST brute le propose (ex. aucun outil d'upload YouTube
alors que `videos.insert` existe). Pour un accès Google durable avec ses propres
identifiants, préférer `google-oauth-setup`.

## 1. Vérifier ce qui est disponible avant de promettre quoi que ce soit

```bash
composio whoami                  # compte et organisation
composio connections list        # toolkits connectés + statut (ACTIVE / FAILED)
composio tools list <toolkit>    # outils réellement exposés (souvent incomplets)
composio search "<cas d'usage>"   # recherche sémantique dans le catalogue
```

Un outil absent du catalogue **ne signifie pas** que l'API est inaccessible : passer par le
proxy. Vérifier aussi quel compte est derrière la connexion (`mine=true` ou équivalent) avant
d'écrire.

## 2. Lectures

```bash
composio proxy "<url_complète>" --toolkit <slug> [-H "Nom: valeur"]
```

Pour connaître le statut réel d'un appel, passer par le sandbox :
`composio run -f script.js` injecte `proxy("<slug>")`, qui renvoie un `fetch()` lié au compte
connecté, lire `res.status`, `res.headers`, `res.text()`. C'est indispensable : la CLI
n'affiche **rien** pour une réponse d'erreur ou sans corps JSON.

## 3. Écritures : toujours via la CLI avec `-d`

```bash
composio proxy "<url>" --toolkit <slug> -X POST \
  -H "Content-Type: application/json" -d '{"…": "…"}'
composio proxy "<url>" --toolkit <slug> -X PATCH -d @payload.json
composio proxy "<url>" --toolkit <slug> -X POST -d -   # corps depuis stdin
```

- `-d` accepte le JSON en ligne, `@fichier` ou `-`. Pour toute charge utile longue ou
  contenant des guillemets, la construire avec un script puis la passer par `@fichier`.
- **Le helper `proxy()` du sandbox ne porte pas le corps de la requête.** Les écritures y
  échouent par un message de corps invalide (`Root element must be a message` côté Google,
  `Error parsing JSON body` côté Notion). Répartition : `composio run` pour **inspecter**,
  la CLI pour **écrire**.
- Plusieurs méthodes HTTP : `-X` (GET, POST, PUT, PATCH, DELETE).

## 4. Vérifier chaque écriture (obligatoire)

Après toute écriture, **relire l'objet** par une route de lecture et comparer au résultat
attendu avant d'annoncer un succès. Exemples : `GET /v1/pages/<id>/markdown` après création
d'une page Notion ; `channels?mine=true` après une modification de chaîne YouTube.
Une réponse de la CLI ne prouve rien : l'absence de sortie est ambiguë (voir §5).

## 5. Pièges

- **Échec silencieux** : la CLI n'imprime rien sur une erreur HTTP ou une réponse vide, un
  `429` ou un `404` ressemble à un succès. En cas de doute, rejouer via `composio run` et lire
  `res.status`.
- **En-têtes d'API obligatoires** : les omettre produit une erreur trompeuse (Notion exige
  `Notion-Version: 2025-09-03` sur chaque appel).
- **Quota imputé au fournisseur** : la consommation va au **projet du fournisseur**
  (Composio), mutualisé entre tous ses utilisateurs ; un `429` peut donc venir de la
  plateforme et non d'une limite propre. Ne pas promettre un volume sans vérifier.
- **Domaines d'authentification restreints** : le proxy n'injecte le jeton que pour les
  domaines de l'API du toolkit visé. Un endpoint voisin (ex. `userinfo` Google via le toolkit
  YouTube) renvoie `401`, ce n'est pas un problème de jeton, c'est un périmètre d'injection.
- **`composio dev …`** (toolkits, auth-configs, connected-accounts) exige un projet
  développeur dans le répertoire courant (`composio dev init`) ; sinon « No developer project
  configured for this directory ».
- Le sandbox échoue aussi par intermittence sur les pages lourdes ; relancer la commande
  avant de conclure à une panne.
- **Écritures en lot : un fichier de charge utile par appel, au nom unique** (`uuid`), et ne pas
  les supprimer tant que la CLI tourne. Deux appels parallèles partageant un nom de fichier font
  échouer la lecture (`ENOENT … /tmp/….json`) et perdent les fichiers concernés. Viser 4–6 appels
  en parallèle, pas plus.
- **Aucun code HTTP dans la sortie** : dans un script qui enchaîne les appels, ne jamais conclure
  « le JSON se parse, donc c'est un succès », une erreur sort aussi en JSON. S'appuyer sur la
  **signature d'erreur propre à l'API** (GitHub : champ `documentation_url`, jamais présent sur un
  succès ; Google : `error.code`).
- **Création idempotente** : un `POST` de création sur un objet déjà existant échoue proprement
  (« already exists ») ; lire l'objet et poursuivre le lot au lieu d'abandonner.

## 6. Recette : créer une page Notion quand `NOTION_API_KEY` est absent

Si la connexion Notion existe dans Composio mais qu'aucun jeton local ni CLI `ntn` n'est
installé (voir le skill `notion` pour la voie officielle), passer par l'API REST :

1. Retrouver la page parente :
   `composio proxy "https://api.notion.com/v1/search" --toolkit notion -X POST -H "Notion-Version: 2025-09-03" -H "Content-Type: application/json" -d '{"query":""}'`
   ne renvoie que ce qui est partagé avec l'intégration.
2. Créer la sous-page :
   `composio proxy "https://api.notion.com/v1/pages" --toolkit notion -X POST -H "Notion-Version: 2025-09-03" -H "Content-Type: application/json" -d @payload.json`
   avec
   ```json
   {"parent": {"page_id": "<id parent>"},
    "properties": {"title": [{"text": {"content": "<titre>"}}]},
    "markdown": "# Titre\n\nContenu en markdown Notion (callout, tableaux, code)"}
   ```
   Le champ `markdown` accepte le markdown enrichi de Notion (blocs `<callout>`, titres,
   listes, code) : inutile de construire l'arbre de blocs à la main.
3. Vérifier : `GET https://api.notion.com/v1/pages/<id>/markdown` et contrôler la longueur et
   les titres relus.

## 7. Autres recettes

- **Publier un dossier entier sur GitHub** (dépôt + arborescence en un commit, sans `gh`
  authentifié), et la forme du dépôt quand on versionne les skills d'un profil :
  `references/github-repo-push.md`.
- **Prouver, ou disculper, un effet de bord** d'un outil lancé par une automatisation (il change
  l'état sans le dire : marque un message comme lu, déplace, étiquette) :
  `references/verifying-side-effects.md`.
