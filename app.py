# Importa os módulos necessários para a aplicação Flask, requisições HTTP, parsing de HTML, manipulação de datas e variáveis de ambiente.
from flask import Flask, render_template, jsonify, url_for, request
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import os
from pytz import timezone

# Define a porta do servidor. Tenta obter da variável de ambiente 'PORT', caso contrário, usa 5000 como padrão.
port = int(os.environ.get("PORT", 5000))
# Inicializa a aplicação Flask.
app = Flask(__name__)

# URL base do site de onde os dados serão extraídos (scraping).
URL = "https://www.praticagem-rj.com.br/"

# Lista de berços específicos que devem ser considerados ao filtrar por "Todos os Terminais".
# Estes berços são de interesse particular para a lógica de negócio.
BERCOS_INCLUIR_TODOS = {
    'TECONTPROLONG', 'TECONT1', 'TECONT2', 'TECONT3', 'TECONT4', 'TECONT5', 
    'MANGUINHOS', 'PG-1'
}

# Função para obter o status da barra da Baía de Guanabara.
# Retorna se a barra está restrita e uma mensagem descritiva.
def get_status_barra():
    try:
        # Faz uma requisição HTTP GET para a URL base.
        response = requests.get(URL)
        # Define a codificação da resposta com base na detecção aparente.
        response.encoding = response.apparent_encoding
        # Cria um objeto BeautifulSoup para parsear o conteúdo HTML da resposta.
        soup = BeautifulSoup(response.text, "lxml")

        # Procura por um elemento <span> que contenha o texto "BAIA DE GUANABARA" (case-insensitive).
        baia_span = soup.find("span", string=re.compile(r"BAIA DE GUANABARA", re.I))
        # Se o <span> for encontrado:
        if baia_span:
            # Encontra o elemento <tr> pai do <span>.
            tr = baia_span.find_parent("tr")
            # Se o <tr> for encontrado:
            if tr:
                # Procura por um <div> dentro do <tr> com um ID que comece com "pnlBarra" seguido de dígitos.
                barra_div = tr.find("div", id=re.compile(r"pnlBarra\d+"))
                # Se o <div> for encontrado:
                if barra_div:
                    # Extrai o texto do <div>, removendo espaços extras e unindo com um único espaço.
                    texto = barra_div.get_text(separator=" ", strip=True)

                    # Verifica se o texto contém a frase "BARRA RESTRITA" (case-insensitive).
                    if "BARRA RESTRITA" in texto.upper():
                        # Retorna um dicionário indicando que a barra está restrita e a mensagem.
                        return {"restrita": True, "mensagem": texto}
                    
                     # Caso de barra restrita
                    elif "BARRA FECHADA"in texto.upper():
                        return {"restrita": True, "fechada": False, "mensagem": texto}
                    # Caso normal
                    else:
                        # Retorna um dicionário indicando que a barra não está restrita e a mensagem.
                        return {"restrita": False, "mensagem": texto}
                    
    except Exception as e:
        # Em caso de erro durante o processo, imprime uma mensagem de erro.
        print(f"Erro ao verificar status da barra: {e}")
    # Se algo falhar ou não for encontrado, retorna um status padrão de não restrita com uma mensagem de erro.
    return {"restrita": False, "mensagem": "Não foi possível obter o status da barra."}


