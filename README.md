# 🍽️ ClearHub — Gestion de Recettes

> Planifiez vos repas, générez vos listes de courses.

**Type :** SaaS | **Secteur :** lifestyle | **Langue :** FR | **Prix :** 19.99€/mois

---

## 🚀 Déploiement rapide (Render.com)

### Prérequis
- Compte [GitHub](https://github.com) gratuit
- Compte [Render.com](https://render.com) gratuit
- Compte [Stripe](https://stripe.com) pour les paiements

### Étapes

1. **Pusher sur GitHub**
   ```bash
   git init -b main
   git add .
   git commit -m "feat: ClearHub v1.0"
   git remote add origin https://github.com/VOTRE_USERNAME/clearhub.git
   git push -u origin main
   ```

2. **Créer le service sur Render.com**
   - New → Web Service → Connect GitHub
   - Sélectionnez le repo `clearhub`
   - Build command : `pip install -r requirements.txt`
   - Start command : `gunicorn server:app --workers 2 --bind 0.0.0.0:$PORT`

3. **Variables d'environnement** (dans Render → Environment)
   ```
   STRIPE_API_KEY=sk_live_VOTRE_CLE
   STRIPE_PRICE_ID=price_mock_clearhub
   STRIPE_WEBHOOK_SECRET=whsec_XXXXXXXXXX
   JWT_SECRET=<généré automatiquement>
   BASE_URL=https://clearhub.onrender.com
   ```

4. **Stripe Webhook**
   - Dashboard Stripe → Webhooks → Add endpoint
   - URL : `https://clearhub.onrender.com/webhook`
   - Événements : `customer.subscription.*`, `invoice.payment_*`

---

## 📁 Structure des fichiers

```
ClearHub/
├── index.html          # Landing page (SaaS)
├── login.html          # Connexion / Inscription
├── app.html            # Dashboard client
├── 404.html            # Page d'erreur
├── mentions-legales.html # CGV & mentions légales
├── server.py           # API Flask + Auth JWT
├── db.py               # Base de données SQLite
├── webhook.py          # Webhooks Stripe
├── mailer.py           # Envoi d'emails
├── cookies.js          # Bandeau RGPD
├── schema.json         # Schema.org SEO
├── sitemap.xml         # Plan du site
├── robots.txt          # Instructions crawlers
├── meta.json           # Métadonnées NeuroFactory
├── requirements.txt    # Dépendances Python
├── Procfile            # Config Gunicorn
├── render.yaml         # Config Render.com
└── .env.example        # Variables d'environnement
```

---

## 💳 Stripe

- **Lien de paiement :** [https://buy.stripe.com/mock_clearhub](https://buy.stripe.com/mock_clearhub)
- **Price ID :** `price_mock_clearhub`
- **Essai gratuit :** 7 jours
- **Prix :** 19.99€/mois

---

## 🛠️ Développement local

```bash
pip install -r requirements.txt
cp .env.example .env
# Éditez .env avec vos clés
python server.py
# → http://localhost:5000
```

---

## 📊 Générateur

Ce site a été généré par **NeuroFactory v7** — [github.com/neurofactory](https://github.com)

*Type : SaaS | Secteur : lifestyle | Généré le 2026-03-30*
