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


if __name__ == "__main__":
    municipios = busca_municipios_tce_ce()

    if not municipios:
        raise SystemExit("Não foi possível carregar a lista de municípios.")

    ativos_df = pd.DataFrame()
    for data_referencia_doc in gerar_datas_referencia():

        print(f"Buscando ativos data: {data_referencia_doc}")

        for municipio in municipios["elements"][1:]:
            dados = busca_agentes_publicos_tce_ce(
                municipio["codigo_municipio"],
                202600,
                data_referencia_doc,
            )

            print(municipio["codigo_municipio"], data_referencia_doc)

            df = json_para_dataframe(dados)

            if not df.empty:
                df["data_referencia_doc"] = data_referencia_doc
                ativos_df = pd.concat([ativos_df, df], ignore_index=True)


    desligados_df = pd.DataFrame()
    for data_referencia_doc in gerar_datas_referencia():
        print(f"Buscando desligados data: {data_referencia_doc}")

        for municipio in municipios["elements"][1:]:
            dados = buscar_desligamentos_agentes_publicos(
                municipio["codigo_municipio"],
                202600,
                data_referencia_doc,
            )

            df = json_para_dataframe(dados)

            if not df.empty:
                df["data_referencia_doc"] = data_referencia_doc
                desligados_df = pd.concat([desligados_df, df], ignore_index=True)

    # ativos_df = (
    #     ativos_df
    #     .sort_values("data_referencia_doc")
    #     .drop_duplicates(subset=["cpf_servidor"], keep="last")
    # )

    # desligados_df = (
    #     desligados_df
    #     .sort_values("data_referencia_doc")
    #     .drop_duplicates(subset=["cpf_servidor"], keep="last")
    # )

    ativos_final = ativos_df.merge(
        desligados_df[["cpf_servidor"]],
        on="cpf_servidor",
        how="left",
        indicator=True,
    )

    ativos_final = ativos_final.loc[
        ativos_final["_merge"] == "left_only"
    ].drop(columns="_merge")

    # Garante que os códigos sejam tratados como texto
    ativos_final["codigo_ingresso"] = ativos_final["codigo_ingresso"].astype(str).str.strip()
    ativos_final["codigo_vinculo"] = ativos_final["codigo_vinculo"].astype(str).str.strip()
    ativos_final["situacao_funcional"] = ativos_final["situacao_funcional"].astype(str).str.strip()

    # Mantém apenas as situações desejadas
    ativos_final = ativos_final[
        ativos_final["situacao_funcional"].isin(["1", "4", "5", "9"])
    ].copy()

    MAPA_INGRESSO = {
        "C": "Nomeação de Cargo Efetivo",
        "M": "Admissão em Emprego Público",
        "N": "Nomeação de Cargo Comissionado",
        "T": "Contratação por Tempo Determinado",
        "R": "Regime Especial",
        "G": "Estágio ou Bolsa",
        "E": "Eleição",
        "P": "Beneficiário de Pensão",
        "V": "Convênio",
        "S": "Cargo Político Administrativo",
    }

    # Tradução do vínculo
    MAPA_VINCULO = {
        "J": "Cargo Efetivo",
        "M": "Emprego Público",
        "E": "Cargo Comissionado",
        "L": "Cargo Eletivo",
        "F": "Estagiário ou Bolsista",
        "H": "Prestação de Serviço (Contratos)",
        "I": "Regime Especial",
        "P": "Pensionista",
        "V": "Conveniado",
        "S": "Cargo Político Administrativo",
        "A": "Cargo Efetivo – Atividade Adicional",
        "B": "Emprego Público – Atividade Adicional",
        "C": "Prestação de Serviço (Contratos) – Atividade Adicional",
        "D": "Regime Especial – Atividade Adicional",
    }

    # Tradução da situação funcional
    MAPA_SITUACAO = {
        "1": "Ativo",
        "4": "Em Disponibilidade",
        "5": "À Disposição",
        "9": "Disponibilizado por Convênio",
    }

    MAPA_PROGRAMA_SOCIAL = {
        "1": "PIS",
        "2": "PASEP",
        "3": "Não se aplica"
    }

    # Traduz os códigos
    ativos_final["codigo_ingresso"] = (
        ativos_final["codigo_ingresso"]
        .map(MAPA_INGRESSO)
        .fillna(ativos_final["codigo_ingresso"])
    )

    ativos_final["codigo_vinculo"] = (
        ativos_final["codigo_vinculo"]
        .map(MAPA_VINCULO)
        .fillna(ativos_final["codigo_vinculo"])
    )

    ativos_final["situacao_funcional"] = (
        ativos_final["situacao_funcional"]
        .map(MAPA_SITUACAO)
        .fillna(ativos_final["situacao_funcional"])
    )

    ativos_final["tipo_programa_social"] = (
        ativos_final["tipo_programa_social"]
        .map(MAPA_PROGRAMA_SOCIAL)
        .fillna(ativos_final["tipo_programa_social"])
    )

    ativos_final = ativos_final.rename(columns={
        "codigo_ingresso": "Forma de Ingresso",
        "codigo_vinculo": "Tipo de Vínculo",
        "situacao_funcional": "Situação Funcional",
        "cpf_servidor": "CPF",
        "nome_servidor": "Nome",
        "numero_matricula": "Matrícula",
        "codigo_orgao": "Órgão",
        "codigo_unidade_orcamentaria": "Unidade Orçamentária",
        "valor_carga_horaria": "Carga Horária",
        "numero_dependentes": "Dependentes",
        "data_referencia_doc": "Competência",
        "tipo_programa_social": "Programa Social",
        "nm_tipo_cargo": "Cargo",
    })

    print(f"Ativos encontrados: {len(ativos_df)}")
    print(f"Desligados encontrados: {len(desligados_df)}")
    print(f"Ativos após cruzamento: {len(ativos_final)}")

    arquivo_externo = "LISTAGEM-20-10-26.xlsx"
    try:
        externo_df = pd.read_excel(arquivo_externo)

        externo_df.columns = (
            externo_df.columns
            .str.strip()
            .str.upper()
        )

        externo_df["NOME"] = (
            externo_df["NOME"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

        ativos_final["Nome"] = (
            ativos_final["Nome"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

        externo_df["CPF"] = (
            externo_df["CPF"]
            .astype(str)
            .str.replace(r"\D", "", regex=True)
            .str.zfill(11)
        )

        ativos_final["CPF"] = (
            ativos_final["CPF"]
            .astype(str)
            .str.replace(r"\D", "", regex=True)
            .str.zfill(11)
        )

        encontrados_nome = ativos_final.merge(
            externo_df[["NOME"]],
            left_on="Nome",
            right_on="NOME",
            how="inner"
        )

        encontrados_cpf = ativos_final.merge(
            externo_df[["CPF"]],
            left_on="CPF",
            right_on="CPF",
            how="inner"
        )

        agentes_localizados = pd.concat(
            [encontrados_nome, encontrados_cpf],
            ignore_index=True
        )

        agentes_localizados = agentes_localizados.drop_duplicates()

        agentes_localizados = agentes_localizados.drop(
            columns=["NOME", "CPF"],
            errors="ignore"
        )

        if "codigo_municipio" in agentes_localizados.columns:
            mapa_municipios = {
                str(m.get("codigo_municipio")): (
                    m.get("nome_municipio")
                    or m.get("nome")
                    or m.get("municipio")
                    or str(m.get("codigo_municipio"))
                )
                for m in municipios["elements"][1:]
            }

            agentes_localizados["municipio"] = (
                agentes_localizados["codigo_municipio"]
                .astype(str)
                .map(mapa_municipios)
            )

            agentes_localizados["municipio"] = agentes_localizados["municipio"].fillna(
                agentes_localizados["codigo_municipio"]
            )

            agentes_localizados = agentes_localizados.drop(columns=["codigo_municipio"])

        agentes_localizados.to_excel(
            "agente_localizado.xlsx",
            index=False
        )

        print(f"Agentes localizados: {len(agentes_localizados)}")
        print("Arquivo criado: agente_localizado.xlsx")


    except FileNotFoundError:
        print(f"Arquivo '{arquivo_externo}' não encontrado.")
