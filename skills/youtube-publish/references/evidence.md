# Preuves des tests de capacité (2026-10-02, host Hermes)

## 1. Ce que Composio expose pour youtube

`composio tools list youtube` → 27 outils, aucun `videos.insert` / `videos.update` :
ADD_VIDEO_TO_PLAYLIST, CREATE_CHANNEL_SECTION, CREATE_COMMENT_REPLY, CREATE_PLAYLIST,
DELETE_CHANNEL_SECTION, DELETE_COMMENT, DELETE_PLAYLIST, DELETE_PLAYLIST_ITEM,
DELETE_VIDEO, GET_CHANNEL_ACTIVITIES, GET_CHANNEL_ID_BY_HANDLE, GET_CHANNEL_STATISTICS,
GET_VIDEO_DETAILS_BATCH, GET_VIDEO_RATING, LIST_CAPTION_TRACK, LIST_CHANNELS,
LIST_CHANNEL_SECTIONS, LIST_CHANNEL_VIDEOS, LIST_COMMENTS, LIST_COMMENT_THREADS,
LIST_LIVE_CHAT_MESSAGES, LIST_MOST_POPULAR_VIDEOS, LIST_PLAYLIST_IMAGES,
LIST_PLAYLIST_ITEMS, LIST_SUPER_CHAT_EVENTS, LIST_USER_PLAYLISTS, LIST_USER_SUBSCRIPTIONS.

## 2. Le proxy parle bien à l'API YouTube authentifiée

```
composio proxy "https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&mine=true" --toolkit youtube
→ youtube#channelListResponse, id <ID_DE_LA_CHAINE>, titre <nom de la chaîne>, @<pseudo>
```

## 3. videos.insert : autorisé, bloqué par le quota partagé

`composio run` avec `proxy("youtube")` et un POST `uploadType=resumable` (aucun octet vidéo) :

```
status 429
{"error":{"code":429,"message":"Quota exceeded for quota metric 'Video Uploads' and limit 'Video Uploads per day' ... consumer 'project_number:1068312718386'",
 "details":[{"...ErrorInfo":{"reason":"RATE_LIMIT_EXCEEDED","metadata":{
   "quota_limit":"defaultVideoInsertPerDayPerProject",
   "quota_limit_value":"966",
   "quota_metric":"youtube.googleapis.com/video_insert",
   "window_start_time":"1790924400",       (= 2026-10-02 07:00 UTC)
   "consumer":"projects/1068312718386", "quota_unit":"1/d/{project}"}}}]}
```

Lecture : un scope manquant produirait 403 `insufficient authentication scopes` avant tout
comptage de quota ; le 429 porte sur la métrique d'upload elle-même → l'autorisation
d'upload est accordée, seule la limite journalière du projet partagé bloque.

Un variant mal formé renvoie :

```
status 400 {"error":{"code":400,"message":"Invalid JSON payload received. Unknown name \"\": Root element must be a message."}}
```

→ utile pour distinguer « corps non transmis » (400) de « quota épuisé » (429).
Une occurrence de 400 a été observée une fois juste après l'écriture du fichier JS puis
n'a plus été reproductible : relancer la sonde avant de conclure.

## 4. Navigateur

Chromium Hermes : `error while loading shared libraries: libatk-1.0.so.0`.
Après `apt-get install` des paquets listés dans le SKILL.md, `ldd` ne signale plus aucune
bibliothèque manquante et le navigateur démarre ; `https://studio.youtube.com` a redirigé
vers `accounts.google.com/v3/signin/identifier` → aucune session Google dans ce profil.

## 5. Autres voies catalogue Composio

Toolkits de publication sociale présents dans le catalogue (`known-toolkit-slugs.json`) :
`ayrshare`, `buffer`, `typefully`, `upload_post`, `make`, `bulk publish`, `onlysocial`,
`woop_social`, `scheduleonce`. `ayrshare` et `upload_post` savent publier des vidéos
YouTube avec **leur** quota et **leur** app OAuth : à considérer si la voie A reste saturée.
Aucun n'est connecté sur ce compte.

## 6. Règles Google officielles (docs au 2026-09-14)

- `videos.insert` : **100 appels par jour** par projet, coût 1 unité dans le bucket
  « Video Uploads » ; taille max 256 Go ; scopes acceptés `youtube.upload`, `youtube`,
  `youtubepartner`, `youtube.force-ssl`.
