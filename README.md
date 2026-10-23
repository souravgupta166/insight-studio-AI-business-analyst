# Insight Studio — AI Business Analyst
### An Evidence-Driven KPI Investigation & Decision Engine

**Insight Studio** is an interactive business analytics application built with Python, Streamlit, and DuckDB. It transforms raw e-commerce data into structured business investigations by combining deterministic KPI calculations, revenue reconciliation, trend analysis, anomaly detection, and evidence validation.

Rather than simply displaying charts or producing unsupported explanations, the application follows a structured analytical workflow: identify the business question, execute the relevant analytical tools, validate the evidence, and present findings with business implications.

**Live application:** https://insight-studio-ai-business-analyst-kacmqzezgfmwzis3gutsib.streamlit.app/

**GitHub repository:** https://github.com/souravgupta166/insight-studio-AI-business-analyst

---

## Table of Contents

1. Project Overview
2. The Business Problem
3. Project Objectives
4. Key Features
5. Technology Stack
6. Dataset and Data Model
7. System Architecture
8. End-to-End Analytical Workflow
9. Mathematical and Statistical Methodology
10. Revenue Decomposition
11. Anomaly Detection and Investigation
12. Evidence Validation and Reliability
13. Example Analytical Findings
14. Project Structure
15. Installation and Setup
16. Running the Application
17. Running the Tests
18. Design Decisions and Trade-offs
19. Limitations
20. Future Improvements
21. Author

---

## 1. Project Overview

Business teams often have access to dashboards containing sales, revenue, order volume, and delivery metrics. However, identifying a change in a KPI does not automatically explain what caused it, how significant it is, or what action should follow.

Insight Studio was developed to bridge that gap.

The application uses the Brazilian Olist e-commerce dataset to investigate business performance through a collection of analytical tools. Its architecture separates the calculation of business metrics from the orchestration of analytical questions and the presentation of findings.

The platform focuses on five main analytical capabilities:

- **KPI analysis:** Calculate and retrieve business performance metrics.
- **Revenue reconciliation:** Compare revenue calculations and investigate differences.
- **Trend analysis:** Measure changes in business performance across time periods.
- **Anomaly investigation:** Identify unusual movements and examine potential contributing factors.
- **Evidence validation:** Check analytical outputs before they are presented as business findings.

The objective is not to claim that every business question can be answered automatically. It is to build a transparent, testable system that answers supported questions using traceable calculations.

## 2. The Business Problem

Traditional reporting often stops at describing what happened.

For example:

- Revenue increased compared with the previous month.
- Order volume changed significantly.
- A particular month appears unusual.
- A KPI differs between two reports.

These observations raise further questions:

- Was the change driven by order volume or order value?
- Is the movement unusual compared with historical performance?
- Which components contributed to the difference?
- Are the underlying calculations consistent?
- Does the available evidence support the proposed explanation?

A reliable analytical system must distinguish between a measured result, a statistical observation, a possible explanation, and a recommendation.

Insight Studio addresses this challenge by organizing its analytical workflow around deterministic calculations, specialized tools, and validation rules.

## 3. Project Objectives

The project was designed to:

1. Build an interactive interface for business performance investigations.
2. Store and query structured e-commerce data efficiently using DuckDB.
3. Implement reusable Python modules for KPI calculations and statistical analysis.
4. Investigate changes in sales and revenue using period comparisons and decomposition.
5. Detect unusual historical movements using statistical methods.
6. validate analytical outputs before presenting findings.
7. Separate the analytical engine from the user interface.
8. Establish automated tests for core business logic and evidence handling.
9. Make analytical assumptions, calculations, and limitations easier to inspect.

## 4. Key Features

### KPI Explorer

Provides access to defined business metrics, including order counts and delivery performance, through dedicated KPI tools.

### Sales and Revenue Analysis

Examines item sales, order activity, and revenue-related calculations. Separate reconciliation logic helps investigate differences between revenue measures rather than assuming that every measure represents the same business concept.

