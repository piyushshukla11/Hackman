/**
 * PRISM Review Intelligence - Popup Controller (MV3)
 */

document.addEventListener("DOMContentLoaded", async () => {
  // Elements
  const statusDot = document.getElementById("status-dot");
  const statusLabel = document.getElementById("status-label");
  const platformBadge = document.getElementById("platform-badge");
  const reviewsCountEl = document.getElementById("reviews-count");
  const productSkuEl = document.getElementById("product-sku");
  const btnCapture = document.getElementById("btn-capture");
  const btnPreview = document.getElementById("btn-preview");
  const resultBanner = document.getElementById("result-banner");
  const resultTitle = document.getElementById("result-title");
  const resultDesc = document.getElementById("result-desc");
  const previewDrawer = document.getElementById("preview-drawer");
  const previewList = document.getElementById("preview-list");
  const btnCloseDrawer = document.getElementById("btn-close-drawer");

  const settingsToggle = document.getElementById("settings-toggle");
  const settingsBody = document.getElementById("settings-body");
  const toggleIcon = document.getElementById("toggle-icon");
  const inputApiUrl = document.getElementById("input-api-url");
  const inputToken = document.getElementById("input-token");
  const inputTenant = document.getElementById("input-tenant");
  const btnSaveSettings = document.getElementById("btn-save-settings");
  const btnUseDemo = document.getElementById("btn-use-demo");

  let detectedReviews = [];

  // Load stored settings
  chrome.storage.local.get(["apiUrl", "token", "tenantId"], (items) => {
    inputApiUrl.value = items.apiUrl || "http://localhost:8000";
    inputToken.value = items.token || "demo-token";
    inputTenant.value = items.tenantId || "default";

    checkBackendHealth(inputApiUrl.value);
  });

  // Check Backend Health
  async function checkBackendHealth(baseUrl) {
    try {
      const resp = await fetch(`${baseUrl.replace(/\/$/, "")}/health`, { method: "GET" });
      if (resp.ok) {
        const data = await resp.json();
        statusDot.className = "status-dot online";
        statusLabel.innerText = "PRISM Online";
      } else {
        statusDot.className = "status-dot offline";
        statusLabel.innerText = "Error (HTTP " + resp.status + ")";
      }
    } catch (e) {
      statusDot.className = "status-dot offline";
      statusLabel.innerText = "Backend Offline";
    }
  }

  // Scan current tab
  async function scanActiveTab() {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab || !tab.id) return;

      chrome.tabs.sendMessage(tab.id, { action: "DETECT_REVIEWS" }, (response) => {
        if (chrome.runtime.lastError || !response) {
          platformBadge.innerText = "Page Ready";
          productSkuEl.innerText = tab.title ? tab.title.slice(0, 45) + "..." : "Active Tab";
          return;
        }

        const count = response.count || 0;
        reviewsCountEl.innerText = count;
        platformBadge.innerText = response.siteName || "Detected";
        productSkuEl.innerText = tab.title ? tab.title.slice(0, 45) + "..." : "Active Product Page";

        if (count > 0) {
          btnCapture.removeAttribute("disabled");
          btnCapture.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            <span>Capture & Ingest ${count} Reviews</span>
          `;
        } else {
          btnCapture.setAttribute("disabled", "true");
          btnCapture.innerHTML = `<span>No Reviews Detected</span>`;
        }
      });
    } catch (err) {
      console.warn("Tab scan error:", err);
    }
  }

  // Trigger Capture & Ingestion
  btnCapture.addEventListener("click", async () => {
    btnCapture.setAttribute("disabled", "true");
    btnCapture.innerHTML = `<span>Capturing Reviews...</span>`;

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) return;

    chrome.tabs.sendMessage(tab.id, { action: "CAPTURE_REVIEWS" }, async (response) => {
      if (chrome.runtime.lastError || !response || !response.data) {
        showResult(false, "Capture Failed", "Could not scrape reviews from active tab.");
        btnCapture.removeAttribute("disabled");
        return;
      }

      const extracted = response.data;
      detectedReviews = extracted.reviews || [];

      if (detectedReviews.length === 0) {
        showResult(false, "No Reviews", "No valid review content found.");
        btnCapture.removeAttribute("disabled");
        return;
      }

      btnCapture.innerHTML = `<span>Ingesting ${detectedReviews.length} to PRISM...</span>`;

      // Dispatch to PRISM API
      const apiUrl = inputApiUrl.value.trim().replace(/\/$/, "");
      const token = inputToken.value.trim();
      const tenantId = inputTenant.value.trim() || "default";

      // Override tenant on reviews
      detectedReviews.forEach(r => { r.tenant_id = tenantId; });

      try {
        const ingestUrl = `${apiUrl}/v1/ingest/extension`;
        const headers = {
          "Content-Type": "application/json",
          "X-Tenant-ID": tenantId
        };
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }

        const apiResp = await fetch(ingestUrl, {
          method: "POST",
          headers: headers,
          body: JSON.stringify({ reviews: detectedReviews })
        });

        if (apiResp.ok) {
          const resData = await apiResp.json();
          showResult(
            true,
            "Successfully Ingested!",
            `Processed ${resData.count || detectedReviews.length} reviews through PRISM pipeline.`
          );
          renderPreview(detectedReviews);
        } else {
          const errText = await apiResp.text();
          showResult(false, `API Error (${apiResp.status})`, errText.slice(0, 100));
        }
      } catch (e) {
        showResult(false, "Network Failure", `Cannot connect to ${apiUrl}: ${e.message}`);
      } finally {
        btnCapture.removeAttribute("disabled");
        btnCapture.innerHTML = `<span>Capture & Ingest Reviews</span>`;
      }
    });
  });

  // Preview Drawer
  btnPreview.addEventListener("click", async () => {
    if (detectedReviews.length === 0) {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab && tab.id) {
        chrome.tabs.sendMessage(tab.id, { action: "CAPTURE_REVIEWS" }, (response) => {
          if (response && response.data && response.data.reviews) {
            detectedReviews = response.data.reviews;
            renderPreview(detectedReviews);
            previewDrawer.classList.remove("hidden");
          }
        });
      }
    } else {
      renderPreview(detectedReviews);
      previewDrawer.classList.toggle("hidden");
    }
  });

  btnCloseDrawer.addEventListener("click", () => {
    previewDrawer.classList.add("hidden");
  });

  function renderPreview(reviews) {
    previewList.innerHTML = "";
    reviews.slice(0, 10).forEach(r => {
      const item = document.createElement("div");
      item.className = "preview-item";
      item.innerHTML = `
        <div class="preview-item-top">
          <span class="preview-author">${r.author?.display_name || "Customer"}</span>
          <span class="preview-rating">${"★".repeat(Math.round(r.rating?.value || 5))}</span>
        </div>
        <div class="preview-text">${r.text || "No text"}</div>
      `;
      previewList.appendChild(item);
    });
  }

  function showResult(success, title, desc) {
    resultBanner.className = `result-banner ${success ? "success" : "error"}`;
    resultTitle.innerText = title;
    resultDesc.innerText = desc;
    resultBanner.classList.remove("hidden");
  }

  // Settings Toggle
  settingsToggle.addEventListener("click", () => {
    settingsBody.classList.toggle("hidden");
    toggleIcon.innerText = settingsBody.classList.contains("hidden") ? "▾" : "▴";
  });

  // Save Settings
  btnSaveSettings.addEventListener("click", () => {
    const apiUrl = inputApiUrl.value.trim();
    const token = inputToken.value.trim();
    const tenantId = inputTenant.value.trim();

    chrome.storage.local.set({ apiUrl, token, tenantId }, () => {
      checkBackendHealth(apiUrl);
      showResult(true, "Settings Saved", `Connected to ${apiUrl}`);
    });
  });

  // Reset to Demo
  btnUseDemo.addEventListener("click", () => {
    inputApiUrl.value = "http://localhost:8000";
    inputToken.value = "demo-token";
    inputTenant.value = "default";

    chrome.storage.local.set({
      apiUrl: "http://localhost:8000",
      token: "demo-token",
      tenantId: "default"
    }, () => {
      checkBackendHealth("http://localhost:8000");
    });
  });

  // Initial tab scan
  scanActiveTab();
});