- **Restriction décisive** : « All videos uploaded via the `videos.insert` endpoint from
  unverified API projects created after 28 July 2020 will be restricted to private viewing
  mode. To lift this restriction, each API project must undergo an audit. »
  → un projet Google perso récent uploade donc en **privé uniquement** tant que l'audit
  n'est pas passé. C'est le point qui distingue vraiment les voies A et B.
- Quotas Data API : 100 `search.list`, 100 `videos.insert`, 10 000 unités/jour pour le reste.
- Identifiants : l'exemple officiel Python utilise un `client_secrets.json` en bloc `"web"` ;
  un OAuth client « Application de bureau » du Cloud Console produit un bloc `"installed"`.
  `google_auth_oauthlib.flow.from_client_secrets_file` gère les deux.

## 7. MCP YouTube

Aucun serveur MCP YouTube officiel de Google. Serveurs communautaires exigeant tes propres
identifiants Google Cloud : `vapvarun/youtube-mcp` (upload, batch, playlists, miniatures,
track de quota) et `pauling-ai/youtube-mcp-server` (40 outils, Data + Analytics + Reporting).
Ils n'apportent pas de quota : ils utilisent le même client OAuth que la voie B.
Côté Hermès : `mcp_servers` dans `config.yaml`, outils exposés en `mcp_<serveur>_<outil>`,
redémarrage nécessaire (pas de hot-reload).

## 8. Le proxy Composio perd le corps des requêtes (mesuré le 2026-10-02)

| Requête | Résultat | Lecture |
|---|---|---|
| `PUT /youtube/v3/videos?part=snippet` (corps JSON) | `400 Root element must be a message` | corps perdu, reproduit 9 fois sur 9 |
| `PUT /upload/youtube/v3/videos?uploadType=resumable` (corps JSON) | `400 Root element must be a message` | corps perdu |
| `POST /upload/youtube/v3/videos?uploadType=resumable` (corps JSON) | `429` quota | ambigu : le quota est évalué avant la lecture du corps, ne prouve pas que le corps est passé |
| `POST /youtube/v3/videos?part=snippet` (corps JSON) | `429` quota « Video Uploads » | un POST sur l'endpoint de métadonnées est traité comme un insert |
| `PATCH /youtube/v3/videos?part=snippet` | `404` corps vide | méthode non routée |
| `GET /youtube/v3/channels?mine=true` | `200` + JSON complet | lectures fiables |

Scopes sondés sans rien modifier (ids bidons) :

| Appel | Résultat | Interprétation |
|---|---|---|
| `videos.update` PUT (id `00000000000`) | `400` corps perdu | non concluant sur le scope, bloqué avant |
| `thumbnails.set` POST (id bidon, PNG 1×1) | `403` « can't be set for the specified video … might not be properly authorized » | erreur de niveau vidéo, pas « insufficient authentication scopes » → scope probablement présent |

Correction d'une conclusion antérieure : la voie A n'est pas « fonctionnelle », elle est
Seulement **autorisée**. Les 429 observés ne validaient ni le transport du corps ni la
capacité réelle d'écriture.

## 9. La connexion Google en automatisation est refusée par Google (2026-10-02)

- Navigateur Hermès piloté par CDP, page `accounts.google.com/v3/signin/identifier` :
  saisie de l'e-mail OK, clic sur `#identifierNext` (le bouton porte cet id, pas
  `#identifierNext button`) → redirection vers
  `accounts.google.com/v3/signin/rejected?continue=…` et message
  « **Couldn't sign you in, This browser or app may not be secure.** »
- Aucun champ mot de passe n'est présenté : le blocage est en amont de l'authentification.
- Conséquence : le flux vault (« save login ») ne peut pas être utilisé pour Google, et la
  voie navigateur n'est viable que si une session Google préexiste dans le navigateur.
- Pièges d'environnement navigateur rencontrés : onglet retombant sur `about:blank` entre
  deux appels (utiliser `ensure_real_tab()` puis `goto_url` avec relances), et timeout IPC de
  5 s du démon sur les pages Google lourdes (relancer l'évaluation JS en boucle).
- Chromium restait cassé au départ (`libatk-1.0.so.0`) ; corrigé par l'installation des
  bibliothèques listées dans le SKILL.md. Le blocage Google est indépendant de ce correctif.