### Monthly Trend Analysis

Compares performance across periods and calculates percentage changes to help identify meaningful movements in historical data.

### Anomaly Investigation

Identifies unusual observations and provides a structured workflow for examining the movement, its magnitude, and its possible contributing factors.

### Evidence-Based Reporting

The agent orchestration and evidence-validation layers help ensure that reports follow defined structures and that findings are supported by analytical outputs.

### Interactive Streamlit Interface

The application presents analytical workflows through a dedicated interface for navigating KPI analysis, sales performance, monthly trends, anomaly investigations, and business questions.

---

## 5. Technology Stack

| Technology | Role in the project |
|---|---|
| Python | Core application and analytical logic |
| Streamlit | Interactive web application |
| DuckDB | Local analytical database |
| Pandas | Data manipulation and analytical transformations |
| NumPy | Numerical and statistical operations |
| Pydantic | Structured data models and schema validation |
| SQLGlot | SQL parsing and query inspection |
| Plotly | Interactive data visualizations |
| Pytest | Automated testing |
| python-dotenv | Environment variable support |

The project uses a modular architecture so that the interface, analytical calculations, database operations, and evidence validation can be maintained and tested independently.

## 6. Dataset and Data Model

The project uses the Brazilian E-Commerce Public Dataset by Olist.

The dataset contains related tables describing orders, customers, products, sellers, payments, reviews, order items, and geographic information.

The local data workflow includes CSV source files and a DuckDB database.

### Main data entities

| Dataset | Analytical purpose |
|---|---|
| Orders | Order dates, status, purchase activity, delivery milestones |
| Order items | Product-level transaction values, freight, seller and order relationships |
| Payments | Payment values and payment methods |
| Customers | Customer records and geographic attributes |
| Products | Product attributes and category information |
| Sellers | Seller records and geographic attributes |
| Reviews | Customer review records and associated order information |
| Geolocation | Geographic coordinates associated with postal-code prefixes |
| Category translation | Translation of Portuguese product category names |

### Data relationships

Orders connect to order items through the order identifier. Order items connect products and sellers to individual orders. Payments and reviews can be linked to their associated orders, while customer and geographic tables provide additional context.

These relationships matter because an order can contain multiple items and can have multiple payment records. Joining tables without considering their grain can multiply rows and distort revenue or order counts.

For example, counting rows in an order-items table does not produce the same result as counting distinct orders.

**Important:** The database's local files are excluded from Git. A user cloning the repository must obtain the source data and prepare the local database before running the full application.

---

## 7. System Architecture

The application is organized into distinct layers.

```text
Business Question
       |
       v
Streamlit User Interface
       |
       v
Agent Orchestrator
       |
       +---------------------------+
       |                           |
       v                           v
Question / Tool Routing      Input Validation
       |
       v
Specialized Analytical Tools
       |
       +---------------------------+
       |             |             |
       v             v             v
      KPI          Trends       Anomalies
       |             |             |
       +-------------+-------------+
                     |
                     v
           Python Analytics Layer
                     |
                     v
               DuckDB / SQL
                     |
                     v
          Structured Analytical Results
                     |
                     v
            Evidence Validation
                     |
                     v
       Findings, Limitations and Reports
```

This is a logical representation of the architecture rather than a claim that every request executes every stage.

### Main components

**1. User interface — `src/ui/app.py`**

Provides the Streamlit interface, navigation, question selection, and presentation of analytical reports.

**2. Agent orchestration — `src/agent/orchestrator.py`**

Coordinates supported business questions and routes them to the appropriate analytical tools. Unsupported questions can be rejected explicitly rather than silently receiving an invented answer.

**3. Evidence validation — `src/agent/evidence_validation.py`**

Contains validation logic for analytical evidence and structured report outputs.

**4. Schemas — `src/agent/schemas.py`**

Defines structured data models used by the orchestration and reporting workflow.

**5. Analytics — `src/analytics/`**

