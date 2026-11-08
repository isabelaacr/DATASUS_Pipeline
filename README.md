# 🧬 Pipeline DCJ: Cruzamento de Dados e Vigilância Epidemiológica

**Pipeline para pareamento determinístico de dados (SINAN x SIM x SIH) e escore de suspeição da Doença de Creutzfeldt-Jakob (DCJ) no Brasil.**

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Tests](https://img.shields.io/badge/tests-79%20passed-green.svg)
![PySUS](https://img.shields.io/badge/PySUS-2.11.7-orange.svg)

---

## 📌 Contexto Epidemiológico

A Doença de Creutzfeldt-Jakob (DCJ) é uma doença priônica rara, neurodegenerativa e invariavelmente fatal (sobrevida média de 5 meses). Apesar de ser de notificação compulsória no Brasil desde 2005, o sistema de vigilância (SINAN) apresenta limitações críticas, documentadas no Boletim Epidemiológico do Ministério da Saúde (2022) e na literatura recente (Barbosa et al., 2026):

*   **Subnotificação:** Estima-se que o país tenha subnotificado mais da metade dos casos esperados.
*   **Dados incompletos:** 55,8% das notificações não possuem dados de evolução (óbito/cura), e 36,3% não têm classificação final.
*   **Inconsistências:** Há registros de "cura" em uma doença com 100% de letalidade, demonstrando falhas de preenchimento.

**A solução proposta por este projeto:** Como o SINAN é frágil, este pipeline cruza as notificações do SINAN com os registros de óbitos (SIM) e internações (SIH) do DATASUS. Utilizando regras temporais e testes de permutação, o código filtra falsos positivos e encontra os "vínculos reais" de pacientes, permitindo uma vigilância ativa mais confiável.

---

## 🚀 Funcionalidades Principais

- **Ingestão Automatizada:** Download e limpeza de dados do SIM, SIH e SINAN via `PySUS`.
- **Filtro Inteligente de UF:** Identifica e mantém apenas residentes do estado/região de interesse (via prefixo IBGE).
- **Deduplicação:** Remove registros duplicados (o SIM costuma ter até 50% de duplicatas).
- **Pareamento Determinístico (SIM x SIH):** Cruza dados por chave (ano nasc., sexo, município) com travas temporais (internação antes do óbito).
- **Escore de Suspeição:** Pontua os pares com base em declínio rápido, faixa etária e CID genérico.
- **Validação Estatística:** Utiliza **Teste de Permutação** (Monte Carlo) e **Intervalo de Wilson** para provar que os cruzamentos não são fruto do acaso.
- **Cruzamento Exploratório (SINAN):** Valida a chave fraca do SINAN contra o SIM e o SIH, gerando listas para revisão médica.

---

## 📊 Parâmetros de Validação (Métricas Esperadas)

Para garantir a sanidade dos resultados gerados pelo pipeline, os outputs brutos para o código **CID-10: A81.0** (ou chaves geradas por escore) devem se alinhar às séries auditadas pelo Ministério da Saúde:

### 🇧🇷 Cenário Nacional
*   **Pico de Notificações:** O ano de 2019 representa o ápice histórico do SINAN com **174 casos suspeitos** notificados.
*   **Efeito Pandemia:** Espera-se uma redução acentuada de registros brutos nos anos de **2020 e 2021** em decorrência da sobrecarga hospitalar por Covid-19.

### 🦅 Recorte Regional: Rio Grande do Sul (RS)
*   **Volumetria Anual:** Devido à incidência global da doença (1 a 2 casos por milhão), a filtragem para o RS deve resultar em uma média estável de **10 a 20 notificações suspeitas por ano**, convertendo-se em **2 a 5 casos reais confirmados/ano**.
*   **Histórico de Confirmações:** No acumulado auditado, o estado do RS possui **35 casos confirmados**, ocupando a 5ª posição no ranking nacional.

---

## 🛠️ Instalação e Uso

### 1. Requisitos e Instalação

```bash
# Clone o repositório
git clone https://github.com
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
