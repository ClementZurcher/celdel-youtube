# Publier un dossier local sur GitHub via le proxy Composio

Cas d'usage : mettre un dossier sur GitHub alors qu'aucun `gh` authentifié n'existe sur la
machine, mais que la connexion **GitHub** est active dans Composio. Aucun secret n'est
manipulé : l'authentification est injectée par Composio.

Méthode : API **Git Data** (blobs → tree → commit → ref). Chaque fichier coûte une requête ;
les blobs partent en parallèle.

## Procédure

1. **Identité**, `GET /user` : c'est ce compte qui possédera le dépôt. L'annoncer à
   l'utilisateur avant de créer quoi que ce soit.
2. **Créer le dépôt**, `POST /user/repos` avec
   `{"name": "…", "private": true, "description": "…", "auto_init": true}`.
   Le plan gratuit autorise les dépôts privés. Un échec « already exists » n'est pas un échec :
   `GET /repos/{owner}/{name}` puis continuer.
3. **Base**, `GET /repos/{o}/{r}/git/ref/heads/{branche}` → sha du commit ;
   `GET /repos/{o}/{r}/git/commits/{sha}` → sha de l'arbre de base (`auto_init` en a créé un).
4. **Blobs**, un `POST /repos/{o}/{r}/git/blobs` par fichier, corps
   `{"content": "<base64>", "encoding": "base64"}`, en parallèle (4–6 fils). Consigner la
   progression tous les 25 fichiers.
5. **Arbre**, `POST /repos/{o}/{r}/git/trees` avec
   `{"base_tree": "<sha>", "tree": [{"path": …, "mode": "100644"|"100755", "type": "blob", "sha": …}]}`.
   Le mode `100755` se déduit du bit exécutable du fichier local (sinon les scripts arrivent
   non exécutables).
6. **Commit puis branche**, `POST /git/commits` avec `{message, tree, parents: [<sha base>]}`,
   puis `PATCH /git/refs/heads/{branche}` avec `{"sha": <commit>, "force": false}`.
7. **Vérifier en relisant le dépôt**, `GET /repos/{o}/{r}/git/trees/{branche}?recursive=1` et
   comparer l'ensemble des chemins à `git ls-files` du dossier local (manquants / en trop).
   Le code de sortie du script ne prouve rien.

## Pièges

- **Fichier de charge utile partagé entre appels parallèles** : la CLI lit le `@fichier` de
  façon asynchrone ; un nom réutilisé puis supprimé provoque `ENOENT … /tmp/….json` et fait
  échouer précisément les fichiers tombés dans la fenêtre. Nom unique par appel, et pas de
  suppression pendant l'exécution du lot.
- **Erreurs avalées comme des succès** : la CLI ne renvoie pas de code HTTP. GitHub signe ses
  erreurs par un champ `documentation_url`, jamais présent sur un succès. Un `422` de création
  (« already exists ») traité comme un succès fait tomber le script au premier accès de champ.
- **Gros fichiers : la limite est basse et bruyante.** Un fichier de 3,9 Mo (≈ 5,2 Mo en
  base64) est refusé par le proxy : `413 Request Entity Too Large` sur
  `POST /git/blobs`. Une charge de 256 Ko passe sans problème. Le seuil se situe donc
  entre les deux, et l'échec n'arrive **qu'à l'étape blobs**, après un long envoi.
  Avant de publier : lister les fichiers lourds (`git ls-files -z | xargs -0 du -h | sort -rh`)
  et exclure via `.gitignore` tout ce qui dépasse quelques centaines de Ko. Vérifier d'abord
  que ces fichiers sont réellement utilisés par le skill (`grep -r "assets/" SKILL.md`) :
  dans la pratique, les gros assets sont souvent des restes de test. Un blob volumineux se
  transmet toujours par `@fichier` (base64), jamais en ligne de commande.
- **Le script de publication ne doit pas vivre dans le dossier publié**, sinon il se versionne
  lui-même au passage suivant (`git ls-files` le verra).
- **Un dépôt fraîchement créé avec `auto_init` contient un `README.md`** : la première poussée
  le remplace si le dossier local en fournit un.
- **Publier depuis l'index** : un fichier non `git add` n'est pas publié. Construire la liste
  avec `git ls-files`, jamais par un parcours disque.

## Versionner les skills d'un profil (forme du dépôt)

Quand le dépôt sert à réinstaller une configuration d'agent ailleurs, un dépôt par profil, privé :

```
skills/<catégorie>/<skill>/…     les skills maison du profil, tels qu'ils sont installés
scripts/                         les scripts que les skills invoquent
docs/                            les guides destinés aux humains
profil/SOUL.md                   la fiche de profil, c'est elle qui définit l'agent
MANIFEST.tsv  install.sh  README.md  .gitignore
```

- **Ne pas embarquer les skills bundled/hub** : ils se rafraîchissent par ailleurs et deviennent des
  copies périmées dans le dépôt. Le dépôt porte ce qui est maison.
- **Un `THIRD_PARTY.md`** nommant les skills tiers et leur origine ; sa seule présence suffit à
  justifier un dépôt **privé**.
- **`install.sh` se teste** : installer pour de vrai, et vérifier qu'il échoue proprement sur un
  profil inexistant.
- **Un seul script pour N dépôts**, piloté par l'environnement (dossier source, nom, description,
  message de commit) plutôt qu'avec des valeurs codées en dur : un dépôt en échec se republie seul,
  sans rejouer les autres. La poussée reconstruit toute l'arborescence en un commit : relancer est
  idempotent.
- **Après publication, vérifier dépôt par dépôt** : comparer `git ls-files` local aux chemins du
  tree distant (`?recursive=1`), et contrôler la présence du fichier de profil.

## Conséquence pour la distribution

Un dépôt **privé** impose des identifiants GitHub pour `git clone` : un destinataire sans accès
au dépôt ne peut pas installer. Avant d'annoncer « c'est installable », proposer l'une des
solutions : l'ajouter comme collaborateur, publier un second dépôt public **filtré** (sans les
contenus internes ni les skills tiers), ou livrer une archive.