Contains focused modules for KPI calculations, revenue reconciliation, sales anomaly investigation, anomaly detection, and trend analysis.

**6. Analytical tools — `src/tools/`**

Provides the tool interfaces used to retrieve KPI results, investigate trends, and examine anomalies.

**7. Data validation — `src/data/`**

Contains modules for data profiling, validation, and review investigation.

**8. Database layer — `src/database/`**

Contains the database loading and validation workflows.

---

## 8. End-to-End Analytical Workflow

A typical investigation follows these stages.

### Stage 1 — Interpret the question

The system identifies whether the question corresponds to a supported analytical workflow, such as retrieving a KPI, comparing periods, or investigating an anomaly.

### Stage 2 — Select the analytical tool

The orchestrator routes the question to a specialized tool instead of placing every calculation inside the user interface.

### Stage 3 — Retrieve and calculate the data

The selected tool obtains the necessary data through the database and analytics layers. The relevant aggregation depends on the metric being investigated.

### Stage 4 — Calculate comparisons and statistical evidence

The analytics layer computes the required metrics, comparisons, deviations, or decomposition components.

### Stage 5 — Validate the output

The validation layer checks structured outputs and the evidence associated with findings. The objective is to prevent unsupported values or explanations from being treated as verified conclusions.

### Stage 6 — Present the report

The interface presents available findings, supporting evidence, recommendations, limitations, and technical details.

This separation makes it easier to test the calculations independently of the user interface and to identify where an analytical result originated.

---

## 9. Mathematical and Statistical Methodology

This section explains the principal calculations used in the project's KPI, trend, revenue, and anomaly workflows.

The exact definitions depend on the selected metric and the relevant table grain. In particular, item-level sales, order-level revenue, payment totals, and delivered-order metrics should not be treated as interchangeable.

### 9.1 Total order count

The total number of distinct orders is:

\[
N_{\text{orders}} = |\{\text{distinct order IDs}\}|
\]

The distinct identifier is important because an order may contain several items or payment records.

A raw row count from the order-items table would instead measure item rows, not distinct orders.

### 9.2 Delivery rate

Delivery rate measures the proportion of orders classified as delivered within the chosen order population.

\[
\text{Delivery Rate} =
\frac{N_{\text{delivered orders}}}
{N_{\text{eligible orders}}}
\times 100
\]

For the historical result established in this project, the delivery rate was approximately **97.02%**, using delivered orders divided by all orders in the reported population.

Interpretation depends on the population definition. If canceled, unavailable, or otherwise ineligible orders are excluded, the denominator must be adjusted and documented accordingly.

### 9.3 Total item sales

Item-level sales can be calculated by summing the item price values for the relevant order-item records.

\[
S_t = \sum_{i \in t} \text{price}_i
\]

where:

- \(S_t\) is item sales for period \(t\).
- \(i\) represents an order-item record assigned to that period.
- \(\text{price}_i\) is the item price recorded in the dataset.

Freight, payment adjustments, and other components should not be silently added to this measure. They should be included only when the selected revenue definition explicitly requires them.

### 9.4 Average order value

Average order value measures the average revenue associated with an order.

\[
\text{AOV}_t =
\frac{R_t}{N_t}
\]

where:

- \(R_t\) is the selected order-level revenue measure for period \(t\).
- \(N_t\) is the number of distinct eligible orders in that period.

AOV must be calculated using a consistent definition of revenue and order population. Item sales divided by distinct orders may be a useful metric, but it should be labeled accordingly if it excludes freight or other components.

### 9.5 Absolute change

For a metric \(X\), the absolute change between two periods is:

\[
\Delta X = X_t - X_{t-1}
\]

A positive result represents an increase, while a negative result represents a decrease.

For example, if monthly item sales increase from R$664,219.43 to R$1,010,271.37, the absolute increase is:

\[
\Delta S =
1{,}010{,}271.37 - 664{,}219.43
\]

\[
\Delta S = \text{R\$346,051.94}
\]

