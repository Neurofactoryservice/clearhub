#!/usr/bin/env python3
"""BoosBrand — Flask Server (NeuroFactory v9)
Auth JWT · Stripe · Trial · Webhooks · Contact · API complète
"""
import os, sqlite3, hashlib, secrets, json, smtplib
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from flask import Flask, request, jsonify, send_file, redirect, make_response, send_from_directory
try:
    import jwt; JWT_OK=True
except ImportError:
    JWT_OK=False
import stripe
from db import init_db, get_db
from mailer import send_welcome_email, send_payment_confirmation
import webhook as wh

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))
stripe.api_key     = os.getenv("STRIPE_API_KEY", "")
PRICE_ID           = os.getenv("STRIPE_PRICE_ID", "")
WEBHOOK_SECRET     = os.getenv("STRIPE_WEBHOOK_SECRET", "")
JWT_SECRET         = os.getenv("JWT_SECRET", secrets.token_hex(32))
BASE_URL           = os.getenv("BASE_URL", "http://localhost:5000")
SITE_NAME          = "BoosBrand"
SITE_SLUG          = "boosbrand"
LANG               = "fr"
SITE_TYPE          = "saas"
PUB_REINVEST_RATE  = 0.15
PUB_STOP_REVENUE   = 10000.0
PUB_MIN_BUDGET     = 5.0
PUB_MAX_BUDGET     = 1500.0
SECTOR             = "marketing"
SITE_NAME           = "BoosBrand"
STRIPE_CONNECT_ACCOUNT_ID = "acct_1TGYG12VTjUdAXll"
CHAT_SYSTEM_PROMPT  = """Tu es l'assistant IA de BoosBrand, une plateforme Emailing & Automation.

INFORMATIONS DU SITE :
- Nom : BoosBrand
- Concept : Emailing & Automation
- Description : Campagnes email personnalisées avec automatisations.
- Secteur : marketing
- Type : SaaS
- Tarification : 19.99€/mois (Plan Pro)
- Essai : 7 jours d'essai gratuit

FONCTIONNALITÉS GRATUITES :
- 500 emails/mois
- 1 séquence
- Templates basiques

FONCTIONNALITÉS PRO :
- Emails illimités
- Séquences avancées
- A/B testing
- Analytics

TES RÈGLES :
1. Réponds UNIQUEMENT en français, de façon concise et utile (max 3-4 phrases)
2. Si tu ne connais pas la réponse exacte, oriente vers la page contact ou le support
3. Pour les questions techniques ou bugs, propose les étapes de dépannage de base
4. Pour les questions de facturation/remboursement, demande de contacter le support
5. Sois chaleureux, professionnel et bienveillant
6. N'invente jamais d'informations que tu ne connais pas
7. Si on te demande ta nature, dis que tu es l'assistant IA de BoosBrand
8. Pour les problèmes urgents : "Contactez-nous sur la page Contact pour un support prioritaire"

PAGE CONTACT : /contact
PAGE TARIFS : /pricing
PAGE FONCTIONNALITÉS : /features"""
CHAT_DEFAULT_REPLY  = 'Merci pour votre question ! Pour une réponse précise, je vous invite à consulter notre page /contact ou à parcourir /features et /pricing. Notre équipe est là pour vous aider.'
CHAT_PRICE_REPLY    = 'Le plan Pro est à 19.99€/mois. Essai gratuit 7 jours sans carte bancaire. Tous les détails sur /pricing.'
CHAT_BUG_REPLY      = 'Désolé pour ce problème ! Essayez : 1) Vider le cache de votre navigateur, 2) Vous déconnecter et reconnecter, 3) Utiliser un autre navigateur. Si le problème persiste, contactez-nous sur /contact.'
CHAT_CANCEL_REPLY   = 'Vous pouvez annuler votre abonnement à tout moment depuis votre espace client (/espace-client), rubrique Facturation. Aucune pénalité.'
CHAT_REFUND_REPLY   = 'Pour toute demande de remboursement, contactez notre équipe depuis la page /contact. Nous traitons les demandes sous 48h.'
CHAT_CONTACT_REPLY  = 'Notre équipe est disponible via la page /contact. Nous répondons généralement sous 24h ouvrées.'
CHAT_TRIAL_REPLY    = "Oui ! Nous offrons 7 jours d'essai gratuit sans carte bancaire. Commencez sur /login."
CHAT_FALLBACK_RESPONSES = {}
SITE_NAME           = "BoosBrand"
STRIPE_CONNECT_ACCOUNT_ID = "acct_1TGYG12VTjUdAXll"
CROSS_PROMO_AFFINITY= {'finance': {'similar': ['personal-finance', 'analytics'], 'complementary': ['crm', 'ecommerce', 'legal', 'hr']}, 'personal-finance': {'similar': ['finance', 'analytics'], 'complementary': ['legal', 'wellness', 'lifestyle']}, 'productivity': {'similar': ['crm', 'hr', 'analytics'], 'complementary': ['finance', 'marketing', 'support']}, 'crm': {'similar': ['productivity', 'marketing', 'support'], 'complementary': ['finance', 'ecommerce', 'analytics']}, 'hr': {'similar': ['productivity', 'crm'], 'complementary': ['finance', 'legal', 'education']}, 'analytics': {'similar': ['marketing', 'crm', 'social-analytics'], 'complementary': ['finance', 'ecommerce', 'support']}, 'marketing': {'similar': ['social-management', 'social-content', 'social-analytics'], 'complementary': ['crm', 'ecommerce', 'analytics', 'ai']}, 'social-management': {'similar': ['marketing', 'social-content', 'social-calendar'], 'complementary': ['social-analytics', 'social-hashtags', 'social-influencer']}, 'social-content': {'similar': ['social-management', 'social-video', 'marketing'], 'complementary': ['social-analytics', 'social-hashtags', 'ai']}, 'social-calendar': {'similar': ['social-management', 'social-content'], 'complementary': ['marketing', 'analytics', 'social-analytics']}, 'social-analytics': {'similar': ['analytics', 'social-management', 'social-competitive'], 'complementary': ['marketing', 'social-content', 'crm']}, 'social-hashtags': {'similar': ['social-content', 'social-management'], 'complementary': ['social-analytics', 'marketing']}, 'social-influencer': {'similar': ['social-management', 'marketing'], 'complementary': ['social-content', 'social-analytics', 'ecommerce']}, 'social-video': {'similar': ['social-content', 'social-management'], 'complementary': ['marketing', 'social-analytics']}, 'social-competitive': {'similar': ['analytics', 'social-analytics'], 'complementary': ['marketing', 'crm', 'social-management']}, 'social-monitoring': {'similar': ['social-analytics', 'social-competitive'], 'complementary': ['crm', 'support', 'marketing']}, 'social-linkinbio': {'similar': ['social-management', 'social-content'], 'complementary': ['marketing', 'ecommerce']}, 'social-community': {'similar': ['social-management', 'support'], 'complementary': ['crm', 'marketing']}, 'ecommerce': {'similar': ['marketing', 'crm'], 'complementary': ['finance', 'analytics', 'support', 'rental-fashion']}, 'support': {'similar': ['crm', 'productivity'], 'complementary': ['ecommerce', 'marketing', 'analytics']}, 'health': {'similar': ['wellness', 'p2p-caregiving'], 'complementary': ['lifestyle', 'booking', 'p2p-childcare']}, 'wellness': {'similar': ['health', 'lifestyle'], 'complementary': ['p2p-caregiving', 'booking', 'education']}, 'lifestyle': {'similar': ['wellness', 'health'], 'complementary': ['personal-finance', 'booking', 'ecommerce']}, 'education': {'similar': ['p2p-tutoring', 'ai'], 'complementary': ['productivity', 'hr', 'booking']}, 'real-estate': {'similar': ['rental-vacation', 'rental-workspace'], 'complementary': ['finance', 'legal', 'booking']}, 'ai': {'similar': ['marketing', 'analytics', 'productivity'], 'complementary': ['crm', 'support', 'education', 'social-content']}, 'security': {'similar': ['ai', 'analytics'], 'complementary': ['crm', 'productivity', 'hr']}, 'legal': {'similar': ['finance', 'hr'], 'complementary': ['crm', 'ecommerce', 'real-estate']}, 'booking': {'similar': ['p2p-handyman', 'p2p-cleaning', 'p2p-caregiving'], 'complementary': ['crm', 'marketing', 'rental-workspace']}, 'p2p-pets': {'similar': ['p2p-caregiving', 'p2p-childcare'], 'complementary': ['p2p-handyman', 'p2p-gardening', 'booking']}, 'p2p-handyman': {'similar': ['p2p-cleaning', 'p2p-tools', 'p2p-gardening'], 'complementary': ['p2p-delivery', 'rental-trucks', 'booking']}, 'p2p-tutoring': {'similar': ['education', 'p2p-caregiving'], 'complementary': ['p2p-childcare', 'wellness', 'booking']}, 'p2p-cleaning': {'similar': ['p2p-handyman', 'p2p-gardening'], 'complementary': ['p2p-tools', 'booking', 'rental-workspace']}, 'p2p-gardening': {'similar': ['p2p-handyman', 'p2p-cleaning'], 'complementary': ['p2p-tools', 'rental-trucks']}, 'p2p-delivery': {'similar': ['p2p-rideshare', 'p2p-carpool'], 'complementary': ['ecommerce', 'p2p-handyman']}, 'p2p-caregiving': {'similar': ['p2p-childcare', 'health'], 'complementary': ['p2p-cleaning', 'wellness', 'booking']}, 'p2p-childcare': {'similar': ['p2p-caregiving', 'p2p-tutoring'], 'complementary': ['p2p-pets', 'wellness', 'education']}, 'p2p-techsupport': {'similar': ['ai', 'security'], 'complementary': ['productivity', 'crm', 'support']}, 'p2p-tools': {'similar': ['p2p-handyman', 'rental-trucks'], 'complementary': ['p2p-gardening', 'p2p-cleaning']}, 'p2p-rideshare': {'similar': ['p2p-delivery', 'p2p-carpool', 'rental-vehicles'], 'complementary': ['p2p-handyman', 'booking']}, 'p2p-carpool': {'similar': ['p2p-rideshare', 'rental-vehicles'], 'complementary': ['p2p-delivery', 'lifestyle']}, 'p2p-barter': {'similar': ['p2p-tools', 'ecommerce'], 'complementary': ['p2p-handyman', 'lifestyle']}, 'rental-vehicles': {'similar': ['p2p-rideshare', 'p2p-carpool'], 'complementary': ['rental-trucks', 'p2p-delivery', 'booking']}, 'rental-vacation': {'similar': ['real-estate', 'rental-workspace'], 'complementary': ['rental-events', 'rental-vehicles', 'booking']}, 'rental-workspace': {'similar': ['rental-vacation', 'booking'], 'complementary': ['productivity', 'crm', 'real-estate']}, 'rental-events': {'similar': ['rental-venues', 'booking'], 'complementary': ['rental-fashion', 'rental-photo', 'p2p-handyman']}, 'rental-venues': {'similar': ['rental-events', 'rental-workspace'], 'complementary': ['booking', 'rental-fashion', 'ecommerce']}, 'rental-fashion': {'similar': ['ecommerce', 'lifestyle'], 'complementary': ['rental-events', 'social-influencer']}, 'rental-sports': {'similar': ['health', 'wellness'], 'complementary': ['rental-vacation', 'booking', 'p2p-carpool']}, 'rental-trucks': {'similar': ['p2p-tools', 'p2p-handyman'], 'complementary': ['p2p-delivery', 'rental-vehicles']}, 'rental-photo': {'similar': ['social-content', 'social-video'], 'complementary': ['rental-events', 'marketing']}, 'rental-boats': {'similar': ['rental-vacation', 'rental-sports'], 'complementary': ['rental-vehicles', 'booking', 'lifestyle']}}
UPSELL_PRICE        = 9.99
PRICE               = 19.99
UPSELL_PRICE_ID     = ""  # À renseigner: Price ID Stripe 9.99€ (stripe.env)
CROSS_SELL_GROUP    = "reseaux_sociaux_marketing"
CROSS_SELL_SAME_SECTORS = ['social-management', 'social-content', 'social-calendar', 'social-analytics', 'social-hashtags', 'social-influencer', 'social-video', 'social-competitive', 'social-monitoring', 'social-linkinbio', 'social-community', 'social-podcast', 'social-live', 'mkt-affiliate', 'mkt-referral', 'mkt-landing', 'mkt-ab', 'mkt-push', 'mkt-chat', 'marketing']
PRICE_AMOUNT       = 19.99
CURRENCY           = "eur"
TRIAL_DAYS         = 7
DESCRIPTION        = "Campagnes email personnalisées avec automatisations."
TAGLINE            = "La solution emailing & automation qui change tout"

