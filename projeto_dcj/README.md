# Pipeline DCJ: pareamento SIM x SIH e escore de suspeição

## Uso (VS Code)

1. `python -m venv .venv`, ative o ambiente e rode `pip install -r requirements.txt`.
2. Aponte para os dados (pasta `dados_rs_drp`): `export DCJ_DADOS=~/dados_rs_drp`
   (PowerShell: `$env:DCJ_DADOS = "D:\dados_rs_drp"`) ou use `--dados <pasta>`.
3. Rode tudo: `python -m dcj`. Para baixar antes: `python -m dcj --baixar`.
   Com `--populacao N` (habitantes da UF) a validação compara óbitos A81.0 com o esperado do Boletim.
4. Uma etapa só: `python -m dcj --etapa pareamento` (limpeza, pareamento, escore, validacao, sinan).
5. Tabelas e gráfico: abra `relatorio.ipynb` (só lê os resultados, não recalcula).
6. Testes: `python -m pytest` (79 testes, dados sintéticos, sem rede).

Brutos esperados: `sim/sim_rs_AAAA.parquet`, `sih/sih_rs_AAAAMM.parquet` e `sinan/sinan_rs_AAAA.parquet`. Qualquer outro
arquivo nessas pastas (como `*_PRONTO_LINKAGE.parquet`) é ignorado de propósito.

## Módulos (um propósito por arquivo)

| Módulo | Responsabilidade |
|---|---|
| `configuracao.py` | parâmetros imutáveis do estudo (`Configuracao`, `RegrasDoEscore`) |
| `colunas.py` | nomes de colunas brutas e derivadas |
| `padronizacao.py` | funções puras: município, datas, sexo, idade, CID |
| `funil.py` | contagem de linhas por etapa de limpeza |
| `arquivos.py`, `armazenamento.py` | leitura e gravação (única camada com I/O de dados) |
| `limpeza.py` | UF, duplicatas, janela de anos; uma `EspecificacaoDaBase` por base |
| `pareamento.py` | chave, travas temporais, 1 internação por óbito |
| `escore.py` | escore, resumo por período, Wilson, Fisher, taxa normalizada |
| `permutacao.py` | quanto o acaso produziria, com as mesmas travas |
| `concordancia.py`, `cobertura.py` | Kappa; auditoria da ingestão e cobertura por ano |
| `ingestao.py` | download via PySUS (injeção de dependência, falhas retornadas) |
| `sinan.py` | cruzamentos SINAN x SIM e SINAN x SIH (chave fraca, validação temporal) |
| `etapas.py`, `cli.py` | orquestração e linha de comando |

## Decisões de método (mudaram em relação ao notebook; os números vão mudar)

1. Ano de nascimento vem da data real, não de `ano do arquivo - idade` (erra em 1 ano).
2. Sexo do SIH: 3 = F. Confira no notebook antigo: `df_sih_temp["SEXO"].value_counts()`.
3. Sem `recordlinkage`: com igualdade exata era só um merge. Descreva como pareamento determinístico por blocagem.
4. Funil inclui janela de anos; deduplicação por `NUMERODO`/`N_AIH` quando existirem.
5. Permutação igual com igual: mesmas travas e mesma deduplicação 1:1 nos dados embaralhados.

## Referência epidemiológica

Fonte: Boletim Epidemiológico, SVS/MS, vol. 53, n. 39, out. 2022 (doença de Creutzfeldt-Jakob). Valores em `dcj/referencias.py`.

| Uso no código | Valor do Boletim | Página |
|---|---|---|
| Óbitos esperados (`--populacao N`) | 1 a 2 mortes por milhão por ano | 12 |
| Faixa etária alternativa do escore | 55 a 74 anos = 60,2% das notificações suspeitas | 18 |
| Justificativa da sensibilidade | 65 anos ou mais = 44,2% (a faixa 30-64 os exclui) | 21 |
| Limites do SINAN | 36,3% sem classificação final; 55,8% sem evolução | 15, 17 |

