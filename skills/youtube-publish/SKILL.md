---
name: youtube-publish
description: "Publier une vidéo YouTube automatiquement."
version: 1.0.0
author: Celdel AI / Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [YouTube, Upload, Publication, API, Composio, OAuth]
    related_skills: [youtube-metadata, youtube-content]
---

# Publication automatisée d'une vidéo YouTube

## When to Use / Quand l'utiliser

Quand on demande de téléverser, programmer ou publier une vidéo YouTube, ou quand on
se demande si c'est techniquement possible. Complète `youtube-metadata` (titre,
description, tags, chapitres) par la mise en ligne effective.

## Les trois voies réelles (état vérifié)

| Voie | État | Quota | Publication publique possible ? |
|---|---|---|---|
| A. Proxy Composio → `videos.insert` | **Autorisée mais NON fiable** : le proxy perd le corps des requêtes en écriture (voir §pièges) | **Partagé** : 966/jour pour tout Composio (`defaultVideoInsertPerDayPerProject`), épuisé la plupart du temps, reset 07:00 UTC | Probablement, non vérifié |
| B. OAuth propre (Google Cloud) | Fonctionnelle | **Dédié** : 100 appels `videos.insert`/jour par projet (bucket « Video Uploads », coût 1 unité/call) | **Non** : projet non vérifié créé après le 28/07/2020 → uploads forcés en **privé** jusqu'à l'[audit API](https://support.google.com/youtube/contact/yt_api_form) |
| C. Navigateur → YouTube Studio | Fonctionnelle | Aucun quota API | **Oui** |
| D. MCP YouTube dans Hermès | Configuration possible | Dépend du client OAuth utilisé | Identique à B si tes propres identifiants, identique à A si un tiers |

### Usage rare (quelques publications par an)

À faible volume, le bon choix est la **voie B** configurée une fois : elle ne demande aucun
mot de passe, ne dépend d'aucun navigateur, et une fois `token.json` obtenu elle tourne
seule indéfiniment. La voie C n'est utilisable que si une session Google est **déjà**
prête dans le navigateur (voir le blocage ci-dessous), et la voie A est non fiable en
écriture.

Rappel de la restriction : un projet Google non vérifié créé après le 28/07/2020 uploade
en **privé uniquement** jusqu'à l'audit — prévoir que la dernière bascule en public se
fasse à la main dans Studio (un clic) tant que l'audit n'est pas passé.

### Ce qui bloque réellement : le client OAuth, jamais l'outil

Le quota et la restriction « privé » sont attachés au **projet Google qui a émis le jeton**
(`client_id`), pas au logiciel qui appelle l'API. Preuve : le 429 de la voie A nomme
`consumer 'project_number:1068312718386'` (projet Composio) et la métrique
`youtube.googleapis.com/video_insert`.

Conséquence directe : **brancher un MCP YouTube ne contourne rien**. Un MCP est un
protocole d'appel ; il lui faut de toute façon un client OAuth. Google ne publie pas de
serveur MCP YouTube officiel ; les serveurs communautaires sérieux
(`vapvarun/youtube-mcp`, `pauling-ai/youtube-mcp-server`) exigent explicitement *tes*
identifiants Google Cloud (« bring your own credentials ») — donc même quota (100/jour)
et même restriction « privé jusqu'à audit » que la voie B. Un MCP hébergé par un tiers
te ferait hériter de **son** quota, comme Composio.

Donc : remplacer Composio par un MCP ne résout le problème que si l'on apporte ses propres
identifiants — et ce n'est pas le MCP qui apporte quoi que ce soit, c'est le projet Google.

### MCP dans Hermès (si tu veux malgré tout la voie D)

Dans `config.yaml` (jamais à la main : `hermes config set`), clé `mcp_servers`, transport
stdio `command`/`args` ou HTTP `url`/`headers` ; redémarrage requis ; les outils
apparaissent en `mcp_<serveur>_<outil>`. Serveur d'upload typique :

```bash
hermes config set mcp_servers.youtube.command uvx
hermes config set mcp_servers.youtube.args '["youtube-mcp"]'
```

Le serveur lit `~/.config/youtube-mcp/client_secret.json` — donc retour à la case voie B,
mais en plus verbeux que le script `yt_upload.py` déjà prêt.

Le toolkit `youtube` de Composio n'expose **aucun** outil d'upload (27 outils : lecture,
playlists, commentaires). Mais `composio proxy` / `proxy()` attaquent directement
`https://www.googleapis.com/upload/youtube/v3/videos`, avec l'auth injectée.

## Voie A — proxy Composio

```bash
composio run -f _probe.js          # teste la porte quota sans envoyer d'octets vidéo
python3 yt_upload.py --via composio --video f.mp4 --title "…" --description-file d.txt
```

Le script complet est `~/.hermes/profiles/youtube/workspace/yt-publish/yt_upload.py`
(`--check` valide tout sans rien envoyer, `--probe-quota` teste la porte quota,
`--confirm-public` seul autorise une mise en public).

Pièges spécifiques :
- **Le proxy ne transmet pas le corps des requêtes en écriture** (mesuré 2026-10-02) : un `PUT`
  renvoie systématiquement `400 Invalid JSON payload received. Unknown name "": Root element
  must be a message` — le corps n'arrive jamais. En `POST`, la réponse est masquée par le 429
  de quota, évalué **avant** la lecture du corps : un 429 ne prouve donc pas que le corps est
  passé. Test rapide : un `PUT` qui renvoie ce 400 = corps perdu. Conclusion : ne pas compter
  sur le proxy Composio pour téléverser ni pour modifier des métadonnées ; il reste bon pour
  les **lectures** (statistiques, vidéos, playlists, commentaires).
- `composio proxy` n'affiche **rien** sur une réponse d'erreur ou sans corps JSON (un 429
  ressemble à un succès silencieux). Toujours vérifier avec `composio run` et lire
  `res.status` / `res.headers` / `res.text()`.
- Le quota est partagé entre tous les utilisateurs Composio : le 429 tombe souvent au
  milieu de la journée et se réinitialise à 07:00 UTC.
- Un 429 sur `quota_metric: youtube.googleapis.com/video_insert` prouve que l'auth est
  passée (un scope manquant renvoie 403 avant la vérification de quota) ; un 400
  `Root element must be a message` signifie que le corps JSON n'a pas été transmis.

## Voie B — OAuth propre

**Procédure sans navigateur local** (le cas normal quand l'agent tourne sur une machine
distante) :

```bash
PY=<venv avec google_auth_oauthlib>/bin/python
$PY yt_upload.py --print-auth-url --client-secret client_secret.json   # → URL + état PKCE
# l'utilisateur ouvre l'URL dans SON navigateur, autorise, copie l'URL de redirection
# (même si la page localhost affiche une erreur) dans un fichier, puis :
$PY yt_upload.py --finish-auth /chemin/url.txt --client-secret client_secret.json
$PY yt_upload.py --via oauth --video f.mp4 --title "…" --description-file d.txt
```

Le code d'autorisation doit transiter par un **fichier**, jamais par le chat. Le
`client_secret.json` (type « Application de bureau ») et `token.json` restent des fichiers
locaux en `chmod 600` ; ne jamais les afficher ni les coller dans la conversation.

Pièges rencontrés sur le terrain :
- **`include_granted_scopes=true` sur un client OAuth partagé** (ex. un client déjà utilisé
  par n8n) fait fusionner les scopes accordés par le passé — typiquement `drive.file`.
  Google **refuse de combiner les scopes `youtube.*` avec `drive.file`** dans une même
  autorisation : `HTTP 400 invalid_request — « This request contains scopes that cannot be
  requested together »`. Correctif : ne pas envoyer `include_granted_scopes` (défaut du
  script), ou utiliser des autorisations incrémentales séparées.
- **`login_hint` + `prompt=select_account`** sont indispensables quand le navigateur de
  l'utilisateur contient plusieurs comptes Google : sans eux, Google peut présélectionner
  le mauvais compte et renvoyer « accès réservé à votre organisation » sur un consentement
  Interne.
- `admin.google.com` n'est **pas** nécessaire à la mise en place, et y accéder exige les
  droits d'administration du domaine Workspace (les posséder n'a rien à voir avec posséder
  une chaîne YouTube). Ne pas y envoyer l'utilisateur.

