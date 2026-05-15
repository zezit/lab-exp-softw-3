# LAB03 — Caracterizando a Atividade de Code Review no GitHub

**Disciplina:** Laboratório de Experimentação de Software  
**Curso:** Engenharia de Software  
**Professor:** João Paulo Carneiro Aramuni  
**Valor:** 20 pontos

---

## Integrantes

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/moraisjo">
        <img src="https://avatars.githubusercontent.com/u/92741380?v=4" width="100px;" alt="Joana Morais"/><br />
        <sub><b>Joana Morais</b></sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/zezit">
        <img src="https://avatars.githubusercontent.com/u/95448020?v=4" width="100px;" alt="José Dias"/><br />
        <sub><b>José Dias</b></sub>
      </a>
    </td>
  </tr>
</table>

---

## Descrição

Este laboratório tem como objetivo caracterizar a atividade de code review em repositórios populares hospedados no GitHub. Por meio da API GraphQL do GitHub, serão coletados dados dos **200 repositórios mais populares**, considerando **pull requests com estado final `MERGED` ou `CLOSED`**, que tenham recebido **pelo menos 1 review** e permanecido abertos por **no mínimo 1 hora**, para responder às seguintes questões de pesquisa:

| # | Questão de Pesquisa |
|---|---|
| RQ01 | Qual a relação entre o tamanho dos PRs e o feedback final? |
| RQ02 | Qual a relação entre o tempo de análise dos PRs e o feedback final? |
| RQ03 | Qual a relação entre a descrição dos PRs e o feedback final? |
| RQ04 | Qual a relação entre as interações nos PRs e o feedback final? |
| RQ05 | Qual a relação entre o tamanho dos PRs e o número de revisões? |
| RQ06 | Qual a relação entre o tempo de análise dos PRs e o número de revisões? |
| RQ07 | Qual a relação entre a descrição dos PRs e o número de revisões? |
| RQ08 | Qual a relação entre as interações nos PRs e o número de revisões? |

### Métricas Utilizadas

| Métrica | Descrição |
|---|---|
| Tamanho | Número de arquivos; total de linhas adicionadas e removidas. |
| Tempo de Análise | Intervalo entre a criação do PR e a última atividade (fechamento ou merge). |
| Descrição | Número de caracteres do corpo de descrição (Markdown). |
| Interações | Número de participantes; número de comentários. |

---

## Entregas

### Lab03S01 — Lista de Repositórios + Script de Coleta *(5 pontos)*
- Seleção dos 200 repositórios mais populares no GitHub.
- Script para coleta automatizada dos repositórios e dos pull requests elegíveis.

### Lab03S02 — Dataset Completo + Relatório Inicial *(5 pontos)*
- Dataset consolidado com os pull requests coletados.
- Primeira versão do relatório com hipóteses para as RQs.

### Lab03S03 — Análise, Visualização e Relatório Final *(10 pontos)*
- Análise estatística e visual das duas dimensões do estudo.
- Relatório final com resultados, discussão e ameaças à validade.

---

## Configuração do Ambiente

### Pré-requisitos

- **Python 3.10+**
- **Git**
- **GitHub Personal Access Token (PAT)** com permissão de leitura pública (`public_repo`)

### Instalação

```bash
# 1. Clone o repositório
git clone <url-do-repositório>
cd <nome-do-repositório>/lab-3

# 2. Crie e ative um ambiente virtual
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# 3. Instale as dependências
pip install -r requirements.txt
```

### Configuração do Token GitHub

O projeto utiliza requisições HTTP diretas para acessar a API GraphQL do GitHub.

**Opção 1: Arquivo .env (Recomendado)**
```bash
cp .env.example .env
```

Depois, edite o arquivo `.env` e preencha com seu token:
```text
GITHUB_TOKEN=ghp_seu_token_aqui
```

**Opção 2: Variável de ambiente**
```bash
export GITHUB_TOKEN=ghp_seu_token_aqui
```

**Como obter um token:**
1. Acesse [GitHub Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens)
2. Clique em "Generate new token (classic)"
3. Selecione o escopo `public_repo`
4. Copie o token gerado e armazene-o com segurança

> **⚠️ IMPORTANTE:** Nunca versione o arquivo `.env` com seu token real.

---

## Como Executar

### 1. Coleta dos 200 repositórios mais populares

```bash
python src/01-fetch-repos.py
```

### 2. Coleta dos pull requests com reviews

```bash
python src/02-fetch-pull-requests.py
```

### 3. Análise da Dimensão A (RQ01–RQ04)

```bash
python src/03-analyze-dimension-a.py
```

### 4. Análise da Dimensão B (RQ05–RQ08)

```bash
python src/04-analyze-dimension-b.py
```

---

## Estrutura do Projeto

```text
.
├── requirements.txt
├── README.md
├── data/                          # Dados brutos coletados
│   ├── repos.csv                  # Lista dos 200 repositórios
│   └── pull_requests.csv          # Dataset de PRs coletados
├── docs/
│   ├── decisions.md               # Decisões de projeto
│   └── LABORATÓRIO 03 -...        # Especificação do laboratório
├── reports/
│   ├── figures/                   # Figuras e gráficos do estudo
│   ├── relatorio.md               # Relatório final
│   └── metodologia.md             # Metodologia detalhada
└── src/
    ├── 01-fetch-repos.py          # Script de coleta dos 200 repositórios
    ├── 02-fetch-pull-requests.py  # Script de coleta dos PRs com revisões
    ├── 03-analyze-dimension-a.py  # Análise RQ01-RQ04 (feedback final)
    ├── 04-analyze-dimension-b.py  # Análise RQ05-RQ08 (número de revisões)
    └── github_query.graphql       # Query GraphQL para busca de repositórios
```

---

## Solução de Problemas

### Erro: `GITHUB_TOKEN não encontrado`
**Problema:** O script não conseguiu localizar o token de autenticação do GitHub.

**Soluções:**
1. Crie um arquivo `.env` na raiz do projeto: `cp .env.example .env`
2. Adicione seu token ao arquivo `.env`: `GITHUB_TOKEN=ghp_seu_token_aqui`
3. Ou configure a variável de ambiente: `export GITHUB_TOKEN=ghp_seu_token_aqui`
4. Se usar `~/.bashrc`, recarregue o terminal ou execute `source ~/.bashrc`

### Erro: resposta `401` ou `403`
**Problema:** Token inválido, expirado ou sem permissões adequadas.

**Soluções:**
- Verifique se o token tem o escopo `public_repo`
- Gere um novo token em [github.com/settings/tokens](https://github.com/settings/tokens)
- Certifique-se de que o token não expirou
- Verifique se copiou o token completo

### Erro: `ModuleNotFoundError`
**Problema:** Dependências Python não instaladas no ambiente virtual.

**Solução:**
```bash
source .venv/bin/activate  # Linux/macOS
# ou
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### Erro: limite de requisições excedido
**Problema:** O limite de requisições da API do GitHub foi excedido.

**Soluções:**
- Aguarde a renovação da janela de limite de requisições
- Verifique seu limite atual em: https://api.github.com/rate_limit
- Reduza a frequência de execução dos scripts de coleta
- Utilize um token válido para aumentar o limite disponível

---

## Referências

- [GitHub GraphQL API](https://docs.github.com/en/graphql)
- [Laboratório 01](../lab-1/README.md)
- [Laboratório 02](../lab-2/README.md)
