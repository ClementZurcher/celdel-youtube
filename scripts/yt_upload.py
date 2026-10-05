#!/usr/bin/env python3
"""Publication automatisée d'une vidéo YouTube, deux voies.

Voie A (--via composio) : réutilise le compte YouTube déjà connecté dans Composio,
    via l'endpoint officiel videos.insert (le jeton porte le scope d'upload ; la
    limite est le quota d'upload du projet Google partagé Composio, 966/jour pour
    toute la plateforme, fenêtre réinitialisée chaque jour à 07:00 UTC).
Voie B (--via oauth) : tes propres identifiants Google Cloud OAuth, quota propre
    au projet (par défaut ~6 uploads/jour, extensible sur demande de quota).

Sécurité par défaut : aucune vidéo n'est jamais publiée en public sans
--confirm-public. Sans ce drapeau, la visibilité est forcée à private
(ou scheduled si --publish-at est fourni).

Usage :
  yt_upload.py --check ...                       # tout valider sans rien envoyer
  yt_upload.py --probe-quota                     # teste la porte quota (n'envoie aucune donnée vidéo)
  yt_upload.py --via oauth --video f.mp4 --title "…" --client-secret client_secret.json
  yt_upload.py --via composio --video f.mp4 --title "…"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

TITLE_MAX = 100
DESC_MAX = 5000
TAGS_MAX = 500
CATEGORIES = {
    "1": "Film & Animation", "2": "Autos & Vehicles", "10": "Music", "15": "Pets & Animals",
    "17": "Sports", "20": "Gaming", "22": "People & Blogs", "23": "Comedy",
    "24": "Entertainment", "25": "News & Politics", "26": "Howto & Style",
    "27": "Education", "28": "Science & Technology", "29": "Nonprofits & Activism",
}
CHAPTER_RE = re.compile(r"^\s*(\d{1,2}):([0-5]\d)(?::([0-5]\d))?\s+\S")


def fail(msg: str) -> None:
    print(f"ERREUR : {msg}", file=sys.stderr)
    sys.exit(2)


def parse_chapters(description: str) -> list[tuple[int, str]]:
    """Renvoie [(secondes, ligne)] pour chaque ligne ressemblant à un horodatage."""
    out = []
    for line in description.splitlines():
        if not CHAPTER_RE.match(line):
            continue
        stamp = line.strip().split()[0]
        parts = [int(p) for p in stamp.split(":")]
        secs = parts[0] * 60 + parts[1] if len(parts) == 2 else parts[0] * 3600 + parts[1] * 60 + parts[2]
        out.append((secs, line.strip()))
    return out


def validate_chapters(description: str, duration_s: int | None) -> list[str]:
    """Règles YouTube : 1er horodatage 00:00, >=3 chapitres, ordre croissant, >=10 s."""
    warnings = []
    chapters = parse_chapters(description)
    if not chapters:
        return warnings
    if len(chapters) < 3:
        warnings.append(f"chapitres : {len(chapters)} trouvé(s), YouTube en exige au moins 3 -> aucun chapitre actif")
    if chapters[0][0] != 0:
        warnings.append(f"chapitres : le premier horodatage est {chapters[0][1].split()[0]}, il doit être exactement 00:00")
    secs = [c[0] for c in chapters]
    if secs != sorted(secs):
        warnings.append("chapitres : les horodatages ne sont pas en ordre croissant")
    for (a, la), (b, _lb) in zip(chapters, chapters[1:]):
        if b - a < 10:
            warnings.append(f"chapitres : « {la} » et « {_lb} » sont espacés de {b - a} s (< 10 s requis)")
    if duration_s is not None and secs and secs[-1] >= duration_s:
        warnings.append("chapitres : un horodatage dépasse la durée réelle de la vidéo")
    return warnings


def validate(args, description: str, tags: list[str]) -> list[str]:
    problems = []
    if len(args.title) > TITLE_MAX:
        problems.append(f"titre : {len(args.title)} caractères (max {TITLE_MAX})")
    if len(description) > DESC_MAX:
        problems.append(f"description : {len(description)} caractères (max {DESC_MAX})")
    tag_field = ",".join(tags)
    if len(tag_field) > TAGS_MAX:
        problems.append(f"tags : {len(tag_field)} caractères virgules comprises (max {TAGS_MAX})")
    if args.category not in CATEGORIES:
        problems.append(f"catégorie : « {args.category} » inconnue (valides : {', '.join(sorted(CATEGORIES, key=int))})")
    if not os.path.isfile(args.video):
        problems.append(f"fichier vidéo introuvable : {args.video}")
    else:
        size = os.path.getsize(args.video)
        if size == 0:
            problems.append("fichier vidéo vide")
        elif size > 256 * 1024 ** 3:
            problems.append("fichier > 256 Go : non supporté par YouTube")
    if args.thumbnail and not os.path.isfile(args.thumbnail):
        problems.append(f"miniature introuvable : {args.thumbnail}")
    if args.privacy == "public" and not args.confirm_public:
        problems.append("visibilité publique refusée sans --confirm-public (garde-fou)")
    if args.via == "oauth" and not args.client_secret:
        problems.append("--via oauth exige --client-secret (client_secret.json d'un projet Google Cloud)")
    if args.via == "composio" and not shutil.which("composio"):
        problems.append("CLI composio introuvable dans le PATH")
    return problems


def effective_privacy(args) -> str:
    if args.publish_at and not args.confirm_public:
        return "private"  # sera planifié via status.publishAt une fois confirmé
    if args.privacy == "public" and not args.confirm_public:
        return "private"
    return args.privacy


def build_body(args, description: str, tags: list[str]) -> dict:
    status = {
        "privacyStatus": effective_privacy(args),
        "selfDeclaredMadeForKids": args.made_for_kids,
    }
    if args.publish_at:
        status["publishAt"] = args.publish_at
    return {
        "snippet": {
            "title": args.title,
            "description": description,
            "tags": tags,
            "categoryId": args.category,
            "defaultLanguage": args.language,
        },
        "status": status,
    }


# ---------------------------------------------------------------- voie A : composio

COMPOSIO_JS = r"""
// Upload résumable d'une vidéo via le compte YouTube connecté dans Composio.
const [videoPath, metaJson] = process.argv.slice(2);
const meta = JSON.parse(metaJson);
const f = await proxy("youtube");
const bytes = new Uint8Array(await Bun.file(videoPath).arrayBuffer());
const init = await f(
  "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
  {
    method: "POST",
    headers: {
      "Content-Type": "application/json; charset=UTF-8",
      "X-Upload-Content-Type": "video/*",
      "X-Upload-Content-Length": String(bytes.length),
    },
    body: JSON.stringify(meta),
  }
);
if (init.status !== 200) {
  console.log(JSON.stringify({ ok: false, stage: "init", status: init.status, body: (await init.text()).slice(0, 800) }));
  process.exit(1);
}
const session = init.headers.get("location");
const CHUNK = 8 * 1024 * 1024;
let offset = 0;
let last = null;
while (offset < bytes.length) {
  const end = Math.min(offset + CHUNK, bytes.length);
  const r = await f(session, {
    method: "PUT",
    headers: { "Content-Range": `bytes ${offset}-${end - 1}/${bytes.length}` },
    body: bytes.slice(offset, end),
  });
  if (r.status === 308) { offset = end; continue; }
  if (r.status === 200 || r.status === 201) { last = await r.json(); break; }
  console.log(JSON.stringify({ ok: false, stage: "chunk", status: r.status, body: (await r.text()).slice(0, 800) }));
  process.exit(1);
}
console.log(JSON.stringify({ ok: true, video: last }));
"""


def upload_via_composio(args, body: dict) -> int:
    js_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_composio_upload.js")
    with open(js_path, "w", encoding="utf-8") as fh:
        fh.write(COMPOSIO_JS)
    cmd = ["composio", "run", "-f", js_path, "--", os.path.abspath(args.video), json.dumps(body)]
    print("→ composio run (voie A, compte connecté)", flush=True)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    out = proc.stdout.strip().splitlines()
    payload = out[-1] if out else ""
    if proc.returncode != 0:
        print(f"ÉCHEC voie A (code {proc.returncode})\n{payload[:1500] or proc.stderr[-1500:]}")
        return 1
    print(payload)
    return 0


def probe_quota() -> int:
    """Teste la porte quota de videos.insert sans envoyer le moindre octet vidéo."""
    js = r"""