This example illustrates the difference between the absolute monetary change and the percentage change.

### 9.6 Month-over-month growth

Month-over-month growth compares the current period with the immediately preceding period.

\[
\text{MoM Growth} =
\frac{X_t-X_{t-1}}{X_{t-1}}
\times 100
\]

where \(X_t\) is the current-period metric and \(X_{t-1}\) is the previous-period metric.

For item sales:

\[
\text{Sales MoM Growth} =
\frac{S_t-S_{t-1}}{S_{t-1}}
\times 100
\]

For order volume:

\[
\text{Order MoM Growth} =
\frac{N_t-N_{t-1}}{N_{t-1}}
\times 100
\]

The denominator is essential: a change of R$100,000 has a different meaning when the previous month recorded R$200,000 than when it recorded R$2 million.

When the previous-period value is zero or unavailable, percentage growth is undefined and should not be reported as an ordinary finite percentage.

### 9.7 Historical trend comparison

Monthly trend analysis organizes observations by a consistent time period and compares their values.

For each period, the analysis can use:

- The observed KPI value.
- The absolute change from the previous period.
- The percentage change from the previous period.
- The corresponding order-volume or value metric.
- The presence of unusually large deviations.

A monthly comparison is descriptive: it identifies what changed. It does not by itself establish why the change occurred or prove that the same pattern will continue.

### 9.8 Median absolute deviation

A robust measure of dispersion is the median absolute deviation (MAD).

For observations \(x_1,x_2,\ldots,x_n\), first calculate the median:

\[
m = \operatorname{median}(x_1,\ldots,x_n)
\]

Then calculate the median absolute deviation:

\[
MAD =
\operatorname{median}(|x_i-m|)
\]

Unlike standard deviation, MAD is less sensitive to extreme observations. This makes it useful when investigating historical business metrics that may contain unusually large spikes or drops.

### 9.9 Robust z-score

A common robust standardized score based on MAD is:

\[
z_i^{*} =
\frac{0.6745(x_i-m)}{MAD}
\]

where:

- \(x_i\) is the observation being evaluated.
- \(m\) is the historical median.
- \(MAD\) is the median absolute deviation.
- \(0.6745\) is a normal-consistency scaling constant.

A large absolute robust z-score indicates that the observation is far from the historical median relative to the robust dispersion estimate.

The project recorded a robust z-score of approximately **5.02** for the November 2017 sales movement. This indicates a strong statistical deviation under the robust-score calculation.

A robust score is evidence that an observation is unusual relative to the comparison distribution. It is not, on its own, proof of a business cause.

If MAD is zero, the formula cannot be applied directly. The implementation must handle that case explicitly rather than dividing by zero.

---

## 10. Revenue Decomposition

A central analytical objective is to explain a change in sales or revenue in terms of volume and average value.

Suppose a consistently defined revenue measure can be represented as:

\[
R_t = N_t \times A_t
\]

where:

- \(R_t\) is revenue in period \(t\).
- \(N_t\) is the number of eligible orders.
- \(A_t\) is average revenue per eligible order.

The total revenue change is:

\[
\Delta R = R_t - R_{t-1}
\]

The decomposition separates this difference into two components.

### 10.1 Volume effect

Using the previous period's average order value as the baseline:

\[
\text{Volume Effect} =
(N_t-N_{t-1})A_{t-1}
\]

This estimates the revenue change associated with the change in order volume while holding average order value at its previous-period level.

### 10.2 Average-value effect

Using the current period's order volume:

\[
\text{Average-Value Effect} =
N_t(A_t-A_{t-1})
\]

This captures the remaining change associated with the difference in average revenue per order.

### 10.3 Reconciliation identity

The two components add up exactly to the total change:

\[
\Delta R =
\text{Volume Effect}
+
\text{Average-Value Effect}
\]

This follows from expanding the terms:

\[
(N_t-N_{t-1})A_{t-1}
+N_t(A_t-A_{t-1})
\]