init_db()

# ── Helpers ──────────────────────────────────────────────────
def hash_pw(p):
    s=secrets.token_hex(16); h=hashlib.sha256((s+p).encode()).hexdigest()
    return f"{s}:{h}"

def check_pw(p,stored):
    try:
        s,h=stored.split(":")
        return hashlib.sha256((s+p).encode()).hexdigest()==h
    except: return False

def make_token(uid,email):
    payload={"user_id":uid,"email":email,"exp":(datetime.now(timezone.utc)+timedelta(days=30)).timestamp()}
    if JWT_OK: return jwt.encode(payload,JWT_SECRET,algorithm="HS256")
    import base64; return base64.b64encode(json.dumps(payload).encode()).decode()

def decode_token(t):
    try:
        if JWT_OK: return jwt.decode(t,JWT_SECRET,algorithms=["HS256"])
        import base64; return json.loads(base64.b64decode(t).decode())
    except: return None

def get_token():
    t=request.headers.get("Authorization","").replace("Bearer ","")
    return t or request.cookies.get("token","")

def require_auth(f):
    @wraps(f)
    def d(*a,**kw):
        p=decode_token(get_token())
        if not p: return jsonify({"error":"Unauthorized"}),401
        request.user=p; return f(*a,**kw)
    d.__name__=f.__name__; return d

def require_active(f):
    @wraps(f)
    def d(*a,**kw):
        p=decode_token(get_token())
        if not p: return redirect("/login?next=/app")
        db=get_db()
        u=db.execute("SELECT * FROM users WHERE id=?",(p["user_id"],)).fetchone()
        if not u or u["subscription_status"] not in ("active","trialing"):
            return redirect("/pricing?reason=inactive")
        request.user=p; return f(*a,**kw)
    d.__name__=f.__name__; return d

def send_file_safe(filename, fallback=None):
    """Sert un fichier HTML avec gestion d'erreur propre."""
    # Résoudre le chemin par rapport au dossier du script (robuste sur Render)
    base = Path(__file__).parent
    p = base / filename
    if p.exists() and p.is_file(): return send_from_directory(str(base), filename)
    if fallback:
        pf = base / fallback
        if pf.exists(): return send_from_directory(str(base), fallback)
    return ("Page introuvable", 404)

# ── Pages statiques ──────────────────────────────────────────
@app.route("/")
def index(): return send_file_safe("index.html")

@app.route("/login")
def login_page():
    # Rediriger vers /app si déjà connecté
    p=decode_token(get_token())
    if p:
        db=get_db(); u=db.execute("SELECT subscription_status FROM users WHERE id=?",(p["user_id"],)).fetchone()
        if u and u["subscription_status"] in ("active","trialing"): return redirect("/app")
    return send_file_safe("login.html")

@app.route("/register")
@app.route("/signup")
def register_page(): return send_file_safe("login.html")

@app.route("/app")
@require_active
def dashboard(): return send_file_safe("app.html")

@app.route("/app/settings")
@require_active
def app_settings(): return send_file_safe("app.html")

@app.route("/espace-client")
def espace_client_page(): return send_file_safe("espace-client.html")

@app.route("/partenaires")
def partenaires_page(): return send_file_safe("partenaires.html")

# ── Stripe Connect ──────────────────────────────────────────
@app.route("/stripe/connect/return")
def stripe_connect_return():
    """Callback après onboarding Stripe Connect Express.
    Vérifie immédiatement le statut via l'API Stripe et met à jour meta.json.
    """
    import stripe as _s, json as _j
    _s.api_key = STRIPE_API_KEY
    acct_id = os.getenv("STRIPE_CONNECT_ACCOUNT_ID", "")
    status_html = ""
    ready = False
    if acct_id:
        try:
            acct = _s.Account.retrieve(acct_id)
            charges = acct.charges_enabled
            details = acct.details_submitted
            payouts = acct.payouts_enabled
            ready   = charges and details
            reqs    = list(acct.requirements.currently_due or [])
            # Mettre à jour meta.json immédiatement
            meta_path = os.path.join(os.path.dirname(__file__), "meta.json")
            try:
                meta = _j.loads(open(meta_path).read()) if os.path.exists(meta_path) else {}
                meta["stripe_connect_ready"]      = ready
                meta["stripe_connect_status"]     = "active" if ready else "pending"
                meta["stripe_connect_checked_at"] = __import__("datetime").datetime.utcnow().isoformat()
                meta["stripe_connect_charges"]    = charges
                meta["stripe_connect_payouts"]    = payouts
                meta["stripe_connect_reqs"]       = reqs[:10]
                open(meta_path, "w").write(_j.dumps(meta, ensure_ascii=False, indent=2))
            except Exception: pass
            if ready:
                status_html = "<p style='color:#34d399'>✅ Paiements et virements activés.</p>"
            elif reqs:
                items = "".join(f"<li>{r}</li>" for r in reqs[:5])
                status_html = f"<p style='color:#fbbf24'>⏳ En attente. Éléments manquants :<ul>{items}</ul></p>"
            else:
                status_html = "<p style='color:#fbbf24'>⏳ En cours de vérification par Stripe.</p>"
        except Exception as e:
            status_html = f"<p style='color:#f87171'>⚠️ Impossible de vérifier : {str(e)[:100]}</p>"
    icon  = "✅" if ready else "⏳"
    title = "Connect configuré !" if ready else "Onboarding en cours"
    return f'''<!DOCTYPE html><html><head><meta charset="utf-8">
    <title>Stripe Connect</title>
    <style>body{{font-family:sans-serif;background:#0a0a12;color:#f1f5f9;
    display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}
    .box{{text-align:center;padding:40px;max-width:420px}}
    a{{color:#6366f1;text-decoration:none}}</style></head>
    <body><div class="box">
    <div style="font-size:3rem">{icon}</div>
    <h2>{title}</h2>
    {status_html}
    <p><a href="/">← Retour au site</a></p>
    </div></body></html>'''

@app.route("/stripe/connect/refresh")
def stripe_connect_refresh():
    """Lien d'onboarding expiré — génère automatiquement un nouveau lien."""
    import stripe as _s
    _s.api_key = STRIPE_API_KEY
    acct_id = os.getenv("STRIPE_CONNECT_ACCOUNT_ID", "")
    base = request.host_url.rstrip("/")
    if acct_id:
        try:
            link = _s.AccountLink.create(
                account=acct_id,
                refresh_url=f"{base}/stripe/connect/refresh",
                return_url=f"{base}/stripe/connect/return",
                type="account_onboarding",
                collect="currently_due",
            )
            return redirect(link.url)
        except Exception as e:
            return f'<html><body style="font-family:sans-serif;background:#0a0a12;color:#f1f5f9;text-align:center;padding:80px"><h2>⚠️ Lien expiré</h2><p>{str(e)[:200]}</p><a href="/" style="color:#6366f1">← Retour</a></body></html>'
    return redirect("/?connect_error=expired")

@app.route("/api/connect/status")
@require_auth
def connect_status_api():
    """Retourne le statut du compte Stripe Connect Express — toujours depuis l'API Stripe."""
    import stripe as _s
    _s.api_key = STRIPE_API_KEY
    acct_id = os.getenv("STRIPE_CONNECT_ACCOUNT_ID", "")
    if not acct_id:
        return jsonify({"connected": False, "status": "not_created",
                        "message": "Compte Connect non créé"})
    if acct_id.startswith("acct_mock"):
        return jsonify({"connected": False, "status": "mock",
                        "message": "Mode simulation — clé Stripe live requise"})
    try:
        acct   = _s.Account.retrieve(acct_id)
        charges = acct.charges_enabled
        details = acct.details_submitted
        payouts = acct.payouts_enabled
        reqs    = acct.requirements or {}
        c_due   = list(reqs.currently_due  or [])
        p_due   = list(reqs.past_due        or [])
        errors  = [{"req": e.requirement, "reason": e.reason}
                   for e in (reqs.errors or [])]
        ready   = charges and details
        status  = "active" if ready else ("restricted" if details else "pending")
        # Mettre à jour meta.json
        import json as _j
        meta_path = os.path.join(os.path.dirname(__file__), "meta.json")
        try:
            meta = _j.loads(open(meta_path).read()) if os.path.exists(meta_path) else {}
            meta["stripe_connect_ready"]  = ready
            meta["stripe_connect_status"] = status
            meta["stripe_connect_reqs"]   = c_due[:10]
            open(meta_path, "w").write(_j.dumps(meta, ensure_ascii=False, indent=2))
        except Exception: pass
        return jsonify({
            "connected":        ready,
            "account_id":       acct_id,
            "charges_enabled":  charges,
            "details_submitted":details,
            "payouts_enabled":  payouts,
            "currently_due":    c_due,
            "past_due":         p_due,
            "errors":           errors,
            "disabled_reason":  reqs.disabled_reason or "",
            "status":           status,
            "message":          ("✅ Actif" if ready else
                                 f"⏳ Manquants : {c_due[0]}" if c_due else
                                 f"❌ {errors[0]['reason']}" if errors else
                                 f"⏳ {status}"),
        })
    except Exception as e:
        return jsonify({"connected": False, "error": str(e)}), 400


