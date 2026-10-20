import glob
import json
import os
import requests
import pandas as pd
from datetime import datetime


def json_para_dataframe(dados):
    if dados is None:
        return pd.DataFrame()

    elementos = dados.get("elements", [])

    if not elementos:
        return pd.DataFrame()

    return pd.json_normalize(elementos, sep="_")


def limpar_arquivos_gerados():
    arquivos = glob.glob("municipios_agentes_*.json") + glob.glob("municipios_agentes_desligamentos_*.json") + ["municipios_agentes_completo.xlsx"]

    for arquivo in arquivos:
        if os.path.exists(arquivo):
            os.remove(arquivo)
            print(f"Arquivo removido: {arquivo}")


def busca_municipios_tce_ce():
    url = "https://api-dados-abertos.tce.ce.gov.br/sim/municipios"
    response = requests.get(url)

    if response.status_code == 200:
        return response.json()

    print(f"Erro ao buscar municípios: {response.status_code}")
    return None


def busca_agentes_publicos_tce_ce(codigo_municipio, exercicio_orcamento, data_referencia_doc, start_index=0, page_size=1000):
    url = "https://api-dados-abertos.tce.ce.gov.br/sim/agentes_publicos_municipais"

    todos_registros = []
    indice_atual = start_index

    while True:
        params = {
            "codigo_municipio": codigo_municipio,
            "exercicio_orcamento": exercicio_orcamento,
            "data_referencia_doc": data_referencia_doc,
            "$start_index": indice_atual,
        }

        response = requests.get(url, params=params, timeout=30)

        if response.status_code != 200:
            print(f"Erro ao buscar agentes públicos para o município {codigo_municipio}: {response.status_code}")
            break

        dados = response.json()
        if not isinstance(dados, dict):
            break

        elementos = dados.get("elements", [])
        if not elementos:
            break

        todos_registros.extend(elementos)

        if len(elementos) < page_size:
            break

        indice_atual += page_size

    if not todos_registros:
        return None

    return {"elements": todos_registros}


def buscar_desligamentos_agentes_publicos(codigo_municipio, exercicio_orcamento, data_referencia_doc, start_index=0, page_size=1000):
    url = "https://api-dados-abertos.tce.ce.gov.br/sim/desligamentos_agentes_publicos"

    todos_registros = []
    indice_atual = start_index

    while True:
        params = {
            "codigo_municipio": codigo_municipio,
            "exercicio_orcamento": exercicio_orcamento,
            "data_referencia_doc": data_referencia_doc,
            "$start_index": indice_atual,
        }

        response = requests.get(url, params=params, timeout=30)

        if response.status_code != 200:
            print(f"Erro ao buscar desligamentos para o município {codigo_municipio}: {response.status_code}")
            break

        dados = response.json()
        if not isinstance(dados, dict):
            break

        elementos = dados.get("elements", [])
        if not elementos:
            break

        todos_registros.extend(elementos)

        if len(elementos) < page_size:
            break

        indice_atual += page_size

    if not todos_registros:
        return None

    return {"elements": todos_registros}


def gerar_datas_referencia():
    hoje = datetime.now()
    ano = hoje.year
    mes_limite = hoje.month - 1

    if mes_limite <= 0:
        ano -= 1
        mes_limite += 12

    return [f"{ano}{mes:02d}" for mes in range(1, mes_limite + 1)]


def salvar_json(dados, arquivo):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

    print(f"\nArquivo salvo com sucesso: {arquivo}")


if __name__ == "__main__":
    limpar_arquivos_gerados()
    municipios = busca_municipios_tce_ce()

    if not municipios:
        raise SystemExit("Não foi possível carregar a lista de municípios.")

    arquivos_agentes_ativos = []
    dados_unificados_agentes_ativos = []

    for data_referencia_doc in gerar_datas_referencia():
        agentes_publicos = []

        for municipio in municipios["elements"][1:]:
            agentes = busca_agentes_publicos_tce_ce(
                municipio["codigo_municipio"],
                202600,
                data_referencia_doc,
            )
            if agentes is not None:
                agentes_publicos.append(agentes)

        arquivo = f"municipios_agentes_ativos_{data_referencia_doc}.json"
        salvar_json(agentes_publicos, arquivo)
        arquivos_agentes_ativos.append(arquivo)

    for arquivo in arquivos_agentes_ativos:
        with open(arquivo, "r", encoding="utf-8") as f:
            dados = json.load(f)
            dados_unificados_agentes_ativos.extend(dados)

    with open("municipios_agentes_ativos_completo.json", "w", encoding="utf-8") as f:
        json.dump(dados_unificados_agentes_ativos, f, ensure_ascii=False, indent=4)


    arquivo_agentes_ativos = "municipios_agentes_ativos_completo.json"

    with open(arquivo_agentes_ativos, "r", encoding="utf-8") as f:
        dados = json.load(f)

    quantidade = 0

    for bloco in dados:
        elementos = bloco.get("elements", [])

        for registro in elementos:
            nome = registro.get("cpf_servidor")

            if nome:
                quantidade += 1

    print(f"Quantidade de registros agentes ativos: {quantidade}")


    arquivos_agentes_desligamentos = []
    dados_unificados_agentes_desligamentos = []

    for data_referencia_doc in gerar_datas_referencia():
        agentes_publicos_desligamentos = []

        for municipio in municipios["elements"][1:]:
            agentes = buscar_desligamentos_agentes_publicos(
                municipio["codigo_municipio"],
                202600,
                data_referencia_doc,
            )
            if agentes is not None:
                agentes_publicos_desligamentos.append(agentes)

        arquivo = f"municipios_agentes_desligamentos_{data_referencia_doc}.json"
        salvar_json(agentes_publicos_desligamentos, arquivo)
        arquivos_agentes_desligamentos.append(arquivo)

    for arquivo in arquivos_agentes_desligamentos:
        with open(arquivo, "r", encoding="utf-8") as f:
            dados = json.load(f)
            dados_unificados_agentes_desligamentos.extend(dados)

    with open("municipios_agentes_desligamentos_completo.json", "w", encoding="utf-8") as f:
        json.dump(dados_unificados_agentes_desligamentos, f, ensure_ascii=False, indent=4)


    arquivo_agentes_desligamentos = "municipios_agentes_desligamentos_completo.json"

    with open(arquivo_agentes_desligamentos, "r", encoding="utf-8") as f:
        dados = json.load(f)

    quantidade = 0

    for bloco in dados:
        elementos = bloco.get("elements", [])

        for registro in elementos:
            nome = registro.get("cpf_servidor")

            if nome:
                quantidade += 1

    print(f"Quantidade de registros agentes desligados: {quantidade}")
