from flask import Flask, render_template, jsonify
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

app = Flask(__name__)

URL = 'https://www.praticagem-rj.com.br/'

def get_navios():
    response = requests.get(URL)
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, 'lxml')

    script_tags = soup.find_all('script')
    hints_items = []
    for script in script_tags:
        if 'var HINTS_ITEMS' in script.text:
            script_text = script.text
            hints_items = re.findall(r"'(<div.*?</div>)'", script_text, re.DOTALL)
            break

    rows = soup.find_all('tr')
    navios = []

    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 12:
            data_hora = cols[0].text.strip()
            navio_nome = cols[1].text.strip()
            calado = cols[2].text.strip()
            manobra = cols[7].text.strip()
            becos = cols[8].text.strip() if cols[8].text.strip() else cols[11].text.strip()

            if 'TECONTPROLONG' in becos or 'TECONT1' in becos:
                try:
                    data, hora = data_hora.split()
                    if ':' not in hora:
                        hora = hora + ':00'
                    elif hora.count(':') == 1 and len(hora.split(':')[1]) == 1:
                        hora = hora.replace(':', ':0')

                    dia, mes = map(int, data.split('/'))
                    hora_part, minuto_part = map(int, hora.split(':'))

                    hoje = datetime.now()
                    navio_date = datetime(hoje.year, mes, dia, hora_part, minuto_part)

                    status = 'futuro'
                    if navio_date.date() == hoje.date():
                        status = 'hoje'
                    elif navio_date < hoje:
                        status = 'passado'

                    imo = None
                    tipo_navio = None

                    for hint in hints_items:
                        if navio_nome.upper() in hint.upper():
                            hint_text = BeautifulSoup(hint, 'html.parser').get_text(separator=' ').upper()
                            match_imo = re.search(r'\bNOME\b\s*(\d+)', hint_text)
                            if match_imo:
                                imo = match_imo.group(1)

                            match_tipo = re.search(
                                r'TIPO DE NAVIO\s+([A-Z ,\'\.\-\(\)]+?)\s+(?:GT|DWT|LOA|BOCA)',
                                hint_text
                            )
                            if match_tipo:
                                bruto = match_tipo.group(1).strip()
                                palavras = bruto.split()

                                tipos_conhecidos = [
                                    'CONTAINER SHIP', 'GENERAL CARGO SHIP', 'OFFSHORE SHIP', 'TANKER',
                                    'RO-RO SHIP', 'BULK CARRIER', 'CRUISE SHIP', 'LNG CARRIER',
                                    'OIL TANKER', 'CHEMICAL TANKER', 'CARGO SHIP'
                                ]

                                tipo_navio = None
                                for tipo in tipos_conhecidos:
                                    if tipo in bruto:
                                        tipo_navio = tipo
                                        break

                                if not tipo_navio:
                                    tipo_navio = ' '.join(palavras[-2:])

                    # Define o caminho do ícone com base no tipo
                    if tipo_navio == 'CONTAINER SHIP':
                        icone = 'icons/icon_container.png'
                    elif 'TANKER' in (tipo_navio or ''):
                        icone = 'icons/icon_tanker.png'
                    elif 'OFFSHORE' in (tipo_navio or ''):
                        icone = 'icons/icon_offshore.png'
                    else:
                        icone = None

                    navios.append({
                        'data': data,
                        'hora': hora,
                        'navio': navio_nome,
                        'calado': calado,
                        'manobra': manobra,
                        'beco': becos,
                        'status': status,
                        'imo': imo,
                        'tipo_navio': tipo_navio,
                        'icone': icone
                    })

                except Exception as e:
                    print(f"Erro ao processar linha: {e}")
                    continue

    return navios

@app.route('/')
def home():
    navios = get_navios()
    ultima_atualizacao = datetime.now().strftime('%d/%m/%Y %H:%M')
    return render_template('index.html', navios=navios, ultima_atualizacao=ultima_atualizacao)

@app.route('/api/navios')
def api_navios():
    navios = get_navios()
    return jsonify({'navios': navios})

if __name__ == '__main__':
    app.run(debug=True)