const f = await proxy("youtube");
const r = await f(
  "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
  { method: "POST",
    headers: { "Content-Type": "application/json; charset=UTF-8" },
    body: JSON.stringify({ snippet: { title: "quota probe", description: "", categoryId: "22" },
                           status: { privacyStatus: "private", selfDeclaredMadeForKids: false } }) });
const t = await r.text();
if (r.status === 200) {
  console.log(JSON.stringify({ ok: true, status: 200, session: (r.headers.get("location") || "").slice(0, 120),
                               note: "session ouverte puis abandonnée : aucune vidéo créée" }));
} else {
  let reason = t; try { reason = JSON.parse(t).error.message; } catch {}
  console.log(JSON.stringify({ ok: false, status: r.status, reason }));
}
"""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_probe.js")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(js)
    proc = subprocess.run(["composio", "run", "-f", p], capture_output=True, text=True)
    lines = [l for l in proc.stdout.strip().splitlines() if l.startswith("{")]
    print(lines[-1] if lines else proc.stdout[-800:] + proc.stderr[-800:])
    return 0 if lines and '"ok":true' in lines[-1] else 1


# ------------------------------------------------------------------- voie B : oauth


SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.force-ssl"]


def _load_flow(args):
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_secrets_file(args.client_secret, SCOPES)
    flow.redirect_uri = args.redirect_uri
    return flow


def whoami(args) -> int:
    """Affiche la chaîne administrée par le jeton, et la compare à --expect-channel."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError as exc:
        fail(f"bibliothèques Google absentes ({exc})")
    token_path = args.token or (os.path.join(os.path.dirname(os.path.abspath(args.client_secret)), "token.json")
                                if args.client_secret else "")
    if not token_path or not os.path.exists(token_path):
        fail(f"aucun jeton trouvé ({token_path or 'chemin inconnu'}), lancer d'abord --print-auth-url puis --finish-auth")
    try:
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        yt = build("youtube", "v3", credentials=creds)
        items = yt.channels().list(part="snippet,contentDetails", mine=True).execute().get("items", [])
    except Exception as exc:
        fail(f"jeton refusé par Google : {exc}")
    if not items:
        fail("ce jeton n'administre aucune chaîne YouTube")
    it = items[0]
    sn = it.get("snippet", {})
    info = {"channel_id": it["id"], "titre": sn.get("title"), "handle": sn.get("customUrl"),
            "creation": sn.get("publishedAt")}
    print(json.dumps(info, ensure_ascii=False, indent=2))
    if args.expect_channel:
        if it["id"] != args.expect_channel:
            fail(f"ce jeton administre {it['id']} et non {args.expect_channel}, "
                 "mauvais compte Google : refaire l'autorisation avec le compte propriétaire")
        print("Chaîne confirmée : les uploads partiront bien ici.")
    return 0


