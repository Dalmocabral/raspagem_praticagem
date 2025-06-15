from flask import Flask, render_template, jsonify, url_for, request
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import os
from pytz import timezone

port = int(os.environ.get("PORT", 5000))
app = Flask(__name__)

URL = "https://www.praticagem-rj.com.br/"

# Lista de berços que devem ser incluídos quando selecionar "Todos os Terminais"
BERCOS_INCLUIR_TODOS = {
    'TECONTPROLONG', 'TECONT1', 'TECONT2', 'TECONT3', 'TECONT4', 'TECONT5', 
    'MANGUINHOS', 'PG1'
}

def get_status_barra():
    try:
        response = requests.get(URL)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "lxml")

        baia_span = soup.find("span", string=re.compile(r"BAIA DE GUANABARA", re.I))
        if baia_span:
            tr = baia_span.find_parent("tr")
            if tr:
                barra_div = tr.find("div", id=re.compile(r"pnlBarra\d+"))
                if barra_div:
                    texto = barra_div.get_text(separator=" ", strip=True)

                    if "BARRA RESTRITA" in texto.upper():
                        return {"restrita": True, "mensagem": texto}
                    else:
                        return {"restrita": False, "mensagem": texto}
    except Exception as e:
        print(f"Erro ao verificar status da barra: {e}")
    return {"restrita": False, "mensagem": "Não foi possível obter o status da barra."}


def get_all_navios_manobras():
    response = requests.get(URL)
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, "lxml")

    navios_manobras = []

    main_table = soup.find("table", class_="tbManobrasArea")
    if not main_table:
        print("Tabela principal de manobras não encontrada.")
        return []
    rows = main_table.find_all(
        "tr", id=re.compile(r"rptAreas_ctl\d+_rptManobrasArea_ctl\d+_trManobraArea")
    )

    for row in rows:
        cols = row.find_all("td", class_="tdManobraArea")
        if len(cols) >= 12:
            try:
                data_hora = cols[0].get_text(strip=True)

                navio_nome_div = cols[1].find("div", class_="tooltipDiv")
                navio_nome = (
                    navio_nome_div.contents[0].strip() if navio_nome_div else "N/A"
                )

                calado = cols[2].get_text(strip=True)
                manobra = cols[7].get_text(strip=True)
                becos = (
                    cols[8].get_text(strip=True)
                    if cols[8].get_text(strip=True)
                    else cols[11].get_text(strip=True)
                )

                # Verifica se o navio está em algum dos berços que nos interessam
                tem_berco_interesse = any(berco in becos for berco in BERCOS_INCLUIR_TODOS)
                
                current_terminal = None
                if not tem_berco_interesse:
                    continue  # Ignora navios que não estão nos berços de interesse
                elif "TECONTPROLONG" in becos or "TECONT1" in becos:
                    current_terminal = "rio"
                elif "TECONT4" in becos or "TECONT2" in becos or "TECONT3" in becos or "TECONT5" in becos:
                    current_terminal = "multi"
                elif "MANGUINHOS" in becos:
                    current_terminal = "manguinhos"
                elif "PG1" in becos:
                    current_terminal = "PG1" in becos or "PG-1" in becos or "PG 1"

                imo = None
                tipo_navio = None
                tooltip_escondida = cols[1].find("div", class_="tooltipDivEscondida")
                if tooltip_escondida:
                    imo_span = tooltip_escondida.find("span", id="ST_NR_IMO")
                    if imo_span:
                        imo = imo_span.get_text(strip=True)
                    tipo_navio_span = tooltip_escondida.find("span", id="DS_TIPO_NAVIO")
                    if tipo_navio_span:
                        tipo_navio = (
                            tipo_navio_span.get_text(strip=True).split("(")[0].strip()
                        )
                
                data, hora = data_hora.split()
                if ":" not in hora:
                    hora = hora + ":00"
                elif hora.count(":") == 1 and len(hora.split(":")[1]) == 1:
                    hora = hora.replace(":", ":0")
                
                dia, mes = map(int, data.split("/"))
                hora_part, minuto_part = map(int, hora.split(":"))
                hoje = datetime.now()
                navio_date = datetime(hoje.year, mes, dia, hora_part, minuto_part)

                status = "futuro"
                if navio_date.date() == hoje.date():
                    status = "hoje"
                elif navio_date < hoje:
                    status = "passado"
                
                alerta = None
                agora = datetime.now()
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
                
                icone = "https://i.ibb.co/cX1DXDhW/icon-container.png"
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
                    ):
                        icone = "https://i.ibb.co/ymWQg66b/offshoer.png"
                    elif "SUPPLY SHIP" in tipo_navio.upper():
                        icone = "https://i.ibb.co/ccHFRkVD/suplay-ship.png"
                
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
                print(f"Erro ao processar linha do navio: {e}")
                continue
    return navios_manobras


def get_navios(terminal_filter='todos'):
    all_navios_manobras = get_all_navios_manobras()
    
    navios_filtrados = []
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

    for n in navios_filtrados:
        chave = (n["data"], n["hora"], n["navio"], n["manobra"])
        if chave not in vistos:
            navios_unicos.append(n)
            vistos.add(chave)
    return navios_unicos


