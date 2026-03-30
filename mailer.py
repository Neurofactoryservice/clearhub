import os,smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
SMTP_HOST=os.getenv("SMTP_HOST","smtp.gmail.com")
SMTP_PORT=int(os.getenv("SMTP_PORT","587"))
SMTP_USER=os.getenv("SMTP_USER","")
SMTP_PASS=os.getenv("SMTP_PASS","")
FROM_NAME=os.getenv("FROM_NAME","NeuroFactory")
def _send(to,subject,html):
    if not SMTP_USER or not SMTP_PASS:
        print(f"[MAIL SIM] → {to} | {subject}"); return True
    try:
        msg=MIMEMultipart("alternative"); msg["Subject"]=subject
        msg["From"]=f"{FROM_NAME} <{SMTP_USER}>"; msg["To"]=to
        msg.attach(MIMEText(html,"html","utf-8"))
        with smtplib.SMTP(SMTP_HOST,SMTP_PORT) as s:
            s.starttls(); s.login(SMTP_USER,SMTP_PASS)
            s.sendmail(SMTP_USER,to,msg.as_string())
        return True
    except Exception as e: print(f"[MAIL ERR] {e}"); return False
def send_welcome_email(to,name,site,lang,base_url):
    if lang=="fr":
        return _send(to,f"Bienvenue sur {site} !",
            f'<div style="font-family:sans-serif;max-width:560px;margin:0 auto">'
            f'<h2 style="color:#6366f1">Bienvenue {name} ! 🎉</h2>'
            f'<p>Votre compte <b>{site}</b> est créé. " + ("Essai gratuit " + str(TRIAL_DAYS) + " jours activé." if TRIAL_DAYS else "Accès immédiat activé.") + "</p>'
            f'<a href="{base_url}/app" style="display:inline-block;margin:16px 0;padding:12px 28px;background:#6366f1;color:#fff;border-radius:50px;text-decoration:none;font-weight:700">Accéder à mon compte</a>'
            f'</div>')
    return _send(to,f"Welcome to {site}!",
        f'<div style="font-family:sans-serif;max-width:560px;margin:0 auto">'
        f'<h2 style="color:#6366f1">Welcome {name}! 🎉</h2>'
        f'<p>Your <b>{site}</b> account is ready. " + (str(TRIAL_DAYS) + "-day free trial activated." if TRIAL_DAYS else "Immediate access activated.") + "</p>'
        f'<a href="{base_url}/app" style="display:inline-block;margin:16px 0;padding:12px 28px;background:#6366f1;color:#fff;border-radius:50px;text-decoration:none;font-weight:700">Access my account</a>'
        f'</div>')
def send_payment_confirmation(to,name,site,amount,currency,lang):
    sym="€" if currency=="eur" else "$"
    if lang=="fr":
        return _send(to,f"{site} — Paiement confirmé ✓",
            f'<div style="font-family:sans-serif;max-width:560px">'
            f'<h2 style="color:#10b981">Paiement confirmé ✓</h2>'
            f'<p>Bonjour {name}, votre abonnement {site} ({amount}{sym}/mois) est actif.</p>'
            f'</div>')
    return _send(to,f"{site} — Payment confirmed ✓",
        f'<div style="font-family:sans-serif;max-width:560px">'
        f'<h2 style="color:#10b981">Payment confirmed ✓</h2>'
        f'<p>Hi {name}, your {site} subscription ({sym}{amount}/mo) is active.</p>'
        f'</div>')
