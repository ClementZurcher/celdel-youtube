---
name: internal-guides
description: "Rédiger des guides internes et les publier dans Notion."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Notion, Documentation, Guides, Redaction]
    related_skills: [notion]
---

# Guides internes (collègue, équipe, direction)

Rédiger un mode opératoire ou une note destinée à une autre personne, direction, collègue,
utilisateur non technique, et la publier dans l'espace Notion de travail, en français.

## When to Use / Quand l'utiliser

« fais-moi un guide pour X », « une note pour ma cheffe », « le mode opératoire », « documente
ça pour l'équipe ». Toute demande d'un document destiné à être lu par un tiers.

## Procédure

1. **Lire la page cible avant d'écrire.** Ouvrir la page existante de l'espace (page parente ou
dernière note du même auteur) et s'en inspirer : tournures, longueur des puces, usage des blocs
de code et des captures. Le lecteur doit retrouver le même registre que dans le reste de son
espace, c'est ce qui distingue un guide intégré d'un document étranger.
2. **Rassembler tout le nécessaire avant de rédiger**, et le garder dans le document :
   prérequis (comptes, outils, coût), ce qu'il faut installer (skills, scripts, CLI), le **bloc
   exact à donner à l'agent**, ce que le lecteur doit faire lui-même, ce que l'agent fait ensuite.
3. **Rédiger au format « quoi taper ».** Tournure validée : « Pour <faire X>, il faut taper ça
   dans Hermès : » suivi d'un bloc `plain text`, puis « Puis suivre les étapes qu'Hermès donne. »
   Le lecteur doit pouvoir copier-coller sans réfléchir.
4. **Publier**, voir `references/notion-pages-via-composio.md`.
5. **Vérifier en relisant la page publiée** (longueur, sections attendues). La réponse de
   création ne prouve pas le contenu.

## Règles de style

- Français simple, phrases courtes, puces à l'infinitif ou à l'impératif ; aucun jargon hors des
  blocs à copier.
- **Ne documenter que le nécessaire.** Avant de rédiger, passer chaque prérequis au test « en
  a-t-on besoin ? » : si un moyen plus simple atteint le même résultat, c'est lui qu'on écrit (un
  usage rare ne justifie ni audit fournisseur ni automatisation lourde). Un prérequis non justifié
  alourdit le guide et décourage le lecteur.
- **Ne jamais couper le nécessaire pour raccourcir.** Ce qui reste : prérequis, skills à
  installer, blocs à copier, ce que le lecteur doit faire. Ce qui sort : quotas, tables
  d'erreurs techniques, justifications de fond.
- **Les prérequis s'écrivent en étapes, jamais en état.** « Un projet Google Cloud avec l'API
  activée » ne sert à rien à qui n'en a aucun : écrire pour quelqu'un qui n'a **rien** fait.
  Étapes numérotées, chemins de menu exacts et liens cliquables (« menu ☰ → IAM et
  administration → Créer un projet »), y compris les pièges de libellé, le projet ne se crée
  **pas** dans « API et services », et l'écrire évite au lecteur l'aller-retour classique.
  De même, donner le lien de ce qu'il faut récupérer (dépôt, archive) et comment y accéder.
  Un lien nu n'est pas une consigne : il faut aussi dire ce qu'on en fait.
- **Une limite matérielle = une ligne**, sans section ni paragraphe (« le passage en public se
  fait en un clic »). Ne pas empiler les avertissements.
- **Ne jamais répéter une information** : elle apparaît une fois, à l'endroit où elle sert.
- Écrire pour le destinataire : direction = bénéfice, sécurité, coût, décisions à prendre ;
  utilisateur outillé = quoi taper, quoi faire ensuite.
- Pas de section « état de validation » dans un document destiné à un tiers, sauf demande.

## Honnêteté

- Un mode opératoire s'écrit au ton affirmé, c'est une procédure, mais **jamais** en y
  affirmant qu'un test a eu lieu s'il n'a pas eu lieu. Signaler l'écart à l'utilisateur dans la
  conversation, pas dans le document.
- Les limites de politique d'un fournisseur (audit, vérification, quota réglementaire) peuvent
  rester : elles resteraient vraies après cent tests réussis.

## Pièges

- Rédiger avant d'avoir lu la page cible → registre et format décalés, réécriture complète.
- Publier sans relire la page → un bloc tronqué passe inaperçu.
- Vouloir modifier le contenu d'une page existante par `PATCH` : le schéma attendu n'est pas
  celui du markdown de création (détail et contournement dans la référence).
- **« Installe le skill <nom> » est faux quand le skill est local** : les registres publics renvoient
  des homonymes tiers et feraient installer le skill de quelqu'un d'autre. Nommer la source de
  fichiers (dépôt, archive, chemin `skills/<catégorie>/…`) et préciser de ne rien installer depuis
  un registre public.
- **Un dépôt privé n'est pas installable par le destinataire.** Un guide qui pointe un dépôt privé
  doit dire comment y accéder (collaborateur ajouté, dépôt public filtré, ou archive livrée), 
  sinon il annonce une installation impossible.
- Publier un document qui affirme des choses sur l'environnement (chemins, noms d'outils, étapes
  d'installation) sans les vérifier : un guide faux coûte plus cher qu'un guide absent.