@app.route("/api/connect/onboard")
@require_auth
def connect_onboard_api():
    """Génère/renouvelle le lien d'onboarding Stripe Connect."""
    import stripe as _s; _s.api_key = STRIPE_API_KEY
    acct_id = os.getenv("STRIPE_CONNECT_ACCOUNT_ID", "")
    base = request.host_url.rstrip("/")
    if not acct_id:
        return jsonify({"error": "Compte Connect non configuré"}), 400
    try:
        link = _s.AccountLink.create(
            account=acct_id,
            refresh_url=f"{base}/stripe/connect/refresh",
            return_url=f"{base}/stripe/connect/return",
            type="account_onboarding",
            collect="currently_due",
        )
        return jsonify({"url": link.url, "expires_at": link.expires_at})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ── Chat IA Assistant ───────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
def chat_api():
    """Assistant IA client — répond aux questions avec contexte du site."""
    import json as _j, os as _os
    body = request.get_json(force=True) or {}
    message = str(body.get("message","")).strip()[:1000]
    history = body.get("history", [])[-8:]  # 4 échanges
    lang    = body.get("lang", LANG)
    if not message:
        return jsonify({"reply": ""}), 400

    system = CHAT_SYSTEM_PROMPT
    messages = [{"role":"system","content":system}] + history + [{"role":"user","content":message}]

    # Cascade IA : Groq → OpenRouter → Pollinations → fallback local
    reply = None
    providers = [("groq",_os.environ.get("GROQ_API_KEY",""),
                  "https://api.groq.com/openai/v1/chat/completions",
                  "llama-3.1-8b-instant"),
                 ("openrouter",_os.environ.get("OPENROUTER_API_KEY",""),
                  "https://openrouter.ai/api/v1/chat/completions",
                  "meta-llama/llama-3.2-3b-instruct:free")]
    import urllib.request, json as _jj
    for prov, key, url, model in providers:
        if not key: continue
        try:
            headers = {"Content-Type":"application/json","Authorization":f"Bearer {key}"}
            if prov=="openrouter":
                headers["HTTP-Referer"]="https://neurofactory.app"
            req = urllib.request.Request(url,
                data=_jj.dumps({"model":model,"messages":messages,"max_tokens":350,"temperature":0.55}).encode(),
                headers=headers,method="POST")
            with urllib.request.urlopen(req,timeout=8) as resp:
                d = _jj.loads(resp.read())
                reply = d["choices"][0]["message"]["content"].strip()
            break
        except: continue

    # Pollinations fallback (sans clé)
    if not reply:
        try:
            import urllib.parse
            full = f"{system[:300]}\n\n{message}"
            enc  = urllib.parse.quote(full[:800])
            req2 = urllib.request.Request(f"https://text.pollinations.ai/{enc}",
                headers={"Accept":"text/plain"},method="GET")
            with urllib.request.urlopen(req2,timeout=8) as resp2:
                reply = resp2.read().decode("utf-8",errors="ignore").strip()[:500]
        except: pass

    # Fallback local intelligent
    if not reply:
        reply = CHAT_FALLBACK_RESPONSES.get(message[:30], CHAT_DEFAULT_REPLY)
        # Analyse basique du message
        msg_l = message.lower()
        if any(w in msg_l for w in ["prix","tarif","price","cost","plan","subscription"]):
            reply = CHAT_PRICE_REPLY
        elif any(w in msg_l for w in ["bug","erreur","problem","issue","crash","marche pas"]):
            reply = CHAT_BUG_REPLY
        elif any(w in msg_l for w in ["annul","cancel","résil","stopper"]):
            reply = CHAT_CANCEL_REPLY
        elif any(w in msg_l for w in ["remboursement","refund"]):
            reply = CHAT_REFUND_REPLY
        elif any(w in msg_l for w in ["contact","support","aide","help","humain"]):
            reply = CHAT_CONTACT_REPLY
        elif any(w in msg_l for w in ["essai","gratuit","trial","free","tester"]):
            reply = CHAT_TRIAL_REPLY
    reply = reply[:600] if reply else CHAT_DEFAULT_REPLY
    return jsonify({"reply": reply, "lang": lang})

# ── Upsell & Cross-sell API ─────────────────────────────────────
@app.route("/api/upsell")
def upsell_api():
    """Retourne les offres cross-sell pour un email donné."""
    import json as _j, os as _os
    email = request.args.get("email","").strip().lower()
    if not email: return jsonify({"offers":[]}),400
    try:
        reg_path = _os.path.join(_os.path.dirname(__file__),"data","saas.json")
        sub_path = _os.path.join(_os.path.dirname(__file__),"data","cross_subscribers.json")
        registry   = _j.loads(open(reg_path).read()) if _os.path.exists(reg_path) else {}
        cross_subs = _j.loads(open(sub_path).read()) if _os.path.exists(sub_path) else {}
        user_subs  = cross_subs.get(email, [])
        active_sectors = {s["sector"] for s in user_subs if s.get("status")=="active"}
        same_nature    = set(CROSS_SELL_SAME_SECTORS)
        has_active     = bool(active_sectors & same_nature)
        up_price       = UPSELL_PRICE if has_active else None
        offers = []
        for sname, sdata in registry.items():
            if sname == SITE_NAME: continue
            if sdata.get("lang") != LANG: continue
            if sdata.get("sector","") not in same_nature: continue
            if sdata.get("status") not in ("live","active","pending"): continue
            orig = PRICE; up = up_price if up_price else orig
            disc = int((1-up/orig)*100) if up_price else 0
            link = sdata.get("url","") or sdata.get("payment_link","")
            reason = (f"Offre abonné − {CROSS_SELL_GROUP}" if has_active else "Service complémentaire") if LANG=="fr" else (f"Subscriber offer − {CROSS_SELL_GROUP}" if has_active else "Complementary service")
            offers.append({"site_name":sname,"concept":sdata.get("concept",""),"emoji":sdata.get("emoji","⚡"),"url":link,"payment_link":sdata.get("payment_link",""),"original_price":orig,"upsell_price":up,"discount_pct":disc,"is_active_subscriber":has_active,"reason":reason,"sector":sdata.get("sector","")})
        offers.sort(key=lambda x:-x["discount_pct"])
        return jsonify({"offers":offers[:5],"has_active_subscriber":has_active,"group":CROSS_SELL_GROUP})
    except Exception as e: return jsonify({"offers":[],"error":str(e)})

@app.route("/api/upsell/checkout",methods=["POST"])
@require_auth
def upsell_checkout():
    """Lance un checkout Stripe avec le prix réduit upsell (9,99€)."""
    d = request.get_json() or {}
    target_site = d.get("target_site","")
    uid   = request.user["user_id"]; email = request.user["email"]
    # Vérifier que l'utilisateur est bien abonné actif sur un site de même nature
    import json as _j, os as _os
    sub_path = _os.path.join(_os.path.dirname(__file__),"data","cross_subscribers.json")
    cross_subs = _j.loads(open(sub_path).read()) if _os.path.exists(sub_path) else {}
    user_subs  = cross_subs.get(email,[])
    active_s   = {s["sector"] for s in user_subs if s.get("status")=="active"}
    same_n     = set(CROSS_SELL_SAME_SECTORS)
    has_active = bool(active_s & same_n)
    if not has_active:
        return jsonify({"error":"Aucun abonnement actif de même nature"}),403
    if not stripe.api_key or not UPSELL_PRICE_ID:
        return jsonify({"url":d.get("fallback_url",BASE_URL+"/pricing"),"simulated":True})
    try:
        sess = stripe.checkout.Session.create(
            payment_method_types=["card"],mode="subscription",
            line_items=[{"price":UPSELL_PRICE_ID,"quantity":1}],
            customer_email=email,
            subscription_data={"trial_period_days":0},
            success_url=BASE_URL+"/api/checkout-success?session_id={CHECKOUT_SESSION_ID}&upsell=1",
            cancel_url=BASE_URL+"/pricing?canceled=1",
            metadata={"user_id":str(uid),"site":SITE_NAME,"upsell":"1","upsell_price":str(UPSELL_PRICE)},
        )
        return jsonify({"url":sess.url,"upsell_price":UPSELL_PRICE})
    except Exception as e: return jsonify({"error":str(e)}),500

# ── Revenue & Lifecycle Management API ──────────────────────
@app.route("/api/revenue", methods=["POST"])
@require_auth
def update_revenue():
    """Met à jour le MRR du site et déclenche les règles pub/lifecycle."""
    import json as _json
    d = request.get_json() or {}
    mrr = float(d.get("mrr", 0))
    db = get_db()
    uid = request.user["user_id"]
    # Mettre à jour les stats dans la BDD locale
    db.execute("UPDATE users SET mrr=? WHERE id=?", (mrr, uid))
    db.commit()
    # Calcul budget pub
    pub_active = mrr > 0 and mrr < PUB_STOP_REVENUE
    ad_budget  = round(mrr * PUB_REINVEST_RATE, 2) if pub_active else 0
    ad_budget  = max(PUB_MIN_BUDGET, min(PUB_MAX_BUDGET, ad_budget)) if pub_active else 0
    is_autonomous = mrr >= PUB_STOP_REVENUE
    return jsonify({
        "ok": True, "mrr": mrr,
        "ad_active": pub_active,
        "ad_budget_eur": ad_budget,
        "is_autonomous": is_autonomous,
        "message": ("Site autonome — pub stoppée" if is_autonomous
                    else f"Budget pub: {ad_budget:.2f}€/mois" if pub_active
                    else "Pas de revenus — pub inactive"),
    })

@app.route("/api/revenue/stats")
@require_auth
def revenue_stats():
    """Retourne les stats revenus + lifecycle du site."""
    db = get_db(); uid = request.user["user_id"]
    u = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    mrr = float(u["mrr"]) if u and u["mrr"] else 0
    pub_active = mrr > 0 and mrr < PUB_STOP_REVENUE
    ad_budget  = round(mrr * PUB_REINVEST_RATE, 2) if pub_active else 0
    return jsonify({
        "mrr": mrr,
        "ad_active": pub_active,
        "ad_budget_eur": ad_budget,
        "pub_stop_threshold": PUB_STOP_REVENUE,
        "pub_rate": PUB_REINVEST_RATE,
        "is_autonomous": mrr >= PUB_STOP_REVENUE,
        "prune_days": PRUNE_DAYS,
    })

