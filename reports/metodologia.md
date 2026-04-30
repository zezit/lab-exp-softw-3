# Metodologia

## 1. Seleção do Dataset

O dataset é composto pelos **200 repositórios mais estrelados do GitHub** que atendem ao critério mínimo de possuir **pelo menos 100 pull requests com estado final `MERGED` ou `CLOSED`**. A seleção parte do pressuposto de que repositórios muito populares concentram grande volume de contribuições e, portanto, oferecem contexto adequado para estudar code review em larga escala.

Após a seleção dos repositórios, os pull requests passam por filtros adicionais para garantir comparabilidade entre os casos analisados:

- apenas PRs com estado final **`MERGED`** ou **`CLOSED`**;
- apenas PRs com **pelo menos 1 review registrado**;
- apenas PRs com **duração mínima de 1 hora** entre criação e fechamento/merge.

Esses filtros removem casos instantâneos, automatizados ou sem evidência observável de revisão.

## 2. Coleta de Dados

A coleta ocorre em **duas etapas**.

### Etapa 1 — Descoberta dos repositórios

Primeiro, a lista de repositórios elegíveis é obtida via **GitHub GraphQL API**, usando uma consulta que recupera os 200 repositórios mais estrelados e os metadados necessários para triagem e exportação.

### Etapa 2 — Coleta de pull requests

Em seguida, para cada repositório selecionado, os pull requests são coletados também via **GraphQL**, com paginação por cursor. Essa abordagem permite recuperar, em uma única estrutura de consulta, os campos necessários sobre PRs, reviews, comentários e participantes.

O resultado consolidado é exportado para arquivos CSV, permitindo inspeção manual, reprodutibilidade e análise posterior com bibliotecas estatísticas em Python.

## 3. Métricas Coletadas

| Dimensão | Métrica | Campo | Descrição |
| --- | --- | --- | --- |
| Tamanho | Arquivos alterados | `changed_files` | Número de arquivos modificados no PR |
| Tamanho | Linhas adicionadas | `additions` | Total de linhas adicionadas |
| Tamanho | Linhas removidas | `deletions` | Total de linhas removidas |
| Tempo de Análise | Tempo até fechamento | `time_to_close_hours` | Diferença, em horas, entre criação e merge/fechamento |
| Descrição | Tamanho da descrição | `body_length` | Quantidade de caracteres da descrição do PR |
| Interações | Participantes | `participants_count` | Número de participantes distintos na discussão do PR |
| Interações | Comentários | `comments_count` | Total de comentários associados ao PR |
| Variável dependente A | Estado final | `state` | Resultado final do PR: `MERGED` ou `CLOSED` |
| Variável dependente B | Número de reviews | `reviews_count` | Total de reviews registrados no PR |

## 4. Análise Estatística

A análise é organizada em duas dimensões complementares.

### Dimensão A — Fatores associados ao merge

Para comparar PRs **`MERGED`** e **`CLOSED`**, será utilizado o **teste de Mann-Whitney U**, adequado para distribuições não normais. Além da significância estatística, será reportado o **tamanho de efeito rank-biserial (`r`)**, permitindo interpretar a magnitude prática das diferenças observadas.

### Dimensão B — Fatores associados ao número de reviews

Para investigar a relação entre as métricas dos PRs e o número de reviews, será usada a **correlação de Spearman (ρ)**. Essa técnica mede associações monotônicas sem exigir linearidade ou normalidade dos dados.

Em ambos os casos, o limiar de significância adotado será **α = 0,05**.

## 5. Ferramentas

As principais ferramentas e tecnologias empregadas no laboratório são:

- **Python 3.10+**;
- **pandas** para manipulação dos dados;
- **matplotlib** e **seaborn** para visualizações;
- **scipy** para testes estatísticos;
- **GitHub GraphQL API** para mineração dos dados.