# Função para obter todas as manobras de navios da página.
# Retorna uma lista de dicionários, cada um representando uma manobra.
def get_all_navios_manobras():
    # Faz uma requisição HTTP GET para a URL base.
    response = requests.get(URL)
    # Define a codificação da resposta.
    response.encoding = response.apparent_encoding
    # Cria um objeto BeautifulSoup para parsear o HTML.
    soup = BeautifulSoup(response.text, "lxml")

    # Lista para armazenar os dados das manobras de navios.
    navios_manobras = []

    # Encontra a tabela principal que contém as manobras.
    main_table = soup.find("table", class_="tbManobrasArea")
    # Se a tabela principal não for encontrada, imprime um erro e retorna uma lista vazia.
    if not main_table:
        print("Tabela principal de manobras não encontrada.")
        return []
    # Encontra todas as linhas (<tr>) da tabela que representam manobras, usando um padrão de ID.
    rows = main_table.find_all(
        "tr", id=re.compile(r"rptAreas_ctl\d+_rptManobrasArea_ctl\d+_trManobraArea")
    )

    # Itera sobre cada linha de manobra encontrada.
    for row in rows:
        # Encontra todas as células (<td>) com a classe "tdManobraArea" dentro da linha.
        cols = row.find_all("td", class_="tdManobraArea")
        # Garante que a linha tenha pelo menos 12 colunas, que são as esperadas para extração de dados.
        if len(cols) >= 12:
            try:
                # Extrai a data e hora da primeira coluna.
                data_hora = cols[0].get_text(strip=True)

                # Extrai o nome do navio da segunda coluna, procurando por um <div> com a classe "tooltipDiv".
                navio_nome_div = cols[1].find("div", class_="tooltipDiv")
                navio_nome = (
                    navio_nome_div.contents[0].strip() if navio_nome_div else "N/A"
                )

                # Extrai o calado da terceira coluna.
                calado = cols[2].get_text(strip=True)
                # Extrai o tipo de manobra (E, S, M) da oitava coluna.
                manobra = cols[7].get_text(strip=True)
                # Extrai o berço da nona coluna, ou da décima segunda se a nona estiver vazia.
                becos = (
                    cols[8].get_text(strip=True)
                    if cols[8].get_text(strip=True)
                    else cols[11].get_text(strip=True)
                )

                # Verifica se o navio está em algum dos berços definidos em BERCOS_INCLUIR_TODOS.
                tem_berco_interesse = any(berco in becos for berco in BERCOS_INCLUIR_TODOS)
                
                current_terminal = None
                # Se o navio não estiver em um berço de interesse, pula para a próxima iteração.
                if not tem_berco_interesse:
                    continue  # Ignora navios que não estão nos berços de interesse
                # Classifica o terminal com base nos berços encontrados.
                elif "TECONTPROLONG" in becos or "TECONT1" in becos:
                    current_terminal = "rio"
                elif "TECONT4" in becos or "TECONT2" in becos or "TECONT3" in becos or "TECONT5" in becos:
                    current_terminal = "multi"
                elif "MANGUINHOS" in becos:
                    current_terminal = "manguinhos"
                elif "PG-1" in becos: # 
                    current_terminal = "pg1"

                imo = None
                tipo_navio = None
                # Procura por informações adicionais (IMO, tipo de navio) em um <div> de tooltip escondida.
                tooltip_escondida = cols[1].find("div", class_="tooltipDivEscondida")
                if tooltip_escondida:
                    # Extrai o número IMO.
                    imo_span = tooltip_escondida.find("span", id="ST_NR_IMO")
                    if imo_span:
                        imo = imo_span.get_text(strip=True)
                    # Extrai o tipo de navio.
                    tipo_navio_span = tooltip_escondida.find("span", id="DS_TIPO_NAVIO")
                    if tipo_navio_span:
                        tipo_navio = (
                            tipo_navio_span.get_text(strip=True).split("(")[0].strip()
                        )
                
                # Divide a string de data_hora em data e hora.
                data, hora = data_hora.split()
                # Normaliza o formato da hora (adiciona ":00" se faltar, ou corrige minutos com um dígito).
                if ":" not in hora:
                    hora = hora + ":00"
                elif hora.count(":") == 1 and len(hora.split(":")[1]) == 1:
                    hora = hora.replace(":", ":0")
                
                # Converte a data e hora para um objeto datetime.
                dia, mes = map(int, data.split("/"))
                hora_part, minuto_part = map(int, hora.split(":"))
                hoje = datetime.now()
                navio_date = datetime(hoje.year, mes, dia, hora_part, minuto_part)

                # Determina o status da manobra (futuro, hoje, passado) em relação à data atual.
                status = "futuro"
                if navio_date.date() == hoje.date():
                    status = "hoje"
                elif navio_date < hoje:
                    status = "passado"
                
                alerta = None
                agora = datetime.now()
                # Lógica para gerar alertas com base no tipo de manobra e proximidade da hora atual.
                if manobra == "E":  # ENTRADA
                    if navio_date - timedelta(hours=1) <= agora < navio_date:
                        alerta = "entrada_antecipada"
                    elif agora >= navio_date:
                        alerta = "entrada_futura"
                elif manobra in ["S", "M"]:  # SAÍDA, MUDANÇA
                    if navio_date - timedelta(hours=1) <= agora < navio_date:
                        alerta = "saida_futura"
                    elif agora >= navio_date:
                        alerta = "saida_atrasada"
                
                # Define o ícone padrão para o navio.
                icone = "https://i.ibb.co/cX1DXDhW/icon-container.png"
                # Altera o ícone com base no tipo de navio, se for reconhecido.
                if tipo_navio:
                    if "CONTAINER SHIP" in tipo_navio.upper():
                        icone = "https://i.ibb.co/cX1DXDhW/icon-container.png"
                    elif (
                        "CHEMICAL TANKER" in tipo_navio.upper()
                        or "PRODUCT TANKER" in tipo_navio.upper()
                        or "TANKER" in tipo_navio.upper()
                    ):
                        icone = "https://i.ibb.co/T315cM3/TANKER.png"
                    elif (
                        "CARGO SHIP" in tipo_navio.upper()
                        or "OFFSHORE SHIP" in tipo_navio.upper()
                        or "OFFSHORE SUPPORT VESSEL" in tipo_navio.upper()
                        or "DIVING SUPPORT VESSEL" in tipo_navio.upper()
                    ):
                        icone = "https://i.ibb.co/ymWQg66b/offshoer.png"
                    elif "SUPPLY SHIP" in tipo_navio.upper():
                        icone = "https://i.ibb.co/ccHFRkVD/suplay-ship.png"
                
                # Adiciona os dados da manobra processada à lista.
                navios_manobras.append(
                    {
                        "data": data,
                        "hora": hora,
                        "navio": navio_nome,
                        "calado": calado,
                        "manobra": manobra,
                        "beco": becos,
                        "status": status,
                        "imo": imo,
                        "tipo_navio": tipo_navio,
                        "icone": icone,
                        "alerta": alerta,
                        "terminal": current_terminal,
                        "navio_date_obj": navio_date,
                    }
                )
            except Exception as e:
                # Em caso de erro ao processar uma linha específica, imprime um erro e continua para a próxima.
                print(f"Erro ao processar linha do navio: {e}")
                continue
    # Retorna a lista completa de manobras de navios.
    return navios_manobras


