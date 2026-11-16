"""
lineup_service.py - Integração com a API de Lineup do Rio Brasil Terminal.
Obtém serviços marítimos (joint, operadoras, viagem) e gerencia as Janelas
Oficiais de Atracação (Berth Windows) com configuração dinâmica e persistente.
"""

import os
import json
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

# Caminho do arquivo de configuração persistente
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "janelas_config.json")

# Nomes dos dias da semana (0 = Domingo até 6 = Sábado)
DIAS_SEMANA = [
    "Domingo",
    "Segunda",
    "Terça",
    "Quarta",
    "Quinta",
    "Sexta",
    "Sábado"
]

# Configurações padrão de serviços e armadores conhecidos
DEFAULT_SERVICOS_MAP = {
    "BCO": {
        "nome": "BRACO",
        "armadores": "Mercosul (Slot LOG-IN)",
        "cor": "secondary",
        "ativo": True,
        "inicio_dia": 0, "inicio_hora": "07:00",
        "fim_dia": 1, "fim_hora": "01:00",
        "descricao": "Domingo 07:00 → Segunda 01:00"
    },
    "ZFS": {
        "nome": "Falcon (ZFS)",
        "armadores": "ZIM",
        "cor": "success",
        "ativo": True,
        "inicio_dia": 0, "inicio_hora": "01:00",
        "fim_dia": 0, "fim_hora": "19:00",
        "descricao": "Domingo 01:00 → Domingo 19:00"
    },
    "LUX": {
        "nome": "LUX / ESE 2 - EEX",
        "armadores": "Cosco - One - OOCL",
        "cor": "primary",
        "ativo": True,
        "inicio_dia": 0, "inicio_hora": "17:00",
        "fim_dia": 1, "fim_hora": "09:00",
        "descricao": "Domingo 17:00 → Segunda 09:00"
    },
    "TGO": {
        "nome": "Tango",
        "armadores": "Hapag Lloyd - Maersk (slot Sealand)",
        "cor": "primary",
        "ativo": True,
        "inicio_dia": 1, "inicio_hora": "11:00",
        "fim_dia": 2, "fim_hora": "01:00",
        "descricao": "Segunda 11:00 → Terça 01:00"
    },
    "NCS": {
        "nome": "Norcoast",
        "armadores": "Norcoast",
        "cor": "info",
        "ativo": True,
        "inicio_dia": 2, "inicio_hora": "01:00",
        "fim_dia": 2, "fim_hora": "19:00",
        "descricao": "Terça 01:00 → Terça 19:00"
    },
    "S2S": {
        "nome": "SEAS 2 (SB)",
        "armadores": "CMA-CGM / Cosco - (Slot Evergreen, PIL e Yang Ming)",
        "cor": "dark",
        "ativo": True,
        "inicio_dia": 2, "inicio_hora": "07:00",
        "fim_dia": 3, "fim_hora": "19:00",
        "descricao": "Terça 07:00 → Quarta 19:00"
    },
    "S2N": {
        "nome": "SEAS 2 (NB)",
        "armadores": "CMA-CGM / Cosco - (Slot Evergreen, PIL e Yang Ming)",
        "cor": "dark",
        "ativo": True,
        "inicio_dia": 2, "inicio_hora": "17:00",
        "fim_dia": 3, "fim_hora": "19:00",
        "descricao": "Terça 17:00 → Quarta 19:00"
    },
    "SE1": {
        "nome": "ESA / SEAS 1",
        "armadores": "CMA CGM (SEAS) - Evergreen (ESA) - COSCO (ESA) - PIL (ES1) (Slot Yang Ming – SA3 - OOCL (TLA1))",
        "cor": "success",
        "ativo": True,
        "inicio_dia": 3, "inicio_hora": "19:00",
        "fim_dia": 4, "fim_hora": "19:00",
        "descricao": "Quarta 19:00 → Quinta 19:00"
    },
    "QUI": {
        "nome": "Químico / Chemical",
        "armadores": "Chemical Tankers",
        "cor": "secondary",
        "ativo": True,
        "inicio_dia": 4, "inicio_hora": "17:00",
        "fim_dia": 5, "fim_hora": "21:00",
        "descricao": "Quinta 17:00 → Sexta 21:00"
    },
    "FED": {
        "nome": "Feeder (Log-In)",
        "armadores": "Log-In (Slot Maersk / Aliança / CMA CGM / Mercosul / ZIM)",
        "cor": "warning",
        "ativo": True,
        "inicio_dia": 5, "inicio_hora": "11:00",
        "fim_dia": 5, "fim_hora": "23:00",
        "descricao": "Sexta 11:00 → Sexta 23:00"
    },
    "COS": {
        "nome": "CONOSUR",
        "armadores": "Maersk - Sealand - Hapag Lloyd",
        "cor": "info",
        "ativo": True,
        "inicio_dia": 5, "inicio_hora": "21:00",
        "fim_dia": 6, "fim_hora": "19:00",
        "descricao": "Sexta 21:00 → Sábado 19:00"
    },
    "BZX": {
        "nome": "BRAZEx",
        "armadores": "CMA CGM – Cosco (Slot Maersk – ONE)",
        "cor": "danger",
        "ativo": True,
        "inicio_dia": 6, "inicio_hora": "13:00",
        "fim_dia": 0, "fim_hora": "04:00",
        "descricao": "Sábado 13:00 → Domingo 04:00"
    },
    "ZGT": {
        "nome": "ZIM Gulf Toucan",
        "armadores": "ZIM",
        "cor": "success",
        "ativo": False,
        "inicio_dia": 0, "inicio_hora": "00:00",
        "fim_dia": 0, "fim_hora": "00:00",
        "descricao": "Janela não configurada"
    },
    "BBK": {
        "nome": "Break Bulk",
        "armadores": "G2 Ocean / BBC",
        "cor": "secondary",
        "ativo": False,
        "inicio_dia": 0, "inicio_hora": "00:00",
        "fim_dia": 0, "fim_hora": "00:00",
        "descricao": "Janela não configurada"
    },
    "TRP": {
        "nome": "Extra Call (Tramp)",
        "armadores": "Extra Call / Tramp",
        "cor": "warning",
        "ativo": False,
        "inicio_dia": 0, "inicio_hora": "00:00",
        "fim_dia": 0, "fim_hora": "00:00",
        "descricao": "Janela não configurada"
    },
    "GEN": {
        "nome": "GENERIC",
        "armadores": "Cargas Gerais / Diversos",
        "cor": "secondary",
        "ativo": False,
        "inicio_dia": 0, "inicio_hora": "00:00",
        "fim_dia": 0, "fim_hora": "00:00",
        "descricao": "Janela não configurada"
    }
}