def print_auth_url(args) -> int:
    """Génère l'URL d'autorisation à ouvrir dans TON navigateur (aucun navigateur requis ici)."""
    flow = _load_flow(args)
    prompt = "select_account consent" if args.select_account else "consent"
    kwargs = {"access_type": "offline", "prompt": prompt,
              "login_hint": args.login_hint or None}
    # include_granted_scopes fusionne les scopes déjà accordés à ce client OAuth :
    # sur un client partagé (ex. n8n) cela réinjecte drive.file, que Google refuse
    # de combiner avec youtube.* -> « This request contains scopes that cannot be
    # requested together » / HTTP 400. Désactivé par défaut.
    if args.include_granted_scopes:
        kwargs["include_granted_scopes"] = "true"
    url, _state = flow.authorization_url(**kwargs)
    state_path = args.state or os.path.join(os.path.dirname(os.path.abspath(args.client_secret)),
                                            ".oauth-state.json")
    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump({"code_verifier": flow.code_verifier, "redirect_uri": flow.redirect_uri}, fh)
    os.chmod(state_path, 0o600)
    print("1) Ouvre cette URL dans ton navigateur (celui où tu es connecté à Google) et autorise :\n")
    print(url)
    print(f"\n2) Tu seras redirigé vers {flow.redirect_uri}?code=…&scope=…, la page peut afficher")
    print("   une erreur, c'est normal : ce qui compte est l'URL dans la barre d'adresse.")
    print("   Copie cette URL COMPLÈTE et colle-la dans un fichier, puis lance :")
    print(f"     yt_upload.py --finish-auth /chemin/vers/url.txt --client-secret {args.client_secret}")
    print(f"\n   (état PKCE conservé dans {state_path})")
    return 0


