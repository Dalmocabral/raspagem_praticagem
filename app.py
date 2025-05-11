from flask import Flask, render_template, jsonify, url_for
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import os
from pytz import timezone
from datetime import timedelta

port = int(os.environ.get('PORT', 5000))
app = Flask(__name__)

# Configuração do fuso horário
TZ = timezone('America/Sao_Paulo')

# URL do site da Praticagem-RJ
URL = 'https://www.praticagem-rj.com.br/'

def get_status_barra():
    try:
        response = requests.get(URL)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'lxml')

        baia_div = soup.find('span', string=re.compile(r'BAIA DE GUANABARA', re.I))
        if baia_div:
            parent_td = baia_div.find_parent('td')
            texto = parent_td.get_text(separator=' ').strip()

            if 'BARRA RESTRITA' in texto:
                return {'restrita': True, 'mensagem': texto}
            else:
                return {'restrita': False, 'mensagem': texto}
    except Exception as e:
        print(f"Erro ao verificar status da barra: {e}")

    return {'restrita': False, 'mensagem': 'Não foi possível obter o status da barra.'}

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
                    
                    # Cria datetime com fuso horário
                    hoje = datetime.now(TZ)
                    navio_date = TZ.localize(datetime(hoje.year, mes, dia, hora_part, minuto_part))
                    
                    # Define alertas considerando o fuso horário
                    agora = datetime.now(TZ)
                    alerta = None
                    
                    if manobra == 'ENTRADA':
                        if navio_date - timedelta(hours=1) <= agora < navio_date:
                            alerta = 'entrada_antecipada'  # 🟠 laranja (1h antes)
                        elif agora >= navio_date:
                            alerta = 'entrada_futura'      # 🟢 verde (chegou a hora)
                    elif manobra in ['SAÍDA', 'MUDANÇA']:
                        if navio_date - timedelta(hours=1) <= agora < navio_date:
                            alerta = 'saida_antecipada'    # 🟡 amarelo (1h antes)
                        elif agora >= navio_date:
                            alerta = 'saida_atrasada'      # 🔴 vermelho

                    # Restante do código para IMO, tipo de navio e ícones...
                    imo = None
                    tipo_navio = 'CHEMICAL TANKER'
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
                                    'CONTAINER SHIP', 'GENERAL CARGO SHIP (OPEN HATCH)', 'OFFSHORE SHIP',
                                    'BULK CARRIER', 'CHEMICAL TANKER', 'CARGO SHIP',
                                    'CHEMICAL/PRODUCTS TANKER', 'OFFSHORE SUPPORT VESSEL',
                                    'PRODUCT TANKER', 'TANKER', 'CHEMICAL'
                                ]
                                tipo_navio = None
                                for tipo in tipos_conhecidos:
                                    if tipo in bruto:
                                        tipo_navio = tipo
                                        break

                                if not tipo_navio:
                                    tipo_navio = ' '.join(palavras[-2:])

                    if tipo_navio == 'CONTAINER SHIP':
                        icone = 'https://i.ibb.co/cX1DXDhW/icon-container.png'
                    elif 'CHEMICAL TANKER' in (tipo_navio or ''):
                        icone = 'https://i.ibb.co/T315cM3/TANKER.png'
                    elif 'CARGO SHIP' in (tipo_navio or ''):
                        icone = 'https://i.ibb.co/ymWQg66b/offshoer.png'
                    else:
                        icone = 'https://i.ibb.co/cX1DXDhW/icon-container.png'

                    navios.append({
                        'data': data,
                        'hora': hora,
                        'navio': navio_nome,
                        'calado': calado,
                        'manobra': manobra,
                        'beco': becos,
                        'status': 'futuro' if navio_date > agora else ('hoje' if navio_date.date() == agora.date() else 'passado'),
                        'imo': imo,
                        'tipo_navio': tipo_navio,
                        'icone': icone,
                        'alerta': alerta
                    })

                except Exception as e:
                    print(f"Erro ao processar linha: {e}")
                    continue

    # Eliminar duplicatas
    navios_unicos = []
    vistos = set()

    for n in navios:
        chave = (n['data'], n['hora'], n['navio'], n['manobra'])
        if chave not in vistos:
            navios_unicos.append(n)
            vistos.add(chave)

    return navios_unicos

@app.route('/')
def home():
    agora = datetime.now(TZ)
    ultima_atualizacao = agora.strftime('%d/%m/%Y %H:%M')

    navios = get_navios()
    barra_info = get_status_barra()
    
    return render_template(
        'index.html',
        navios=navios,
        ultima_atualizacao=ultima_atualizacao,
        barra_info=barra_info
    )

@app.route('/api/navios')
def api_navios():
    agora = datetime.now(TZ)
    ultima_atualizacao = agora.strftime('%d/%m/%Y %H:%M')

    navios = get_navios()
    barra_info = get_status_barra()

    return jsonify({
        'navios': navios,
        'ultima_atualizacao': ultima_atualizacao,
        'barra_info': barra_info
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True)