def _montar_descricao(inicio_dia, inicio_hora, fim_dia, fim_hora):
    """Gera o texto legível da janela semanal (ex: 'Domingo 07:00 → Segunda 01:00')."""
    try:
        d_ini = DIAS_SEMANA[int(inicio_dia)]
        d_fim = DIAS_SEMANA[int(fim_dia)]
        return f"{d_ini} {inicio_hora} → {d_fim} {fim_hora}"
    except Exception:
        return f"Dia {inicio_dia} {inicio_hora} → Dia {fim_dia} {fim_hora}"


def carregar_janelas_config():
    """
    Carrega o dicionário de configurações de janelas a partir do arquivo JSON.
    Se o arquivo não existir, inicializa com o padrão e salva.
    Garante que todos os serviços essenciais existam no arquivo.
    """
    config = {}
    precisa_salvar = False

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            print(f"Erro ao ler {CONFIG_FILE}: {e}. Recriando padrão.")
            config = {}

    # Completa chaves que porventura faltem
    for joint, padrao in DEFAULT_SERVICOS_MAP.items():
        if joint not in config:
            config[joint] = {
                "joint": joint,
                "nome": padrao["nome"],
                "armadores": padrao["armadores"],
                "cor": padrao["cor"],
                "ativo": padrao["ativo"],
                "inicio_dia": padrao["inicio_dia"],
                "inicio_hora": padrao["inicio_hora"],
                "fim_dia": padrao["fim_dia"],
                "fim_hora": padrao["fim_hora"],
                "descricao": padrao["descricao"],
                "novo": False
            }
            precisa_salvar = True

    if precisa_salvar or not os.path.exists(CONFIG_FILE):
        salvar_janelas_config_arquivo(config)

    return config