\[
=N_tA_t-N_{t-1}A_{t-1}
\]

\[
=R_t-R_{t-1}
\]

This is an accounting decomposition, not a causal model. The volume and average-value effects explain how the selected revenue measure changed under this mathematical representation; they do not establish the underlying reasons customers purchased more or spent differently.

### 10.4 Example from the project

The November 2017 investigation recorded the following decomposition:

| Component | Amount |
|---|---:|
| Total revenue change | R$346,051.94 |
| Volume effect | +R$405,055.38 |
| Average-value effect | −R$59,003.44 |
| Reconciliation difference | R$0.00 |

The interpretation is that the increase in order volume contributed more than the total observed increase, while the average-value component offset part of that gain.

The components reconcile:

\[
405{,}055.38 - 59{,}003.44
=346{,}051.94
\]

This is more informative than reporting the revenue increase alone because it separates two distinct mathematical contributors.

The decomposition is valid only when the revenue, order-count, and average-value definitions are aligned across the two periods.

---

## 11. Anomaly Detection and Investigation

Anomaly analysis is designed to identify unusual business movements and organize the evidence needed to investigate them.

### Step 1 — Identify the observation

Select the KPI and time period being investigated, such as monthly item sales.

### Step 2 — Compare against historical behavior

Compare the observation with an appropriate historical baseline. Depending on the analytical workflow, this can include the median, historical dispersion, and period-over-period change.

### Step 3 — Quantify the deviation

Calculate the absolute and relative change, alongside the available robust statistical evidence.

### Step 4 — Investigate potential contributors

Examine related metrics such as order volume and average order value. Where supported by the available data, additional breakdowns may help locate the components associated with the movement.

### Step 5 — Report the evidence and limitations

The final report should distinguish:

- The observed movement.
- The statistical evidence that it is unusual.
- The components that mathematically reconcile the movement.
- Possible explanations requiring further verification.
- Limitations caused by the data or the calculation method.

A large change is not necessarily an error or an undesirable business outcome. It may reflect genuine demand, seasonality, operational changes, data issues, or other factors that need further investigation.

### Example: November 2017

The project's historical investigation recorded:

| Metric | Result |
|---|---:|
| Item sales | R$1,010,271.37 |
| Orders | 7,544 |
| Item orders | 7,451 |
| Month-over-month sales growth | +52.1% |
| Month-over-month order growth | +62.9% |
| Robust z-score | 5.02 |

These observations show that sales and order activity increased substantially compared with the previous month and that the sales movement was statistically unusual under the robust-score analysis.

The robust score and the revenue decomposition answer different questions: one quantifies unusualness relative to a historical baseline, while the other separates the arithmetic contribution of volume and average value.

Neither calculation alone proves the business cause of the change.

---

## 12. Evidence Validation and Reliability

A business analytics application should not treat every generated statement as equally reliable.

Insight Studio includes a dedicated evidence-validation layer and structured schemas to help enforce a consistent reporting workflow.

### Why evidence validation matters

A result can be misleading even when its arithmetic is correct. Common examples include:

- Counting item rows instead of distinct orders.
- Comparing revenue measures with different definitions.
- Joining tables at incompatible grains.
- Reporting a percentage change without a valid baseline.
- Treating a statistical anomaly as proof of causation.
- Making a recommendation that is not supported by the available evidence.

The project's separation of analytics, orchestration, schemas, and validation makes these risks easier to inspect and test.

### Validation principles

The intended reporting principles are:

1. Calculate metrics using explicit analytical logic.
2. Preserve the distinction between a measurement and its interpretation.
3. Use structured outputs for report components.
4. Validate analytical evidence before presenting conclusions.
5. Communicate unsupported questions or limitations instead of inventing missing results.

Validation reduces the risk of misleading reports, but it does not guarantee that every source-data assumption or analytical interpretation is correct. Data quality and business definitions still matter.

---

## 13. Example Analytical Findings

