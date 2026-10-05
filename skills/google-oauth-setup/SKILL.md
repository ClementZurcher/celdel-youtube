---
name: google-oauth-setup
description: "Configurer un accès OAuth Google pour une API."
version: 1.0.0
author: Celdel AI / Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Google, OAuth, API, Credentials, Cloud, Workspace]
    related_skills: [youtube-publish, google-workspace]
---

# Accès OAuth à une API Google avec ses propres identifiants

## When to Use / Quand l'utiliser

Quand il faut un accès **automatisé et durable** à une API Google (YouTube, Gmail, Drive,
Sheets, Calendar…) depuis l'agent, sans dépendre de l'app OAuth d'un tiers — celle d'un
service mutualisé partage son quota entre tous ses utilisateurs. Sert aussi à diagnostiquer
pourquoi une autorisation Google échoue. Cas d'usage YouTube : voir `youtube-publish`.

## Étape 0 — Diagnostiquer le compte avant tout

- **Workspace ou compte Google à adresse personnalisée ?** Interroger les MX du domaine :
  `dig +short MX <domaine>` → des `aspmx.l.google.com` = Google Workspace (console
d'administration existante, audience « Interne » disponible) ; un autre fournisseur = simple
  compte Google, **sans** console d'administration et **sans** option « Interne ». Trancher
  par le DNS avant de conseiller « Interne ».
- **Ne pas confondre « pas administrateur » et « pas de compte ».** `admin.google.com`
  n'accepte que les administrateurs du domaine : y échouer ne prouve rien sur l'accès au
  compte Google, et posséder un service (chaîne, boîte, espace) ne donne aucun droit
  d'administration. N'y envoyer l'utilisateur **que** si une politique de domaine bloque
  l'app OAuth ; sinon c'est un faux chemin qui coûte des allers-retours.
- **L'e-mail propriétaire n'est exposé par aucune API Google** : les endpoints d'identité
  (`openidconnect.googleapis.com/v1/userinfo`, `oauth2/v3|v1/userinfo`) refusent un jeton
  qui ne porte pas les scopes `openid`/`email`. Faire lire l'adresse dans l'interface du
  service concerné (pour YouTube : Studio → Paramètres → Autorisations, ligne « Propriétaire »).
- **Demander une capture de l'écran « Sélectionner un compte »** : la liste des comptes du
  navigateur révèle d'un coup les adresses disponibles et désigne sans ambiguïté celle à
  autoriser.

## Étape 1 — Projet et activation de l'API

1. Le **projet** se crée dans Menu ☰ → **IAM et administration** → **Créer un projet**
   (`console.cloud.google.com/projectcreate`). ⚠️ Pas dans « API et services » — c'est la
   confusion la plus fréquente chez l'utilisateur.
2. Activer l'API dans **API et services** → **Bibliothèque**
   (`console.cloud.google.com/apis/library/<api>.googleapis.com`).
3. Si le client OAuth est créé dans un **projet réutilisé**, l'API doit y être activée :
   ouvrir la bibliothèque avec `?project=<id du projet>` pour viser le bon projet.

## Étape 2 — Écran de consentement (Google Auth platform)

Le chemin actuel est Menu ☰ → **Google Auth platform** (`console.cloud.google.com/auth/overview`),
avec les onglets Branding / **Audience** / **Clients** / Data Access. « Get started » demande :
App name, e-mail d'assistance, **Audience**, e-mail de contact, acceptation de la politique.

| Audience | Vérification | Utilisateurs test | Jeton de rafraîchissement |
|---|---|---|---|
| **Interne** (Workspace) | Aucune | Aucune liste | **Durable** |
| Externe | Requise pour publier | Obligatoire (max 100) | **7 jours** tant que le statut est Testing |

- Préférer **Interne** dès que le compte est un Google Workspace : aucune vérification, pas
de liste d'utilisateurs test, scopes sensibles/restreints sans revue Google, **et la règle
des 7 jours ne s'applique pas** (elle vise explicitement « external user type + publishing
status Testing »). Contrepartie : un administrateur du domaine peut bloquer l'app
(`admin.google.com` → Sécurité → Contrôles API → Contrôle d'accès des applications ; le
marquage « Trusted » la traite comme interne).
- **Audience Externe** : ajouter le compte propriétaire dans Utilisateurs test, et passer
  ensuite **Audience → « Publish app »** (statut « In production ») pour un jeton durable —
