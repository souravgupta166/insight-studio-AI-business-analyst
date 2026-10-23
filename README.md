# Insight Studio — AI Business Analyst

An evidence-driven business analytics platform built with Python, Streamlit, and DuckDB to investigate e-commerce KPIs, revenue trends, and sales anomalies.

## Overview

Insight Studio turns business questions into structured analytical investigations. Instead of relying on unsupported AI-generated numbers, the application uses analytical tools, data validation, and evidence checks to produce explainable results.

The project uses the Brazilian Olist e-commerce dataset for its business analytics workflows.

## Key Features

- **KPI Analysis:** Retrieve and examine business performance metrics.
- **Revenue Analysis:** Reconcile revenue figures and investigate differences.
- **Trend Analysis:** Explore changes in business performance over time.
- **Anomaly Investigation:** Examine unusual sales or revenue patterns and their potential drivers.
- **Evidence Validation:** Validate analytical outputs before presenting findings.
- **Interactive Dashboard:** Explore the analytical workflows through a Streamlit interface.
- **Automated Tests:** Validate key analytics, tools, schemas, and orchestration logic.

## Technology Stack

- Python
- Streamlit
- DuckDB
- Pandas and NumPy
- Pydantic
- SQLGlot
- Plotly
- Pytest

## Project Structure

```text
ai-business-analyst/
├── data/
│   ├── raw/                 # Local source datasets (not committed)
│   └── processed/           # Local database and processed data (not committed)
├── src/
│   ├── agent/               # Question orchestration and evidence validation
│   ├── analytics/           # KPI, revenue, trend, and anomaly analysis
│   ├── data/                # Data profiling and validation
│   ├── database/            # Data loading and database validation
│   ├── tools/               # Analytical tools used by the agent
│   └── ui/                  # Streamlit application
├── tests/                   # Automated tests
├── .gitignore
├── requirements.txt
└── README.md
```

## Getting Started

### 1. Prerequisites

Install a compatible Python version and Git. The project has been developed and tested locally; check your installed Python version before creating the environment.

### 2. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd ai-business-analyst
```

### 3. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 5. Prepare the data

The raw datasets and local DuckDB database are intentionally excluded from Git. Obtain the Olist dataset from its legitimate source, place the required CSV files under `data/raw/`, and follow the project's data-loading workflow to create the local database.

The exact required files and database preparation steps should be confirmed against the data-loading code before running the application.

### 6. Run the application

```powershell
streamlit run src/ui/app.py
```

### 7. Run the tests

```powershell
python -m pytest -q
```

## Analytical Approach

The project separates business-question orchestration from the analytical calculations.

1. **Question orchestration:** The agent layer coordinates the requested analytical workflow.
2. **Specialized tools:** KPI, trend, and anomaly tools delegate to focused analytical modules.
3. **Data validation:** Data and database validation modules help check inputs and data quality.
4. **Evidence validation:** Analytical results are checked before they are presented.
5. **Business interpretation:** The interface presents findings and supporting evidence where available.

The exact calculations, assumptions, validation rules, and limitations are defined in the source code and should be reviewed alongside the results.

## Testing

Run the automated test suite with:

```powershell
python -m pytest -q
```

Tests cover the agent schemas, analytics, evidence validation, analytical tools, and orchestration.

## Data and Reproducibility

This repository does not include the raw datasets or the generated DuckDB database. Results depend on the data available locally and the database preparation process. For reproducible results, use the intended source data and document any changes to the loading or analytical workflows.

## Current Limitations

- Results depend on the completeness and quality of the local dataset.
- Analytical findings should be interpreted within the assumptions of the implemented methods.
- The application should not be assumed to support every possible business question.
- Setup and data preparation may require additional documentation as the project evolves.

## License

A license has not yet been specified. Add an appropriate license before redistributing the project or inviting others to reuse it.