# Função para obter navios, com opção de filtragem por terminal e remoção de duplicatas.
def get_navios(terminal_filter='todos'):
    # Obtém todas as manobras de navios.
    all_navios_manobras = get_all_navios_manobras()
    
    navios_filtrados = []
    # Filtra os navios com base no terminal_filter fornecido.
    for n in all_navios_manobras:
        if terminal_filter == 'todos':
            navios_filtrados.append(n)
        elif terminal_filter == 'rio' and n['terminal'] == 'rio':
            navios_filtrados.append(n)
        elif terminal_filter == 'multi' and n['terminal'] == 'multi':
            navios_filtrados.append(n)
        elif terminal_filter == 'manguinhos' and n['terminal'] == 'manguinhos':
            navios_filtrados.append(n)
        elif terminal_filter == 'pg1' and n['terminal'] == 'pg1':
            navios_filtrados.append(n)

    navios_unicos = []
    vistos = set()

    # Remove navios duplicados com base em uma chave única (data, hora, navio, manobra).
    for n in navios_filtrados:
        chave = (n["data"], n["hora"], n["navio"], n["manobra"])
        if chave not in vistos:
            navios_unicos.append(n)
            vistos.add(chave)
    # Retorna a lista de navios únicos e filtrados.
    return navios_unicos


