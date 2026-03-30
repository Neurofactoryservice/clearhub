import json, os
from datetime import datetime, timezone
from flask import jsonify
from db import get_db

COMMISSION_RATE = float(os.getenv("COMMISSION_RATE","0.10"))

def handle(request, stripe, webhook_secret):
    payload=request.get_data(); sig=request.headers.get("Stripe-Signature","")
    try:
        event=stripe.Webhook.construct_event(payload,sig,webhook_secret) if webhook_secret else json.loads(payload)
    except Exception as e: return jsonify({"error":str(e)}),400
    db=get_db(); now=datetime.now(timezone.utc).isoformat()
    t=event.get("type",""); obj=event.get("data",{}).get("object",{})

    # ── Abonnements SaaS ─────────────────────────────────────────
    if t=="customer.subscription.created":
        new_stat=obj.get("status","active")
        db.execute("UPDATE users SET subscription_status=?,stripe_sub_id=? WHERE stripe_customer_id=?",(new_stat,obj.get("id",""),obj.get("customer","")))
        # Enregistrer dans le registre central cross-sell
        try:
            u3=db.execute("SELECT email FROM users WHERE stripe_customer_id=?",(obj.get("customer",""),)).fetchone()
            if u3:
                import json as _j, os as _os
                sub_p=_os.path.join(_os.path.dirname(__file__),"data","cross_subscribers.json")
                csubs=_j.loads(open(sub_p).read()) if _os.path.exists(sub_p) else {}
                email3=u3["email"]; subs3=csubs.get(email3,[])
                ex3=[s for s in subs3 if s["site"]==SITE_NAME]
                if ex3: ex3[0]["status"]=new_stat; ex3[0]["updated_at"]=now
                else: subs3.append({"site":SITE_NAME,"sector":SECTOR,"status":new_stat,"price":PRICE,"lang":LANG,"subscribed_at":now,"updated_at":now})
                csubs[email3]=subs3
                open(sub_p,"w").write(_j.dumps(csubs))
        except: pass
    elif t=="customer.subscription.updated":
        new_status = obj.get("status","inactive")
        db.execute("UPDATE users SET subscription_status=? WHERE stripe_sub_id=?",(new_status,obj.get("id","")))
        # Mettre à jour le registre central cross-sell
        try:
            u2=db.execute("SELECT email FROM users WHERE stripe_sub_id=?",(obj.get("id",""),)).fetchone()
            if u2:
                import json as _j, os as _os
                sub_p=_os.path.join(_os.path.dirname(__file__),"data","cross_subscribers.json")
                csubs=_j.loads(open(sub_p).read()) if _os.path.exists(sub_p) else {}
                email2=u2["email"]; subs2=csubs.get(email2,[])
                ex=[s for s in subs2 if s["site"]==SITE_NAME]
                if ex: ex[0]["status"]=new_status; ex[0]["updated_at"]=now
                else: subs2.append({"site":SITE_NAME,"sector":SECTOR,"status":new_status,"price":PRICE,"lang":LANG,"subscribed_at":now,"updated_at":now})
                csubs[email2]=subs2
                open(sub_p,"w").write(_j.dumps(csubs))
        except: pass
    elif t in ("customer.subscription.deleted","customer.subscription.canceled"):
        db.execute("UPDATE users SET subscription_status='canceled' WHERE stripe_sub_id=?",(obj.get("id",""),))
    elif t=="invoice.payment_failed":
        db.execute("UPDATE users SET subscription_status='past_due' WHERE stripe_customer_id=?",(obj.get("customer",""),))
    elif t=="invoice.payment_succeeded":
        cid=obj.get("customer",""); amt=obj.get("amount_paid",0)/100
        u=db.execute("SELECT id FROM users WHERE stripe_customer_id=?",(cid,)).fetchone()
        if u: db.execute("INSERT INTO invoices (user_id,amount,currency,status,stripe_id,created_at) VALUES (?,?,?,?,?,?)",(u["id"],amt,obj.get("currency","eur"),"paid",obj.get("id",""),now))
        db.execute("UPDATE users SET subscription_status='active' WHERE stripe_customer_id=?",(cid,))

    # ── Transactions Marketplace (P2P / Location) ────────────────
    elif t=="payment_intent.amount_capturable_updated":
        # Fonds autorises et sequestres sur la carte acheteur
        pi_id2=obj.get("id",""); meta2=obj.get("metadata",{})
        bid2=meta2.get("booking_id")
        if bid2:
            db.execute("UPDATE bookings SET status='held',stripe_pi_id=? WHERE id=? AND status='pending'",[pi_id2,bid2])
            db.commit()
    elif t=="payment_intent.succeeded":
        # Paiement d'une réservation confirmé par Stripe
        pi_id    = obj.get("id","")
        meta     = obj.get("metadata",{})
        booking_id = meta.get("booking_id")
        if booking_id:
            amt_cts  = obj.get("amount",0)
            fee_cts  = obj.get("application_fee_amount",0) or int(amt_cts * COMMISSION_RATE)
            amount   = amt_cts / 100
            commission = fee_cts / 100
            net      = amount - commission
            # Confirmer la réservation
            db.execute("UPDATE bookings SET status='confirmed',stripe_pi_id=? WHERE id=?",(pi_id,booking_id))
            # Mettre à jour les stats de commission
            db.execute("INSERT OR IGNORE INTO platform_stats (key,value) VALUES ('total_commission',0)")
            db.execute("UPDATE platform_stats SET value=value+? WHERE key='total_commission'",(commission,))
            db.execute("INSERT OR IGNORE INTO platform_stats (key,value) VALUES ('total_transactions',0)")
            db.execute("UPDATE platform_stats SET value=value+1 WHERE key='total_transactions'")
            db.execute("INSERT OR IGNORE INTO platform_stats (key,value) VALUES ('total_gmv',0)")
            db.execute("UPDATE platform_stats SET value=value+? WHERE key='total_gmv'",(amount,))

    elif t=="payment_intent.payment_failed":
        # Échec de paiement — marquer la réservation comme échouée
        pi_id = obj.get("id","")
        meta  = obj.get("metadata",{})
        booking_id = meta.get("booking_id")
        if booking_id:
            db.execute("UPDATE bookings SET status='failed',stripe_pi_id=? WHERE id=?",(pi_id,booking_id))

    elif t=="account.updated":
        # Stripe Connect — mise à jour d'un compte prestataire
        acct_id = obj.get("id","")
        details_submitted = obj.get("details_submitted",False)
        if acct_id and details_submitted:
            db.execute("UPDATE users SET stripe_account_id=? WHERE stripe_account_id=?",(acct_id,acct_id))

    elif t=="transfer.created":
        # Virement au prestataire créé (Stripe Connect)
        acct_id = obj.get("destination","")
        amount  = obj.get("amount",0)/100
        if acct_id:
            db.execute("UPDATE users SET total_earned=COALESCE(total_earned,0)+? WHERE stripe_account_id=?",(amount,acct_id))

    db.commit()
    return jsonify({"received":True})