def salvar_janelas_config_arquivo(config):
    """Salva o dicionário de configuração em formato JSON no disco."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Erro ao salvar configurações de janelas em {CONFIG_FILE}: {e}")
        return False


def salvar_janelas_usuario(servicos_atualizados):
    """
    Atualiza as configurações das janelas recebidas do usuário (via modal).
    O usuário pode alterar: ativo, inicio_dia, inicio_hora, fim_dia, fim_hora.
    Nomes de serviços e armadores são mantidos intactos para evitar erros de digitação.
    """
    config_atual = carregar_janelas_config()

    for item in servicos_atualizados:
        joint = (item.get("joint") or "").strip().upper()
        if not joint:
            continue

        if joint not in config_atual:
            # Caso não exista previamente, cria com dados informados
            config_atual[joint] = {
                "joint": joint,
                "nome": item.get("nome", joint),
                "armadores": item.get("armadores", "Não especificado"),
                "cor": item.get("cor", "info"),
                "ativo": bool(item.get("ativo", False)),
                "inicio_dia": int(item.get("inicio_dia", 0)),
                "inicio_hora": item.get("inicio_hora", "00:00"),
                "fim_dia": int(item.get("fim_dia", 0)),
                "fim_hora": item.get("fim_hora", "00:00"),
                "novo": False
            }
        else:
            # Atualiza apenas os parâmetros operacionais de tempo e ativação
            config_atual[joint]["ativo"] = bool(item.get("ativo", False))
            config_atual[joint]["inicio_dia"] = int(item.get("inicio_dia", 0))
            config_atual[joint]["inicio_hora"] = item.get("inicio_hora", "00:00")
            config_atual[joint]["fim_dia"] = int(item.get("fim_dia", 0))
            config_atual[joint]["fim_hora"] = item.get("fim_hora", "00:00")
            # Ao ser salvo pelo usuário, o status de "novo" é removido
            config_atual[joint]["novo"] = False

        # Atualiza a descrição textual legível
        if config_atual[joint]["ativo"]:
            config_atual[joint]["descricao"] = _montar_descricao(
                config_atual[joint]["inicio_dia"],
                config_atual[joint]["inicio_hora"],
                config_atual[joint]["fim_dia"],
                config_atual[joint]["fim_hora"]
            )
        else:
            config_atual[joint]["descricao"] = "Janela inativa"

    salvar_janelas_config_arquivo(config_atual)
    return config_atual


def sincronizar_servicos_com_api(todos_lineup):
    """
    Varre a lista de navios retornada pela API do Rio Brasil Terminal.
    Se encontrar qualquer 'joint' que ainda não esteja no arquivo de configuração,
    adiciona-o automaticamente com os nomes e operadoras extraídos da própria API.
    Assim, novos serviços ficam prontos para o usuário definir apenas dia e hora.
    """
    config = carregar_janelas_config()
    novos_detectados = False

    for item in todos_lineup:
        joint = (item.get("joint") or "").strip().upper()
        if not joint:
            continue

        if joint not in config:
            service_name = (item.get("serviceName") or "").strip()
            operator = (item.get("operator") or "").strip()

            nome_final = service_name if service_name else joint
            armador_final = operator if operator else "Extraído da API"

            # Auto-adiciona o serviço detectado na API
            config[joint] = {
                "joint": joint,
                "nome": nome_final,
                "armadores": armador_final,
                "cor": "info",
                "ativo": False, # Aguarda configuração do usuário
                "inicio_dia": 0,
                "inicio_hora": "00:00",
                "fim_dia": 0,
                "fim_hora": "00:00",
                "descricao": "Novo serviço detectado na API (aguardando horários)",
                "novo": True # Destaca visualmente na interface
            }
            novos_detectados = True
            print(f"[Lineup Auto-Sync] Novo serviço marítimo detectado na API: {joint} ({nome_final})")

    if novos_detectados:
        salvar_janelas_config_arquivo(config)

    return config


def verificar_status_janela(joint, dt, manobra):
    """
    Avalia se a manobra de Entrada ('E') está dentro ou fora da janela semanal de atracação
    de acordo com as configurações ativas no arquivo de persistência.
    Retorna (status, descricao, texto_tooltip).
    """
    if not joint or not dt:
        return None, None, None

    config = carregar_janelas_config()
    info = config.get(joint)

    if not info or not info.get("ativo", False):
        return None, None, None

    desc = info.get("descricao") or _montar_descricao(
        info.get("inicio_dia", 0),
        info.get("inicio_hora", "00:00"),
        info.get("fim_dia", 0),
        info.get("fim_hora", "00:00")
    )

    # O foco da janela oficial de atracação é na manobra de Entrada (E)
    if manobra != "E":
        return None, desc, f"Janela Oficial: {desc}"

    try:
        # Extrai horas e minutos de início e fim
        h_ini, m_ini = map(int, str(info.get("inicio_hora", "00:00")).split(":"))
        h_fim, m_fim = map(int, str(info.get("fim_hora", "00:00")).split(":"))

        # Domingo = 0, Segunda = 1, ..., Sábado = 6
        dia_semana_domingo_0 = (dt.weekday() + 1) % 7
        minutos_navio = dia_semana_domingo_0 * 1440 + dt.hour * 60 + dt.minute

        inicio_min = int(info.get("inicio_dia", 0)) * 1440 + h_ini * 60 + m_ini
        fim_min = int(info.get("fim_dia", 0)) * 1440 + h_fim * 60 + m_fim

        # Avaliação de intervalo dentro da mesma semana ou virando a semana
        if inicio_min <= fim_min:
            na_janela = (inicio_min <= minutos_navio <= fim_min)
        else:
            # Vira a semana (ex: Sábado para Domingo)
            na_janela = (minutos_navio >= inicio_min or minutos_navio <= fim_min)

        if na_janela:
            return "NA_JANELA", desc, f"Dentro da Janela Oficial ({desc})"
        else:
            return "FORA_DA_JANELA", desc, f"Fora da Janela Oficial (Programado: {desc})"

    except Exception as e:
        print(f"Erro ao verificar janela para {joint}: {e}")
        return None, desc, f"Janela Oficial: {desc}"


def obter_lineup_rio_brasil():
    """
    Chama a API do Rio Brasil Terminal, sincroniza serviços automaticamente
    e retorna um dicionário com os navios e seus respectivos serviços.
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

        # Sincroniza novos serviços detectados na API com o arquivo de configuração
        config_servicos = sincronizar_servicos_com_api(todos)

        lineup_map = {}

        for item in todos:
            navio_nome = (item.get("navio") or "").strip().upper()
            if not navio_nome:
                continue

            joint = (item.get("joint") or "").strip().upper()
            service_name = (item.get("serviceName") or "").strip()
            viagem = (item.get("viagem") or "").strip()
            operator = (item.get("operator") or "").strip()

            # Obtém dados da configuração persistente ou usa fallback inteligente
            info_cadastrada = config_servicos.get(joint)
            if info_cadastrada:
                nome_exibicao = info_cadastrada["nome"]
                armadores_exibicao = info_cadastrada["armadores"]
                cor_badge = info_cadastrada.get("cor", "secondary")
            else:
                nome_exibicao = service_name if service_name else (joint if joint else "Outro")
                armadores_exibicao = operator if operator else "Não especificado"
                cor_badge = "secondary"

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

    # Aplica para navios do terminal rio brasil
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
