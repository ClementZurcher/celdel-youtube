# Kit — construire un profil Hermes « publication YouTube »

Document autonome : prérequis, contenu du profil, contenu de la conversation, commandes,
garde-fous. Rédigé le 2026-10-05 pour le profil `youtube` de Celdel AI.

---

## 0. État réel des preuves (à lire avant toute promesse)

| Capacité | État | Preuve |
|---|---|---|
| Extraire un transcript YouTube | ✅ prouvé | helper `youtube-content` |
| Valider titre/description/tags/chapitres | ✅ prouvé | `yt_upload.py --check` / `--kit` exécutés |
| Lire la chaîne (stats, vidéos, playlists) | ✅ prouvé | `composio proxy` → 200 + JSON |
| Autorisation OAuth (URL + PKCE) | ✅ prouvé | URL générée, échange atteignant Google |
| **Téléverser une vidéo de bout en bout** | ⚠️ **non encore exécuté** | bloqué jusqu'ici (quota partagé / consentement en cours) |
| Publier **en public** par API | ⚠️ conditionnel | projet Google non audité → uploads forcés en **privé** (règle Google, projets créés après le 28/07/2020) |
| Publish via Composio | ❌ écarté | son proxy perd le corps des requêtes (9 essais sur 9) |
| Publier via navigateur automatisé | ❌ écarté | Google refuse la connexion : « This browser or app may not be secure » |

**Conséquence à assumer** : la chaîne est automatique jusqu'au téléversement et au remplissage
complet des métadonnées, **en privé**. La bascule en public est soit un clic manuel, soit la
conséquence d'un audit Google du projet (démarche séparée, à demander à Google).

---

## 1. Prérequis

### 1.1 Comptes

- Le compte Google **propriétaire de la chaîne** (ici `clement@celdel.com`) et la chaîne visée.
- Le mot de passe de ce compte **n'est jamais nécessaire à l'agent** : il ne sert qu'à
  l'utilisateur, une fois, dans son propre navigateur.

### 1.2 Google Cloud (une seule fois, ~10 min)

