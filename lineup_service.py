"""
lineup_service.py - Integração com a API de Lineup do Rio Brasil Terminal.
Obtém serviços marítimos (joint, operadoras, viagem) para navios do Terminal Rio Brasil.
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
    Enriquece o dicionário do navio com as informações do serviço
    caso ele pertença ao Terminal Rio Brasil.
    """
    terminal = navio_dict.get("terminal")
    navio_nome = (navio_dict.get("navio") or "").strip().upper()

    # Aplica somente para navios do terminal rio brasil
    if terminal == "rio" and navio_nome in lineup_map:
        lista_viagens = lineup_map[navio_nome]
        # Pega a viagem mais relevante (por enquanto o primeiro item)
        viagem_info = lista_viagens[0]
        navio_dict["servico"] = viagem_info["nome_servico"]
        navio_dict["servico_armadores"] = viagem_info["armadores"]
        navio_dict["servico_viagem"] = viagem_info["viagem"]
        navio_dict["servico_cor"] = viagem_info["cor_badge"]
        navio_dict["servico_joint"] = viagem_info["joint"]
    else:
        navio_dict["servico"] = None
        navio_dict["servico_armadores"] = None
        navio_dict["servico_viagem"] = None
        navio_dict["servico_cor"] = None
        navio_dict["servico_joint"] = None

    return navio_dict

