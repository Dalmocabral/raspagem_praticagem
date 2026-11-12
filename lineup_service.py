"""
lineup_service.py - Integração com a API de Lineup do Rio Brasil Terminal.
Obtém serviços marítimos (joint, operadoras, viagem) e calcula o status
de conformidade com a Janela Oficial de Atracação (Berth Window).
"""

import requests
from datetime import datetime, timedelta, timezone

LINEUP_API_URL = "https://servicosabertosapim.azure-api.net/lineup/ObterLineupCompleto"
SUBSCRIPTION_KEY = "8f6bc3758c2143e99e59d54cc7d1bfe7"

HEADERS = {
    "Content-Type": "application/json",
    "Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Origin": "https://servicosabertosriobrasil.azurewebsites.net",
    "Referer": "https://servicosabertosriobrasil.azurewebsites.net/"
}

# Mapeamento oficial dos serviços e consórcios (Joints/Armadores)
SERVICOS_MAP = {
    "TGO": {
        "nome": "Tango",
        "armadores": "Hapag Lloyd - Maersk (slot Sealand)",
        "cor": "primary"
    },
    "COS": {
        "nome": "CONOSUR",
        "armadores": "Maersk - Sealand - Hapag Lloyd",
        "cor": "info"
    },
    "SE1": {
        "nome": "ESA / SEAS 1",
        "armadores": "CMA CGM (SEAS) - Evergreen (ESA) - COSCO (ESA) - PIL (ES1) (Slot Yang Ming – SA3 - OOCL (TLA1))",
        "cor": "success"
    },
    "FED": {
        "nome": "Feeder (Log-In)",
        "armadores": "Log-In (Slot Maersk / Aliança / CMA CGM / Mercosul / ZIM)",
        "cor": "warning"
    },
    "BZX": {
        "nome": "BRAZEx",
        "armadores": "CMA CGM – Cosco (Slot Maersk – ONE)",
        "cor": "danger"
    },
    "BCO": {
        "nome": "BRACO",
        "armadores": "Mercosul (Slot LOG-IN)",
        "cor": "secondary"
    },
    "S2N": {
        "nome": "SEAS 2",
        "armadores": "CMA-CGM / Cosco - (Slot Evergreen, PIL e Yang Ming)",
        "cor": "dark"
    },
    "S2S": {
        "nome": "SEAS 2",
        "armadores": "CMA-CGM / Cosco - (Slot Evergreen, PIL e Yang Ming)",
        "cor": "dark"
    },
    "LUX": {
        "nome": "LUX / ESE 2 - EEX",
        "armadores": "Cosco - One - OOCL",
        "cor": "primary"
    },
    "NCS": {
        "nome": "Norcoast",
        "armadores": "Norcoast",
        "cor": "info"
    },
    "ZFS": {
        "nome": "Falcon (ZFS)",
        "armadores": "ZIM",
        "cor": "success"
    },
    "ZGT": {
        "nome": "ZIM Gulf Toucan",
        "armadores": "ZIM",
        "cor": "success"
    },
    "BBK": {
        "nome": "Break Bulk",
        "armadores": "G2 Ocean / BBC",
        "cor": "secondary"
    },
    "TRP": {
        "nome": "Extra Call",
        "armadores": "Extra Call",
        "cor": "warning"
    }
}