Saídas novas: `escore_sensibilidade_faixa_etaria.csv` (sinalizados por faixa, mesmos pares) e
`obitos_a810_vs_esperado.csv` (só com `--populacao`). O Boletim trata de notificações **suspeitas**, não de casos
confirmados; óbitos abaixo do esperado também podem refletir cobertura incompleta do SIM, não só mascaramento.

## PySUS (módulo `dcj/fonte_pysus.py`)

Baseado na documentação do PySUS 2.x (pysus.readthedocs.io, versão 2.11.7). Para cada base o código tenta, em ordem,
`pysus.ftp.sim/sih/sinan(..., as_dataframe=True)`, as funções planas legadas (`pysus.sim`) e o cliente `PySUS.query`.
Se todas falharem, o erro mostra a versão instalada e o motivo de cada tentativa. O SINAN usa o código de agravo `DCRJ`
(a documentação só cita DENG e ZIKA como exemplo; `python -m dcj --verificar-pysus` tenta confirmar o DCRJ).
Nunca foi executado contra o PySUS real, só contra versões simuladas nos testes.

## Cruzamento com o SINAN (etapa `sinan`)

Entrada: `sinan/sinan_rs_AAAA.parquet`, baixado por `--baixar` (PySUS, agravo `DCRJ`, arquivo nacional filtrado para
residentes da UF e CID A81). Sem esses arquivos a etapa é ignorada com aviso. Regras do notebook original:
chave ano de nascimento + sexo + município; óbito >= primeiros sintomas; internação >= primeiros sintomas - 30 dias.
Se o PySUS não listar o agravo `DCRJ`, o `--baixar` registra a falha por ano; nesse caso baixe `DCRJBRAA.dbc` do
FTP do DATASUS, converta como no notebook e salve como `sinan_rs_AAAA.parquet` (colunas `ID_AGRAVO`, `CS_SEXO`,
`ID_MN_RESI`, `ANO_NASC`, `DT_SIN_PRI`).
Saídas: `sinan_resumo.csv`, `sinan_x_sim_validos.csv`, `sinan_x_sih_validos.csv`. A chave é fraca (sem dia e mês de
nascimento): trate os cruzamentos como lista para revisão manual, não como estimativa.

## Validação do cruzamento SINAN x SIM (etapa `validacao_sinan`)

Os 348 pares do notebook vinham de um merge só pela chave, sem trava temporal; o v2 aplica óbito >= sintomas e uma
janela de sobrevida de 1 ano (Boletim DCJ), então os números serão menores. A permutação embaralha o ano de nascimento
dos óbitos dentro de cada bloco (município, sexo) e refaz o cruzamento: `permutacao_sinan.csv` compara observado e
acaso por etapa. A primeira etapa tem p = 1 por construção (o embaralhamento preserva as contagens por ano); o que
discrimina são as etapas temporais. Só interprete `sinan_individuos.csv` e `sinan_perfil_individuos.csv` (um óbito
por chave e data) se essas etapas tiverem p pequeno. `sinan_resumo.csv` traz `notificacoes_brutas` para você ver
quantas foram descartadas por sexo fora de M/F, ano de nascimento ou sintomas ausentes.

Antes do primeiro `--baixar`: `python -m dcj --verificar-pysus` mostra quais APIs o PySUS instalado oferece.

## Na primeira execução com dados reais

- Funil: 31.722 → 13.020 → 6.519 (bruto → residentes do RS → sem duplicata) valem para o download antigo do notebook.
  Se o PySUS já entregar só residentes, o primeiro passo virá próximo de 13 mil e o filtro de UF será neutro: isso é
  estrutural, não erro (não confirmei o que o PySUS filtra). Compare a partir do passo de residentes; a janela de anos
  pode tirar mais algumas linhas.
- `cobertura_por_ano.csv`: não reporte diferença entre períodos se a cobertura estiver desigual;
  use `escore_taxa_normalizada.csv`.
- `permutacao.csv`: se o `p_valor_unilateral` da última linha não for pequeno, os pares não se distinguem do acaso.
- Sinalizados são casos para revisão clínica. Kappa baixo entre CID da internação e causa do óbito não é erro.
- Testado em pandas 3.0 (sandbox); `pandas>=2.2` declarado, não rodado em 2.2 aqui.
