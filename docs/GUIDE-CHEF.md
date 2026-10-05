# Publier sur YouTube avec l'assistant IA — note de présentation

Document destiné à la direction. Objectif : expliquer ce que l'outil fait, ce qu'il
demande, ce qu'il coûte, et ce qu'il reste à valider. Aucune connaissance technique requise.

---

## 1. En une phrase

L'assistant prépare **et** met en ligne les vidéos YouTube de l'entreprise à partir d'un
simple fichier vidéo : il rédige le titre, la description, les chapitres, les tags et la
miniature, puis téléverse la vidéo et remplit lui-même tous les champs de la chaîne.

---

## 2. Ce que ça change concrètement

| Étape | Aujourd'hui | Avec l'assistant |
|---|---|---|
| Rédiger le titre, la description, les chapitres, les tags | 30 à 60 min de travail manuel | quelques minutes, relues en un coup d'œil |
| Téléverser et remplir les champs dans YouTube Studio | 15 à 30 min de manipulation | automatique |
| Vérifier les métadonnées publiées | manuel | vérification automatique + lien fourni |

**Bénéfice principal** : plus de recopie manuelle ni d'oubli de champs, et une qualité de
métadonnées homogène d'une vidéo à l'autre.

---

## 3. Ce qu'il faut mettre en place (une seule fois)

| Élément | Qui | Durée |
|---|---|---|
| Autoriser l'accès à la chaîne depuis un compte Google technique | La personne qui administre le compte Google de l'entreprise | ~10 min |
| Installer l'outil et le script sur un poste | Profil technique | ~10 min |
| Valider par une vidéo de test, en privé | Direction + technique | ~15 min |

Coût de fonctionnement : **0 €** (l'API YouTube est gratuite, dans la limite de 100
téléversements par jour — très au-delà de notre rythme).

---

## 4. Sécurité et contrôle — les points qui rassurent

1. **Rien ne part en public sans validation humaine.** La vidéo est téléversée en
   **privé** par défaut ; la mise en public est un feu vert explicite.
2. **Aucun mot de passe n'est transmis à l'assistant.** L'autorisation se fait une fois,
   par une personne, dans son propre navigateur. L'assistant ne voit jamais le mot de passe.
3. **La clé d'accès reste sur notre machine**, chiffrée, et peut être révoquée à tout moment
   depuis le compte Google (une page, un bouton).
4. **Un contrôle automatique vérifie qu'on publie sur la bonne chaîne** avant tout envoi ;
   en cas de doute, l'opération s'arrête.
5. Aucune donnée n'est envoyée à un service tiers : l'outil parle directement à l'API
   officielle de Google.

---

## 5. Périmètre et limites (transparence)

- **Ce qui est déjà validé** : préparation et contrôle des métadonnées, lecture des
  statistiques de la chaîne, mécanique d'autorisation.
- **Ce qui reste à valider** : le **premier téléversement réel**, qui sert de test de bout
  en bout. C'est une étape de recette normale, pas un doute sur la faisabilité.
- **Limite connue de Google** : pour publier **en public** via l'API, Google exige une
  procédure d'audit du projet technique. Sans cet audit, le téléversement et le remplissage
  sont automatiques, mais **la bascule en public reste un clic** dans YouTube Studio.
- Une automatisation par navigateur (sans clé API) a été écartée : Google bloque les
  connexions depuis un navigateur piloté automatiquement.

---

## 6. Décisions demandées

| # | Décision | Options |
|---|---|---|
| 1 | Sur quel compte Google technique rattacher l'accès | compte existant dédié / nouveau compte technique |
| 2 | Autoriser l'accès API à la chaîne depuis le poste de travail | oui / non |
| 3 | Engager ou non la procédure d'audit Google | plus tard (recommandé) / maintenant |

Recommandation : lancer le test de bout en bout sur une vidéo courte, en privé, puis décider
de l'audit en fonction de l'usage réel.

---

## 7. Annexe technique (pour la personne qui installe)

```bash
# 1. skills à copier
cp -r pack/skills/youtube-* ~/.hermes/profiles/<profil>/skills/media/

# 2. autorisation (une fois)
python yt_upload.py --print-auth-url --client-secret client_secret.json \
  --redirect-uri "http://localhost" --login-hint <adresse> --select-account
python yt_upload.py --finish-auth url.txt --client-secret client_secret.json
python yt_upload.py --whoami --expect-channel <ID_DE_LA_CHAINE>

# 3. publication
python yt_upload.py --via oauth --video video.mp4 --title "…" --description-file desc.txt
```

Détails complets, erreurs connues et correctifs : `GUIDE-RAPIDE.md`.