The following results were established during the project's historical analysis. They are examples of calculated findings, not live operational metrics.

### Overall order activity

The dataset analysis recorded **99,441 total orders**.

This figure represents the total order population used in the established analysis. Any future comparison should preserve the same order identifier and population definition.

### Delivery performance

The reported delivery rate was approximately **97.02%**.

The calculation compares delivered orders with the defined order population. Its interpretation depends on the order-status and denominator rules used in the query.

### November 2017 sales investigation

The project recorded **R$1,010,271.37** in item sales for November 2017, with 7,544 orders and 7,451 item orders.

The month-over-month comparisons showed sales growth of approximately **52.1%** and order growth of approximately **62.9%**.

A robust z-score of approximately **5.02** indicated that the sales observation was unusual relative to the comparison baseline.

### Revenue-change explanation

The recorded change of **R$346,051.94** decomposed into a positive volume effect of R$405,055.38 and a negative average-value effect of R$59,003.44.

This reconciled the observed change and illustrated how an increase in volume can outweigh a decline in average value.

These historical findings depend on the data, period boundaries, metric definitions, and calculation logic used in the analysis.

---

## 14. Project Structure

```text
ai-business-analyst/
├── data/
│   ├── raw/                         # Local Olist source CSVs
│   └── processed/                   # Local DuckDB database
├── docs/                            # Project documentation
├── logs/                            # Local application logs
├── src/
│   ├── agent/
│   │   ├── evidence_validation.py   # Evidence and report validation
│   │   ├── orchestrator.py          # Question routing and workflow
│   │   └── schemas.py               # Structured report schemas
│   ├── analytics/
│   │   ├── anomaly_detection.py
│   │   ├── investigate_revenue_differences.py
│   │   ├── investigate_sales_anomaly.py
│   │   ├── kpi_engine.py
│   │   ├── reconcile_revenue.py
│   │   └── trend_analysis.py
│   ├── data/
│   │   ├── investigate_reviews.py
│   │   ├── profile_data.py
│   │   └── validate_data.py
│   ├── database/
│   │   ├── load_data.py
│   │   └── validate_database.py
│   ├── tools/
│   │   ├── anomaly_investigation_tool.py
│   │   ├── kpi_lookup.py
│   │   └── trend_analysis_tool.py
│   └── ui/
│       └── app.py                   # Streamlit application
├── tests/
│   ├── test_agent_schemas.py
│   ├── test_analytics.py
│   ├── test_anomaly_investigation_tool.py
│   ├── test_evidence_integration.py
│   ├── test_evidence_validation.py
│   ├── test_kpi_lookup.py
│   ├── test_orchestrator.py
│   ├── test_tool_output_validation.py
│   └── test_trend_analysis_tool.py
├── .gitignore
├── requirements.txt
└── README.md
```

The `data/` and `logs/` directories are local runtime resources and are not committed to the repository.

---

## 15. Installation and Setup

### Prerequisites

- Python compatible with the project's dependencies.
- Git.
- Access to the Olist dataset.
- A terminal such as PowerShell on Windows.

### Step 1 — Clone the repository

```powershell
git clone https://github.com/souravgupta166/insight-studio-AI-business-analyst.git
cd insight-studio-AI-business-analyst
```

### Step 2 — Create a virtual environment

```powershell
python -m venv .venv
```

On Windows, activate it using:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script activation, you can use the environment's Python executable directly:

```powershell
.\.venv\Scripts\python.exe --version
```

### Step 3 — Install dependencies

```powershell
python -m pip install -r requirements.txt
```

If the virtual environment is not activated, use:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Step 4 — Obtain the data

Download the Brazilian E-Commerce Public Dataset by Olist from its legitimate source and place the required CSV files in `data/raw/`.

The source files are not included in this repository. Check `src/database/load_data.py` to confirm the exact filenames, schema expectations, and local database path before loading the data.

### Step 5 — Prepare the local database

Inspect the database-loading implementation and run the project's intended data preparation workflow. Validate the resulting database before starting the application.