# Função para detectar conflitos de manobra entre navios dos terminais 'rio' e 'multi'.
def detectar_conflitos(navios_rio_manobras, navios_multi_manobras):
    conflitos = []

    # Agrupa as manobras do terminal 'rio' pelo nome do navio.
    navios_rio_agrupados = {}
    for manobra_rio in navios_rio_manobras:
        navio_nome = manobra_rio["navio"]
        if navio_nome not in navios_rio_agrupados:
            navios_rio_agrupados[navio_nome] = []
        navios_rio_agrupados[navio_nome].append(manobra_rio)
    
    # Itera sobre cada navio agrupado do terminal 'rio'.
    for navio_nome_rio, manobras_rio in navios_rio_agrupados.items():
        # Ordena as manobras do navio por data e hora.
        manobras_rio.sort(key=lambda x: x["navio_date_obj"])

        periodo_inicio_rio = None
        periodo_fim_rio = None

        # Encontra o início do período de ocupação (primeira manobra de entrada ou a primeira manobra).
        for m in manobras_rio:
            if m["manobra"] == "E" or periodo_inicio_rio is None:
                periodo_inicio_rio = m["navio_date_obj"]
                break
        
        # Encontra o fim do período de ocupação (última manobra de saída ou a última manobra).
        for m in reversed(manobras_rio):
            if m["manobra"] == "S" or periodo_fim_rio is None:
                periodo_fim_rio = m["navio_date_obj"]
                break

        # Ajusta os períodos se apenas um for encontrado ou se forem iguais.
        if periodo_inicio_rio and not periodo_fim_rio:
            periodo_fim_rio = periodo_inicio_rio + timedelta(hours=4)
        elif not periodo_inicio_rio and periodo_fim_rio:
            periodo_inicio_rio = periodo_fim_rio - timedelta(hours=4)
        elif not periodo_inicio_rio and not periodo_fim_rio and manobras_rio:
            periodo_inicio_rio = manobras_rio[0]["navio_date_obj"]
            periodo_fim_rio = manobras_rio[-1]["navio_date_obj"]
            if periodo_inicio_rio == periodo_fim_rio:
                periodo_fim_rio = periodo_inicio_rio + timedelta(hours=4)

        # Se os períodos não puderem ser determinados, pula para o próximo navio.
        if not periodo_inicio_rio or not periodo_fim_rio:
            continue

        # Compara o período de ocupação do navio 'rio' com as manobras do terminal 'multi'.
        for manobra_multi in navios_multi_manobras:
            # Considera apenas manobras de Entrada (E) ou Saída (S) para o terminal 'multi'.
            if manobra_multi["manobra"] in ["E", "S"]:
                # Define uma janela de tempo para a manobra do navio 'multi' (+/- 1 hora).
                janela_multi_inicio = manobra_multi["navio_date_obj"] - timedelta(hours=1)
                janela_multi_fim = manobra_multi["navio_date_obj"] + timedelta(hours=1)

                # Verifica se há sobreposição entre os períodos do navio 'rio' e a janela do navio 'multi'.
                if max(periodo_inicio_rio, janela_multi_inicio) < min(periodo_fim_rio, janela_multi_fim):
                    manobra_afetada_rio = None
                    min_diff = timedelta(days=999)

                    # Encontra a manobra do navio 'rio' mais próxima em tempo da manobra do navio 'multi'.
                    for m_rio in manobras_rio:
                        if m_rio["manobra"] in ["E", "S"]:
                            diff = abs(m_rio["navio_date_obj"] - manobra_multi["navio_date_obj"])

                            if (m_rio["manobra"] == manobra_multi["manobra"] and diff <= min_diff):
                                min_diff = diff
                                manobra_afetada_rio = m_rio["manobra"]
                                if diff == timedelta(0):
                                    break
                            elif (m_rio["manobra"] != manobra_multi["manobra"] and diff < min_diff):
                                min_diff = diff
                                manobra_afetada_rio = m_rio["manobra"]

                    # Se nenhuma manobra específica foi afetada, tenta determinar uma manobra padrão.
                    if manobra_afetada_rio is None:
                        for m_rio in manobras_rio:
                            if m_rio["manobra"] == "E":
                                manobra_afetada_rio = "E"
                                break
                        if manobra_afetada_rio is None:
                            for m_rio in manobras_rio:
                                if m_rio["manobra"] == "S":
                                    manobra_afetada_rio = "S"
                                    break

                    # Adiciona o conflito encontrado à lista de conflitos.
                    conflitos.append({
                        "navio_rio": navio_nome_rio,
                        "manobra_rio_afetada": manobra_afetada_rio,
                        "manobra_rio_inicio": periodo_inicio_rio.strftime("%d/%m %H:%M"),
                        "manobra_rio_fim": periodo_fim_rio.strftime("%d/%m %H:%M"),
                        "navio_multi": manobra_multi["navio"],
                        "manobra_multi_tipo": manobra_multi["manobra"],
                        "manobra_multi_data_hora": manobra_multi["navio_date_obj"].strftime("%d/%m %H:%M"),
                    })
    # Retorna a lista de conflitos encontrados.
    return conflitos


