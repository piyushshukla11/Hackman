# PRISM Review Intelligence — Browser Extension (Chrome MV3)

This is the production-ready **Manifest V3 Chrome Extension** for the PRISM Intelligence Engine. It enables team members and evaluators to capture customer reviews directly from live websites (Amazon, Flipkart, Shopify, or internal seller portals) and stream them into PRISM's pipeline.

---

## 🚀 Quick Setup (Load Unpacked in 30 Seconds)

1. Open **Google Chrome**, **Brave**, or **Microsoft Edge**.
2. Navigate to: `chrome://extensions/`
3. In the top right corner, enable **Developer mode** toggle.
4. Click **"Load unpacked"** in the top left.
5. Select this directory:
   ```
   c:\Workspace\code\Hackathons\PRISM\prism-new\extension
   ```
6. The **PRISM** icon will appear in your browser toolbar!

---

## 🧪 How to Test and Demo Live

### Option A: Using the Included Offline Demo Store
1. Open [`extension/demo_store.html`](./demo_store.html) in your browser.
2. Notice the in-page floating pill in the bottom right: **`PRISM Active • 4 Reviews`**.
3. Click the **PRISM extension icon** in your toolbar.
4. Click **"Capture & Ingest 4 Reviews"**.
5. All 4 reviews on the page are highlighted with a neon teal outline and labeled `PRISM Captured`.
6. The batch is sent directly to `POST /v1/ingest/extension`!

### Option B: On Live E-Commerce Pages
1. Visit any product page with reviews on **Amazon.in**, **Amazon.com**, or **Flipkart.com**.
2. Click the PRISM toolbar icon.
3. The extension automatically detects the platform profile and visible review cards.
4. Click **"Capture & Ingest to PRISM"**.

---

## ⚙️ Architecture & Features

- **Manifest V3 Compliant:** Uses lightweight service workers and non-intrusive content scripts.
- **Site Selector Profiles (`site_profiles.json`):** Dynamic CSS selector mappings for Amazon, Flipkart, Simulator Sites, and generic schema.org markup.
- **Context Capture:**
  - Review text, title, and 0.5–5.0 star rating
  - Verified buyer badge status
  - Customer review images & attachments
  - Hardware batch/lot codes (`LOT-XXXX-XX`)
  - Product SKU and title
- **Direct Backend Ingestion:** Dispatches to `POST /v1/ingest/extension` with tenant scoping and Bearer auth.