**Variantes, même identifiants Google Cloud** :

- **B1 (script `yt_upload.py --via oauth`)** — la plus directe.
- **B2 (auth config personnalisée dans Composio)** — garder Composio et ses outils, mais
  avec *tes* identifiants : dashboard → Authentication management → Create Auth Config →
  toolkit YouTube → OAuth2 → activer « Use your own developer credentials » → Client ID +
  Secret. La doc Composio confirme la motivation : « Composio's default OAuth app shares
  quota across all users. Your own app gets a dedicated quota ». Utile si tu veux garder les
  20+ outils YouTube de Composio **et** ton quota propre.

### Chemins exacts dans la console (2026) — à donner tels quels à l'utilisateur

| Étape | Où | Lien direct |
|---|---|---|
| 1. Créer le projet | Menu ☰ → **IAM et administration** → **Créer un projet** (⚠️ **pas** dans « API et services ») | console.cloud.google.com/projectcreate |
| 2. Activer l'API | **API et services** → **Bibliothèque** → « YouTube Data API v3 » → Activer | console.cloud.google.com/apis/library/youtube.googleapis.com |
| 3. Consentement | Menu ☰ → **Google Auth platform** → **Get started** (App name, e-mail d'assistance, **Audience = Interne** si le compte est un Google Workspace, sinon Externe, e-mail de contact, acceptation de la politique) | console.cloud.google.com/auth/overview |
| 4. Utilisateurs test | **Google Auth platform** → **Audience** → Utilisateurs test → ajouter l'adresse du propriétaire de la chaîne — **uniquement si Audience = Externe** | console.cloud.google.com/auth/audience |
| 5. Client OAuth | **Google Auth platform** → **Clients** → Créer un client → type **Application de bureau** → télécharger le JSON | console.cloud.google.com/auth/clients |

La bibliothèque se trouve bien sous « API et services », mais le **projet** non : c'est une
confusion classique à lever d'emblée.

### Si le compte propriétaire de la chaîne est un Google Workspace (domaine propre)

Choisir **Audience = Interne** plutôt qu'Externe, c'est nettement plus simple et Google le
documente ainsi : un consentement **Interne** n'exige **aucune vérification**, ne se sert
pas d'une liste d'utilisateurs test, et **la règle du jeton valable 7 jours ne s'applique
pas** (elle vise explicitement « external user type + publishing status Testing »). Les
scopes sensibles/restreints (dont `youtube.upload`) ne nécessitent aucune revue Google pour
un usage interne à l'organisation.

Seule contrainte supplémentaire : un administrateur Workspace peut bloquer n'importe quelle
app OAuth (Security → API controls → App access control). Si l'API est bloquée pour le
domaine, autoriser l'app dans la console d'administration (ou la marquer « Trusted », ce qui
la traite comme interne).

### Piège majeur : statut « Testing » = jeton mort en 7 jours

Un consentement **Externe resté en Testing** délivre un jeton de rafraîchissement valable
**7 jours** (documenté par Google). Re-authentifier ne fait que repousser de 7 jours. Le
correctif est **Audience → « Publish app »** (statut « In production ») — l'application peut
rester **non vérifiée**, ce qui est acceptable pour un usage personnel, mais « Publish app »
peut être grisé si les champs de marque (page d'accueil, politique de confidentialité,
domaine autorisé) manquent.

Détection automatique : `yt_upload.py --finish-auth` lit le champ `refresh_token_expires_in`
de la réponse de jeton et avertit si le jeton est à durée limitée. La publication n'est pas
rétroactive : un jeton émis en Testing garde son échéance, il faut refaire l'autorisation
une fois après la bascule.

### Suite de la configuration

L'identifiant OAuth de type **Application de bureau** fournit `client_secret.json`. Une fois
l'autorisation initiale terminée (`--print-auth-url` puis `--finish-auth`) :

```bash
<venv>/bin/python yt_upload.py --via oauth --client-secret client_secret.json \
  --video f.mp4 --title "…" --description-file d.txt --tags "a, b"
```

Le premier lancement ouvre le flux d'autorisation et écrit `token.json` (chmod 600).
Ne jamais demander ni saisir de mot de passe : l'utilisateur s'authentifie lui-même
dans son navigateur ; les secrets restent hors conversation.

## Voie C — navigateur (YouTube Studio)

⚠️ **Connexion Google impossible en automatisation** (vérifié 2026-10-02) : Google refuse
un navigateur piloté par CDP. Après l'e-mail, on atterrit sur
`accounts.google.com/v3/signin/rejected` → « This browser or app may not be secure. Try
using a different browser. » Aucun mot de passe n'est même demandé. Ce n'est pas un bug
d'Hermès (le vault ne peut rien y faire) : la voie C suppose une session Google **déjà**
présente dans le navigateur. Pour obtenir l'accès initial, passer par la voie B.

1. Vérifier la connexion : ouvrir `https://studio.youtube.com` ; si redirection vers
   `accounts.google.com`, aucune session n'est disponible → voir le blocage ci-dessus.
2. Studio → « Créer » → « Importer une vidéo » → fichier → titre, description, tags,
   miniature → visibilité **Privée** ou **Planifiée** → Enregistrer.
3. Ne jamais choisir « Publique » sans confirmation explicite de l'utilisateur.

Piège d'environnement : le Chromium Hermes échoue avec
`libatk-1.0.so.0: cannot open shared object file`. Correctif appliqué (host Ubuntu) :

```bash
apt-get install -y --no-install-recommends libxcomposite1 libxdamage1 libxfixes3 \
  libxrandr2 libatk1.0-0t64 libatk-bridge2.0-0t64 libatspi2.0-0t64 libcairo2 \
  libcups2t64 libgbm1 libpango-1.0-0 libasound2t64
```

## Distribuer l'installation (piège vérifié)

`youtube-metadata` et `youtube-publish` sont des skills **locaux** (`hermes skills list` →
origine `local`), absents des registres publics. `hermes skills search youtube-metadata`
renvoie des **homonymes tiers** (magics-meal-kits, shipshow, un « YouTube Publisher » de
clawhub) : une consigne du type « installe le skill youtube-metadata » depuis un hub
installerait le skill de quelqu'un d'autre, pas celui-ci.

Règle : tout prompt d'installation doit **nommer une source de fichiers** (chemin du pack
`celdel-youtube-pack.zip`, ou chemins `skills/media/…` existants) et préciser « n'installe
aucun skill venant d'un registre public, même si le nom ressemble ». Sur une machine déjà
installée, la bonne instruction est une **copie** (plus le script `yt_upload.py`), pas un
téléchargement.