# Mapeamento das Janelas Oficiais (Proforma Windows) por dia da semana e horário
# Domingo = 0, Segunda = 1, Terça = 2, Quarta = 3, Quinta = 4, Sexta = 5, Sábado = 6
JANELAS_SERVICO = {
    # BRACO: Domingo 07:00 até Segunda 01:00
    "BCO": {
        "inicio_dia": 0, "inicio_hora": 7, "inicio_min": 0,
        "fim_dia": 1, "fim_hora": 1, "fim_min": 0,
        "descricao": "Domingo 07:00 → Segunda 01:00"
    },
    # ZFS FALCON: Domingo 01:00 até Domingo 19:00
    "ZFS": {
        "inicio_dia": 0, "inicio_hora": 1, "inicio_min": 0,
        "fim_dia": 0, "fim_hora": 19, "fim_min": 0,
        "descricao": "Domingo 01:00 → Domingo 19:00"
    },
    # LUX / ESE 2: Domingo 17:00 até Segunda 09:00
    "LUX": {
        "inicio_dia": 0, "inicio_hora": 17, "inicio_min": 0,
        "fim_dia": 1, "fim_hora": 9, "fim_min": 0,
        "descricao": "Domingo 17:00 → Segunda 09:00"
    },
    # TANGO NB: Segunda 11:00 até Terça 01:00
    "TGO": {
        "inicio_dia": 1, "inicio_hora": 11, "inicio_min": 0,
        "fim_dia": 2, "fim_hora": 1, "fim_min": 0,
        "descricao": "Segunda 11:00 → Terça 01:00"
    },
    # NORCOAST: Terça 01:00 até Terça 19:00
    "NCS": {
        "inicio_dia": 2, "inicio_hora": 1, "inicio_min": 0,
        "fim_dia": 2, "fim_hora": 19, "fim_min": 0,
        "descricao": "Terça 01:00 → Terça 19:00"
    },
    # SEAS 2 SB (Southbound): Terça 07:00 até Quarta 19:00
    "S2S": {
        "inicio_dia": 2, "inicio_hora": 7, "inicio_min": 0,
        "fim_dia": 3, "fim_hora": 19, "fim_min": 0,
        "descricao": "Terça 07:00 → Quarta 19:00"
    },
    # SEAS 2 NB (Northbound): Terça 17:00 até Quarta 19:00
    "S2N": {
        "inicio_dia": 2, "inicio_hora": 17, "inicio_min": 0,
        "fim_dia": 3, "fim_hora": 19, "fim_min": 0,
        "descricao": "Terça 17:00 → Quarta 19:00"
    },
    # SEAS 1 / ESA 1: Quarta 19:00 até Quinta 19:00
    "SE1": {
        "inicio_dia": 3, "inicio_hora": 19, "inicio_min": 0,
        "fim_dia": 4, "fim_hora": 19, "fim_min": 0,
        "descricao": "Quarta 19:00 → Quinta 19:00"
    },
    # CHEMICAL: Quinta 17:00 até Sexta 21:00
    "QUI": {
        "inicio_dia": 4, "inicio_hora": 17, "inicio_min": 0,
        "fim_dia": 5, "fim_hora": 21, "fim_min": 0,
        "descricao": "Quinta 17:00 → Sexta 21:00"
    },
    # FEEDER SSR (Log-In): Sexta 11:00 até Sexta 23:00
    "FED": {
        "inicio_dia": 5, "inicio_hora": 11, "inicio_min": 0,
        "fim_dia": 5, "fim_hora": 23, "fim_min": 0,
        "descricao": "Sexta 11:00 → Sexta 23:00"
    },
    # CONOSUR: Sexta 21:00 até Sábado 19:00
    "COS": {
        "inicio_dia": 5, "inicio_hora": 21, "inicio_min": 0,
        "fim_dia": 6, "fim_hora": 19, "fim_min": 0,
        "descricao": "Sexta 21:00 → Sábado 19:00"
    },
    # BRAZEX: Sábado 13:00 até Domingo 04:00
    "BZX": {
        "inicio_dia": 6, "inicio_hora": 13, "inicio_min": 0,
        "fim_dia": 0, "fim_hora": 4, "fim_min": 0,
        "descricao": "Sábado 13:00 → Domingo 04:00"
    }
}


def verificar_status_janela(joint, dt, manobra):
    """
    Avalia se a manobra de Entrada ('E') está dentro ou fora da janela semanal de atracação.
    Retorna (status, descricao, texto_tooltip).
    """
    info = JANELAS_SERVICO.get(joint)
    if not info or not dt:
        return None, None, None

    # O foco na janela de atracação é na manobra de Entrada (E)
    if manobra != "E":
        return None, info["descricao"], f"Janela Oficial: {info['descricao']}"

    # Domingo = 0, Segunda = 1, ..., Sábado = 6
    dia_semana_domingo_0 = (dt.weekday() + 1) % 7
    minutos_navio = dia_semana_domingo_0 * 1440 + dt.hour * 60 + dt.minute

    inicio_min = info["inicio_dia"] * 1440 + info["inicio_hora"] * 60 + info["inicio_min"]
    fim_min = info["fim_dia"] * 1440 + info["fim_hora"] * 60 + info["fim_min"]

    # Verifica intervalo
    if inicio_min <= fim_min:
        na_janela = (inicio_min <= minutos_navio <= fim_min)
    else:
        # Vira a semana (ex: Sábado para Domingo)
        na_janela = (minutos_navio >= inicio_min or minutos_navio <= fim_min)

    desc = info["descricao"]
    if na_janela:
        return "NA_JANELA", desc, f"Dentro da Janela Oficial ({desc})"
    else:
        return "FORA_DA_JANELA", desc, f"Fora da Janela Oficial (Programado: {desc})"


