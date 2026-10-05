---
name: youtube-metadata
description: "Préparer titre, description, tags et chapitres YouTube."
version: 1.0.0
author: Celdel AI / Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [YouTube, Metadata, SEO, Description, Tags, Chapters]
    related_skills: [youtube-content]
---

# Paquet de métadonnées YouTube (titre, description, tags, chapitres)

Répondre en français. Champs séparés et copiables, ton professionnel et clair.

## When to Use / Quand l'utiliser

Dès qu'on demande un titre, une description, des tags, des chapitres, un texte de
miniature, une catégorie ou « les métadonnées » d'une vidéo YouTube. Pour extraire un
transcript et en tirer un résumé ou des chapitres, utiliser d'abord `youtube-content`
(helper `scripts/fetch_transcript.py`, option `--timestamps`).

## Entrées nécessaires : et quoi faire s'il en manque

| Élément | Sert à | S'il est absent |
|---|---|---|
| Fichier vidéo ou transcript | Fonder le résumé, les chapitres, les tags | Demander le fichier/transcript, ou livrer une version provisoire signalée « provisoire, à compléter » |
| Durée | Valider les horodatages, la longueur des chapitres | Ne pas inventer d'horodatages ; proposer des chapitres seulement si le transcript en contient |
| Audience cible | Choisir le vocabulaire et les mots-clés | Demander, ou proposer deux variantes étiquetées |
| Objectif (notoriété, lead, formation) | Prioriser le CTA | Demander, ou proposer un CTA neutre sans promesse |
| Charte/nom de chaîne, liens | Description, crédits | Laisser des emplacements `[à compléter]`, ne rien inventer |

## Règles de production

- **Titre** : 100 caractères max côté YouTube, mais ~60–70 visibles en recherche et
  moins en fil mobile. Mettre les mots réellement recherchés au début, le nom de chaîne
  à la fin. Pas de majuscules criardes ni de promesse absente de la vidéo.
- **Description** : 5 000 caractères max ; seuls les ~150 premiers sont visibles avant
  « Plus ». Ces premiers caractères = résumé d'une phrase + lien principal. Ensuite :
  chapitres, ressources citées, crédits, mentions commerciales.
- **Chapitres** : règles strictes, premier horodatage exactement `00:00`, au moins
  3 horodatages, ordre croissant, chaque chapitre ≥ 10 secondes ; `m:ss` sous une heure,
  `h:mm:ss` au-delà. Un horodatage faux invalide toute la liste : ne les établir que
  depuis le transcript, une liste de timecodes fournie, ou la durée réelle. Sinon, ne pas
  mettre de chapitres du tout.
- **Tags YouTube** : budget total de 500 caractères, virgules comprises. ~10–15 tags
  courts suffisent. Tags = sujet précis, nom d'outil/marque, orthographes alternatives.
  Jamais de tags trompeurs ou sans rapport (spam). Ne pas confondre avec les hashtags.
- **Hashtags (description)** : n'en garder que 3 utiles. Au-delà de 15 dans la
  description, YouTube ignore tous les hashtags.
- **Catégorie** : proposer une seule catégorie YouTube officielle, avec une justification
  d'une ligne.
- **Miniature** : si demandé, texte de 3–6 mots lisible en petit + description du visuel.
  Ne jamais affirmer avoir produit un fichier image sans l'avoir réellement produit.
- Les limites chiffrées ci-dessus viennent de la documentation YouTube et des guides
  créateurs ; les re-vérifier dans YouTube Studio avant de les présenter comme confirmées.

## Vérifications avant livraison

1. Chaque promesse du titre et de la description existe dans la vidéo (pas de contenu trompeur).
2. Noms propres, liens, dates, mentions commerciales (sponsor, partenariat), droits
   musicaux, personnes identifiables, données confidentielles : à confirmer avec
   l'utilisateur, jamais présentés comme validés.
3. Longueurs comptées, pas estimées : utiliser le terminal (`python -c`), jamais le calcul mental.
4. Aucun horodatage inventé.

## Format de livraison

Toujours proposer les champs séparés, prêts à coller :

```
## Titre (<n>/100 caractères)
…

## Description (<n>/5000 caractères)
…

## Chapitres
00:00 …

## Tags YouTube (<n>/500 caractères, virgules comprises)
tag1, tag2, …

## Hashtags (description, 3 max)
#…

## Catégorie suggérée
…, justification en une ligne

## Texte de miniature
…

## Statut
Préparation à valider
```

## Publication

- Statut par défaut : « Préparation à valider ». Un fichier fourni n'est pas une
  autorisation de téléverser.
- Aucun outil d'upload n'est exposé par le toolkit `youtube` de Composio (27 outils,
  ni `videos.insert` ni `videos.update`), mais la publication reste possible par proxy
  Composio, par OAuth propre ou par le navigateur. Voir le skill `youtube-publish` pour
  les voies vérifiées, les limites de quota et le script `yt_upload.py`. Ne jamais
  annoncer un téléversement non vérifié.
- Ne téléverser, programmer, publier, supprimer ou modifier aucune vidéo sans
  instruction explicite portant sur le fichier, la chaîne et l'action concernée.
- Si une intégration autorisée existe : téléverser en privé/brouillon, confirmer titre,
  description, tags, miniature et visibilité, puis demander une confirmation explicite
  avant toute mise en public. Ne jamais annoncer un téléversement non vérifié.

## Pièges

- Horodatages devinés « à l'œil » → chapitres refusés silencieusement par YouTube.
- Timestamps dans un commentaire épinglé : liens cliquables mais aucun chapitre.
- Titre/description gonflés au-delà des limites → champ refusé ou tronqué.
- Mur de hashtags (>15) → tous ignorés.
- Estimer les totaux de caractères de tête → compter avec un outil.

## Références

- Chapitres (règles officielles) : https://support.google.com/youtube/answer/9884579
- Extraction de transcript et formats de sortie : skill `youtube-content`.
