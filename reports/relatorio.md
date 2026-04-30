# Caracterizando a Atividade de Code Review no GitHub: Um Estudo Empírico

# 1 Introdução

## 1.1 Contextualização

Code review é uma prática central da engenharia de software moderna, pois ajuda a identificar defeitos, disseminar conhecimento e aumentar a qualidade das mudanças antes de sua integração. No ecossistema do GitHub, essa prática ocorre majoritariamente por meio de *pull requests* (PRs), que registram o código proposto, as discussões, os comentários e os reviews formais associados à mudança. Compreender quais fatores influenciam a aceitação de um PR e a intensidade do processo de revisão é relevante tanto para pesquisadores quanto para desenvolvedores e mantenedores de projetos open-source.

## 1.2 Problema

Este estudo busca identificar quais características observáveis dos pull requests influenciam dois desfechos importantes do processo de code review no GitHub: **(A)** se o PR termina em `MERGED` ou `CLOSED`; e **(B)** quantos reviews formais o PR recebe. A análise é feita sob a perspectiva de fatores perceptíveis aos desenvolvedores, como tamanho da mudança, tempo de análise, qualidade contextual da descrição e volume de interações ao redor da revisão.

## 1.3 Questões de Pesquisa

O estudo é guiado pelas seguintes questões de pesquisa:

### Dimensão A — Fatores associados ao merge

- **RQ01:** O tamanho do pull request (arquivos alterados, adições e deleções) influencia seu estado final (`MERGED` vs `CLOSED`)?
- **RQ02:** O tempo de análise do pull request está associado ao seu estado final (`MERGED` vs `CLOSED`)?
- **RQ03:** O tamanho da descrição do pull request influencia seu estado final (`MERGED` vs `CLOSED`)?
- **RQ04:** O nível de interação no pull request (participantes e comentários) influencia seu estado final (`MERGED` vs `CLOSED`)?

### Dimensão B — Fatores associados ao número de reviews

- **RQ05:** O tamanho do pull request (arquivos alterados, adições e deleções) está correlacionado ao número de reviews recebidos?
- **RQ06:** O tempo de análise do pull request está correlacionado ao número de reviews recebidos?
- **RQ07:** O tamanho da descrição do pull request está correlacionado ao número de reviews recebidos?
- **RQ08:** O nível de interação no pull request (participantes e comentários) está correlacionado ao número de reviews recebidos?

## 1.4 Hipóteses Informais

Com base na literatura sobre colaboração em software e na experiência prática com revisão de código, foram formuladas as seguintes hipóteses informais:

- **H01:** PRs que são integrados tendem a ser menores do que PRs fechados sem merge. Mudanças menores costumam ser mais fáceis de compreender, revisar e aprovar, enquanto mudanças grandes podem gerar receio de risco, retrabalho ou escopo excessivo.
- **H02:** O efeito do tempo de análise sobre o merge não é trivial. PRs merged podem ter tempos moderados, pois passam por revisão real antes da integração; já PRs muito longos podem sinalizar impasse, baixa prioridade ou dificuldade técnica e acabar fechados. Portanto, espera-se diferença entre os grupos, mas sem direção totalmente óbvia.
- **H03:** PRs com descrições mais completas tendem a ser merged com maior frequência, porque fornecem contexto, motivação e instruções de validação. Uma descrição mais rica pode reduzir dúvidas dos revisores e aumentar a confiança na mudança.
- **H04:** Maior interação pode estar associada tanto a colaboração produtiva quanto a controvérsia. Ainda assim, a hipótese inicial é que PRs merged apresentem interações mais qualificadas, com comentários e participantes engajados na melhoria da proposta, enquanto PRs fechados podem morrer cedo ou acumular discussões inconclusivas.
- **H05:** PRs maiores tendem a receber mais reviews porque exigem mais esforço de inspeção e, muitas vezes, envolvem múltiplos arquivos ou áreas do sistema. Por outro lado, PRs excessivamente grandes também podem desestimular revisores; assim, espera-se uma correlação positiva fraca a moderada.
- **H06:** PRs que permanecem mais tempo em análise tendem a acumular mais reviews, já que ficam visíveis por mais tempo e oferecem maior janela para participação de diferentes revisores. Em contrapartida, durações extremas podem refletir abandono; portanto, a tendência esperada é positiva, mas não necessariamente forte.
- **H07:** Descrições mais longas e informativas devem atrair mais reviews, pois tornam o objetivo da mudança mais claro, facilitam a entrada de revisores no contexto e podem sinalizar maior cuidado do autor com o processo colaborativo.
- **H08:** Pull requests com mais comentários e participantes provavelmente terão mais reviews, pois essas variáveis representam atividade social e técnica em torno da mudança. Espera-se aqui a associação mais clara do estudo, ainda que parte dessa interação possa surgir depois dos próprios reviews.

