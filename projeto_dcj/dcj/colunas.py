"""Nomes de colunas em um só lugar: evita strings mágicas espalhadas pelo código."""


class Bruto:
    """Nomes originais do DATASUS."""

    ORIGEM_DO_ARQUIVO = "ARQUIVO_ORIGEM"

    OBITO_MUNICIPIO = "CODMUNRES"
    OBITO_NASCIMENTO = "DTNASC"
    OBITO_DATA = "DTOBITO"
    OBITO_SEXO = "SEXO"
    OBITO_IDADE = "IDADE"
    OBITO_CAUSA = "CAUSABAS"
    OBITO_NUMERO_DA_DECLARACAO = "NUMERODO"

    INTERNACAO_MUNICIPIO = "MUNIC_RES"
    INTERNACAO_NASCIMENTO = "NASC"
    INTERNACAO_DATA = "DT_INTER"
    INTERNACAO_SEXO = "SEXO"
    INTERNACAO_DIAGNOSTICO = "DIAG_PRINC"
    INTERNACAO_DIAGNOSTICO_SECUNDARIO = "DIAG_SECUN"
    INTERNACAO_NUMERO_DA_AIH = "N_AIH"

    NOTIFICACAO_AGRAVO = "ID_AGRAVO"
    NOTIFICACAO_MUNICIPIO = "ID_MN_RESI"
    NOTIFICACAO_SEXO = "CS_SEXO"
    NOTIFICACAO_ANO_NASCIMENTO = "ANO_NASC"
    NOTIFICACAO_NASCIMENTO = "DT_NASC"
    NOTIFICACAO_PRIMEIROS_SINTOMAS = "DT_SIN_PRI"
    NOTIFICACAO_DATA = "DT_NOTIFIC"
    NOTIFICACAO_CLASSIFICACAO_FINAL = "CLASSI_FIN"
    NOTIFICACAO_EVOLUCAO = "EVOLUCAO"


class Col:
    """Colunas derivadas pelo pipeline."""

    MUNICIPIO = "municipio"
    SEXO = "sexo"
    DATA_NASCIMENTO = "data_nascimento"
    ANO_NASCIMENTO = "ano_nascimento"
    MES_DIA_NASCIMENTO = "mes_dia_nascimento"
    IDADE_ANOS = "idade_anos"
    CAUSA_BASICA = "causa_basica"
    DATA_OBITO = "data_obito"
    DATA_INTERNACAO = "data_internacao"
    DIAGNOSTICO_PRINCIPAL = "diagnostico_principal"
    ID_OBITO = "id_obito"
    ID_INTERNACAO = "id_internacao"
    DIAS_ATE_OBITO = "dias_ate_obito"
    PONTOS_DECLINIO = "pontos_declinio_rapido"
    PONTOS_IDADE = "pontos_faixa_etaria"
    PONTOS_CID = "pontos_cid_generico"
    ESCORE = "escore_dcj"
    SINALIZADO = "sinalizado"
    PERIODO = "periodo"
    DATA_PRIMEIROS_SINTOMAS = "data_primeiros_sintomas"
