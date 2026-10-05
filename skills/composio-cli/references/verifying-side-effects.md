# Prouver : ou disculper : l'effet de bord d'un outil

Situation : l'utilisateur constate qu'un état change dans un de ses comptes connectés (« mes
mails s'ouvrent tout seuls », « je ne sais plus lesquels j'ai lus ») et soupçonne une
automatisation de l'agent. Le but n'est pas de rassurer mais de **mesurer**.

## Règle 0 : ne jamais conclure depuis le schéma de l'outil

Un outil sans paramètre « marquer comme lu » peut changer l'état côté fournisseur (déclencheur en
*poll* de la plateforme, effet de bord côté service, autre client du même compte). Le manifeste
d'un outil n'est pas une preuve d'innocence, et un seul test ne disculpe pas un compte entier.

## 1. Observer par un chemin neutre, autour d'un appel contrôlé

Choisir **un** objet témoin, lire son état par un appel de lecture qui ne partage pas le code de
l'outil testé (`composio proxy` en GET), lancer l'outil **une fois** (`composio execute`), puis
relire l'état. Avant/après sur un seul objet : c'est décisif et réparable.

Exemple Gmail, l'outil marque-t-il comme lu ?

```bash
export PATH="$HOME/.local/bin:$PATH"; C=composio
# 1. cible : un message non lu
$C proxy "https://gmail.googleapis.com/gmail/v1/users/me/messages?q=is:unread%20in:inbox&maxResults=3" --toolkit gmail
# 2. état AVANT : labelIds doit contenir UNREAD
$C proxy "https://gmail.googleapis.com/gmail/v1/users/me/messages/<ID>?format=minimal" --toolkit gmail
# 3. l'outil soupçonné, appelé tel que l'automatisation l'appelle
$C execute GMAIL_FETCH_EMAILS --account <alias> -d '{"query":"is:unread in:inbox","max_results":1,"verbose":true}'
# 4. état APRÈS
$C proxy "https://gmail.googleapis.com/gmail/v1/users/me/messages/<ID>?format=minimal" --toolkit gmail
```

`UNREAD` toujours là → l'outil est innocent **pour cet usage précis**. Disparu → il marque bien
comme lu.

Deux détails qui faussent la lecture du résultat :
- `composio execute` peut renvoyer la charge utile **dans un fichier** (`storedInFile` /
  `outputFilePath`) plutôt qu'en ligne, suivre le chemin avant de parser.
- `composio proxy` n'imprime rien sur une erreur (voir `../SKILL.md` §5) : un relevé vide n'est pas
  un état.

## 2. Lister ce qui est réellement appelé, avant d'accuser

```bash
grep -rhoI --exclude-dir=.hub --exclude-dir=cache --exclude-dir=node_modules \
  -E "GMAIL_[A-Z_]+" \
  /root/.hermes/profiles/*/cron /root/.hermes/profiles/*/workspace /root/.hermes/sessions \
  | sort | uniq -c | sort -rn
```

⚠️ Toujours exclure `.hub` et `cache` : `skills/.hub/index-cache/*.json` est un **JSON d'une seule
ligne de plusieurs dizaines de Mo** ; sans exclusion il noie la sortie (tronquée) et le signal
disparaît.

## 3. Écarter d'un coup les hypothèses de protocole

Un client IMAP/POP marque lu par conception ; un transfert automatique déplace. Une requête de
réglages suffit à trancher :

```bash
$C proxy "https://gmail.googleapis.com/gmail/v1/users/me/settings/imap" --toolkit gmail
$C proxy "https://gmail.googleapis.com/gmail/v1/users/me/settings/pop" --toolkit gmail
$C proxy "https://gmail.googleapis.com/gmail/v1/users/me/settings/autoForwarding" --toolkit gmail
```

## 4. Rendre un verdict borné

« L'outil X, tel qu'il est appelé, ne produit pas cet effet » est un verdict. « Le compte est
propre » n'en est pas un. Nommer ce qui est disculpé, ce qui est écarté (réglages), et ce qui
reste hors du périmètre de la mesure : déclencheurs de la plateforme, autres clients, autres
automatisations branchées sur le même compte, un scénario externe partageant le même projet OAuth
est un candidat courant.

- Déclencheurs : `composio triggers list <toolkit>` montre le **catalogue**. Chez Gmail les deux
  entrées (`GMAIL_NEW_GMAIL_MESSAGE`, `GMAIL_EMAIL_SENT_TRIGGER`) sont de `type: poll`, un
  déclencheur actif interroge donc la boîte en continu et reste un candidat à ne pas écarter.
  Les **instances actives** ne se listent pas avec la clé du compte (l'API de gestion renvoie
  `401 APIKey_InvalidAPIKey` sur une clé utilisateur, et `composio dev triggers status` exige un
  projet développeur, `composio dev init`) : renvoyer à la section Triggers du dashboard.
- Log d'accès du fournisseur, pour fermer la boucle : Gmail → « Dernière activité du compte » →
  Détails (type d'accès, IP, horodatage). Des accès API à des heures où rien de connu ne tourne
  désignent un autre client.

## 5. Proposer une action, pas une conviction

- **Réparer** ce qui est réparable : l'état se réécrit par l'API quand elle le permet
  (`POST /messages/{id}/modify` avec `addLabelIds: ["UNREAD"]`). Annoncer d'abord la liste des
  objets concernés et la faire valider avant d'écrire.
- **Prendre en flagrant délit** : journaliser l'état à intervalle régulier et l'horodatage de chaque
  bascule, puis croiser avec les heures connues des automatisations, on identifie par élimination
  au lieu de deviner.
- **Suspendre** l'automatisation soupçonnée une période, même disculpée : test à coût nul, qui
  tranche par l'absence.
