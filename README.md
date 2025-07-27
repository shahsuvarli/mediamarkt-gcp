# MediaMarkt.de Data Pipeline (GCP)

This project implements an **end-to-end data pipeline** on **Google Cloud Platform (GCP)** to scrape product data from [MediaMarkt.de](https://www.mediamarkt.de), transform it, and create interactive business intelligence dashboards.

---

## Architecture

![Pipeline Architecture](architecture/pipeline-diagram.png)

The pipeline consists of the following components:

1. **Web Scraping (Cloud Run + Python)**
2. **File Storage (CSV in GCP Cloud Storage)**
3. **Data Transformation (BigQuery SQL + Views)**
4. **Reporting (Looker BI)**

---

## Pipeline Steps

### 1. Web Scraping – Cloud Run

- Scrapes MediaMarkt.de product data using Python scripts.
- Deployed on Cloud Run.
- Scheduled with Cloud Scheduler.

### 2. File Storage – Cloud Storage

- Scraped data is exported as CSV.
- CSV files are stored in a GCP Cloud Storage bucket.

### 3. Data Transformation – BigQuery

- BigQuery loads CSV data from Cloud Storage.
- SQL scripts clean, transform, and normalize the data.
- Data is saved as a **BigQuery view** for analytics.

### 4. Reporting – Looker

- Looker connects to the BigQuery clean view.
- Dashboards and reports are created for analytics.

---

## Technology Stack

- **Scraping:** Python, Cloud Run
- **Data Storage:** Cloud Storage (CSV)
- **Processing:** BigQuery SQL
- **Visualization:** Looker (BI)
- **Orchestration:** Cloud Scheduler