l'application peut rester **non vérifiée** pour un usage personnel. « Publish app » peut
  être grisé tant que les champs de marque (page d'accueil, politique de confidentialité,
domaine autorisé) manquent. La publication **n'est pas rétroactive** : un jeton émis en
Testing garde son échéance, il faut refaire une autorisation après la bascule.
- **Détection automatique** : la réponse de jeton contient `refresh_token_expires_in`
  (en secondes) quand le jeton est à durée limitée ; champ absent ou nul = durable.
  Consigner ce contrôle dans le script d'échange de code.
- Ne pas mettre « Google » ni le nom du service (« YouTube », « Gmail ») dans l'App name :
  Google les refuse.

## Étape 3 — Client OAuth « Application de bureau »

- **Google Auth platform → Clients → Create client → Application de bureau → Download JSON**.
  Le fichier est un bloc `"installed"` (l'exemple officiel d'un autre service peut être un
  bloc `"web"` ; `from_client_secrets_file` gère les deux).
- **Stocker le secret hors conversation** : `chmod 600`, dans le dossier de travail du
  projet. Ne jamais le réafficher, même s'il a été fourni en pièce jointe : copier le fichier
  depuis le dossier d'attachements, puis ne contrôler que des métadonnées non secrètes
  (type de bloc, `project_id`, `client_id` tronqué, `redirect_uris`, longueur du secret).
- **Relever `redirect_uris`** : l'URI de redirection utilisé devra le reproduire tel quel
  (souvent `http://localhost`, sans port ni slash final). Un URI différent échoue en
  `redirect_uri_mismatch`.

## Étape 4 — Autoriser sans navigateur local

Sur une machine distante, l'agent ne peut pas faire le consentement à la place de
l'utilisateur : **Google refuse la connexion depuis un navigateur piloté par automatisation**
(page `accounts.google.com/v3/signin/rejected` → « This browser or app may not be secure. »,
avant même de demander le mot de passe). Le consentement doit donc venir du navigateur de
l'utilisateur. Procédure :

1. Générer l'**URL d'autorisation avec PKCE** (`access_type=offline`, `prompt=consent`) et
   conserver l'état PKCE (`code_verifier`) dans un fichier local, nécessaire à l'échange.
2. Ajouter **`login_hint=<adresse>` et forcer le choix du compte**
   (`prompt=select_account consent`) dès que l'utilisateur a plusieurs comptes Google dans son navigateur. Sans cela,
   Google présélectionne le dernier compte utilisé : un consentement **Interne** échoue alors
   sur un compte hors domaine avec un message d'« accès réservé à l'organisation », qui
   ressemble à tort à un blocage d'administration. Recommander une **fenêtre de navigation
   privée** pour n'y connecter que le bon compte.
3. L'utilisateur autorise, puis **copie l'URL de redirection complète** (la page `localhost`
   échoue à s'ouvrir, c'est attendu et normal) dans un **fichier** — jamais dans le chat.
4. Échanger le code contre les jetons et écrire `token.json` en `chmod 600`.
5. **Vérifier immédiatement l'identité obtenue** avant toute écriture : interroger une route
   en lecture du service et comparer la ressource à l'identifiant attendu, en refusant
   l'action si ça ne correspond pas (pour YouTube : `--whoami --expect-channel <ID>`).

## Étape 5 — Ensuite

- Le jeton se rafraîchit seul ; ne jamais redemander le mot de passe ni un nouvel accord sans
  raison (≈50 jetons vivants par compte et par client, Google révoque silencieusement les
  plus anciens).
- Refaire l'autorisation est nécessaire si : l'utilisateur révoque l'accès, le jeton reste
  inutilisé ~6 mois, les scopes demandés changent, ou l'app repasse en Testing.
- Le quota et les restrictions d'une API donnée restent attachés au **projet Google qui a
  émis le jeton**, jamais à l'outil qui appelle : changer d'outil ne change pas le quota.

## Détail des chemins de console et des règles de jeton

`references/console-and-token-rules.md` — libellés actuels de la console, tableau
Interne/Externe, règle des 7 jours, sources officielles.
