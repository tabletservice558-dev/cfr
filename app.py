#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Server web RSS pentru clubferoviar.ro
Porneste un mic server local care afiseaza ultimele stiri feroviare
intr-o pagina web, accesibila din browser.

Cum il rulezi in Pydroid 3:
1. Deschide Pydroid 3.
2. In terminalul Pydroid (Pip), instaleaza pachetele necesare:
       pip install flask feedparser requests beautifulsoup4
3. Copiaza acest fisier in Pydroid (ex: rss_server.py) si apasa Run (▶).
4. Deschide browserul telefonului si mergi la:
       http://127.0.0.1:5000
   (sau apasa direct notificarea/linkul care apare in consola Pydroid)
5. Pagina se poate reincarca oricand pentru stiri actualizate, sau
   foloseste butonul "Actualizeaza" de pe pagina.

Optional: daca vrei sa accesezi pagina si de pe alt dispozitiv din
aceeasi retea Wi-Fi, foloseste adresa IP locala a telefonului in loc
de 127.0.0.1 (ex: http://192.168.1.23:5000).
"""

import sys
from datetime import datetime
from xml.sax.saxutils import escape

try:
    from flask import Flask, render_template_string, Response
except ImportError:
    print("Lipseste pachetul 'flask'. Instaleaza-l cu:")
    print("    pip install flask")
    sys.exit(1)

try:
    import feedparser
except ImportError:
    print("Lipseste pachetul 'feedparser'. Instaleaza-l cu:")
    print("    pip install feedparser")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Lipseste pachetul 'requests'. Instaleaza-l cu:")
    print("    pip install requests")
    sys.exit(1)


RSS_URL = "https://clubferoviar.ro/feed/"
SITE_URL = "https://clubferoviar.ro/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Android; Mobile) RSS-Reader/1.0"
}

app = Flask(__name__)

PAGINA_HTML = """
<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stiri Club Feroviar</title>
<style>
  body {
    font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif;
    background: #f4f4f4;
    margin: 0;
    padding: 0;
    color: #222;
  }
  header {
    background: #0a3d62;
    color: #fff;
    padding: 16px;
    text-align: center;
  }
  header h1 { margin: 0; font-size: 1.3em; }
  header p { margin: 4px 0 0; font-size: 0.85em; opacity: 0.85; }
  .continut { max-width: 700px; margin: 0 auto; padding: 12px; }
  .stire {
    background: #fff;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  }
  .stire h2 { margin: 0 0 6px; font-size: 1.05em; }
  .stire h2 a { color: #0a3d62; text-decoration: none; }
  .stire .data { font-size: 0.8em; color: #888; margin-bottom: 6px; }
  .stire .rezumat { font-size: 0.92em; color: #444; }
  .goale { text-align: center; padding: 30px; color: #888; }
  .actualizeaza {
    display: block;
    text-align: center;
    margin: 16px auto;
    padding: 10px 20px;
    background: #0a3d62;
    color: #fff;
    border-radius: 6px;
    text-decoration: none;
    width: fit-content;
  }
  footer { text-align: center; padding: 20px; font-size: 0.75em; color: #999; }
</style>
</head>
<body>
<header>
  <h1>🚆 Stiri Club Feroviar</h1>
  <p>Actualizat: {{ ora }}</p>
</header>
<div class="continut">
  <a class="actualizeaza" href="/">Actualizeaza</a>
  <p style="text-align:center; font-size:0.8em;">
    <a href="/rss.xml">📡 Link feed RSS (pentru cititoare RSS)</a>
  </p>
  {% if stiri %}
    {% for s in stiri %}
    <div class="stire">
      <h2><a href="{{ s.link }}" target="_blank">{{ s.titlu }}</a></h2>
      {% if s.data %}<div class="data">{{ s.data }}</div>{% endif %}
      {% if s.rezumat %}<div class="rezumat">{{ s.rezumat }}</div>{% endif %}
    </div>
    {% endfor %}
  {% else %}
    <div class="goale">Nu am putut incarca stirile momentan.</div>
  {% endif %}
</div>
<footer>Sursa: clubferoviar.ro</footer>
</body>
</html>
"""


def ia_stiri_din_rss(numar_stiri=20):
    raspuns = requests.get(RSS_URL, headers=HEADERS, timeout=15)
    raspuns.raise_for_status()
    feed = feedparser.parse(raspuns.content)

    stiri = []
    for articol in feed.entries[:numar_stiri]:
        rezumat = articol.get("summary", "")
        rezumat = rezumat.replace("\n", " ").strip()
        if len(rezumat) > 220:
            rezumat = rezumat[:220].rstrip() + "..."
        stiri.append({
            "titlu": articol.get("title", "Fara titlu"),
            "link": articol.get("link", "#"),
            "data": articol.get("published", ""),
            "rezumat": rezumat,
        })
    return stiri


def ia_stiri_din_pagina(numar_stiri=20):
    from bs4 import BeautifulSoup

    raspuns = requests.get(SITE_URL, headers=HEADERS, timeout=15)
    raspuns.raise_for_status()
    soup = BeautifulSoup(raspuns.content, "html.parser")

    stiri = []
    vazute = set()
    for tag in soup.select("h2 a, h3 a, .entry-title a"):
        titlu = tag.get_text(strip=True)
        link = tag.get("href", "")
        if titlu and link.startswith("http") and link not in vazute:
            vazute.add(link)
            stiri.append({"titlu": titlu, "link": link, "data": "", "rezumat": ""})
        if len(stiri) >= numar_stiri:
            break
    return stiri


def obtine_stiri():
    try:
        stiri = ia_stiri_din_rss()
        if stiri:
            return stiri
    except Exception as e:
        print(f"RSS indisponibil ({e}), incerc extragerea din pagina...")

    try:
        return ia_stiri_din_pagina()
    except Exception as e:
        print(f"Nici extragerea din pagina nu a functionat: {e}")
        return []


@app.route("/")
def index():
    stiri = obtine_stiri()
    ora = datetime.now().strftime("%d.%m.%Y %H:%M")
    return render_template_string(PAGINA_HTML, stiri=stiri, ora=ora)


import os
import socket


def ia_ip_local():
    """Incearca sa afle adresa IP locala a telefonului in retea (nu 127.0.0.1)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None

# Unde se salveaza fisierul .xml. Pe Android, in Pydroid, folderul curent
# de lucru e de obicei accesibil; daca vrei sa il vezi si in Fisiere/
# Descarcari, schimba calea de mai jos cu ceva de tipul:
#   "/storage/emulated/0/Download/rss_clubferoviar.xml"
# (ai nevoie ca Pydroid sa aiba permisiune de stocare, activata din
# Setari Android > Aplicatii > Pydroid 3 > Permisiuni > Fisiere)
CALE_FISIER_XML = "rss_clubferoviar.xml"


def genereaza_xml(stiri):
    items_xml = []
    for s in stiri:
        items_xml.append(f"""
    <item>
      <title>{escape(s['titlu'])}</title>
      <link>{escape(s['link'])}</link>
      <guid>{escape(s['link'])}</guid>
      {f"<pubDate>{escape(s['data'])}</pubDate>" if s['data'] else ""}
      <description>{escape(s['rezumat'])}</description>
    </item>""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Club Feroviar - Stiri</title>
    <link>{escape(SITE_URL)}</link>
    <description>Ultimele stiri feroviare, preluate de pe clubferoviar.ro</description>
    <language>ro-ro</language>
    <lastBuildDate>{datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')}</lastBuildDate>
    {''.join(items_xml)}
  </channel>
</rss>"""


def salveaza_xml(xml, cale=CALE_FISIER_XML):
    try:
        with open(cale, "w", encoding="utf-8") as f:
            f.write(xml)
        print(f"Fisier XML salvat la: {os.path.abspath(cale)}")
        return True
    except Exception as e:
        print(f"Nu am putut salva fisierul XML: {e}")
        return False


@app.route("/rss.xml")
@app.route("/feed")
def rss_xml():
    """Genereaza un feed RSS 2.0 valid, ce poate fi adaugat direct
    intr-un cititor RSS (Feedly, Reeder, NetNewsWire, Podcast Addict,
    Inoreader etc.), si il salveaza si local ca fisier .xml."""
    stiri = obtine_stiri()
    xml = genereaza_xml(stiri)
    salveaza_xml(xml)
    return Response(xml, mimetype="application/rss+xml")


# Token-ul tau gratuit de pe https://dashboard.ngrok.com/get-started/your-authtoken
# Lasa gol ("") daca vrei ca serverul sa mearga doar in reteaua locala.
NGROK_AUTHTOKEN = "3GeCVIThNZ4Nie7yYDmWLvUiZwo_3RCzyrWp6CvwMEJbzvjAP"

# Domeniu static gratuit (optional). Il obtii din dashboard ngrok:
# Universal Gateway -> Domains -> Create domain (ex: "ceva-random.ngrok-free.app")
# Daca il completezi aici, URL-ul public NU se mai schimba la fiecare pornire.
NGROK_DOMAIN = "portable-dispersed-appointee.ngrok-free.dev"


def porneste_tunel_public(port=5000):
    """Porneste un tunel ngrok, ca serverul sa fie accesibil de pe internet,
    nu doar din reteaua Wi-Fi locala. Returneaza URL-ul public sau None."""
    if not NGROK_AUTHTOKEN:
        print("NGROK_AUTHTOKEN nu e setat -> serverul ramane accesibil doar local.")
        print("Pentru acces de pe internet, seteaza NGROK_AUTHTOKEN in script.")
        return None

    try:
        from pyngrok import ngrok
    except ImportError:
        print("Lipseste pachetul 'pyngrok'. Instaleaza-l cu:")
        print("    pip install pyngrok")
        return None

    try:
        ngrok.set_auth_token(NGROK_AUTHTOKEN)
        if NGROK_DOMAIN:
            tunel = ngrok.connect(port, "http", domain=NGROK_DOMAIN)
        else:
            tunel = ngrok.connect(port, "http")
        return tunel.public_url
    except Exception as e:
        print(f"Nu am putut porni tunelul public: {e}")
        return None


if __name__ == "__main__":
    print("Pornesc serverul...")
    print("Generez fisierul XML initial...")
    salveaza_xml(genereaza_xml(obtine_stiri()))

    ip_local = ia_ip_local()
    print("\n" + "=" * 50)
    if ip_local:
        print(f"Adresa IP a telefonului in retea: {ip_local}")
        print(f"Foloseste asta in TT-RSS ca URL de feed:")
        print(f"   http://{ip_local}:5000/rss.xml")
    else:
        print("Nu am putut detecta automat IP-ul local.")
        print("Cauta-l manual in Setari > Wi-Fi > (numele retelei) > detalii IP.")
    print("=" * 50 + "\n")

    print("Pagina web (doar pe acest telefon): http://127.0.0.1:5000")
    print("Feed RSS (doar pe acest telefon):   http://127.0.0.1:5000/rss.xml")

    url_public = porneste_tunel_public(5000)
    if url_public:
        print("\n" + "=" * 50)
        print(f"URL public (functioneaza de oriunde):")
        print(f"   {url_public}/rss.xml")
        print("Foloseste acest link in TT-RSS de pe orice retea/device.")
        print("=" * 50 + "\n")

    app.run(host="0.0.0.0", port=5000, debug=False)