# Rota principal da aplicação Flask (página inicial).
@app.route("/")
def home():
    # Define o fuso horário para 'America/Sao_Paulo'.
    tz = timezone("America/Sao_Paulo")
    # Obtém a hora atual no fuso horário definido.
    agora = datetime.now(tz)
    # Formata a data e hora da última atualização.
    ultima_atualizacao = agora.strftime("%d/%m/%Y %H:%M")

    # Obtém todos os dados de manobras de navios.
    all_navios_data = get_all_navios_manobras()

    # Filtra os navios por terminal ('rio' e 'multi').
    navios_rio = [n for n in all_navios_data if n["terminal"] == "rio"]
    navios_multi = [n for n in all_navios_data if n["terminal"] == "multi"]

    # Detecta conflitos entre os navios dos terminais 'rio' e 'multi'.
    conflitos_encontrados = detectar_conflitos(navios_rio, navios_multi)

    # Inicializa a flag de conflito para os navios do terminal 'rio'.
    for navio_rio_manobra in navios_rio:
        navio_rio_manobra["conflito_porterne"] = False
        navio_rio_manobra["conflito_manobra_tipo"] = None

    # Marca os navios do terminal 'rio' que estão em conflito.
    navios_com_porterne_marcado = {}
    for conflito in conflitos_encontrados:
        navio_nome = conflito["navio_rio"]
        manobra_afetada = conflito["manobra_rio_afetada"]

        if navio_nome in navios_com_porterne_marcado:
            continue
        
        for navio_rio_manobra in navios_rio:
            if (navio_rio_manobra["navio"] == navio_nome and 
                navio_rio_manobra["manobra"] == manobra_afetada):
                navio_rio_manobra["conflito_porterne"] = True
                navio_rio_manobra["conflito_manobra_tipo"] = manobra_afetada
                navios_com_porterne_marcado[navio_nome] = manobra_afetada
                break

    # Prepara a lista de navios para exibição, removendo duplicatas.
    navios_para_exibir = []
    vistos = set()
    for n in all_navios_data:
        chave = (n["data"], n["hora"], n["navio"], n["manobra"])
        if chave not in vistos:
            navios_para_exibir.append(n)
            vistos.add(chave)

    # Obtém o status da barra.
    barra_info = get_status_barra()

    # Renderiza o template 'index.html' passando os dados para a interface.
    return render_template(
        "index.html",
        navios=navios_para_exibir,
        ultima_atualizacao=ultima_atualizacao,
        barra_info=barra_info,
        terminal_selecionado="todos",
    )