@app.route("/api/cross-promo")
def cross_promo_api():
    """Retourne les sites partenaires depuis le registre saas.json."""
    import json, os, random
    n = min(50, int(request.args.get("n", 3)))
    reg_path = os.path.join(os.path.dirname(__file__), "data", "saas.json")
    try:
        registry = json.loads(open(reg_path).read())
    except: registry = {}
    # Affinités du site courant
    sector = SECTOR
    aff = CROSS_PROMO_AFFINITY.get(sector, {})
    sim = set(aff.get("similar", []))
    comp = set(aff.get("complementary", []))
    scored = []
    for sname, data in registry.items():
        if data.get("lang") != LANG: continue
        s = data.get("sector", "")
        score = (3 if s == sector else 2 if s in sim else 1 if s in comp else 0)
        if score: scored.append((score, sname, data))
    scored.sort(key=lambda x: -x[0])
    random.shuffle(scored[:min(len(scored), n*3)])
    scored.sort(key=lambda x: -x[0])
    partners = [
        {"name":sn,"concept":d.get("concept",""),"description":d.get("description",""),
         "emoji":d.get("emoji","⚡"),"sector":d.get("sector",""),
         "site_type":d.get("site_type",""),"url":d.get("url",""),
         "payment_link":d.get("payment_link",""),"score":sc}
        for sc, sn, d in scored[:n]]
    return jsonify({"partners": partners, "total": len(partners), "sector": sector})

@app.route("/utilisateurs")
def utilisateurs_page():
    if SITE_TYPE not in ("p2p","rental"): return redirect("/")
    return send_file_safe("utilisateurs.html")

@app.route("/pricing")
def pricing(): return send_file_safe("pricing.html","index.html")

@app.route("/features")
def features(): return send_file_safe("features.html","index.html")

@app.route("/about")
def about(): return send_file_safe("about.html","index.html")

@app.route("/contact")
def contact_page(): return send_file_safe("contact.html","index.html")

@app.route("/blog")
def blog(): return send_file_safe("blog.html","index.html")

@app.route("/merci")
@app.route("/thank-you")
def merci(): return send_file_safe("merci.html","app.html")

@app.route("/mentions-legales")
@app.route("/legal")
@app.route("/terms")
def legal(): return send_file_safe("mentions-legales.html")

@app.route("/confidentialite")
@app.route("/privacy")
def privacy(): return send_file_safe("mentions-legales.html")

@app.route("/api/health")
def health():
    return jsonify({"status":"ok","site":SITE_NAME,"version":"v9","lang":LANG})

@app.errorhandler(404)
def not_found(e): return send_file_safe("404.html"), 404

@app.errorhandler(500)
def server_error(e): return jsonify({"error":"Internal server error"}), 500

@app.route("/<path:fn>")
def static_files(fn):
    # Bloquer accès aux fichiers sensibles
    blocked = (".env","stripe.env",".git","server.py","db.py","webhook.py")
    if any(fn.startswith(b) or fn.endswith(b) for b in blocked):
        return send_file_safe("404.html"), 404
    p=Path(fn)
    if p.exists() and p.is_file() and not fn.startswith("."):
        return send_file(fn)
    return send_file_safe("404.html"), 404

# ── Auth ─────────────────────────────────────────────────────
@app.route("/api/register",methods=["POST"])
def register():
    d=request.get_json() or {}
    email=d.get("email","").strip().lower(); pwd=d.get("password",""); nm=d.get("name","")
    if not email or len(pwd)<8: return jsonify({"error":"Email et mot de passe requis (8+ car.)"}),400
    db=get_db()
    if db.execute("SELECT id FROM users WHERE email=?",(email,)).fetchone():
        return jsonify({"error":"Email déjà utilisé"}),409
    cur=db.execute(
        "INSERT INTO users (email,password_hash,name,first_name,last_name,departement,city,service_title,created_at,subscription_status) VALUES (?,?,?,?,?,?,?,?,?,?)"
        ,(email,hash_pw(pwd),nm,d.get("first_name",""),d.get("last_name",""),d.get("departement",""),d.get("city",""),d.get("service_title",""),datetime.now(timezone.utc).isoformat(),"trialing"))
    db.commit()
    # ── Vérifier les offres cross-sell au moment de l'inscription ──
    upsell_offers = []
    try:
        import json as _j, os as _os
        reg_path = _os.path.join(_os.path.dirname(__file__),"data","saas.json")
        sub_path = _os.path.join(_os.path.dirname(__file__),"data","cross_subscribers.json")
        registry = _j.loads(open(reg_path).read()) if _os.path.exists(reg_path) else {}
        cross_subs = _j.loads(open(sub_path).read()) if _os.path.exists(sub_path) else {}
        user_subs  = cross_subs.get(email,[])
        active_subs_sectors = {s["sector"] for s in user_subs if s.get("status")=="active"}
        same_nature = set(CROSS_SELL_SAME_SECTORS)
        has_active  = bool(active_subs_sectors & same_nature)
        up_price    = UPSELL_PRICE if has_active else None
        for sname, sdata in registry.items():
            if sname == SITE_NAME: continue
            if sdata.get("lang") != LANG: continue
            if sdata.get("sector","") not in same_nature: continue
            if sdata.get("status") not in ("live","active","pending"): continue
            upsell_offers.append({
                "site_name":sname,"concept":sdata.get("concept",""),
                "emoji":sdata.get("emoji","⚡"),"url":sdata.get("url",""),
                "payment_link":sdata.get("payment_link",""),
                "original_price":PRICE,
                "upsell_price":up_price if up_price else PRICE,
                "discount_pct":int((1-up_price/PRICE)*100) if up_price else 0,
                "is_active_subscriber":has_active,
                "reason":(f"Offre abonné — {CROSS_SELL_GROUP}" if has_active else "Service complémentaire")
            })
    except: pass
    try: send_welcome_email(email,nm or email,SITE_NAME,LANG,BASE_URL)
    except: pass
    token = make_token(cur.lastrowid, email)
    resp = jsonify({"token":token,"email":email,"name":nm,"subscription_status":"trialing","redirect":"/app","upsell_offers":upsell_offers[:3]})
    resp.set_cookie("token",token,max_age=2592000,httponly=True,samesite="Lax")
    return resp, 201

@app.route("/api/login",methods=["POST"])
def login():
    d=request.get_json() or {}
    email=d.get("email","").strip().lower(); pwd=d.get("password","")
    db=get_db(); u=db.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
    if not u or not check_pw(pwd,u["password_hash"]):
        return jsonify({"error":"Email ou mot de passe incorrect"}),401
    token = make_token(u["id"],email)
    sub   = u["subscription_status"] or "inactive"
    redir = "/app" if sub in ("active","trialing") else "/pricing"
    resp  = jsonify({"token":token,"email":email,"name":u["name"],"subscription_status":sub,"redirect":redir})
    resp.set_cookie("token",token,max_age=2592000,httponly=True,samesite="Lax")
    return resp

@app.route("/api/logout",methods=["POST"])
def logout():
    resp = jsonify({"ok":True})
    resp.delete_cookie("token")
    return resp

@app.route("/api/me")
@require_auth
def me():
    db=get_db()
    u=db.execute("SELECT id,email,name,first_name,last_name,departement,city,service_title,subscription_status,created_at,trial_ends_at FROM users WHERE id=?",(request.user["user_id"],)).fetchone()
    if not u: return jsonify({"error":"Not found"}),404
    data = dict(u)
    # Calculer jours restants trial
    if u["subscription_status"]=="trialing" and u["trial_ends_at"]:
        try:
            ends=datetime.fromisoformat(u["trial_ends_at"])
            data["trial_days_left"]=max(0,(ends-datetime.now(timezone.utc)).days)
        except: data["trial_days_left"]=0
    return jsonify(data)

@app.route("/api/me/update",methods=["PATCH"])
@require_auth
def update_profile():
    d=request.get_json() or {}
    db=get_db(); uid=request.user["user_id"]
    if "name" in d: db.execute("UPDATE users SET name=? WHERE id=?",(d["name"],uid))
    if "password" in d and len(d["password"])>=8:
        db.execute("UPDATE users SET password_hash=? WHERE id=?",(hash_pw(d["password"]),uid))
    for col in ["first_name","last_name","departement","city","service_title"]:
        if col in d: db.execute(f"UPDATE users SET {col}=? WHERE id=?",(d[col],uid))
    if "first_name" in d or "last_name" in d:
        u2=db.execute("SELECT first_name,last_name FROM users WHERE id=?",(uid,)).fetchone()
        dn=((u2["first_name"] or "")+" "+(u2["last_name"] or "")).strip()
        if dn: db.execute("UPDATE users SET name=? WHERE id=?",(dn,uid))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/delete-account",methods=["DELETE"])
@require_auth
def delete_account():
    uid=request.user["user_id"]; db=get_db()
    db.execute("DELETE FROM users WHERE id=?",(uid,))
    db.execute("DELETE FROM activity WHERE user_id=?",(uid,))
    db.commit()
    resp=jsonify({"ok":True,"redirect":"/"})
    resp.delete_cookie("token"); return resp

# ── Stripe ───────────────────────────────────────────────────
@app.route("/api/create-checkout",methods=["POST"])
@require_auth
def create_checkout():
    uid=request.user["user_id"]; email=request.user["email"]
    if not stripe.api_key or not PRICE_ID:
        db=get_db(); db.execute("UPDATE users SET subscription_status='active' WHERE id=?",(uid,)); db.commit()
        return jsonify({"url":BASE_URL+"/app","simulated":True})
    try:
        sess=stripe.checkout.Session.create(
            payment_method_types=["card"],mode="subscription",
            line_items=[{"price":PRICE_ID,"quantity":1}],
            customer_email=email,
            subscription_data=({"trial_period_days":TRIAL_DAYS} if TRIAL_DAYS else {}),
            success_url=BASE_URL+"/api/checkout-success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=BASE_URL+"/pricing?canceled=1",
            metadata={"user_id":str(uid),"site":SITE_NAME},
        )
        return jsonify({"url":sess.url})
    except Exception as e: return jsonify({"error":str(e)}),500

@app.route("/api/checkout-success")
def checkout_success():
    sid=request.args.get("session_id","")
    if sid and stripe.api_key:
        try:
            sess=stripe.checkout.Session.retrieve(sid)
            uid=int(sess.metadata.get("user_id",0))
            if uid:
                db=get_db()
                db.execute("UPDATE users SET subscription_status='active',stripe_customer_id=? WHERE id=?",(sess.customer,uid))
                db.commit()
                u=db.execute("SELECT email,name FROM users WHERE id=?",(uid,)).fetchone()
                if u:
                    try: send_payment_confirmation(u["email"],u["name"] or u["email"],SITE_NAME,PRICE_AMOUNT,CURRENCY,LANG)
                    except: pass
        except: pass
    return redirect("/merci")