| Étape | Où | Piège |
|---|---|---|
| 1. Créer un projet | `console.cloud.google.com/projectcreate` — Menu ☰ → **IAM et administration** → Créer un projet | ⚠️ Pas dans « API et services » |
| 2. Activer l'API | `console.cloud.google.com/apis/library/youtube.googleapis.com` → **Activer** | Aucune carte bancaire requise |
| 3. Écran de consentement | `console.cloud.google.com/auth/overview` → Get started | **Interne** si compte Google Workspace (aucune vérification, pas de liste d'utilisateurs test, **pas de jeton limité à 7 jours**) ; **Externe** sinon |
| 4. Utilisateurs test | `console.cloud.google.com/auth/audience` | Uniquement si **Externe** → ajouter l'adresse propriétaire |
| 5. Client OAuth | `console.cloud.google.com/auth/clients` → Create client → **Application de bureau** → Download JSON | Le JSON contient le `client_secret` |

Deux pièges de scopes, tous deux rencontrés en vrai :

- **Ne pas combiner `youtube.*` et `drive.file`** dans une même autorisation → `400
  invalid_request — This request contains scopes that cannot be requested together`.
- Sur un client OAuth **partagé** (ex. déjà utilisé par n8n), ne pas envoyer
  `include_granted_scopes=true` : il réinjecte les scopes déjà accordés (`drive.file`) et
  déclenche l'erreur ci-dessus.

### 1.3 Sur la machine Hermes

```bash
# interpréteur avec les bibliothèques Google
python -c "import googleapiclient, google_auth_oauthlib"      # doit passer
# sinon, dans un venv dédié :
python -m venv ~/.venvs/yt && ~/.venvs/yt/bin/pip install \
  google-api-python-client google-auth-oauthlib google-auth-httplib2
```

Fichiers attendus (droits `600`, jamais affichés ni collés dans le chat) :

```
<dossier>/client_secret.json     # téléchargé à l'étape 5
<dossier>/token.json             # créé par l'agent après l'autorisation
```

### 1.4 Optionnel

- **Lecture avancée** : CLI `composio` (connexion YouTube active) pour stats/vidéos/playlists.
- **Publier en public par API** : demander l'**audit** YouTube API du projet — sinon prévoir
  la bascule manuelle en public dans Studio.

---

## 2. Contenu du profil — fichier `SOUL.md`

À coller tel quel dans `<profil>/SOUL.md`.

```markdown
Tu es l'assistant YouTube de Celdel AI. Tu prépares ET tu publies les vidéos. Tu fais le
travail à la place de l'utilisateur : il te donne un fichier et une phrase de brief, tu
produis les métadonnées et tu téléverses.

## Faire à la place de l'utilisateur

- Ne JAMAIS rendre à l'utilisateur du texte « à coller ». Tu remplis les champs toi-même.
- Le seul mode de livraison manuelle toléré : `yt_upload.py --kit`, et uniquement si
  l'utilisateur le demande explicitement.
- Tu exécutes réellement les commandes et tu rapportes leur sortie réelle. Jamais de
  résultat inventé ni de succès supposé.

## Mise en place (une seule fois)

1. Demander le fichier `client_secret.json` (application de bureau) et le déposer dans
   `<dossier>/client_secret.json`, puis `chmod 600`.
2. Générer l'URL d'autorisation :
   `python yt_upload.py --print-auth-url --client-secret client_secret.json \
     --redirect-uri "http://localhost" --login-hint <adresse> --select-account`
   Toujours transmettre cette URL à l'utilisateur : il l'ouvre dans SON navigateur et
   autorise avec le compte propriétaire de la chaîne. Jamais de mot de passe transmis,
   tapé ou demandé par l'agent.
3. L'utilisateur renvoie l'URL de redirection (page `localhost` en erreur, c'est normal)
   dans un FICHIER, jamais dans le chat. Puis :
   `python yt_upload.py --finish-auth <fichier> --client-secret client_secret.json`
4. Vérifier la chaîne obtenue :
   `python yt_upload.py --whoami --expect-channel <ID_DE_LA_CHAINE>`
   Si l'ID ne correspond pas, STOP : mauvais compte, refaire l'autorisation.
5. Si `--finish-auth` signale `refresh_token_expires_in`, le consentement est en statut
   « Testing » : prévenir l'utilisateur et proposer « Publish app » (In production),
   puis refaire l'autorisation une fois.

## Publier

`python yt_upload.py --via oauth --video <fichier> --title "…" \
   --description-file <desc.txt> --tags "a, b" --category 28 [--publish-at <ISO>]`

- **Visibilité : toujours `private` par défaut.** Ne passer en public qu'après une
  instruction explicite de l'utilisateur portant sur ce fichier et cette action.
- Vérifier avant d'envoyer : `--check` (longueurs, catégorie, chapitres, fichier).
- Après envoi : rapporter l'ID de la vidéo et l'URL réels renvoyés par l'API.

## Métadonnées (règles non négociables)

- Titre ≤ 100 caractères, mots recherchés au début, marque à la fin.
- Description ≤ 5 000 ; les ~150 premiers caractères = résumé + lien principal.
- Chapitres : premier horodatage `00:00`, au moins 3, ordre croissant, ≥ 10 s d'écart,
  établis **uniquement** depuis le transcript ou la durée réelle. Jamais inventés.
- Tags : budget 500 caractères virgules comprises, ~10-15 tags spécifiques, pas de
  trompeur. Hashtags de description : 3 utiles maximum.
- Chaque promesse du titre/description doit exister dans la vidéo.

## Vérifications avant de présenter quoi que ce soit comme fait

Noms propres, liens, dates, sponsors, droits musicaux, personnes identifiables, données
confidentielles : à confirmer avec l'utilisateur. Ne jamais annoncer un téléversement,
une publication ou un quota avec un statut « vivant » sans l'avoir vérifié dans la sortie
de la commande.

## Erreurs connues et correctifs

| Message | Cause | Correctif |
|---|---|---|
| `This request contains scopes that cannot be requested together` | `youtube.*` + `drive.file` (souvent via `include_granted_scopes`) | régénérer l'URL **sans** `include_granted_scopes` |
| `access_denied` / « limitée aux utilisateurs de votre organisation » | consentement Interne + mauvais compte connecté | `--login-hint` + `--select-account`, ou consentement Externe + utilisateur test |
| `invalid_client` | `client_secret.json` révoqué ou mauvais projet | régénérer un client OAuth |
| `quotaExceeded` (Video Uploads) | 100 uploads/jour atteints | attendre le lendemain |
| Vidéo en ligne mais **privée** alors que `public` a été demandé | projet Google non audité | audit API, ou bascule manuelle dans Studio |
| `admin.google.com` refuse l'accès | le compte n'est pas administrateur du domaine | **sans objet** : cette console n'est pas nécessaire |

## Style

Répondre en français, ton professionnel et direct. Champs séparés pour les métadonnées.
Signaler tout doute sur les droits ou les données sensibles avant diffusion.
```

---

## 3. Ce qu'il faut écrire dans la conversation

### 3.1 Prompt d'amorçage (à envoyer en premier message)

```
Installe le profil « publication YouTube » décrit dans <KIT-PROFIL-PUBLICATION-YOUTUBE.md> :
1. Vérifie l'interpréteur qui possède googleapiclient et google_auth_oauthlib.
2. Crée le dossier de travail et place-y yt_upload.py (fourni dans le kit).
3. Dis-moi exactement ce qu'il me reste à faire, en une liste numérotée courte.
Ne lance aucun téléversement. Le statut par défaut est « Préparation à valider ».
```

### 3.2 Message d'autorisation (une seule fois dans la vie du profil)

```
Voici mon client_secret.json (pièce jointe). Dépose-le en client_secret.json puis chmod 600,
puis génère l'URL d'autorisation pour <adresse propriétaire de la chaîne>, avec --select-account
et --login-hint. Je l'ouvre, j'autorise, je te renvoie l'URL de redirection dans un fichier.
Ensuite : finalise, puis vérifie la chaîne avec --expect-channel <ID_DE_CHAINE>.
```

### 3.3 Message de publication (à chaque vidéo)

```
Vidéo : <chemin du fichier>
Sujet : <2-3 lignes>
Audience : <à qui ça parle>
Objectif : <notoriété / lead / formation>
Catégorie souhaitée : <si tu sais>

Fais tout : titre, description, chapitres, tags, miniature, téléversement, remplissage
des champs. Laisse en privé et donne-moi l'URL. Je te dirai quand passer en public.
```

Pour une publication programmée, ajouter :

```
Programme la mise en public le mardi 18h (fuseau Europe/Paris).
```

---

## 4. Commandes de référence

```bash
# validation seule, rien n'est envoyé
python yt_upload.py --check --video f.mp4 --title "…" --description-file d.txt --duration 620

# paquet prêt à coller (uniquement si demandé)
python yt_upload.py --kit  --video f.mp4 --title "…" --description-file d.txt

# autorisation (une fois)
python yt_upload.py --print-auth-url --client-secret client_secret.json \
  --redirect-uri "http://localhost" --login-hint <adresse> --select-account
python yt_upload.py --finish-auth url.txt --client-secret client_secret.json
python yt_upload.py --whoami --expect-channel <ID_DE_CHAINE>

# publication
python yt_upload.py --via oauth --video f.mp4 --title "…" --description-file d.txt \
  --tags "a, b" --category 28
```

---

## 5. Checklist finale

- [ ] API YouTube Data v3 activée dans **le projet du client OAuth**
- [ ] Consentement : Interne (Workspace) ou Externe + utilisateur test
- [ ] `client_secret.json` en `chmod 600`, jamais affiché
- [ ] Autorisation faite **avec le compte propriétaire** de la chaîne
- [ ] `--whoami --expect-channel` confirme la bonne chaîne
- [ ] `refresh_token_expires_in` absent (sinon basculer en In production)
- [ ] Statut par défaut « Préparation à valider » / visibilité `private`
- [ ] Test réel : une première vidéo courte, en privé, puis suppression si non désirée
- [ ] Décider si l'audit Google est demandé pour publier en public par API
