import requests
import time
import asyncio
from telegram import Bot

# ✅ Remplace avec ton Token API et Chat ID
TELEGRAM_BOT_TOKEN = "7986693467:AAFfkHe86PZIdBmboJdjaKSWvIOPMZCqZx4"
TELEGRAM_CHAT_ID = "5703410124"

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# ✅ Paramètres de filtrage et d'attente
MIN_MARKET_CAP = 1_000_000  # Market Cap minimum (1M USD)
DELAY_BETWEEN_CHECKS = 600  # Vérifie toutes les 10 minutes
API_SLEEP_TIME = 30  # Attente en cas de surcharge API (CoinGecko)

# ✅ Liste des cryptos déjà envoyées (pour éviter les doublons)
sent_cryptos = {}

def get_new_cryptos():
    """Récupère les nouvelles cryptos listées sur CoinGecko avec gestion des erreurs."""
    url = "https://api.coingecko.com/api/v3/coins/list"
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 429:
            print("⏳ Trop de requêtes ! Pause de 60 secondes pour éviter un blocage API.")
            time.sleep(60)  # Pause pour éviter le blocage
            return []
        
        response.raise_for_status()
        data = response.json()
        time.sleep(API_SLEEP_TIME)  # ✅ Pause pour éviter d'être bloqué par CoinGecko
        return data[-5:]  # Récupère les 5 derniers tokens listés
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur CoinGecko : {e}")
        return []

def analyze_crypto(crypto):
    """Analyse rapide d'une crypto et retourne ses détails."""
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{crypto['id']}"
        response = requests.get(url, timeout=10)

        if response.status_code == 429:
            print("⏳ Trop de requêtes sur analyse ! Pause de 60 secondes...")
            time.sleep(60)
            return None
        
        response.raise_for_status()
        details = response.json()
        
        market_cap = details.get('market_data', {}).get('market_cap', {}).get('usd', 0)
        volume = details.get('market_data', {}).get('total_volume', {}).get('usd', 0)

        if market_cap < MIN_MARKET_CAP:
            return None  # Ignore si le Market Cap est trop bas

        return {
            "Nom": crypto['name'],
            "Symbole": crypto['symbol'],
            "Market Cap": f"{market_cap:,.0f} USD",
            "Volume": f"{volume:,.0f} USD",
            "Lien": f"https://www.coingecko.com/en/coins/{crypto['id']}"
        }
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur analyse {crypto['name']} : {e}")
        return None

async def send_telegram_message(message, crypto_id):
    """Envoie une alerte sur Telegram si la crypto n'a pas déjà été envoyée récemment."""
    global sent_cryptos
    current_time = time.time()

    # Vérifier si la crypto a déjà été envoyée dans les 24h
    if crypto_id in sent_cryptos:
        last_sent_time = sent_cryptos[crypto_id]
        if current_time - last_sent_time < 86400:  # 86400 secondes = 24 heures
            print(f"🚫 Crypto déjà envoyée récemment : {crypto_id}. Ignorée.")
            return

    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print(f"📩 Nouvelle alerte envoyée : {crypto_id}")

        # Stocker l'heure d'envoi de la crypto pour éviter les doublons
        sent_cryptos[crypto_id] = current_time

    except Exception as e:
        print(f"❌ Erreur envoi Telegram : {e}")

def main():
    """Vérifie les nouvelles cryptos en continu et envoie des alertes."""
    while True:
        try:
            print("🔍 Vérification des nouvelles cryptos...")
            new_cryptos = get_new_cryptos()

            if new_cryptos:
                for crypto in new_cryptos:
                    analysis = analyze_crypto(crypto)
                    if analysis:
                        message = (
                            f"🚀 Nouvelle Crypto Détectée : {analysis['Nom']} ({analysis['Symbole']})\n"
                            f"📊 Market Cap : {analysis['Market Cap']}\n"
                            f"💰 Volume : {analysis['Volume']}\n"
                            f"🔗 Lien : {analysis['Lien']}\n"
                            f"🔥 Cette crypto pourrait exploser, ne rate pas cette opportunité !"
                        )
                        asyncio.run(send_telegram_message(message, crypto['id']))
                        time.sleep(5)  # Délai entre les messages

            print(f"⏳ Prochaine vérification dans {DELAY_BETWEEN_CHECKS // 60} minutes...")
            time.sleep(DELAY_BETWEEN_CHECKS)  # Attend avant la prochaine vérification

        except Exception as e:
            print(f"⚠️ Erreur dans la boucle principale : {e}")
            time.sleep(60)  # Attends 1 minute avant de recommencer

if __name__ == "__main__":
    main()