@app.route("/api/cancel-subscription",methods=["POST"])
@require_auth
def cancel_subscription():
    db=get_db(); uid=request.user["user_id"]
    u=db.execute("SELECT stripe_customer_id FROM users WHERE id=?",(uid,)).fetchone()
    if u and u["stripe_customer_id"] and stripe.api_key:
        try:
            subs=stripe.Subscription.list(customer=u["stripe_customer_id"],limit=1)
            if subs.data: stripe.Subscription.cancel(subs.data[0].id)
        except Exception as e: return jsonify({"error":str(e)}),500
    db.execute("UPDATE users SET subscription_status='canceled' WHERE id=?",(uid,))
    db.commit()
    return jsonify({"ok":True,"redirect":"/"})

@app.route("/api/create-portal",methods=["POST"])
@require_auth
def customer_portal():
    db=get_db()
    u=db.execute("SELECT stripe_customer_id FROM users WHERE id=?",(request.user["user_id"],)).fetchone()
    if not u or not u["stripe_customer_id"] or not stripe.api_key:
        return jsonify({"error":"Portail non disponible sans Stripe configuré"}),400
    try:
        sess=stripe.billing_portal.Session.create(customer=u["stripe_customer_id"],return_url=BASE_URL+"/app")
        return jsonify({"url":sess.url})
    except Exception as e: return jsonify({"error":str(e)}),500

@app.route("/webhook/stripe",methods=["POST"])
def stripe_webhook(): return wh.handle(request,stripe,WEBHOOK_SECRET)

# ── API Dashboard & activité ──────────────────────────────────
@app.route("/api/dashboard")
@require_auth
def dashboard_data():
    db=get_db(); uid=request.user["user_id"]
    u=db.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone()
    act=db.execute("SELECT COUNT(*) as total FROM activity WHERE user_id=?",(uid,)).fetchone()
    inv=db.execute("SELECT COUNT(*) as cnt,COALESCE(SUM(amount),0) as total FROM invoices WHERE user_id=?",(uid,)).fetchone()
    # Actions récentes
    recent=db.execute("SELECT action,created_at FROM activity WHERE user_id=? ORDER BY id DESC LIMIT 10",(uid,)).fetchall()
    return jsonify({
        "user":dict(u),"stats":dict(act),"invoices":dict(inv),
        "recent_activity":[dict(r) for r in recent],
        "site":{"name":SITE_NAME,"type":SITE_TYPE,"lang":LANG,"tagline":TAGLINE},
    })

