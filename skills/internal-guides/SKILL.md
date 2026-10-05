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

Rédiger un mode opératoire ou une note destinée à une autre personne — direction, collègue,
utilisateur non technique — et la publier dans l'espace Notion de travail, en français.

## When to Use / Quand l'utiliser

« fais-moi un guide pour X », « une note pour ma cheffe », « le mode opératoire », « documente
ça pour l'équipe ». Toute demande d'un document destiné à être lu par un tiers.

## Procédure

1. **Lire la page cible avant d'écrire.** Ouvrir la page existante de l'espace (page parente ou
dernière note du même auteur) et s'en inspirer : tournures, longueur des puces, usage des blocs
de code et des captures. Le lecteur doit retrouver le même registre que dans le reste de son
espace — c'est ce qui distingue un guide intégré d'un document étranger.
2. **Rassembler tout le nécessaire avant de rédiger**, et le garder dans le document :
   prérequis (comptes, outils, coût), ce qu'il faut installer (skills, scripts, CLI), le **bloc
   exact à donner à l'agent**, ce que le lecteur doit faire lui-même, ce que l'agent fait ensuite.
3. **Rédiger au format « quoi taper ».** Tournure validée : « Pour <faire X>, il faut taper ça
   dans Hermès : » suivi d'un bloc `plain text`, puis « Puis suivre les étapes qu'Hermès donne. »
   Le lecteur doit pouvoir copier-coller sans réfléchir.
4. **Publier** — voir `references/notion-pages-via-composio.md`.
5. **Vérifier en relisant la page publiée** (longueur, sections attendues). La réponse de
   création ne prouve pas le contenu.

## Règles de style

- Français simple, phrases courtes, puces à l'infinitif ou à l'impératif ; aucun jargon hors des
  blocs à copier.
- **Ne jamais couper le nécessaire pour raccourcir.** Ce qui reste : prérequis, skills à
  installer, blocs à copier, ce que le lecteur doit faire. Ce qui sort : quotas, tables
  d'erreurs techniques, justifications de fond.
- **Une limite matérielle = une ligne**, sans section ni paragraphe (« le passage en public se
  fait en un clic »). Ne pas empiler les avertissements.
- **Ne jamais répéter une information** : elle apparaît une fois, à l'endroit où elle sert.
- Écrire pour le destinataire : direction = bénéfice, sécurité, coût, décisions à prendre ;
  utilisateur outillé = quoi taper, quoi faire ensuite.
- Pas de section « état de validation » dans un document destiné à un tiers, sauf demande.

## Honnêteté

- Un mode opératoire s'écrit au ton affirmé — c'est une procédure — mais **jamais** en y
  affirmant qu'un test a eu lieu s'il n'a pas eu lieu. Signaler l'écart à l'utilisateur dans la
  conversation, pas dans le document.
- Les limites de politique d'un fournisseur (audit, vérification, quota réglementaire) peuvent
  rester : elles resteraient vraies après cent tests réussis.

## Pièges

- Rédiger avant d'avoir lu la page cible → registre et format décalés, réécriture complète.
- Publier sans relire la page → un bloc tronqué passe inaperçu.
- Vouloir modifier le contenu d'une page existante par `PATCH` : le schéma attendu n'est pas
  celui du markdown de création (détail et contournement dans la référence).
- Publier un document qui affirme des choses sur l'environnement (chemins, noms d'outils, étapes
  d'installation) sans les vérifier : un guide faux coûte plus cher qu'un guide absent.