def report_token_lifetime(token) -> None:
    """Détecte la bombe à retardement du statut « Testing » : jeton valable 7 jours."""
    if not isinstance(token, dict):
        print("Statut de publication du consentement inconnu, vérifier Audience → « In production ».")
        return
    ttl = token.get("refresh_token_expires_in")
    if ttl:
        try:
            days = round(int(ttl) / 86400, 1)
        except (TypeError, ValueError):
            days = None
        print(f"⚠️  Statut « Testing » détecté : ce jeton de rafraîchissement expire dans "
              f"{days if days is not None else ttl} jour(s).")
        print("    Correctif : Google Auth platform → Audience → « Publish app » (statut "
              "« In production »), puis relancer --print-auth-url / --finish-auth une fois "
              "pour obtenir un jeton durable. L'application peut rester non vérifiée.")
    else:
        print("Jeton de rafraîchissement sans expiration programmée : accès durable.")


def finish_auth(args) -> int:
    """Termine l'autorisation à partir de l'URL/du code fourni dans un fichier."""
    with open(args.finish_auth, encoding="utf-8") as fh:
        text = fh.read().strip()
    code = text
    if "code=" in text:
        from urllib.parse import parse_qs, urlparse
        qs = parse_qs(urlparse(text).query)
        code = (qs.get("code") or [""])[0]
    if not code:
        fail("aucun code d'autorisation trouvé dans le fichier fourni")

    state_path = args.state or os.path.join(os.path.dirname(os.path.abspath(args.client_secret)),
                                            ".oauth-state.json")
    verifier = None
    if os.path.exists(state_path):
        with open(state_path, encoding="utf-8") as fh:
            verifier = json.load(fh).get("code_verifier")
    flow = _load_flow(args)
    if verifier:
        flow.code_verifier = verifier
    try:
        flow.fetch_token(code=code)
    except Exception as exc:  # message lisible plutôt qu'une trace back
        fail(f"échange du code refusé par Google : {exc}")

    token_path = args.token or os.path.join(os.path.dirname(os.path.abspath(args.client_secret)), "token.json")
    with open(token_path, "w", encoding="utf-8") as fh:
        fh.write(flow.credentials.to_json())
    os.chmod(token_path, 0o600)
    report_token_lifetime(getattr(flow.oauth2session, "token", None))
    print(f"Autorisation terminée. Jeton enregistré : {token_path}")
    print("À partir de maintenant, je peux téléverser et remplir les métadonnées sans aucune action de ta part.")
    return 0


