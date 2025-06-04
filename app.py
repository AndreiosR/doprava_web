from flask import Flask, render_template, request, jsonify
import os
import googlemaps
import csv
import json
from datetime import datetime, timedelta

app = Flask(__name__)

#vloženo při poslední úpravě
API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("❌ GOOGLE_API_KEY není nastaven!")

gmaps = googlemaps.Client(key=API_KEY)

#konec vkladu poslední úpravy

def nacti_mapovani(cesta):
    mapovani = {}
    with open(cesta, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            mapovani[row['obec_nazev']] = {'uzel_nazev': row['uzel_nazev']}
    return mapovani

def nacti_jizdni_rady(cesta):
    with open(cesta, encoding='utf-8') as f:
        return json.load(f)

mapovani = nacti_mapovani('mapovani_obec_uzel.csv')
jizdni_rady = nacti_jizdni_rady('jizdni_rady.json')

def najdi_nejblizsi_spoj(uzel, cas_na_miste):
    spoje = jizdni_rady.get(uzel, [])
    dnes = datetime.today().strftime('%a').lower()[:3]
    for spoj in spoje:
        if 'dny' in spoj and dnes not in spoj['dny']:
            continue
        hod, min = map(int, spoj['odjezd'].split(':'))
        odjezd_cas = datetime.combine(datetime.today(), datetime.min.time()) + timedelta(hours=hod, minutes=min)
        if odjezd_cas >= cas_na_miste:
            return spoj, odjezd_cas
    return None, None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/vypocet', methods=['POST'])
def vypocet():
    data = request.json
    origin = data.get('origin')
    destination = data.get('destination')
    now = datetime.now()

    try:
        vysledek_auto = gmaps.distance_matrix(
            origins=origin,
            destinations=destination,
            mode="driving",
            departure_time=now,
            traffic_model="best_guess"
        )
        cas_auto = vysledek_auto['rows'][0]['elements'][0].get('duration_in_traffic', {}).get('value', None)
        if not cas_auto:
            return jsonify({'vystup': 'Nepodařilo se zjistit čas jízdy autem.'})

        cas_auto_min = cas_auto / 60
        vlakovy_vystup = ""

        if 'Brno' in destination and origin in mapovani:
            uzel = mapovani[origin]['uzel_nazev']
            if origin == uzel:
                cas_k_uzlu_min = 3
            else:
                vysledek_k_uzlu = gmaps.distance_matrix(
                    origins=origin,
                    destinations=uzel,
                    mode="driving",
                    departure_time=now,
                    traffic_model="best_guess"
                )
                cas_do_uzlu = vysledek_k_uzlu['rows'][0]['elements'][0].get('duration_in_traffic', {}).get('value', None)
                cas_k_uzlu_min = (cas_do_uzlu / 60 + 3) if cas_do_uzlu else None

            if cas_k_uzlu_min is not None:
                cas_na_miste = now + timedelta(minutes=cas_k_uzlu_min)
                spoj, odjezd_cas = najdi_nejblizsi_spoj(uzel, cas_na_miste)
                if spoj and odjezd_cas:
                    cas_cekani = (odjezd_cas - cas_na_miste).total_seconds() / 60
                    celkova_doba_spoj = cas_k_uzlu_min + cas_cekani + int(spoj['jizdni_doba_min'])
                    cas_prijezdu = (odjezd_cas + timedelta(minutes=int(spoj['jizdni_doba_min']))).strftime('%H:%M')

                    vlakovy_vystup = (
                        f"Spojení přes uzel {uzel} linkou {spoj['linka']}:\n"
                        f"Odjezd vlaku v {spoj['odjezd']}, příjezd do Brna v {cas_prijezdu}.\n"
                        f"Celková doba: přibližně {round(celkova_doba_spoj)} min."
                    )

                    if celkova_doba_spoj < cas_auto_min:
                        vystup = (
                            f"Nejrychlejší je cesta přes vlakový uzel.\n"
                            f"{vlakovy_vystup}\n\n"
                            f"Alternativa: autem ({round(cas_auto_min)} min)."
                        )
                    else:
                        vystup = (
                            f"Nejrychlejší je cesta autem ({round(cas_auto_min)} min).\n\n"
                            f"Alternativa:\n{vlakovy_vystup}"
                        )
                    return jsonify({'vystup': vystup})

        return jsonify({'vystup': f"Nejrychlejší je cesta autem ({round(cas_auto_min)} min)."})

    except Exception as e:
        return jsonify({'vystup': f"Chyba: {str(e)}"})

# Spusť pomocí: flask run
