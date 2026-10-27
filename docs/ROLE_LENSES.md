# PRISM Role Lenses Specification

## 1. Concept: Lenses, Not Permission Silos

In PRISM, **Role Lenses** are **not** access control gates. Every authenticated team member has access to the full dataset. A Role Lens is a specialized analytical viewport that reorganizes the exact same classified backend outputs to answer the specific questions of a particular department.

A global role lens selector in the top bar switches views instantly:
`[ QA ]  [ Operations ]  [ Support ]  [ Marketing ]  [ Leadership ]`

---

## 2. Lens Specifications

### 2.1 QA & Engineering Lens
* **Primary Questions**: Which batch is failing? What is the physical failure mechanism? Did the recent packaging or firmware revision resolve the issue?
* **Featured Components**:
  - **Review X-Ray**: Forensic view of reviewer phrasing, anchor cosine similarities, and text/rating tensions.
  - **Confidence Waterfall**: Deconstruction of statistical evidence and semantic consistency.
  - **Batch Capsule Inspector**: Lists all affected batch codes (`B-0716`), manufacturing dates, and warehouse origins ($W_2$).
  - **Version Lens (`/compare?lens=version`)**: Before/after analysis of engineering modifications.

### 2.2 Operations & Logistics Lens
* **Primary Questions**: Are damages happening in warehouse transit or couriers? Is one marketplace seller mishandling inventory? Are ingestion sources lagging?
* **Featured Components**:
  - **Batch Flow Map**: Sankey diagram connecting manufacturing, warehouse $W_2$, and delivery regions.
  - **Channel Comparison (`/compare?lens=channel`)**: Detects channel-specific defects (e.g. Amazon seller packing vs. brand direct).
  - **Source Health Monitor (`/sources`)**: Real-time volume anomalies, API lag, and schema drift across all 6 simulated storefronts.

### 2.3 Customer Support & CX Lens
* **Primary Questions**: Which safety hazards require immediate escalation? Which customers need verification surveys?
* **Featured Components**:
  - **Serious Safety Queue (`/serious`)**: Prioritized triage of electric shock, smoke, battery swelling, or burn complaints with one-click escalation to Slack.
  - **Closed-Loop Investigations (`/investigations`)**: Survey threads dispatched to consenting customers with live response tracking.
  - **Review Drilldown**: Paginated, filterable review browser with sentiment polarity filters.

### 2.4 Marketing & Brand Lens
* **Primary Questions**: What features are customers praising? How do customer perceptions differ between Amazon and Flipkart? What is the impact of product revisions on star ratings?
* **Featured Components**:
  - **Praise Clusters**: Highlights positive sentiment clusters to extract customer testimonials and ad copy.
  - **Site Performance Matrix**: Side-by-side comparison of ratings, sentiment, and volume across channels.
  - **Headline Health Score**: Portfolios of products with Steam-style sentiment summaries.

### 2.5 Executive & Leadership Lens
* **Primary Questions**: What is the overall health index? What are our top 3 risk exposures? What is the quantified financial lead-time advantage?
* **Featured Components**:
  - **One-Line Risk Brief**: Executive summary generated from top active issues.
  - **Forensic Lead-Time Headline**: Demonstrates how PRISM flagged defects 15 days ahead of customer returns.
  - **One-Click Company Report PDF (`/reports`)**: Clean, WeasyPrint-generated executive report download for board briefings.
