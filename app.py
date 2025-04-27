from flask import Flask, render_template_string, jsonify
import requests
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)

URL = 'https://www.praticagem-rj.com.br/'

def get_navios():
    response = requests.get(URL)
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, 'lxml')
    rows = soup.find_all('tr')
    navios = []

    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 12:
            data_hora = cols[0].text.strip()
            navio = cols[1].text.strip()
            calado = cols[2].text.strip()
            manobra = cols[7].text.strip()
            becos = cols[8].text.strip() if cols[8].text.strip() else cols[11].text.strip()

            if 'TECONTPROLONG' in becos or 'TECONT1' in becos:
                try:
                    data, hora = data_hora.split()
                    # Garantir que a hora tenha sempre 2 dígitos para minutos
                    if ':' not in hora:
                        hora = hora + ':00'
                    elif hora.count(':') == 1 and len(hora.split(':')[1]) == 1:
                        hora = hora.replace(':', ':0')
                    
                    dia, mes = map(int, data.split('/'))
                    hora_part, minuto_part = map(int, hora.split(':'))
                    
                    # Obter data atual
                    hoje = datetime.now()
                    # Criar objeto datetime para o navio (assumindo ano atual)
                    navio_date = datetime(hoje.year, mes, dia, hora_part, minuto_part)
                    
                    # Determinar status
                    if navio_date.date() == hoje.date():
                        status = 'hoje'
                    elif navio_date < hoje:
                        status = 'passado'
                    else:
                        status = 'futuro'
                        
                    navios.append({
                        'data': data,
                        'hora': hora,
                        'navio': navio,
                        'calado': calado,
                        'manobra': manobra,
                        'beco': becos,
                        'status': status
                    })
                except Exception as e:
                    print(f"Erro ao processar linha: {e}")
                    continue

    return navios

@app.route('/')
def home():
    navios = get_navios()
    ultima_atualizacao = datetime.now().strftime('%d/%m/%Y %H:%M')
    
    html = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Navios TECONT</title>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css" rel="stylesheet">
        <style>
            .hoje { background-color: #c8e6c9; }    /* Verde clarinho para hoje */
            .passado { background-color: #ffcdd2; } /* Vermelho clarinho para datas passadas */
            #last-update {
                text-align: center;
                font-style: italic;
                margin: 20px 0;
                padding: 10px;
                background-color: #e3f2fd;
                border-radius: 5px;
                font-size: 18px;
            }
        </style>
    </head>
    <body class="grey lighten-4">
    <div class="container">
        <h3 class="center-align">Navios no TECONTPROLONG / TECONT1</h3>
        
        <div id="last-update">Última atualização: {{ ultima_atualizacao }}</div>
        
        <table class="highlight centered responsive-table z-depth-2">
            <thead class="blue lighten-1 white-text">
                <tr>
                    <th>Data</th>
                    <th>Hora</th>
                    <th>Navio</th>
                    <th>Calado</th>
                    <th>Manobra</th>
                    <th>Beço</th>
                </tr>
            </thead>
            <tbody id="navios-body">
                {% for navio in navios %}
                <tr class="{{ navio.status }}">
                    <td>{{ navio.data }}</td>
                    <td>{{ navio.hora }}</td>
                    <td>{{ navio.navio }}</td>
                    <td>{{ navio.calado }}</td>
                    <td>{{ navio.manobra }}</td>
                    <td>{{ navio.beco }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/js/materialize.min.js"></script>
    <script>
        // Atualiza silenciosamente a cada 10 minutos (600000 milissegundos)
        setInterval(fetchNavios, 600000);
        
        function fetchNavios() {
            fetch('/api/navios')
                .then(response => response.json())
                .then(data => {
                    const tbody = document.getElementById('navios-body');
                    tbody.innerHTML = '';
                    
                    data.navios.forEach(navio => {
                        const row = document.createElement('tr');
                        if (navio.status) row.className = navio.status;
                        
                        row.innerHTML = `
                            <td>${navio.data}</td>
                            <td>${navio.hora}</td>
                            <td>${navio.navio}</td>
                            <td>${navio.calado}</td>
                            <td>${navio.manobra}</td>
                            <td>${navio.beco}</td>
                        `;
                        
                        tbody.appendChild(row);
                    });
                    
                    // Atualiza a informação da última atualização
                    document.getElementById('last-update').textContent = 
                        `Última atualização: ${data.ultima_atualizacao}`;
                });
        }
    </script>
    </body>
    </html>
    """
    return render_template_string(html, navios=navios, ultima_atualizacao=ultima_atualizacao)

@app.route('/api/navios')
def api_navios():
    return jsonify({
        'navios': get_navios(),
        'ultima_atualizacao': datetime.now().strftime('%d/%m/%Y %H:%M')
    })

if __name__ == '__main__':
    app.run(debug=True)