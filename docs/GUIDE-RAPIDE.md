# Guide rapide : publier sur YouTube depuis Hermès

Version courte, opérationnelle. Mise en place une fois, puis une commande par vidéo.

---

## 1. Ce dont tu as besoin

| | Détail |
|---|---|
| Compte | Le compte Google **propriétaire de la chaîne**. Son mot de passe n'est jamais donné à l'agent : il ne sert qu'à toi, une fois, dans ton navigateur |
| Google Cloud | Un projet, l'API **YouTube Data API v3** activée, un client OAuth **Application de bureau** (`client_secret.json`) |
| Machine | Un Python avec `googleapiclient` et `google_auth_oauthlib`, plus le script `yt_upload.py` |
| Coût | 0 €, API gratuite, 100 téléversements/jour |

---

## 2. Skills à installer

Trois skills, tous dans le dossier `media` :

| Skill | Rôle | Installation |
|---|---|---|
| `youtube-content` | Transcript → résumé, chapitres | déjà fourni avec Hermès (bundled) |
| `youtube-metadata` | Titre, description, chapitres, tags, catégorie | à copier (fourni dans le pack) |
| `youtube-publish` | Autorisation OAuth + téléversement + garde-fous | à copier (fourni dans le pack) |

Installation des deux skills du pack :

```bash
PROFIL=~/.hermes/profiles/<nom_du_profil>
cp -r pack/skills/youtube-metadata $PROFIL/skills/media/
cp -r pack/skills/youtube-publish  $PROFIL/skills/media/
```

> Alternative : `hermes skills install <URL_https_du_SKILL.md> --category media --name youtube-publish`
> (l'installateur officiel accepte une URL directe vers un `SKILL.md`).

Skills utiles en option : `humanizer` (écrit moins « IA »), `youtube-content` pour les
chapitres depuis un transcript.

---

## 3. Mise en route (une seule fois, ~10 min)

```bash
cd <dossier_de_travail>
chmod 600 client_secret.json            # le fichier téléchargé depuis Google Cloud

# a) générer le lien d'autorisation
python yt_upload.py --print-auth-url --client-secret client_secret.json \
  --redirect-uri "http://localhost" --login-hint <adresse_du_proprietaire> --select-account

# b) ouvrir le lien dans TON navigateur, choisir le compte PROPRIÉTAIRE, Autoriser
#    la page finale affiche une erreur localhost : c'est normal
#    coller l'URL de la barre d'adresse dans un fichier url.txt

# c) finaliser
python yt_upload.py --finish-auth url.txt --client-secret client_secret.json

# d) vérifier que le jeton administre la bonne chaîne
python yt_upload.py --whoami --expect-channel <ID_DE_LA_CHAINE>
```

Si l'étape (c) affiche `refresh_token_expires_in` : le consentement est en statut *Testing*.
Passer « Publish app » (In production) puis refaire (a) et (c) une fois.

---

## 4. Publier une vidéo

```bash
# contrôle à blanc, rien n'est envoyé
python yt_upload.py --check --video ma_video.mp4 --title "…" --description-file desc.txt --duration 620

# envoi réel (privé par défaut)
python yt_upload.py --via oauth --video ma_video.mp4 --title "…" \
  --description-file desc.txt --tags "a, b" --category 28 [--publish-at 2026-10-08T18:00:00+02:00]
```

Dans Hermès, le message à envoyer suffit :

```
Vidéo : /chemin/ma_video.mp4
Sujet : <2-3 lignes>   Audience : <…>   Objectif : <…>
Fais tout : métadonnées, chapitres, tags, miniature, téléversement. Laisse en privé.
```

---

## 5. Les 5 erreurs qu'on a rencontrées (et leur correctif)

| Message | Cause | Correctif |
|---|---|---|
| `This request contains scopes that cannot be requested together` | `youtube.*` + `drive.file` (souvent via `include_granted_scopes`) | régénérer l'URL **sans** `include_granted_scopes` |
| `Access blocked` / « limitée aux utilisateurs de votre organisation » | consentement **Interne** + mauvais compte connecté | `--login-hint` + `--select-account`, ou passer en **Externe** + utilisateur test |
| « This browser or app may not be secure » | Google bloque la connexion depuis un navigateur automatisé | ne pas automatiser la connexion : l'utilisateur autorise lui-même |
| `quotaExceeded, Video Uploads` | 100 téléversements/jour atteints | attendre le lendemain |
| Vidéo en ligne mais **privée** alors que `public` demandé | projet Google non audité | audit API, ou bascule manuelle dans Studio |

Non-erreur à ignorer : `admin.google.com` refuse l'accès → cette console n'est pas nécessaire
au montage.

---

## 6. Garde-fous

- **Privé par défaut.** Passage en public seulement sur instruction explicite.
- **Aucun mot de passe** ne passe par l'agent : l'autorisation se fait dans ton navigateur.
- `client_secret.json` et `token.json` en `chmod 600`, jamais affichés ni collés dans le chat.
- Vérification systématique de la chaîne cible (`--whoami --expect-channel`) avant tout envoi.

---

## 7. État de validation

| | |
|---|---|
| Prouvé | métadonnées (validation script), lecture chaîne, génération du lien d'autorisation |
| **À prouver** | le **premier téléversement réel** : à faire sur une vidéo courte, en privé, puis suppression si non désirée |
| Limite structurelle | publication **publique** par API = audit Google ; sinon un clic manuel dans Studio |