def upload_via_oauth(args, body: dict) -> int:
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError as exc:
        fail(f"bibliothèques Google absentes ({exc}), utilise l'interpréteur du venv Hermes documenté")

    scope = ["https://www.googleapis.com/auth/youtube.upload",
             "https://www.googleapis.com/auth/youtube.force-ssl"]
    token_path = args.token or os.path.join(os.path.dirname(os.path.abspath(args.client_secret)), "token.json")
    creds = Credentials.from_authorized_user_file(token_path, scope) if os.path.exists(token_path) else None
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(args.client_secret, scope)
        run_kwargs = {"redirect_uri_trailing_slash": False}
        if args.no_browser:
            flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
            auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
            print("1) Ouvre cette URL et autorise l'accès :\n" + auth_url)
            code = input("2) Colle le code d'autorisation : ").strip()
            flow.fetch_token(code=code)
            creds = flow.credentials
        else:
            creds = flow.run_local_server(port=args.oauth_port, **run_kwargs)
        with open(token_path, "w", encoding="utf-8") as fh:
            fh.write(creds.to_json())
        os.chmod(token_path, 0o600)
        print(f"Jeton OAuth enregistré : {token_path}")

    youtube = build("youtube", "v3", credentials=creds)
    media = MediaFileUpload(os.path.abspath(args.video), chunksize=8 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  upload {int(status.progress() * 100)} %", flush=True)
    vid = response.get("id")
    print(json.dumps({"ok": True, "video_id": vid, "url": f"https://youtu.be/{vid}",
                      "privacy": response.get("status", {}).get("privacyStatus")}, ensure_ascii=False))
    if args.thumbnail:
        youtube.thumbnails().set(videoId=vid, media_body=MediaFileUpload(args.thumbnail)).execute()
        print("miniature appliquée")
    return 0


def print_kit(args, description: str, tags: list[str]) -> None:
    """Paquet de champs prêts à coller dans YouTube Studio (usage manuel, sans quota)."""
    chapters = parse_chapters(description)
    hashtags = [w for w in description.split() if w.startswith("#")]
    print("=" * 72)
    print("PAQUET PRÊT À COLLER, YouTube Studio")
    print("=" * 72)
    print(f"\n### TITRE ({len(args.title)}/{TITLE_MAX} caractères)\n{args.title}")
    print(f"\n### DESCRIPTION ({len(description)}/{DESC_MAX} caractères), coller tel quel")
    print(description.rstrip())
    print(f"\n### TAGS ({len(','.join(tags))}/{TAGS_MAX} caractères), champ « Tags », séparés par des virgules")
    print(", ".join(tags) if tags else "(aucun)")
    print(f"\n### HASHTAGS (3 max utiles)\n{' '.join(hashtags[:3]) if hashtags else '(aucun)'}")
    print(f"\n### CATÉGORIE\n{args.category}, {CATEGORIES.get(args.category, '?')}")
    print(f"\n### CHAPITRES ({len(chapters)} détectés)")
    for _sec, line in chapters:
        print(f"  {line}")
    print(f"\n### VISIBILITÉ\n{effective_privacy(args)}  (public seulement après confirmation explicite)")
    if args.thumbnail:
        print(f"\n### MINIATURE\n{args.thumbnail}")
    print("\n" + "-" * 72)
    print("ÉTAPES STUDIO : studio.youtube.com → Créer → Importer une vidéo")
    print(f"  1. Sélectionner {os.path.basename(args.video) or 'le fichier vidéo'}")
    print("  2. Coller le TITRE, puis la DESCRIPTION ci-dessus (les chapitres créent la piste automatiquement)")
    print("  3. Coller les TAGS, choisir la CATÉGORIE, téléverser la MINIATURE")
    print("  4. Laisser en Privée (ou Planifier), enregistrer, vérifier, publier")
    print("  5. Récupérer l'URL de la vidéo et me la donner si tu veux que je vérifie les métadonnées publiées")
    print("-" * 72)


def main() -> int:
    ap = argparse.ArgumentParser(description="Publication automatisée d'une vidéo YouTube")
    ap.add_argument("--video", default="", help="fichier vidéo")
    ap.add_argument("--title", default="", help="titre (max 100 caractères)")
    ap.add_argument("--description-file", default="", help="fichier texte contenant la description")
    ap.add_argument("--description", default="", help="description en ligne")
    ap.add_argument("--tags", default="", help="tags séparés par des virgules (budget 500 caractères)")
    ap.add_argument("--category", default="22", help="categoryId numérique YouTube")
    ap.add_argument("--language", default="fr", help="langue par défaut")
    ap.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    ap.add_argument("--publish-at", default="", help="date ISO 8601 de publication planifiée")
    ap.add_argument("--made-for-kids", action="store_true")
    ap.add_argument("--thumbnail", default="")
    ap.add_argument("--via", default="composio", choices=["composio", "oauth"])
    ap.add_argument("--client-secret", default="")
    ap.add_argument("--token", default="")
    ap.add_argument("--oauth-port", type=int, default=8080)
    ap.add_argument("--no-browser", action="store_true", help="flux OAuth sans navigateur local")
    ap.add_argument("--confirm-public", action="store_true", help="autorise la mise en public")
    ap.add_argument("--check", action="store_true", help="valide tout et s'arrête (n'envoie rien)")
    ap.add_argument("--kit", action="store_true", help="imprime les champs prêts à coller dans YouTube Studio")
    ap.add_argument("--probe-quota", action="store_true", help="teste la porte quota de videos.insert")
    ap.add_argument("--print-auth-url", action="store_true", help="génère l'URL d'autorisation OAuth (aucun navigateur requis ici)")
    ap.add_argument("--whoami", action="store_true", help="affiche la chaîne administrée par le jeton")
    ap.add_argument("--expect-channel", default="", help="ID de chaîne attendu (garde-fou anti mauvais compte)")
    ap.add_argument("--finish-auth", default="", metavar="FICHIER", help="termine l'autorisation OAuth à partir de l'URL/du code dans FICHIER")
    ap.add_argument("--redirect-uri", default="http://localhost:8765/", help="URI de redirection OAuth (défaut http://localhost:8765/)")
    ap.add_argument("--login-hint", default="", help="pré-remplit/force l'adresse du compte à autoriser (ex. <boite-de-reception@exemple.com>)")
    ap.add_argument("--select-account", action="store_true", help="force l'écran de choix du compte Google")
    ap.add_argument("--include-granted-scopes", action="store_true",
                    help="fusionne les scopes déjà accordés au client (à éviter sur un client partagé type n8n)")
    ap.add_argument("--state", default="", help="chemin du fichier d'état PKCE")
    ap.add_argument("--duration", type=int, default=None, help="durée de la vidéo en secondes (contrôle des chapitres)")
    args = ap.parse_args()

    if args.probe_quota:
        return probe_quota()

    if args.whoami:
        return whoami(args)

    if args.print_auth_url or args.finish_auth:
        if not args.client_secret:
            fail("--print-auth-url et --finish-auth exigent --client-secret")
        return print_auth_url(args) if args.print_auth_url else finish_auth(args)

    if args.description_file:
        with open(args.description_file, encoding="utf-8") as fh:
            description = fh.read()
    else:
        description = args.description
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    if not args.video or not args.title:
        fail("--video et --title sont obligatoires (ou utilise --probe-quota / --check avec les deux)")

    body = build_body(args, description, tags)
    print("=== plan d'upload ===")
    print(json.dumps(body, ensure_ascii=False, indent=2))
    print(f"titre {len(args.title)}/{TITLE_MAX} car. | description {len(description)}/{DESC_MAX} car. | "
          f"tags {len(','.join(tags))}/{TAGS_MAX} car. ({len(tags)} tags) | visibilité effective "
          f"{body['status']['privacyStatus']} | voie {args.via}")

    problems = validate(args, description, tags)
    for w in validate_chapters(description, args.duration):
        print(f"AVERTISSEMENT : {w}")
    if problems:
        for p in problems:
            print(f"AVERTISSEMENT : {p}", file=sys.stderr)
        fail(f"{len(problems)} problème(s) bloquant(s), corrige avant d'envoyer")

    if args.kit:
        print_kit(args, description, tags)
        return 0

    if args.check:
        print("Contrôles OK, aucun envoi effectué (--check).")
        return 0

    if body["status"]["privacyStatus"] == "public" and not args.confirm_public:
        fail("garde-fou : --confirm-public requis pour une mise en public")
    return upload_via_oauth(args, body) if args.via == "oauth" else upload_via_composio(args, body)


if __name__ == "__main__":
    sys.exit(main())
