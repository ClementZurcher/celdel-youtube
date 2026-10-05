# Console Google (libellés 2026) et règles de jeton

## Chemins exacts à transmettre à l'utilisateur

| Étape | Où | Lien |
|---|---|---|
| Créer le projet | Menu ☰ → **IAM et administration** → **Créer un projet** (⚠️ pas dans « API et services ») | console.cloud.google.com/projectcreate |
| Activer l'API | **API et services** → **Bibliothèque** | console.cloud.google.com/apis/library/<api>.googleapis.com |
| Consentement / marque | **Google Auth platform** → Get started / Branding | console.cloud.google.com/auth/overview |
| Audience, utilisateurs test, « Publish app » | **Google Auth platform** → **Audience** | console.cloud.google.com/auth/audience |
| Client OAuth | **Google Auth platform** → **Clients** → Create client | console.cloud.google.com/auth/clients |
| Console d'administration Workspace | Sécurité → Contrôles API → Contrôle d'accès des applications | admin.google.com/ac/owl |

« API et services » héberge la bibliothèque et les identifiants, **pas** la création du projet.

## Tableau Interne / Externe (comportement documenté par Google)

| Publishing status | User type | Utilisateurs test | Vérification | Notes |
|---|---|---|---|---|
| N/A | **Internal** | Non | N/A | Tous les utilisateurs de l'organisation ; vérification inutile ; la liste des scopes peut ne pas s'afficher ; scopes sensibles/restreints sans revue pour un usage interne |
| Testing | External | Oui (max 100) | N/A | Écran d'avertissement « app en test » ; **jeton de rafraîchissement limité à 7 jours** |
| Published | External | Non | Non vérifiée | Écran « Google n'a pas vérifié cette application » (contournable via Avancé) ; plafond de 100 utilisateurs |
| Published | External | Non | Vérifiée | Nom, logo et scopes affichés sans avertissement |

Un administrateur Workspace peut bloquer **n'importe quelle** app OAuth ; une app marquée
« Trusted » est traitée comme interne pour le domaine, ce qui lève notamment la limite des
7 jours et le plafond de 100 utilisateurs.

## Règle des jetons

- Un projet avec consentement **externe + statut Testing** délivre un jeton de rafraîchissement
  expirant en **7 jours** (sauf si les seuls scopes demandés sont `openid`, `email`, `profile`).
  Re-authentifier ne repousse que de 7 jours.
- Indice dans la réponse de jeton : `refresh_token_expires_in: 604800` = sur la horloge des
  7 jours ; champ absent ou nul = durable.
- Sécurité : environ 50 jetons vivants par compte et par client ; au-delà, Google révoque
  silencieusement le plus ancien. Ne pas boucler des autorisations.

## Sources officielles

- Récupération des identifiants et types de client : developers.google.com/workspace/guides/create-credentials
- Consentement et scopes : developers.google.com/workspace/guides/configure-oauth-consent
- Types d'audience / statut de publication : support.google.com/cloud/answer/15549945
- Google Auth platform : support.google.com/cloud/answer/15544987
- Expiration des jetons : developers.google.com/identity/protocols/oauth2
- Catégories de scopes et vérification : support.google.com/cloud/answer/9110914