# Rota da API para obter dados de navios em formato JSON.
@app.route("/api/navios")
def api_navios():
    # Define o fuso horário para 'America/Sao_Paulo'.
    tz = timezone("America/Sao_Paulo")
    # Obtém a hora atual no fuso horário definido.
    agora = datetime.now(tz)
    # Formata a data e hora da última atualização.
    ultima_atualizacao = agora.strftime("%d/%m/%Y %H:%M")

    # Obtém o filtro de terminal da query string da requisição (padrão: 'todos').
    terminal_filter = request.args.get("terminal", "todos")

    # Obtém todos os dados de manobras de navios.
    all_navios_data = get_all_navios_manobras()

    # Filtra os navios por terminal ('rio' e 'multi').
    navios_rio = [n for n in all_navios_data if n["terminal"] == "rio"]
    navios_multi = [n for n in all_navios_data if n["terminal"] == "multi"]

    # Detecta conflitos entre os navios dos terminais 'rio' e 'multi'.
    conflitos_encontrados = detectar_conflitos(navios_rio, navios_multi)

    # Inicializa a flag de conflito para os navios do terminal 'rio'.
    for navio_rio_manobra in navios_rio:
        navio_rio_manobra["conflito_porterne"] = False
        navio_rio_manobra["conflito_manobra_tipo"] = None

    # Marca os navios do terminal 'rio' que estão em conflito.
    navios_com_porterne_marcado = {}
    for conflito in conflitos_encontrados:
        navio_nome = conflito["navio_rio"]
        manobra_afetada = conflito["manobra_rio_afetada"]

        if navio_nome in navios_com_porterne_marcado:
            continue
        
        for navio_rio_manobra in navios_rio:
            if (navio_rio_manobra["navio"] == navio_nome and 
                navio_rio_manobra["manobra"] == manobra_afetada):
                navio_rio_manobra["conflito_porterne"] = True
                navio_rio_manobra["conflito_manobra_tipo"] = manobra_afetada
                navios_com_porterne_marcado[navio_nome] = manobra_afetada
                break

    # Prepara a lista de navios para exibição, aplicando o filtro de terminal e removendo duplicatas.
    navios_para_exibir = []
    vistos = set()
    for n in all_navios_data:
        if (terminal_filter == 'todos' or
            (terminal_filter == 'rio' and n['terminal'] == 'rio') or
            (terminal_filter == 'multi' and n['terminal'] == 'multi') or
            (terminal_filter == 'manguinhos' and n['terminal'] == 'manguinhos') or
            (terminal_filter == 'pg1' and n['terminal'] == 'pg1')):
            
            chave = (n["data"], n["hora"], n["navio"], n["manobra"])
            if chave not in vistos:
                navios_para_exibir.append(n)
                vistos.add(chave)

    # Obtém o status da barra.
    barra_info = get_status_barra()

    # Retorna os dados em formato JSON, incluindo navios, última atualização, info da barra e conflitos.
    return jsonify({
        "navios": navios_para_exibir,
        "ultima_atualizacao": ultima_atualizacao,
        "barra_info": barra_info,
        "conflitos": conflitos_encontrados,
    })


# Bloco principal de execução do script.
# Garante que o servidor Flask seja iniciado apenas quando o script é executado diretamente.
if __name__ == "__main__":
    # Inicia o servidor Flask.
    # host="0.0.0.0" faz com que o servidor seja acessível de qualquer IP.
    # port=port usa a porta definida anteriormente (variável de ambiente ou 5000).
    # debug=True ativa o modo de depuração, que recarrega o servidor automaticamente em mudanças e fornece informações de erro detalhadas.
    # ATENÇÃO: debug=True NÃO DEVE SER USADO EM AMBIENTE DE PRODUÇÃO por questões de segurança e performance.
    app.run(host="0.0.0.0", port=port, debug=False)


