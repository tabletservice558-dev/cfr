#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Server web RSS pentru clubferoviar.ro - versiune pentru hosting (Render.com)

Acest fisier e identic ca functionalitate cu varianta pentru Pydroid, dar
fara partea de tunel ngrok si detectare IP local (nu sunt necesare cand
aplicatia ruleaza pe un server din cloud cu URL public permanent).
"""

from datetime import datetime
from xml.sax.saxutils import escape

from flask import Flask, render_template_string, Response
import feedparser
import requests

RSS_URL = "https://clubferoviar.ro/feed/"
SITE_URL = "https://clubferoviar.ro/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible) RSS-Reader/1.0"
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
  .stire .rezumat { font-size: 0.92em; color: #444; white-space: pre-line; }
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
      {% if s.continut %}<div class="rezumat">{{ s.continut }}</div>{% endif %}
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


def ia_continut_complet(link):
    """Deschide pagina articolului si extrage textul complet al stirii
    (nu doar rezumatul din RSS)."""
    from bs4 import BeautifulSoup

    raspuns = requests.get(link, headers=HEADERS, timeout=15)
    raspuns.raise_for_status()
    soup = BeautifulSoup(raspuns.content, "html.parser")

    # WordPress foloseste de obicei una din aceste clase pentru corpul articolului
    zona = (
        soup.select_one(".entry-content")
        or soup.select_one(".post-content")
        or soup.select_one("article .content")
        or soup.select_one("article")
    )
    if not zona:
        return ""

    # scoate scripturi, reclame, related-posts etc.
    for tag in zona.select("script, style, .sharedaddy, .jp-relatedposts, .related-posts"):
        tag.decompose()

    paragrafe = [p.get_text(" ", strip=True) for p in zona.find_all(["p", "h2", "h3", "li"])]
    paragrafe = [p for p in paragrafe if p]
    return "\n\n".join(paragrafe)


def ia_stiri_din_rss():
    raspuns = requests.get(RSS_URL, headers=HEADERS, timeout=15)
    raspuns.raise_for_status()
    feed = feedparser.parse(raspuns.content)

    stiri = []
    for articol in feed.entries:
        link = articol.get("link", "#")

        rezumat = articol.get("summary", "")
        rezumat = rezumat.replace("\n", " ").strip()

        try:
            continut = ia_continut_complet(link)
        except Exception as e:
            print(f"Nu am putut lua continutul complet pentru {link}: {e}")
            continut = ""

        stiri.append({
            "titlu": articol.get("title", "Fara titlu"),
            "link": link,
            "data": articol.get("published", ""),
            "rezumat": rezumat,
            "continut": continut or rezumat,
        })
    return stiri


def ia_stiri_din_pagina():
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
            try:
                continut = ia_continut_complet(link)
            except Exception as e:
                print(f"Nu am putut lua continutul complet pentru {link}: {e}")
                continut = ""
            stiri.append({
                "titlu": titlu,
                "link": link,
                "data": "",
                "rezumat": "",
                "continut": continut,
            })
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


def genereaza_xml(stiri):
    items_xml = []
    for s in stiri:
        items_xml.append(f"""
    <item>
      <title>{escape(s['titlu'])}</title>
      <link>{escape(s['link'])}</link>
      <guid>{escape(s['link'])}</guid>
      {f"<pubDate>{escape(s['data'])}</pubDate>" if s['data'] else ""}
      <description>{escape(s['continut'])}</description>
      <content:encoded><![CDATA[{s['continut']}]]></content:encoded>
    </item>""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Club Feroviar - Stiri</title>
    <link>{escape(SITE_URL)}</link>
    <description>Ultimele stiri feroviare, preluate de pe clubferoviar.ro</description>
    <language>ro-ro</language>
    <lastBuildDate>{datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')}</lastBuildDate>
    {''.join(items_xml)}
  </channel>
</rss>"""


@app.route("/")
def index():
    stiri = obtine_stiri()
    ora = datetime.now().strftime("%d.%m.%Y %H:%M")
    return render_template_string(PAGINA_HTML, stiri=stiri, ora=ora)


@app.route("/rss.xml")
@app.route("/feed")
def rss_xml():
    stiri = obtine_stiri()
    xml = genereaza_xml(stiri)
    return Response(xml, mimetype="application/rss+xml")


if __name__ == "__main__":
    # Foloseste asta doar pentru testare locala pe calculator.
    # Pe Render, aplicatia e pornita de gunicorn (vezi Procfile), nu de aici.
    app.run(host="0.0.0.0", port=5000, debug=False)