def detectar_conflitos(navios_rio_manobras, navios_multi_manobras):
    conflitos = []

    navios_rio_agrupados = {}
    for manobra_rio in navios_rio_manobras:
        navio_nome = manobra_rio["navio"]
        if navio_nome not in navios_rio_agrupados:
            navios_rio_agrupados[navio_nome] = []
        navios_rio_agrupados[navio_nome].append(manobra_rio)
    
    for navio_nome_rio, manobras_rio in navios_rio_agrupados.items():
        manobras_rio.sort(key=lambda x: x["navio_date_obj"])

        periodo_inicio_rio = None
        periodo_fim_rio = None

        for m in manobras_rio:
            if m["manobra"] == "E" or periodo_inicio_rio is None:
                periodo_inicio_rio = m["navio_date_obj"]
                break
        
        for m in reversed(manobras_rio):
            if m["manobra"] == "S" or periodo_fim_rio is None:
                periodo_fim_rio = m["navio_date_obj"]
                break

        if periodo_inicio_rio and not periodo_fim_rio:
            periodo_fim_rio = periodo_inicio_rio + timedelta(hours=4)
        elif not periodo_inicio_rio and periodo_fim_rio:
            periodo_inicio_rio = periodo_fim_rio - timedelta(hours=4)
        elif not periodo_inicio_rio and not periodo_fim_rio and manobras_rio:
            periodo_inicio_rio = manobras_rio[0]["navio_date_obj"]
            periodo_fim_rio = manobras_rio[-1]["navio_date_obj"]
            if periodo_inicio_rio == periodo_fim_rio:
                periodo_fim_rio = periodo_inicio_rio + timedelta(hours=4)

        if not periodo_inicio_rio or not periodo_fim_rio:
            continue

        for manobra_multi in navios_multi_manobras:
            if manobra_multi["manobra"] in ["E", "S"]:
                janela_multi_inicio = manobra_multi["navio_date_obj"] - timedelta(hours=1)
                janela_multi_fim = manobra_multi["navio_date_obj"] + timedelta(hours=1)

                if max(periodo_inicio_rio, janela_multi_inicio) < min(periodo_fim_rio, janela_multi_fim):
                    manobra_afetada_rio = None
                    min_diff = timedelta(days=999)

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

                    conflitos.append({
                        "navio_rio": navio_nome_rio,
                        "manobra_rio_afetada": manobra_afetada_rio,
                        "manobra_rio_inicio": periodo_inicio_rio.strftime("%d/%m %H:%M"),
                        "manobra_rio_fim": periodo_fim_rio.strftime("%d/%m %H:%M"),
                        "navio_multi": manobra_multi["navio"],
                        "manobra_multi_tipo": manobra_multi["manobra"],
                        "manobra_multi_data_hora": manobra_multi["navio_date_obj"].strftime("%d/%m %H:%M"),
                    })
    return conflitos


@app.route("/")
def home():
    tz = timezone("America/Sao_Paulo")
    agora = datetime.now(tz)
    ultima_atualizacao = agora.strftime("%d/%m/%Y %H:%M")

    all_navios_data = get_all_navios_manobras()

    navios_rio = [n for n in all_navios_data if n["terminal"] == "rio"]
    navios_multi = [n for n in all_navios_data if n["terminal"] == "multi"]

    conflitos_encontrados = detectar_conflitos(navios_rio, navios_multi)

    for navio_rio_manobra in navios_rio:
        navio_rio_manobra["conflito_porterne"] = False
        navio_rio_manobra["conflito_manobra_tipo"] = None

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

    navios_para_exibir = []
    vistos = set()
    for n in all_navios_data:
        chave = (n["data"], n["hora"], n["navio"], n["manobra"])
        if chave not in vistos:
            navios_para_exibir.append(n)
            vistos.add(chave)

    barra_info = get_status_barra()

    return render_template(
        "index.html",
        navios=navios_para_exibir,
        ultima_atualizacao=ultima_atualizacao,
        barra_info=barra_info,
        terminal_selecionado="todos",
    )


@app.route("/api/navios")
def api_navios():
    tz = timezone("America/Sao_Paulo")
    agora = datetime.now(tz)
    ultima_atualizacao = agora.strftime("%d/%m/%Y %H:%M")

    terminal_filter = request.args.get("terminal", "todos")

    all_navios_data = get_all_navios_manobras()

    navios_rio = [n for n in all_navios_data if n["terminal"] == "rio"]
    navios_multi = [n for n in all_navios_data if n["terminal"] == "multi"]

    conflitos_encontrados = detectar_conflitos(navios_rio, navios_multi)

    for navio_rio_manobra in navios_rio:
        navio_rio_manobra["conflito_porterne"] = False
        navio_rio_manobra["conflito_manobra_tipo"] = None

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

    barra_info = get_status_barra()

    return jsonify({
        "navios": navios_para_exibir,
        "ultima_atualizacao": ultima_atualizacao,
        "barra_info": barra_info,
        "conflitos": conflitos_encontrados,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port, debug=True)