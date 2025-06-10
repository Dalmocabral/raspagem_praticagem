from flask import Flask, render_template, jsonify, url_for
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import os
from pytz import timezone
from datetime import timedelta


port = int(os.environ.get("PORT", 5000))
app = Flask(__name__)

URL = 'https://www.praticagem-rj.com.br/'

def get_status_barra():
    try:
        response = requests.get(URL)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'lxml')

        # Encontrar a <span> que contém "BAIA DE GUANABARA"
        baia_span = soup.find('span', string=re.compile(r'BAIA DE GUANABARA', re.I))
        if baia_span:
            # Subir para a <tr> que contém tudo
            tr = baia_span.find_parent('tr')
            if tr:
                # Buscar o <div> com o status da barra
                barra_div = tr.find('div', id=re.compile(r'pnlBarra\d+'))
                if barra_div:
                    texto = barra_div.get_text(separator=' ', strip=True)

                    if 'BARRA RESTRITA' in texto.upper():
                        return {
                            'restrita': True,
                            'mensagem': texto
                        }
                    else:
                        return {
                            'restrita': False,
                            'mensagem': texto
                        }

    except Exception as e:
        print(f"Erro ao verificar status da barra: {e}")

    return {
        'restrita': False,
        'mensagem': 'Não foi possível obter o status da barra.'
    }

def get_navios():
    response = requests.get(URL)
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, 'lxml')

    navios = []

    # Encontrar a tabela principal de manobras
    main_table = soup.find('table', class_='tbManobrasArea')
    if not main_table:
        print("Tabela principal de manobras não encontrada.")
        return []

    rows = main_table.find_all('tr', id=re.compile(r'rptAreas_ctl\d+_rptManobrasArea_ctl\d+_trManobraArea'))

    for row in rows:
        cols = row.find_all('td', class_='tdManobraArea')
        if len(cols) >= 12: # Verificar se tem colunas suficientes
            try:
                data_hora = cols[0].get_text(strip=True)
                
                navio_nome_div = cols[1].find('div', class_='tooltipDiv')
                navio_nome = navio_nome_div.contents[0].strip() if navio_nome_div else 'N/A'

                calado = cols[2].get_text(strip=True)
                manobra = cols[7].get_text(strip=True)
                becos = cols[8].get_text(strip=True) if cols[8].get_text(strip=True) else cols[11].get_text(strip=True)

                # FILTRO ADICIONADO AQUI
                if 'TECONTPROLONG' not in becos and 'TECONT1' not in becos:
                    continue # Pula para a próxima linha se não corresponder ao filtro

                imo = None
                tipo_navio = None
                tooltip_escondida = cols[1].find('div', class_='tooltipDivEscondida')
                if tooltip_escondida:
                    imo_span = tooltip_escondida.find('span', id='ST_NR_IMO')
                    if imo_span:
                        imo = imo_span.get_text(strip=True)

                    tipo_navio_span = tooltip_escondida.find('span', id='DS_TIPO_NAVIO')
                    if tipo_navio_span:
                        # LINHA ALTERADA AQUI PARA REMOVER O TEXTO ENTRE PARÊNTESES
                        tipo_navio = tipo_navio_span.get_text(strip=True).split('(')[0].strip()

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

                alerta = None
                agora = datetime.now()
                if manobra == 'E': # ENTRADA
                    if navio_date - timedelta(hours=1) <= agora < navio_date:
                        alerta = 'entrada_antecipada'
                    elif agora >= navio_date:
                        alerta = 'entrada_futura'
                elif manobra in ['S', 'M']: # SAÍDA, MUDANÇA
                    if navio_date - timedelta(hours=1) <= agora < navio_date:
                        alerta = 'saida_futura'
                    elif agora >= navio_date:
                        alerta = 'saida_atrasada'

                icone = 'https://i.ibb.co/cX1DXDhW/icon-container.png'
                if tipo_navio:
                    if 'CONTAINER SHIP' in tipo_navio.upper():
                        icone = 'https://i.ibb.co/cX1DXDhW/icon-container.png'
                    elif 'CHEMICAL TANKER' in tipo_navio.upper() or 'PRODUCT TANKER' in tipo_navio.upper() or 'TANKER' in tipo_navio.upper():
                        icone = 'https://i.ibb.co/T315cM3/TANKER.png'
                    elif 'CARGO SHIP' in tipo_navio.upper() or 'OFFSHORE SHIP' in tipo_navio.upper() or 'OFFSHORE SUPPORT VESSEL' in tipo_navio.upper():
                        icone = 'https://i.ibb.co/ymWQg66b/offshoer.png'
                    elif 'SUPPLY SHIP' in tipo_navio.upper():
                        icone = 'https://i.ibb.co/ccHFRkVD/suplay-ship.png'

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
                    'icone': icone,
                    'alerta': alerta
                })

            except Exception as e:
                print(f"Erro ao processar linha do navio: {e}")
                continue

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
    tz = timezone('America/Sao_Paulo')
    agora = datetime.now(tz)
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
    tz = timezone('America/Sao_Paulo')
    agora = datetime.now(tz)
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