## Garde-fous (non négociables)

- Statut par défaut : privé / brouillon. `--confirm-public` (ou un accord écrit explicite
  fichier + chaîne + action) est requis pour la mise en public.
- Aucune vidéo n'est téléversée, modifiée, supprimée ou publiée sans instruction
  explicite portant sur le fichier, la chaîne et l'action.
- Les sondes de capacité (init de session résumable sans octets) ne créent aucune vidéo,
  mais consomment une unité de quota : les limiter et le dire.
- Signaler tout doute sur droits, personnes identifiables, données confidentielles.

## Vérifier ce que cette fiche affirme

Les états de la table datent de la vérification ; les re-tester avant de les présenter
comme actuels : `composio whoami`, `composio connections list`, `yt_upload.py --probe-quota`,
`composio tools list youtube`. Détail des preuves : `references/evidence.md`.

Sources officielles : quota `videos.insert` (100/jour, audit requis pour sortir du privé)
https://developers.google.com/youtube/v3/docs/videos/insert ; quotas YouTube Data API
https://developers.google.com/youtube/v3/getting-started#quota ; identifiants OAuth
developers.google.com/youtube/v3/guides/uploading_a_video (le `client_secrets.json` de
Google est un bloc `"web"`, alors que le fichier « Application de bureau » du Cloud Console
est un bloc `"installed"` : `yt_upload.py` accepte les deux via `from_client_secrets_file`).
