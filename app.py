from flask import Flask, render_template, jsonify, url_for
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import os

port = int(os.environ.get('PORT', 5000))
# Inicializa o aplicativo Flask
app = Flask(__name__)

# URL do site da Praticagem-RJ, que será usado como fonte dos dados
URL = 'https://www.praticagem-rj.com.br/'

# Função que verifica o status atual da barra da Baía de Guanabara
def get_status_barra():
    try:
        # Faz uma requisição à página e define o encoding correto
        response = requests.get(URL)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'lxml')

        # Procura o texto "BAIA DE GUANABARA" para encontrar a linha correspondente
        baia_div = soup.find('span', string=re.compile(r'BAIA DE GUANABARA', re.I))
        if baia_div:
            parent_td = baia_div.find_parent('td')
            texto = parent_td.get_text(separator=' ').strip()

            # Verifica se a barra está restrita ou não com base no texto encontrado
            if 'BARRA RESTRITA' in texto:
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
        # Em caso de erro, imprime no terminal e retorna uma mensagem padrão
        print(f"Erro ao verificar status da barra: {e}")

    return {
        'restrita': False,
        'mensagem': 'Não foi possível obter o status da barra.'
    }

# Função que extrai a lista de navios com informações detalhadas da página HTML
def get_navios():
    response = requests.get(URL)
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, 'lxml')

    # Procura dentro dos scripts pelo bloco 'HINTS_ITEMS' com dados adicionais dos navios
    script_tags = soup.find_all('script')
    hints_items = []
    for script in script_tags:
        if 'var HINTS_ITEMS' in script.text:
            script_text = script.text
            hints_items = re.findall(r"'(<div.*?</div>)'", script_text, re.DOTALL)
            break

    # Procura todas as linhas da tabela de navios
    rows = soup.find_all('tr')
    navios = []

    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 12:
            # Extrai colunas relevantes
            data_hora = cols[0].text.strip()
            navio_nome = cols[1].text.strip()
            calado = cols[2].text.strip()
            manobra = cols[7].text.strip()
            becos = cols[8].text.strip() if cols[8].text.strip() else cols[11].text.strip()

            # Filtra navios que estão atracando ou atracarão no TECONTPROLONG / TECONT1
            if 'TECONTPROLONG' in becos or 'TECONT1' in becos:
                try:
                    # Normaliza e converte a data/hora para datetime
                    data, hora = data_hora.split()
                    if ':' not in hora:
                        hora = hora + ':00'
                    elif hora.count(':') == 1 and len(hora.split(':')[1]) == 1:
                        hora = hora.replace(':', ':0')

                    dia, mes = map(int, data.split('/'))
                    hora_part, minuto_part = map(int, hora.split(':'))
                    hoje = datetime.now()
                    navio_date = datetime(hoje.year, mes, dia, hora_part, minuto_part)

                    # Define o status do navio em relação à data atual
                    status = 'futuro'
                    if navio_date.date() == hoje.date():
                        status = 'hoje'
                    elif navio_date < hoje:
                        status = 'passado'

                    # Tenta encontrar informações adicionais (IMO e tipo) usando o bloco hints_items
                    imo = None
                    tipo_navio = 'SEM INFORMAÇÕES'
                    for hint in hints_items:
                        if navio_nome.upper() in hint.upper():
                            hint_text = BeautifulSoup(hint, 'html.parser').get_text(separator=' ').upper()
                            
                            # Extrai número IMO
                            match_imo = re.search(r'\bNOME\b\s*(\d+)', hint_text)
                            if match_imo:
                                imo = match_imo.group(1)

                            # Extrai tipo de navio com base em padrões conhecidos
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
                                        'PRODUCT TANKER'
                                    ]
                                tipo_navio = None
                                for tipo in tipos_conhecidos:
                                    if tipo in bruto:
                                        tipo_navio = tipo
                                        break

                                if not tipo_navio:
                                    tipo_navio = ' '.join(palavras[-2:])

                    # Define ícone baseado no tipo do navio
                    if tipo_navio == 'CONTAINER SHIP':
                        icone = 'https://i.ibb.co/cX1DXDhW/icon-container.png'
                    elif 'TANKER' in (tipo_navio or ''):
                        icone = 'https://i.ibb.co/cX1DXDhW/icon-container.png'
                    elif 'OFFSHORE' in (tipo_navio or ''):
                        icone = 'https://i.ibb.co/ymWQg66b/offshoer.png'
                    else:
                        icone = 'https://i.ibb.co/cX1DXDhW/icon-container.png'

                    # Adiciona o navio à lista final
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
                    # Se algum dado estiver mal formatado, ignora essa linha
                    print(f"Erro ao processar linha: {e}")
                    continue

    return navios

# Rota principal da aplicação, renderiza o template HTML com os dados obtidos
@app.route('/')
def home():
    navios = get_navios()
    barra_info = get_status_barra()
    ultima_atualizacao = datetime.now().strftime('%d/%m/%Y %H:%M')
    return render_template(
        'index.html',
        navios=navios,
        ultima_atualizacao=ultima_atualizacao,
        barra_info=barra_info
    )

# Rota da API para retornar os dados em formato JSON (útil para outras aplicações)
@app.route('/api/navios')
def api_navios():
    navios = get_navios()
    ultima_atualizacao = datetime.now().strftime('%d/%m/%Y %H:%M')
    return jsonify({
        'navios': navios,
        'ultima_atualizacao': ultima_atualizacao
    })
# Ponto de entrada da aplicação
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)
