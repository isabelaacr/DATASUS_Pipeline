# 🧬 Pipeline DCJ: Detecção Computacional de Subnotificação no SUS

**Pipeline de pareamento determinístico (SIM x SIH x SINAN), escoragem de suspeição e validação estatística para a Doença de Creutzfeldt-Jakob (DCJ).**

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![PySUS](https://img.shields.io/badge/PySUS-2.11.7-orange.svg)
![Tests](https://img.shields.io/badge/tests-79%20passed-green.svg)
![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)

---

## 📌 Contexto Epidemiológico

A Doença de Creutzfeldt-Jakob (DCJ) é uma doença priônica rara, neurodegenerativa e invariavelmente fatal (sobrevida média de 5 meses). Apesar de ser de notificação compulsória no Brasil desde 2005, o sistema de vigilância (SINAN) apresenta limitações críticas, documentadas no Boletim Epidemiológico do Ministério da Saúde (2022) e na literatura recente (Barbosa et al., 2026):

* **Subnotificação:** Estima-se que o país tenha subnotificado mais da metade dos casos esperados.
* **Dados incompletos:** 55,8% das notificações não possuem dados de evolução (óbito/cura), e 36,3% não têm classificação final.
* **Inconsistências:** Há registros de "cura" em uma doença com 100% de letalidade, demonstrando falhas de preenchimento.

**A solução proposta:** Como o SINAN é frágil, este pipeline cruza as notificações com os registros de óbitos (SIM) e internações (SIH) do DATASUS. Utilizando regras temporais rigorosas e testes de permutação (Monte Carlo), o código filtra falsos positivos e encontra os "vínculos reais" de pacientes, permitindo uma vigilância ativa e auditável.

---

## 🚀 Funcionalidades Principais

- **Ingestão Automatizada:** Download e limpeza de dados do SIM, SIH e SINAN via `PySUS`.
- **Filtro Inteligente de UF:** Identifica e mantém apenas residentes do estado/região de interesse (via prefixo IBGE).
- **Deduplicação Crítica:** Remoção de duplicatas estruturais (o SIM bruto costuma apresentar ~50% de registros duplicados por sobreposição de arquivos nacionais/estaduais).
- **Pareamento Determinístico (SIM x SIH):** Cruzamento por chave (ano nasc., sexo, município) com travas temporais (internação obrigatoriamente antes do óbito e janela de até 365 dias).
- **Escore de Suspeição:** Pontua os pares com base em declínio fulminante, faixa etária atípica e CID genérico (mascaramento).
- **Validação Estatística:** Utiliza **Teste de Permutação** (Monte Carlo), **Teste Exato de Fisher**, **Intervalo de Wilson** e **Captura-Recaptura (Chapman)** para provar que os cruzamentos não são fruto do acaso.
- **Auditoria TabNet:** Módulo de checagem cruzada que compara os totais do pipeline com a extração oficial do DATASUS.

---

## 📊 Resultados e Métricas de Validação

Para garantir a sanidade dos resultados, os outputs do pipeline para o **CID-10: A81.0** (e CIDs genéricos mascaradores) são auditados contra a série oficial do Ministério da Saúde.

### 🦅 Recorte Regional: Rio Grande do Sul (RS), 2017–2022

* **População (Censo 2022):** 10.882.965 habitantes.
* **Esperado teoricamente:** 11 a 22 óbitos reais por DCJ/ano (65 a 131 no período).
* **Validação TabNet (Ingestão):** O pipeline deduplicado encontrou **52.345** óbitos por causa básica, contra **52.740** do TabNet oficial (margem de erro de 0,7%).
* **Pareamento SIM x SIH:** Foram gerados **640 pares finais** válidos. O teste de permutação provou que isso é altamente significativo (esperado ao acaso: 186,4; *p* = 0,0005).
* **Cruzamento SINAN x SIM:** Recuperou **18 vínculos reais** (esperado ao acaso: 0,70; *p* = 0,0005).
* **Subnotificação (Chapman):** Estimativa de **187 casos reais** (IC 95%: 106–268) no período, contra apenas 45 notificações no SINAN.
* **Escore de Suspeição:** Sinalizou 312 casos (180 na pandemia; 132 no pré-pandemia). O Teste de Fisher entre os períodos retornou *p* = 0,34, **descartando** um aumento estatisticamente significativo causado pela pandemia.

---

## 📊 Resultados Principais (Estudo de Caso: RS, 2017-2022)

O pipeline foi executado na base do Rio Grande do Sul e os resultados foram auditados estatisticamente:

| Métrica | Resultado Encontrado | Validação Estatística / Oficial |
| :--- | :--- | :--- |
| **Qualidade da Base (TabNet)** | 52.345 óbitos (causa básica) | 99,2% de concordância com o DATASUS (52.740 oficiais) |
| **Pareamento SIM x SIH** | 640 pares válidos | *p = 0.0005* (Esperado ao acaso: 186) |
| **Cruzamento SINAN x SIM** | 18 vínculos reais | *p = 0.0005* (Esperado ao acaso: 0.70) |
| **Subnotificação (Chapman)** | 187 casos estimados (IC 95%: 106-268) | Apenas 45 notificações formais no SINAN |
| **Escore de Suspeição** | 312 casos sinalizados | 180 na Pandemia vs 132 Pré-Pandemia |
| **Hipótese Pandêmica** | Não confirmada estatisticamente | *Teste de Fisher: p = 0.34* |

**Conclusão do Estudo:** A integração das bases provou que a DCJ possui um passivo histórico de subnotificação. Não houve aumento estatisticamente significativo de casos causados pela pandemia de COVID-19; o problema é estrutural (falhas de codificação de causa básica e perda de seguimento).

## 🛠️ Instalação e Uso

### 1. Requisitos e Instalação

Recomenda-se o uso de um ambiente virtual (`venv` ou `conda`).

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/DATASUS_Pipeline.git
cd DATASUS_Pipeline

# Crie e ative o ambiente virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Instale as dependências
pip install -r requirements.txt
```

### 2. Executando os Testes

O projeto conta com uma suíte de testes unitários e de integração utilizando dados sintéticos para validar os algoritmos de pareamento e permutação:

```bash
pytest projeto_dcj/tests/
```

### 3. Executando o Pipeline (CLI)

O motor de processamento foi desenhado como uma ferramenta de linha de comando (CLI). Para rodar a esteira completa (ingestão, limpeza, pareamento, escore e validação):

```bash
python -m dcj --dados ..\dados_rs_drp --populacao 10882965
```

*Isso gerará os arquivos de resultado na pasta indicada.*

### 4. Gerando a Camada Gold

Para consolidar os resultados em tabelas agregadas (prontas para o painel):

```bash
python gerar_gold.py
```

---

## 🖥️ Painel Interativo (Streamlit)

O projeto conta com uma camada de visualização interativa e auditoria, separada do motor de processamento.

Para iniciar o painel:

```bash
streamlit run painel.py
```

O painel consome apenas tabelas agregadas da camada **Gold** (em `dados_rs_drp/gold/`), garantindo a **conformidade com a LGPD** e a privacidade dos pacientes. Ele apresenta abas para:
1. **Pareamento (SIM x SIH):** Validação por permutação.
2. **SINAN x SIM:** Prova da existência de vínculos reais.
3. **Chapman:** Estimativa de casos ocultos.
4. **Escore de Suspeição:** Funil de casos sinalizados por período.
5. **Validação TabNet:** Comparação direta com os dados oficiais do DATASUS.

---

## 📂 Estrutura do Projeto

```text
├── dados_rs_drp/          # Pasta de dados (brutos, processados e Gold)
├── projeto_dcj/           # Código-fonte do pacote Python
│   ├── cli.py             # Ponto de entrada da linha de comando
│   ├── limpeza.py         # Funções de deduplicação e padronização
│   ├── pareamento.py      # Motor de linkage e travas temporais
│   ├── permutacao.py      # Testes de Monte Carlo e Fisher
│   ├── escore.py          # Regras de negócio do escore DCJ
│   └── testes/            # Suíte de testes unitários
├── painel.py              # Código do dashboard Streamlit
├── gerar_gold.py          # Script de exportação para o painel
├── auditar_tabnet.py      # Script de auditoria externa (DATASUS)
├── requirements.txt       # Dependências do projeto
└── README.md              # Este documento
```

---


## 📄 Licença

Este projeto está licenciado sob a licença MIT. Consulte o arquivo `LICENSE` para mais detalhes.