def obter_lineup_rio_brasil():
    """
    Chama a API do Rio Brasil Terminal e retorna um dicionário com os navios
    e seus respectivos serviços.
    """
    try:
        now = datetime.now(timezone.utc)
        payload = {
            "ChegadaDe": (now - timedelta(days=15)).isoformat(),
            "ChegadaAte": (now + timedelta(days=35)).isoformat()
        }

        response = requests.post(LINEUP_API_URL, headers=HEADERS, json=payload, timeout=8)
        if response.status_code != 200:
            print(f"Aviso: Lineup API retornou status {response.status_code}")
            return {}

        data = response.json()
        resp_obj = data.get("responseObject", [])
        if not resp_obj:
            return {}

        todos = resp_obj[0].get("todos", [])
        lineup_map = {}

        for item in todos:
            navio_nome = (item.get("navio") or "").strip().upper()
            if not navio_nome:
                continue

            joint = (item.get("joint") or "").strip().upper()
            service_name = (item.get("serviceName") or "").strip()
            viagem = (item.get("viagem") or "").strip()
            operator = (item.get("operator") or "").strip()

            # Mapeia informações do serviço
            info_cadastrada = SERVICOS_MAP.get(joint)
            if info_cadastrada:
                nome_exibicao = info_cadastrada["nome"]
                armadores_exibicao = info_cadastrada["armadores"]
                cor_badge = info_cadastrada["cor"]
            else:
                nome_exibicao = service_name if service_name else (joint if joint else "Outro")
                armadores_exibicao = operator if operator else "Não especificado"
                cor_badge = "secondary"

            # Salva na lista do navio
            if navio_nome not in lineup_map:
                lineup_map[navio_nome] = []

            lineup_map[navio_nome].append({
                "joint": joint,
                "service_name": service_name,
                "nome_servico": nome_exibicao,
                "armadores": armadores_exibicao,
                "viagem": viagem,
                "cor_badge": cor_badge,
                "data_chegada": item.get("previsaoChegada") or item.get("chegada")
            })

        return lineup_map

    except Exception as e:
        print(f"Erro ao consultar Lineup API do Rio Brasil Terminal: {e}")
        return {}


def enriquecer_navio_com_servico(navio_dict, lineup_map):
    """
    Enriquece o dicionário do navio com as informações do serviço e status da janela
    caso ele pertença ao Terminal Rio Brasil.
    """
    terminal = navio_dict.get("terminal")
    navio_nome = (navio_dict.get("navio") or "").strip().upper()

    # Aplica somente para navios do terminal rio brasil
    if terminal == "rio" and navio_nome in lineup_map:
        lista_viagens = lineup_map[navio_nome]
        viagem_info = lista_viagens[0]
        joint = viagem_info["joint"]

        navio_dict["servico"] = viagem_info["nome_servico"]
        navio_dict["servico_armadores"] = viagem_info["armadores"]
        navio_dict["servico_viagem"] = viagem_info["viagem"]
        navio_dict["servico_cor"] = viagem_info["cor_badge"]
        navio_dict["servico_joint"] = joint

        # Validação da Janela de Atracação
        dt = navio_dict.get("navio_date_obj")
        manobra = navio_dict.get("manobra")
        status_j, desc_j, texto_j = verificar_status_janela(joint, dt, manobra)

        navio_dict["status_janela"] = status_j
        navio_dict["janela_descricao"] = desc_j
        navio_dict["janela_texto"] = texto_j
    else:
        navio_dict["servico"] = None
        navio_dict["servico_armadores"] = None
        navio_dict["servico_viagem"] = None
        navio_dict["servico_cor"] = None
        navio_dict["servico_joint"] = None
        navio_dict["status_janela"] = None
        navio_dict["janela_descricao"] = None
        navio_dict["janela_texto"] = None

    return navio_dict