The DuckDB database is generated locally and is intentionally excluded from Git.

---

## 16. Running the Application

From the repository root:

```powershell
streamlit run src/ui/app.py
```

Streamlit will print a local URL in the terminal. Open that URL in a browser to access the application.

The deployed version is available at:

https://insight-studio-ai-business-analyst-kacmqzezgfmwzis3gutsib.streamlit.app/

The deployment requires access to the expected data and runtime configuration. A successful local run does not by itself guarantee that a separate deployment has the same database files or configuration.

---

## 17. Running the Tests

The project includes automated tests for the analytical modules, tool interfaces, schemas, evidence validation, and orchestration.

Run the complete test suite:

```powershell
python -m pytest -q
```

If Python is not available as a global command but the virtual environment exists, run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

### Verified test status

During development, the project passed **107 automated tests** in approximately 1.89 seconds.

This is a development test result, not a guarantee that every possible input, business question, or production deployment scenario has been tested.

The test suite is intended to provide repeatable checks of the implemented logic and reduce regressions as the application evolves.

---

## 18. Design Decisions and Trade-offs

### Deterministic calculations over unsupported estimates

Business metrics are calculated by defined analytical logic rather than being treated as values that can be safely generated by narrative text.

This improves repeatability and makes the calculation path easier to inspect.

### Specialized modules over a monolithic application

KPI calculations, revenue reconciliation, trend analysis, anomaly investigation, and evidence validation live in separate modules.

This separation makes the code easier to maintain, test, and extend.

### DuckDB for analytical queries

DuckDB provides an embedded analytical database suitable for local analysis of structured datasets without requiring a separately managed database server.

### Distinct order counts and consistent metric definitions

The data model contains multiple records associated with the same order. Calculations therefore need to respect the relevant table grain and use consistent definitions across periods.

### Statistical unusualness versus causal explanation

An anomaly score can indicate that an observation differs from historical behavior. It cannot independently establish why the observation occurred.

The project treats statistical evidence and business explanations as different parts of an investigation.

### Local data excluded from version control

The source data and processed database are excluded to avoid committing large runtime artifacts and to keep the repository focused on source code and documentation.

---

## 19. Limitations

- The project is an analytical portfolio application built around a historical public e-commerce dataset, not a live enterprise data platform.
- Findings depend on the completeness, quality, and interpretation of the source data.
- The application supports defined analytical workflows; it should not be assumed to answer every possible natural-language question.
- Anomaly detection identifies unusual behavior but does not prove a causal explanation.
- Revenue and sales calculations depend on the selected business definition and the grain of the source tables.
- The local database is not bundled with the repository, so data preparation is required for a reproducible local run.
- Historical results should not be interpreted as current business performance.
- Automated tests validate selected code paths but cannot prove that every business assumption is correct.
- No forecasting accuracy, causal inference, or production service-level guarantees are claimed by this project.

---

## 20. Future Improvements

Potential extensions include:

- More explicit data-dictionary and KPI-definition documentation.
- Additional automated reconciliation checks across orders, items, and payments.
- Configurable anomaly thresholds and historical comparison windows.
- More detailed breakdowns by product category, seller, or customer segment where supported by the data.
- Improved reporting of data-quality issues and metric limitations.
- Additional tests for missing periods, zero denominators, duplicate records, and unusual data distributions.
- Reproducible database setup scripts and documented data prerequisites.
- Continuous integration to run automated tests on each change.
- Deployment monitoring and clearer handling of missing runtime data.

These are potential future improvements rather than claims about currently implemented functionality.

---

## 21. Author

**Sourav Gupta**

GitHub: https://github.com/souravgupta166

Project repository: https://github.com/souravgupta166/insight-studio-AI-business-analyst

Live application: https://insight-studio-ai-business-analyst-kacmqzezgfmwzis3gutsib.streamlit.app/

---

*Insight Studio — turning business questions into structured, evidence-driven investigations.*