@app.route("/api/invoices")
@require_auth
def get_invoices():
    db=get_db(); uid=request.user["user_id"]
    rows=db.execute("SELECT * FROM invoices WHERE user_id=? ORDER BY created_at DESC LIMIT 24",(uid,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/activity",methods=["POST"])
@require_auth
def log_activity():
    d=request.get_json() or {}; uid=request.user["user_id"]
    action=d.get("action",""); data=json.dumps(d.get("data",{}))
    if not action: return jsonify({"error":"action required"}),400
    db=get_db()
    db.execute("INSERT INTO activity (user_id,action,data,created_at) VALUES (?,?,?,?)",
               (uid,action,data,datetime.now(timezone.utc).isoformat()))
    db.commit()
    return jsonify({"ok":True})

# ── Contact form ─────────────────────────────────────────────
@app.route("/api/contact",methods=["POST"])
def contact_form():
    d=request.get_json() or {}
    nom=d.get("name","").strip(); email=d.get("email","").strip(); msg=d.get("message","").strip()
    if not nom or not email or not msg: return jsonify({"error":"Tous les champs sont requis"}),400
    if len(msg) < 10: return jsonify({"error":"Message trop court"}),400
    # Enregistrer en base
    db=get_db()
    db.execute("CREATE TABLE IF NOT EXISTS contacts (id INTEGER PRIMARY KEY, name TEXT, email TEXT, message TEXT, created_at TEXT)")
    db.execute("INSERT INTO contacts (name,email,message,created_at) VALUES (?,?,?,?)",
               (nom,email,msg,datetime.now(timezone.utc).isoformat()))
    db.commit()
    # Tentative d'envoi email admin
    admin_email=os.getenv("SMTP_USER","")
    if admin_email:
        try:
            from mailer import _send
            _send(admin_email, f"[BoosBrand] Nouveau contact de {nom}",
                  f"<p><b>Nom:</b> {nom}</p><p><b>Email:</b> {email}</p><p><b>Message:</b><br>{msg}</p>")
        except: pass
    return jsonify({"ok":True,"message":"Message envoyé, nous vous répondrons sous 24h"})

# ── Newsletter ───────────────────────────────────────────────
@app.route("/api/newsletter",methods=["POST"])
def newsletter():
    d=request.get_json() or {}; email=d.get("email","").strip().lower()
    if not email or "@" not in email: return jsonify({"error":"Email invalide"}),400
    db=get_db()
    db.execute("CREATE TABLE IF NOT EXISTS newsletter (id INTEGER PRIMARY KEY, email TEXT UNIQUE, created_at TEXT)")
    try:
        db.execute("INSERT INTO newsletter (email,created_at) VALUES (?,?)",(email,datetime.now(timezone.utc).isoformat()))
        db.commit()
        return jsonify({"ok":True})
    except: return jsonify({"ok":True})  # Email déjà inscrit = pas d'erreur

# ── API publique ─────────────────────────────────────────────
@app.route("/api/site-info")
def site_info():
    return jsonify({"name":SITE_NAME,"type":SITE_TYPE,"lang":LANG,"description":DESCRIPTION,"tagline":TAGLINE,"price":PRICE_AMOUNT,"currency":CURRENCY,"trial_days":TRIAL_DAYS if TRIAL_DAYS else 0})

# ══════════════════════════════════════════════════════════════
# MARKETPLACE — Routes P2P / Location avec commission 10%
# ══════════════════════════════════════════════════════════════
# La commission est prélevée automatiquement via Stripe Connect
# sur chaque transaction : montant_net = montant - (montant * 0.10)

COMMISSION_RATE = float(os.getenv("COMMISSION_RATE","0.10"))  # 10% par défaut

# ── Annonces ─────────────────────────────────────────────────
@app.route("/api/listings", methods=["GET"])
def get_listings():
    """Retourne les annonces filtrées par département, catégorie, prix."""
    dep    = request.args.get("dep","").strip()
    cat    = request.args.get("cat","").strip()
    page   = max(1, int(request.args.get("page",1)))
    per    = min(50, max(1, int(request.args.get("per",12))))
    sort   = request.args.get("sort","recent")  # recent | price_asc | price_desc | rating
    db     = get_db()
    query  = "SELECT * FROM listings WHERE status='active'"
    params = []
    if dep:  query += " AND departement=?"; params.append(dep)
    if cat:  query += " AND category=?";    params.append(cat)
    if sort == "price_asc":  query += " ORDER BY price ASC"
    elif sort == "price_desc": query += " ORDER BY price DESC"
    elif sort == "rating":   query += " ORDER BY rating DESC"
    else:                    query += " ORDER BY created_at DESC"
    query += f" LIMIT {per} OFFSET {(page-1)*per}"
    rows = db.execute(query, params).fetchall()
    total = db.execute("SELECT COUNT(*) FROM listings WHERE status='active'"+(f" AND departement=?" if dep else ""), [dep] if dep else []).fetchone()[0]
    return jsonify({"listings":[dict(r) for r in rows],"total":total,"page":page,"pages":(total+per-1)//per})

@app.route("/api/listings", methods=["POST"])
def create_listing():
    """Créer une annonce (prestataire connecté)."""
    token=request.cookies.get("token"); user=_decode_token(token)
    if not user: return jsonify({"error":"Connexion requise"}),401
    d=request.get_json() or {}
    title    = d.get("title","").strip()
    desc     = d.get("description","").strip()
    price    = float(d.get("price",0))
    dep      = d.get("departement","").strip()
    category = d.get("category","").strip()
    if not title or price <= 0 or not dep:
        return jsonify({"error":"Titre, prix et département requis"}),400
    if price < 5:  return jsonify({"error":"Prix minimum 5€"}),400
    if price > 10000: return jsonify({"error":"Prix maximum 10 000€"}),400
    # Calcul commission affichée au prestataire
    commission = round(price * COMMISSION_RATE, 2)
    net        = round(price - commission, 2)
    db=get_db()
    db.execute("CREATE TABLE IF NOT EXISTS listings (id INTEGER PRIMARY KEY, provider_id INTEGER, title TEXT, description TEXT, price REAL, commission REAL, net_amount REAL, departement TEXT, category TEXT, status TEXT DEFAULT 'active', rating REAL DEFAULT 0.0, review_count INTEGER DEFAULT 0, created_at TEXT, updated_at TEXT)")
    cur=db.execute("INSERT INTO listings (provider_id,title,description,price,commission,net_amount,departement,category,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,'active',?,?)",
        (user["id"],title,desc,price,commission,net,dep,category,datetime.now(timezone.utc).isoformat(),datetime.now(timezone.utc).isoformat()))
    db.commit()
    return jsonify({"ok":True,"listing_id":cur.lastrowid,"price":price,"commission":commission,"net":net}),201

@app.route("/api/listings/<int:listing_id>", methods=["GET"])
def get_listing(listing_id):
    db=get_db()
    row=db.execute("SELECT * FROM listings WHERE id=?", [listing_id]).fetchone()
    if not row: return jsonify({"error":"Annonce introuvable"}),404
    l=dict(row)
    # Ajouter le prestataire
    provider=db.execute("SELECT id,name,avatar FROM users WHERE id=?", [l["provider_id"]]).fetchone()
    if provider: l["provider"]=dict(provider)
    return jsonify(l)

# ── Réservations / Bookings ───────────────────────────────────
@app.route("/api/bookings", methods=["POST"])
def create_booking():
    """Initie une réservation avec paiement Stripe + commission 10%."""
    token=request.cookies.get("token"); user=_decode_token(token)
    if not user: return jsonify({"error":"Connexion requise"}),401
    d=request.get_json() or {}
    listing_id = int(d.get("listing_id",0))
    date_str   = d.get("date","").strip()
    message    = d.get("message","").strip()
    if not listing_id or not date_str:
        return jsonify({"error":"listing_id et date requis"}),400
    db=get_db()
    listing=db.execute("SELECT * FROM listings WHERE id=? AND status='active'", [listing_id]).fetchone()
    if not listing: return jsonify({"error":"Annonce introuvable ou indisponible"}),404
    if listing["provider_id"] == user["id"]:
        return jsonify({"error":"Impossible de réserver votre propre annonce"}),400
    price      = float(listing["price"])
    commission = round(price * COMMISSION_RATE, 2)
    net        = round(price - commission, 2)
    amount_cts = int(price * 100)
    fee_cts    = int(commission * 100)
    # Création réservation en BDD (statut pending)
    db.execute("CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY, listing_id INTEGER, client_id INTEGER, provider_id INTEGER, amount REAL, commission REAL, net_amount REAL, date_service TEXT, message TEXT, status TEXT DEFAULT 'pending', stripe_pi_id TEXT, created_at TEXT, validated_at TEXT, disputed_at TEXT, dispute_reason TEXT)")
    cur=db.execute("INSERT INTO bookings (listing_id,client_id,provider_id,amount,commission,net_amount,date_service,message,status,created_at) VALUES (?,?,?,?,?,?,?,?,'pending',?)",
        (listing_id,user["id"],listing["provider_id"],price,commission,net,date_str,message,datetime.now(timezone.utc).isoformat()))
    booking_id=cur.lastrowid; db.commit()
    # Créer le PaymentIntent Stripe avec application_fee (commission)
    stripe_key=os.getenv("STRIPE_API_KEY","")
    pi_data={"booking_id":booking_id,"price":price,"commission":commission,"net":net}
    if stripe_key and not "COLLEZ" in stripe_key:
        try:
            import stripe; stripe.api_key=stripe_key
            provider_acct=db.execute("SELECT stripe_account_id FROM users WHERE id=?", [listing["provider_id"]]).fetchone()
            pi_kwargs={"amount":amount_cts,"currency":"eur","capture_method":"manual","automatic_payment_methods":{"enabled":True},
                        "metadata":{"booking_id":str(booking_id),"listing_id":str(listing_id),"commission":str(commission),"commission_cts":str(fee_cts),"provider_id":str(listing["provider_id"])}}
            if provider_acct and provider_acct["stripe_account_id"]:
                # Séquestre : transfert déclenché après validation acheteur
                pi_kwargs["transfer_data"]={"destination":provider_acct["stripe_account_id"]}
                pi_kwargs["application_fee_amount"]=fee_cts
            pi=stripe.PaymentIntent.create(**pi_kwargs)
            db.execute("UPDATE bookings SET stripe_pi_id=? WHERE id=?", [pi.id, booking_id])
            db.commit()
            pi_data["client_secret"]=pi.client_secret
            pi_data["stripe_pi_id"]=pi.id
        except Exception as e:
            pi_data["stripe_error"]=str(e)
    return jsonify({"ok":True,"booking_id":booking_id,**pi_data}),201

@app.route("/api/bookings/<int:booking_id>/confirm", methods=["POST"])
def confirm_booking(booking_id):
    """Confirme une réservation après paiement Stripe réussi."""
    token=request.cookies.get("token"); user=_decode_token(token)
    if not user: return jsonify({"error":"Connexion requise"}),401
    d=request.get_json() or {}
    pi_id=d.get("payment_intent_id","")
    db=get_db()
    booking=db.execute("SELECT * FROM bookings WHERE id=? AND client_id=?", [booking_id,user["id"]]).fetchone()
    if not booking: return jsonify({"error":"Réservation introuvable"}),404
    # Vérifier le paiement Stripe
    stripe_key=os.getenv("STRIPE_API_KEY","")
    confirmed=False
    if stripe_key and pi_id and not "COLLEZ" in stripe_key:
        try:
            import stripe; stripe.api_key=stripe_key
            pi=stripe.PaymentIntent.retrieve(pi_id)
            confirmed=(pi.status=="succeeded")
        except: pass
    else:
        confirmed=True  # Mode test sans Stripe
    if not confirmed:
        return jsonify({"error":"Paiement non confirmé par Stripe"}),402
    db.execute("UPDATE bookings SET status='held',stripe_pi_id=?=? WHERE id=?", [pi_id,booking_id])
    # Mettre à jour les stats de commission
    commission=float(booking["commission"])
    db.execute("INSERT OR IGNORE INTO platform_stats (key,value) VALUES ('total_commission',0)")
    db.execute("UPDATE platform_stats SET value=value+? WHERE key='total_commission'", [commission])
    db.execute("INSERT OR IGNORE INTO platform_stats (key,value) VALUES ('total_transactions',0)")
    db.execute("UPDATE platform_stats SET value=value+1 WHERE key='total_transactions'")
    db.commit()
    return jsonify({"ok":True,"status":"confirmed","commission_earned":commission})

@app.route("/api/bookings", methods=["GET"])
def my_bookings():
    """Liste les réservations de l'utilisateur connecté."""
    token=request.cookies.get("token"); user=_decode_token(token)
    if not user: return jsonify({"error":"Connexion requise"}),401
    db=get_db()
    as_client   = db.execute("SELECT * FROM bookings WHERE client_id=? ORDER BY created_at DESC LIMIT 50", [user["id"]]).fetchall()
    as_provider = db.execute("SELECT * FROM bookings WHERE provider_id=? ORDER BY created_at DESC LIMIT 50", [user["id"]]).fetchall()
    return jsonify({"as_client":[dict(r) for r in as_client],"as_provider":[dict(r) for r in as_provider]})

# ── Départements et stats ─────────────────────────────────────
@app.route("/api/deps", methods=["GET"])
def get_deps_stats():
    """Stats par département pour la carte interactive."""
    db=get_db()
    rows=db.execute("SELECT departement, COUNT(*) as count, AVG(rating) as rating FROM listings WHERE status='active' GROUP BY departement ORDER BY count DESC").fetchall()
    return jsonify({"deps":[{"code":r["departement"],"count":r["count"],"rating":round(float(r["rating"] or 0),1)} for r in rows]})

@app.route("/api/deps/<code>", methods=["GET"])
def get_dep_listings(code):
    """Annonces d'un département spécifique pour la carte."""
    db=get_db()
    rows=db.execute("SELECT id,title,price,commission,rating,category FROM listings WHERE departement=? AND status='active' ORDER BY rating DESC LIMIT 20", [code]).fetchall()
    total=db.execute("SELECT COUNT(*) FROM listings WHERE departement=? AND status='active'", [code]).fetchone()[0]
    return jsonify({"dep":code,"total":total,"listings":[dict(r) for r in rows]})

# ── Avis / Reviews ────────────────────────────────────────────
@app.route("/api/reviews", methods=["POST"])
def add_review():
    """Ajouter un avis après une réservation confirmée."""
    token=request.cookies.get("token"); user=_decode_token(token)
    if not user: return jsonify({"error":"Connexion requise"}),401
    d=request.get_json() or {}
    booking_id=int(d.get("booking_id",0))
    rating=float(d.get("rating",0))
    comment=d.get("comment","").strip()
    if not booking_id or not (1 <= rating <= 5): return jsonify({"error":"booking_id et note 1-5 requis"}),400
    db=get_db()
    booking=db.execute("SELECT * FROM bookings WHERE id=? AND client_id=? AND status='confirmed'", [booking_id,user["id"]]).fetchone()
    if not booking: return jsonify({"error":"Réservation confirmée non trouvée"}),404
    db.execute("CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY, booking_id INTEGER UNIQUE, listing_id INTEGER, reviewer_id INTEGER, rating REAL, comment TEXT, created_at TEXT)")
    try:
        db.execute("INSERT INTO reviews (booking_id,listing_id,reviewer_id,rating,comment,created_at) VALUES (?,?,?,?,?,?)",
                   (booking_id,booking["listing_id"],user["id"],rating,comment,datetime.now(timezone.utc).isoformat()))
        # Mettre à jour la note moyenne de l'annonce
        avg=db.execute("SELECT AVG(rating),COUNT(*) FROM reviews WHERE listing_id=?", [booking["listing_id"]]).fetchone()
        db.execute("UPDATE listings SET rating=?,review_count=? WHERE id=?", [round(avg[0],1),avg[1],booking["listing_id"]])
        db.commit()
        return jsonify({"ok":True,"rating":rating}),201
    except Exception as e:
        return jsonify({"error":"Avis déjà soumis pour cette réservation"}),409

# ── Stats commission plateforme ───────────────────────────────
@app.route("/api/platform/stats", methods=["GET"])
def platform_stats():
    """Stats globales de la plateforme (admin seulement)."""
    token=request.cookies.get("token"); user=_decode_token(token)
    if not user: return jsonify({"error":"Connexion requise"}),401
    db=get_db()
    total_listings=db.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
    active_listings=db.execute("SELECT COUNT(*) FROM listings WHERE status='active'").fetchone()[0]
    total_bookings=db.execute("SELECT COUNT(*) FROM bookings WHERE status='confirmed'").fetchone()[0]
    total_gmv=db.execute("SELECT SUM(amount) FROM bookings WHERE status='confirmed'").fetchone()[0] or 0
    total_commission=db.execute("SELECT SUM(commission) FROM bookings WHERE status='confirmed'").fetchone()[0] or 0
    by_dep=db.execute("SELECT departement,COUNT(*) as n FROM listings WHERE status='active' GROUP BY departement ORDER BY n DESC LIMIT 10").fetchall()
    return jsonify({"total_listings":total_listings,"active_listings":active_listings,
        "total_bookings":total_bookings,"total_gmv":round(total_gmv,2),
        "total_commission":round(total_commission,2),"commission_rate":COMMISSION_RATE,
        "top_deps":[{"dep":r["departement"],"count":r["n"]} for r in by_dep]})

# ── Profil prestataire ────────────────────────────────────────
# ══════════════════════════════════════════════════════════════
# PROFILS PRESTATAIRES — Visibles publiquement
# ══════════════════════════════════════════════════════════════

# Champs publics exposés sur le profil (sans email/mdp/données sensibles)
_PUBLIC_FIELDS = [
    "id","first_name","last_name","display_name","bio","profile_photo",
    "is_professional","company_name","service_title","service_description",
    "service_categories","price_from","price_to","price_unit",
    "departement","city","zip_code","intervention_radius",
    "website","availability","response_time","languages",
    "years_experience","certifications","rating_avg","review_count",
    "completed_jobs","verified","profile_complete","created_at"
]

@app.route("/api/providers/<int:provider_id>", methods=["GET"])
def get_provider(provider_id):
    """Profil public complet d'un prestataire."""
    db=get_db()
    sql="SELECT "+",".join(_PUBLIC_FIELDS)+" FROM users WHERE id=?"
    user=db.execute(sql,[provider_id]).fetchone()
    if not user: return jsonify({"error":"Prestataire introuvable"}),404
    u=dict(user)
    # Annonces actives
    u["listings"]=[
        dict(r) for r in db.execute(
            "SELECT id,title,price,commission,rating,review_count,departement,category,description FROM listings WHERE provider_id=? AND status='active' ORDER BY rating DESC",
            [provider_id]).fetchall()]
    # Derniers avis
    u["reviews"]=[
        dict(r) for r in db.execute(
            "SELECT r.rating,r.comment,r.created_at,u.first_name,u.last_name,u.display_name"
            " FROM reviews r"
            " JOIN listings l ON r.listing_id=l.id"
            " JOIN users u ON r.reviewer_id=u.id"
            " WHERE l.provider_id=? ORDER BY r.created_at DESC LIMIT 12",
            [provider_id]).fetchall()]
    # Portfolio
    u["portfolio"]=[
        dict(r) for r in db.execute(
            "SELECT id,title,description,image_url,category FROM portfolio WHERE user_id=? ORDER BY sort_order",
            [provider_id]).fetchall()]
    # Calculer le score de profil
    score=sum([
        20 if u.get("profile_photo") else 0,
        20 if u.get("service_description") else 0,
        20 if u.get("city") else 0,
        20 if len(u.get("portfolio",[])) > 0 else 0,
        20 if u.get("certifications") else 0,
    ])
    u["profile_score"]=score
    return jsonify(u)

@app.route("/api/providers/search", methods=["GET"])
def search_providers():
    """Recherche de prestataires avec filtres."""
    dep      = request.args.get("dep","").strip()
    cat      = request.args.get("cat","").strip()
    q        = request.args.get("q","").strip()
    pro_only = request.args.get("pro","0") == "1"
    verified = request.args.get("verified","0") == "1"
    sort     = request.args.get("sort","rating")  # rating | price_asc | price_desc | recent
    page     = max(1,int(request.args.get("page",1)))
    per      = min(48,max(1,int(request.args.get("per",12))))
    db=get_db()
    fields=",".join(["u."+f for f in _PUBLIC_FIELDS])
    sql=f"SELECT {fields} FROM users u WHERE u.service_title!=''"
    params=[]
    if dep:      sql+=" AND u.departement=?";       params.append(dep)
    if cat:      sql+=" AND u.service_categories LIKE ?"; params.append(f"%{cat}%")
    if q:        sql+=" AND (u.service_title LIKE ? OR u.display_name LIKE ? OR u.city LIKE ?)"; params+=[f"%{q}%",f"%{q}%",f"%{q}%"]
    if pro_only: sql+=" AND u.is_professional=1"
    if verified: sql+=" AND u.verified=1"
    if sort=="price_asc":  sql+=" ORDER BY u.price_from ASC"
    elif sort=="price_desc": sql+=" ORDER BY u.price_from DESC"
    elif sort=="recent":   sql+=" ORDER BY u.created_at DESC"
    else:                  sql+=" ORDER BY u.rating_avg DESC, u.review_count DESC"
    total_sql=sql.replace(f"SELECT {fields}","SELECT COUNT(*)",1)
    total=db.execute(total_sql,params).fetchone()[0]
    sql+=f" LIMIT {per} OFFSET {(page-1)*per}"
    rows=db.execute(sql,params).fetchall()
    providers=[dict(r) for r in rows]
    # Ajouter note moyenne pour chaque provider
    for p in providers:
        p["listing_count"]=db.execute("SELECT COUNT(*) FROM listings WHERE provider_id=? AND status='active'",[p["id"]]).fetchone()[0]
    return jsonify({"providers":providers,"total":total,"page":page,"pages":(total+per-1)//per})

@app.route("/api/profile", methods=["GET"])
@require_auth
def get_my_profile():
    """Retourne le profil complet de l'utilisateur connecté (inclut champs privés)."""
    db=get_db(); uid=request.user["user_id"]
    user=db.execute("SELECT * FROM users WHERE id=?",[uid]).fetchone()
    if not user: return jsonify({"error":"Introuvable"}),404
    u=dict(user); u.pop("password_hash",None)
    # Portfolio
    u["portfolio"]=[dict(r) for r in db.execute("SELECT * FROM portfolio WHERE user_id=? ORDER BY sort_order",[uid]).fetchall()]
    # Stats
    u["listing_count"]=db.execute("SELECT COUNT(*) FROM listings WHERE provider_id=? AND status='active'",[uid]).fetchone()[0]
    u["booking_count"]=db.execute("SELECT COUNT(*) FROM bookings WHERE provider_id=? AND status='confirmed'",[uid]).fetchone()[0]
    u["total_earned"]=db.execute("SELECT COALESCE(SUM(net_amount),0) FROM bookings WHERE provider_id=? AND status='confirmed'",[uid]).fetchone()[0]
    # Calcul complétude profil
    score=sum([20 if u.get("profile_photo") else 0,20 if u.get("service_description") else 0,
               20 if u.get("city") else 0,20 if u["listing_count"]>0 else 0,
               20 if u.get("certifications") else 0])
    u["profile_score"]=score
    return jsonify(u)

@app.route("/api/profile", methods=["PATCH"])
@require_auth
def update_full_profile():
    """Met à jour le profil public complet du prestataire."""
    db=get_db(); uid=request.user["user_id"]
    d=request.get_json() or {}
    # Champs autorisés à mettre à jour
    allowed=["first_name","last_name","display_name","bio","profile_photo",
             "is_professional","company_name","siret","service_title",
             "service_description","service_categories","price_from","price_to","price_unit",
             "departement","city","zip_code","address","intervention_radius",
             "phone","website","availability","response_time","languages",
             "years_experience","certifications"]
    updates=[]; vals=[]
    for k in allowed:
        if k in d:
            updates.append(f"{k}=?"); vals.append(d[k])
    if not updates: return jsonify({"error":"Aucun champ à mettre à jour"}),400
    # Calcul automatique display_name
    if "first_name" in d or "last_name" in d:
        fn=d.get("first_name") or db.execute("SELECT first_name FROM users WHERE id=?",[uid]).fetchone()["first_name"] or ""
        ln=d.get("last_name") or db.execute("SELECT last_name FROM users WHERE id=?",[uid]).fetchone()["last_name"] or ""
        dn=(fn+" "+ln).strip()
        if dn: updates.append("display_name=?"); vals.append(dn)
    # Calcul profil complet
    user=db.execute("SELECT * FROM users WHERE id=?",[uid]).fetchone()
    merged={**dict(user),**d}
    score=sum([20 if merged.get("profile_photo") else 0,20 if merged.get("service_description") else 0,
               20 if merged.get("city") else 0,20 if merged.get("service_title") else 0,
               20 if merged.get("certifications") else 0])
    updates.append("profile_complete=?"); vals.append(1 if score>=60 else 0)
    updates.append("name=?"); vals.append(merged.get("display_name",merged.get("first_name","")))
    vals.append(uid)
    db.execute(f"UPDATE users SET {chr(44).join(updates)} WHERE id=?",vals)
    db.commit()
    return jsonify({"ok":True,"profile_score":score})

@app.route("/api/portfolio", methods=["POST"])
@require_auth
def add_portfolio():
    """Ajouter une réalisation au portfolio du prestataire."""
    db=get_db(); uid=request.user["user_id"]
    d=request.get_json() or {}
    title=d.get("title","").strip()
    if not title: return jsonify({"error":"Titre requis"}),400
    count=db.execute("SELECT COUNT(*) FROM portfolio WHERE user_id=?",[uid]).fetchone()[0]
    if count >= 20: return jsonify({"error":"Maximum 20 réalisations"}),400
    cur=db.execute("INSERT INTO portfolio (user_id,title,description,image_url,category,sort_order,created_at) VALUES (?,?,?,?,?,?,?)",
        (uid,title,d.get("description",""),d.get("image_url",""),d.get("category",""),count,
         __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()))
    db.commit()
    return jsonify({"ok":True,"id":cur.lastrowid}),201

@app.route("/api/portfolio/<int:item_id>", methods=["DELETE"])
@require_auth
def delete_portfolio(item_id):
    db=get_db(); uid=request.user["user_id"]
    item=db.execute("SELECT id FROM portfolio WHERE id=? AND user_id=?",[item_id,uid]).fetchone()
    if not item: return jsonify({"error":"Introuvable"}),404
    db.execute("DELETE FROM portfolio WHERE id=?",[item_id])
    db.commit()
    return jsonify({"ok":True})

@app.route("/profil/<int:provider_id>")
def profil_public(provider_id):
    """Rendu de la page profil publique — sert le fichier profil.html."""
    return send_from_directory(".", "profil.html")

# ── SERVICE WIDGET ROUTES ──────────────────────────────────────
@app.route("/api/service", methods=["POST"])
def api_service():
    uid, err = require_auth()
    if err: return err
    data = request.get_json(force=True) or {}
    stype = data.get("type","default")
    lang  = data.get("lang", LANG)
    result = ""; summary = ""
    if stype == "booking":
        n=data.get("name",""); e=data.get("email","")
        d=data.get("date",""); t=data.get("time","")
        note=data.get("note","")
        result = f"Réservation confirmée : {n} le {d} à {t}." if lang=="fr" else f"Booking confirmed: {n} on {d} at {t}."
        summary = f"RDV {d} {t}"
        try:
            subj = f"Confirmation — {SITE_NAME}"
            body = f"Bonjour {n},\n\nRéservation : {d} à {t}.\n{note}\n\n— {SITE_NAME}" if lang=="fr" else f"Hi {n},\n\nBooking: {d} at {t}.\n{note}\n\n— {SITE_NAME}"
            mailer.send(e, subj, body)
        except: pass
    elif stype in ("ai_generator","learning","document"):
        prompt = data.get("prompt","") or data.get("topic","") or data.get("details","")
        tone   = data.get("tone","Professionnel"); length = data.get("length","")
        try:
            import httpx
            rr = httpx.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":f"Bearer {os.getenv("GROQ_API_KEY","")}"},
                json={"model":"llama3-8b-8192","max_tokens":600,
                      "messages":[{"role":"user","content":f"Ton:{tone}. {prompt}"}]},
                timeout=20)
            result = rr.json()["choices"][0]["message"]["content"]
        except:
            result = f"[Configurez GROQ_API_KEY pour la génération IA] Sujet: {prompt[:80]}"
        summary = prompt[:60]
        try:
            u=db.session.get(User,uid)
            if u and u.email:
                subj=f"Votre résultat — {SITE_NAME}" if lang=="fr" else f"Your result — {SITE_NAME}"
                mailer.send(u.email, subj, f"{result}\n\n— {SITE_NAME}")
        except: pass
    elif stype in ("crm","tasks","inventory"):
        val  = data.get("fname","") or data.get("task","") or data.get("item","")
        result  = f"Enregistrement créé : {val[:60]}" if lang=="fr" else f"Record created: {val[:60]}"
        summary = val[:60]
        try:
            u=db.session.get(User,uid)
            if u and u.email:
                subj=f"Confirmation — {SITE_NAME}"
                mailer.send(u.email, subj, f"{result}\n\n— {SITE_NAME}")
        except: pass
    else:
        inp=data.get("input","") or data.get("prompt","")
        result=f"Action : {inp[:80]}"; summary=inp[:60]
    try:
        act=Activity(user_id=uid,action=stype,detail=summary[:200])
        db.session.add(act); db.session.commit()
    except: pass
    return jsonify({"ok":True,"result":result,"summary":summary})

@app.route("/api/service/history", methods=["GET"])
def api_service_history():
    uid,err=require_auth()
    if err: return err
    try:
        acts=Activity.query.filter_by(user_id=uid).order_by(Activity.id.desc()).limit(20).all()
        return jsonify({"items":[{"type":a.action,"summary":a.detail,"created_at":str(getattr(a,"created_at",""))} for a in acts]})
    except: return jsonify({"items":[]})

@app.route("/api/service/analytics", methods=["GET"])
def api_service_analytics():
    uid,err=require_auth()
    if err: return err
    try:
        n=Activity.query.filter_by(user_id=uid).count()
        return jsonify({"kpis":{"total":str(n),"growth":f"+{min(n*5,99)}%","avg":str(round(n/7,1)),"best":str(min(n,12))}})
    except: return jsonify({"kpis":{"total":"0","growth":"—","avg":"—","best":"—"}})

@app.route("/api/service/export", methods=["GET"])
def api_service_export():
    uid,err=require_auth()
    if err: return err
    acts=Activity.query.filter_by(user_id=uid).order_by(Activity.id.desc()).all()
    csv="type,summary,date\n"+"\n".join(f"{a.action},{a.detail},{getattr(a,chr(99)+chr(114)+chr(101)+chr(97)+chr(116)+chr(101)+chr(100)+chr(95)+chr(97)+chr(116),chr(0))}" for a in acts)
    from flask import Response
    return Response(csv,mimetype="text/csv",headers={"Content-Disposition":"attachment;filename=history.csv"})

AUTO_RELEASE_DAYS = int(os.getenv("AUTO_RELEASE_DAYS","7"))
@app.route("/api/bookings/<int:booking_id>/validate", methods=["POST"])
def validate_booking(booking_id):
    token=request.cookies.get("token"); user=_decode_token(token)
    if not user: return jsonify({"error":"Non autorise"}),401
    db=get_db()
    bk=db.execute("SELECT * FROM bookings WHERE id=? AND client_id=?",[booking_id,user["id"]]).fetchone()
    if not bk: return jsonify({"error":"Reservation introuvable"}),404
    if bk["status"] not in ("confirmed","paid","held"): return jsonify({"error":"Non validable"}),400
    sk=os.getenv("STRIPE_API_KEY",""); released=False
    if sk and "COLLEZ" not in sk:
        try:
            import stripe; stripe.api_key=sk
            pi=stripe.PaymentIntent.capture(bk["stripe_pi_id"])
            released=(pi.status=="succeeded")
        except Exception as e: return jsonify({"error":str(e)}),500
    else: released=True
    if released:
        db.execute("UPDATE bookings SET status='completed',validated_at=? WHERE id=?",[datetime.now(timezone.utc).isoformat(),booking_id]); db.commit()
        try:
            import mailer; pv=db.execute("SELECT email,name FROM users WHERE id=?",[bk["provider_id"]]).fetchone()
            if pv and pv["email"]: mailer.send(pv["email"],f"Paiement recu - {SITE_NAME}",f"Service valide par acheteur. Net: {bk['net_amount']} EUR. Virement en cours.\n-- {SITE_NAME}")
        except: pass
        return jsonify({"ok":True,"message":"Service valide, paiement libere.","net":bk["net_amount"]})
    return jsonify({"error":"Echec capture"}),500
@app.route("/api/bookings/<int:booking_id>/dispute", methods=["POST"])
def dispute_booking(booking_id):
    token=request.cookies.get("token"); user=_decode_token(token)
    if not user: return jsonify({"error":"Non autorise"}),401
    db=get_db()
    bk=db.execute("SELECT * FROM bookings WHERE id=? AND client_id=?",[booking_id,user["id"]]).fetchone()
    if not bk: return jsonify({"error":"Introuvable"}),404
    if bk["status"] not in ("confirmed","paid","held"): return jsonify({"error":"Litige impossible"}),400
    reason=(request.get_json() or {}).get("reason","Non precise")[:500]
    sk=os.getenv("STRIPE_API_KEY",""); refunded=False
    if sk and "COLLEZ" not in sk:
        try:
            import stripe; stripe.api_key=sk
            pi=stripe.PaymentIntent.cancel(bk["stripe_pi_id"])
            refunded=(pi.status=="canceled")
        except Exception as e: return jsonify({"error":str(e)}),500
    else: refunded=True
    if refunded:
        db.execute("UPDATE bookings SET status='disputed',dispute_reason=?,disputed_at=? WHERE id=?",[reason,datetime.now(timezone.utc).isoformat(),booking_id]); db.commit()
        try:
            import mailer
            by=db.execute("SELECT email FROM users WHERE id=?",[user["id"]]).fetchone()
            pv=db.execute("SELECT email FROM users WHERE id=?",[bk["provider_id"]]).fetchone()
            if by and by["email"]: mailer.send(by["email"],f"Litige - {SITE_NAME}",f"Litige enregistre. Motif: {reason}\nRemboursement en cours.\n-- {SITE_NAME}")
            if pv and pv["email"]: mailer.send(pv["email"],f"Litige - {SITE_NAME}",f"Litige ouvert sur votre prestation. Motif: {reason}\nPaiement rembourse a acheteur.\n-- {SITE_NAME}")
        except: pass
        return jsonify({"ok":True,"message":"Litige ouvert, remboursement en cours."})
    return jsonify({"error":"Echec remboursement"}),500
@app.route("/api/bookings/<int:booking_id>/release", methods=["POST"])
def release_booking(booking_id):
    token=request.cookies.get("token"); user=_decode_token(token)
    if not user: return jsonify({"error":"Non autorise"}),403
    db=get_db()
    bk=db.execute("SELECT * FROM bookings WHERE id=? AND provider_id=?",[booking_id,user["id"]]).fetchone()
    if not bk: return jsonify({"error":"Non autorise"}),403
    from datetime import datetime as _dt,timezone as _tz,timedelta
    created=_dt.fromisoformat(bk["created_at"]) if bk.get("created_at") else None
    if created and (_dt.now(_tz.utc)-created).days < AUTO_RELEASE_DAYS:
        return jsonify({"error":f"Liberation apres {AUTO_RELEASE_DAYS} jours"}),400
    if bk["status"] not in ("confirmed","paid","held"): return jsonify({"error":"Liberation impossible"}),400
    sk=os.getenv("STRIPE_API_KEY","")
    if sk and "COLLEZ" not in sk:
        try:
            import stripe; stripe.api_key=sk
            pi=stripe.PaymentIntent.capture(bk["stripe_pi_id"])
            if pi.status=="succeeded":
                db.execute("UPDATE bookings SET status='completed',validated_at=? WHERE id=?",[datetime.now(timezone.utc).isoformat(),booking_id]); db.commit()
                return jsonify({"ok":True,"message":"Paiement libere."})
        except Exception as e: return jsonify({"error":str(e)}),500
    db.execute("UPDATE bookings SET status='completed' WHERE id=?",[booking_id]); db.commit()
    return jsonify({"ok":True,"message":"Libere (test)."})
@app.route("/api/bookings/<int:booking_id>/status", methods=["GET"])
def booking_escrow_status(booking_id):
    token=request.cookies.get("token"); user=_decode_token(token)
    if not user: return jsonify({"error":"Non autorise"}),401
    db=get_db()
    b=db.execute("SELECT * FROM bookings WHERE id=? AND (client_id=? OR provider_id=?)",[booking_id,user["id"],user["id"]]).fetchone()
    if not b: return jsonify({"error":"Introuvable"}),404
    is_b=(b["client_id"]==user["id"]); in_e=b["status"] in ("confirmed","paid","held")
    from datetime import datetime as _dt,timezone as _tz
    created=_dt.fromisoformat(b["created_at"]) if b.get("created_at") else None
    days_held=(_dt.now(_tz.utc)-created).days if created else 0
    return jsonify({"ok":True,"booking":dict(b),
        "can_validate":is_b and in_e,"can_dispute":is_b and in_e,
        "can_release":(not is_b) and in_e and days_held>=AUTO_RELEASE_DAYS,
        "days_held":days_held,"auto_release_days":AUTO_RELEASE_DAYS,
        "amount":b["amount"],"net":b["net_amount"],"commission":b["commission"]})
# ── Auto-registration webhook si RENDER_EXTERNAL_URL est défini ────
render_url = os.getenv("RENDER_EXTERNAL_URL", "")
if render_url and not os.path.exists(".webhook_registered"):
    try:
        import requests as _req
        import stripe as _st; _st.api_key = os.getenv("STRIPE_API_KEY","")
        wh_url = f"{render_url.rstrip(chr(47))}/webhook/stripe"
        existing = _st.WebhookEndpoint.list(limit=50)
        already = any(w.url == wh_url for w in existing.auto_paging_iter())
        if not already:
            events = ["checkout.session.completed","customer.subscription.created",
                "customer.subscription.updated","customer.subscription.deleted",
                "invoice.payment_succeeded","invoice.payment_failed",
                "payment_intent.succeeded","payment_intent.amount_capturable_updated",
                "payment_intent.canceled","transfer.created","account.updated"]
            wh = _st.WebhookEndpoint.create(url=wh_url, enabled_events=events)
            with open(".webhook_registered","w") as f: f.write(wh.id+"\n"+wh.secret)
            os.environ["STRIPE_WEBHOOK_SECRET"] = wh.secret
            print(f"✅ Webhook auto-enregistré: {wh.id}")
        elif os.path.exists(".webhook_registered"):
            data = open(".webhook_registered").read().split("\n")
            if len(data) >= 2: os.environ["STRIPE_WEBHOOK_SECRET"] = data[1]
    except Exception as _e: print(f"⚠️  Auto-webhook: {_e}")

if __name__ == "__main__":
    port=int(os.getenv("PORT",5000))
    debug=os.getenv("FLASK_DEBUG","0")=="1"
    print(f"🚀 {SITE_NAME} — http://localhost:{port}")
    app.run(host="0.0.0.0",port=port,debug=debug)
