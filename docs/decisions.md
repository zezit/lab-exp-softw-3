# Architectural & Implementation Decisions

This document records the key decisions made throughout the project, in chronological order.

---

## D01 — GraphQL over REST for repository discovery
**Decision:** Use the GitHub GraphQL API to fetch the top 200 repositories used in the study.  
**Rationale:** A single request can retrieve all repository-level fields needed for selection and export, reducing the number of round trips and simplifying the collection pipeline.

---

## D02 — GraphQL over REST for PR collection
**Decision:** Use GraphQL (with pagination) to collect pull requests, instead of the REST API.  
**Rationale:** GraphQL allows nested data such as reviews, participants, and comments to be fetched in one request, reducing total calls and helping preserve API rate-limit budget.

---

## D03 — External `.graphql` file for repository query
**Decision:** Store the repository discovery query in `src/github_query.graphql`.  
**Rationale:** Keeping the query outside Python code improves maintainability, keeps the GraphQL easier to read and review, and enables editor syntax highlighting.

---

## D04 — Inline GraphQL for PR collection
**Decision:** Keep the pull request query embedded as a Python string constant in the collection script.  
**Rationale:** The PR query is tightly coupled to repository-specific variables (`owner` and `name`) and to the data-collection flow itself, so keeping it inline reduces indirection for this part of the pipeline.

---

## D05 — CSV as data interchange format
**Decision:** Export the collected data to `data/repos.csv` and `data/pull_requests.csv`.  
**Rationale:** CSV is universally readable, easy to inspect manually, and sufficient for a dataset with 200 repositories and a flat pull-request table.

---

## D06 — Filter: at least 1 hour duration
**Decision:** Exclude pull requests whose closing or merge timestamp is less than one hour after creation.  
**Rationale:** Very short-lived PRs are more likely to reflect automated activity, bot behavior, or instant approvals that could distort the analysis of human review behavior.

---

## D07 — Filter: at least 1 review
**Decision:** Only include pull requests with at least one registered review.  
**Rationale:** PRs without reviews do not provide a valid observation for the review-count dimension and add noise when studying code review activity.

---

## D08 — Median as central tendency measure
**Decision:** Use the median, rather than the mean, as the primary central tendency measure in all summaries.  
**Rationale:** Pull request metrics such as additions, comments, and time-to-close are typically strongly right-skewed, making the median a more robust summary statistic.

---

## D09 — Mann-Whitney U for Dimension A
**Decision:** Use the Mann-Whitney U test to compare metric distributions between `MERGED` and `CLOSED` pull requests.  
**Rationale:** The studied metrics are not expected to follow normal distributions, so a non-parametric test is more appropriate and avoids unsupported distributional assumptions.

---

## D10 — Spearman correlation for Dimension B
**Decision:** Use Spearman's rank correlation coefficient (ρ) to relate pull-request metrics to the number of reviews.  
**Rationale:** Spearman captures monotonic relationships without assuming linearity or normality and is less sensitive to outliers than Pearson correlation.

---

## D11 — Cap at 200 PRs per repository
**Decision:** Limit collection to at most 200 pull requests per repository.  
**Rationale:** Large repositories can contain thousands of PRs; a per-repository cap keeps the dataset manageable and representative while respecting GitHub API rate limits.

---

## D12 — Resume logic via `prDataCollected` flag
**Decision:** Track collection progress with a `prDataCollected` column (`true` / `false` / empty) in `repos.csv`.  
**Rationale:** PR mining may be interrupted by rate limits, network issues, or long runs; a resume flag enables idempotent continuation without restarting the entire pipeline.
