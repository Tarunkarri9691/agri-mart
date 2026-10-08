"""Notifications: always stored in-app + pushed over WebSocket; optionally sent as SMS/WhatsApp (Twilio) when configured."""
import logging

from sqlalchemy.orm import Session

from .. import config
from ..models import Notification, User
from ..ws import manager

log = logging.getLogger(__name__)

TEMPLATES = {
    "en": {
        "price_move": ("Price alert", "{crop} price at {market} is expected to move {pct}% to Rs {price}/quintal."),
        "best_option_changed": ("Best option changed", "Your best option for {crop} changed: {name} now gives Rs {net} (was Rs {old})."),
        "offer_received": ("New offer", "New offer on {crop}: Rs {price}/quintal for {qty} quintals."),
        "offer_countered": ("Counter offer", "Counter offer on {crop}: Rs {price}/quintal for {qty} quintals."),
        "offer_accepted": ("Offer accepted", "Your offer on {crop} was accepted."),
        "offer_rejected": ("Offer declined", "Your offer on {crop} was declined."),
        "payment_paid": ("Payment sent", "Buyer marked payment of Rs {amount} as sent for {crop}. Please confirm when received."),
        "deal_completed": ("Deal completed", "Deal completed for {crop}. Please rate the other party."),
        "dispute_opened": ("Dispute opened", "A dispute was opened on your {crop} deal."),
        "dispute_resolved": ("Dispute resolved", "The dispute on your {crop} deal was resolved: {outcome}."),
        "model_drift": ("Model drift", "Price model error is {recent}% vs {base}% at training. Retraining started."),
    },
    "te": {
        "price_move": ("ధర హెచ్చరిక", "{market}లో {crop} ధర {pct}% మారి ₹{price}/క్వింటాల్ అవుతుందని అంచనా."),
        "best_option_changed": ("ఉత్తమ ఎంపిక మారింది", "మీ {crop}కు ఉత్తమ ఎంపిక మారింది: {name} ఇప్పుడు ₹{net} ఇస్తుంది (ముందు ₹{old})."),
        "offer_received": ("కొత్త ఆఫర్", "{crop}పై కొత్త ఆఫర్: {qty} క్వింటాళ్లకు ₹{price}/క్వింటాల్."),
        "offer_countered": ("ప్రతి ఆఫర్", "{crop}పై ప్రతి ఆఫర్: {qty} క్వింటాళ్లకు ₹{price}/క్వింటాల్."),
        "offer_accepted": ("ఆఫర్ అంగీకరించబడింది", "{crop}పై మీ ఆఫర్ అంగీకరించబడింది."),
        "offer_rejected": ("ఆఫర్ తిరస్కరించబడింది", "{crop}పై మీ ఆఫర్ తిరస్కరించబడింది."),
        "payment_paid": ("చెల్లింపు పంపబడింది", "{crop} కోసం కొనుగోలుదారు ₹{amount} చెల్లించినట్లు నమోదు చేశారు. అందిన తర్వాత నిర్ధారించండి."),
        "deal_completed": ("ఒప్పందం పూర్తైంది", "{crop} ఒప్పందం పూర్తైంది. దయచేసి ఇతర పక్షానికి రేటింగ్ ఇవ్వండి."),
        "dispute_opened": ("వివాదం నమోదైంది", "మీ {crop} ఒప్పందంపై వివాదం నమోదైంది."),
        "dispute_resolved": ("వివాదం పరిష్కరించబడింది", "మీ {crop} ఒప్పందంపై వివాదం పరిష్కరించబడింది: {outcome}."),
        "model_drift": ("మోడల్ డ్రిఫ్ట్", "ధర మోడల్ లోపం {recent}% (శిక్షణలో {base}%). తిరిగి శిక్షణ ప్రారంభమైంది."),
    },
}


def _send_external(phone: str, text: str) -> str:
    """Returns delivery status: logged | sent | failed."""
    provider = config.NOTIFY_PROVIDER
    if provider == "console":
        log.info("[notify %s] %s", phone, text)
        return "logged"
    try:
        import httpx
        to = phone if phone.startswith("+") else f"+91{phone}"
        sender = config.TWILIO_FROM
        if provider == "twilio_whatsapp":
            to, sender = f"whatsapp:{to}", sender if sender.startswith("whatsapp:") else f"whatsapp:{sender}"
        r = httpx.post(f"https://api.twilio.com/2010-04-01/Accounts/{config.TWILIO_ACCOUNT_SID}/Messages.json",
                       data={"From": sender, "To": to, "Body": text},
                       auth=(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN), timeout=10)
        return "sent" if r.status_code < 300 else "failed"
    except Exception as exc:
        log.warning("external notification failed: %s", exc)
        return "failed"


def notify(db: Session, user: User, kind: str, **params) -> Notification:
    lang = user.language if user.language in TEMPLATES else "en"
    title, body = TEMPLATES[lang][kind]
    body = body.format(**params)
    delivery = _send_external(user.phone, f"{title}: {body}")   # console provider only logs
    n = Notification(user_id=user.id, kind=kind, title=title, body=body,
                     channel=config.NOTIFY_PROVIDER, delivery=delivery)
    db.add(n)
    db.commit()
    manager.push(user.id, {"type": "notification", "id": n.id, "kind": kind, "title": title, "body": body})
    return n