## 1.5 Objetivos

**Objetivo principal:** Caracterizar empiricamente a atividade de code review em pull requests do GitHub, identificando fatores associados ao merge de mudanças e ao número de reviews recebidos.

**Objetivos específicos:**

1. Construir um dataset de PRs provenientes dos 200 repositórios mais populares do GitHub.
2. Coletar, para cada PR, métricas de tamanho, tempo de análise, descrição e interação.
3. Comparar os grupos `MERGED` e `CLOSED` com testes estatísticos apropriados.
4. Medir correlações entre as métricas observadas e o número de reviews.
5. Confrontar os resultados obtidos com as hipóteses informais do estudo.

---

# 2 Metodologia

Este trabalho caracteriza-se como um estudo empírico observacional com mineração de dados públicos do GitHub. O dataset é formado pelos **200 repositórios mais estrelados** que possuem **ao menos 100 pull requests** com estado final `MERGED` ou `CLOSED`. Após a seleção dos repositórios, são considerados apenas PRs com **pelo menos 1 review** e **duração mínima de 1 hora** entre criação e fechamento/merge.

A coleta ocorre em duas etapas: (1) descoberta dos repositórios elegíveis via **GitHub GraphQL API**; e (2) coleta paginada dos pull requests por repositório, também via GraphQL. A análise quantitativa utiliza o teste de **Mann-Whitney U** para a Dimensão A e a **correlação de Spearman** para a Dimensão B, sempre com **α = 0,05**.

Os detalhes completos do procedimento experimental estão documentados em [`reports/metodologia.md`](./metodologia.md).

## 2.1 Métricas analisadas

| Dimensão | Métricas |
| --- | --- |
| Tamanho | `changed_files`, `additions`, `deletions` |
| Tempo de análise | `time_to_close_hours` |
| Descrição | `body_length` |
| Interações | `participants_count`, `comments_count` |
| Variável dependente A | `state` (`MERGED` / `CLOSED`) |
| Variável dependente B | `reviews_count` |

---

# 3 Resultados

*[Resultados a serem preenchidos após coleta e análise estatística]*

### RQ01 — Tamanho vs Feedback Final
*[Resultados a serem preenchidos após análise]*

### RQ02 — Tempo de Análise vs Feedback Final
*[Resultados a serem preenchidos após análise]*

### RQ03 — Descrição vs Feedback Final
*[Resultados a serem preenchidos após análise]*

### RQ04 — Interações vs Feedback Final
*[Resultados a serem preenchidos após análise]*

### RQ05 — Tamanho vs Número de Reviews
*[Resultados a serem preenchidos após análise]*

### RQ06 — Tempo de Análise vs Número de Reviews
*[Resultados a serem preenchidos após análise]*

### RQ07 — Descrição vs Número de Reviews
*[Resultados a serem preenchidos após análise]*

### RQ08 — Interações vs Número de Reviews
*[Resultados a serem preenchidos após análise]*

---

# 4 Discussão

*[A ser preenchido após análise dos resultados]*

---

# 5 Conclusão

*[A ser preenchido após conclusão do estudo]*

---

# Referências

- GitHub. *GraphQL API Documentation*. Disponível em: <https://docs.github.com/en/graphql>.
- Spearman, C. (1904). *The proof and measurement of association between two things*.
- Mann, H. B.; Whitney, D. R. (1947). *On a test of whether one of two random variables is stochastically larger than the other*.
- [Laboratório 1 — Relatório](../../lab-1/reports/relatorio.md).
- [Laboratório 2 — Decisions](../../lab-2/docs/decisions.md).
