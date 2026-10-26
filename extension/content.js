/**
 * PRISM Review Intelligence - Content Script (MV3)
 * Scrapes customer reviews with photos, ratings, and batch context from active e-commerce pages.
 */

(() => {
  let siteProfiles = null;
  let activeProfile = null;
  let detectedReviewsCount = 0;

  // Embedded default site profiles for zero-latency execution
  const DEFAULT_PROFILES = [
    {
      name: "Amazon",
      domains: ["amazon.in", "amazon.com", "amazon.co.uk", "amazon.de"],
      container: "[data-hook='review'], div.a-section.review",
      title: "[data-hook='review-title'] span:not(.a-icon-alt), .review-title",
      text: "[data-hook='review-body'] span, .review-text-content span",
      rating: "i[data-hook='review-star-rating'] span, i[data-hook='cmps-review-star-rating'] span, .a-icon-alt",
      author: "[data-hook='genome-widget'] .a-profile-name, .a-profile-name",
      date: "[data-hook='review-date'], .review-date",
      verified: "[data-hook='avp-badge'], .a-color-state",
      media: "img.review-image-tile, .review-image-tile-section img",
      sku: "#ASIN, input[name='ASIN']"
    },
    {
      name: "Flipkart",
      domains: ["flipkart.com"],
      container: "div._27M-vq, div.cPHDOP, div.col-12-12._1q8A8-",
      title: "p._2-N8zT, p.z9E0IG, div._2-N8zT",
      text: "div.ZmyHeo, div._1mXzrF, div.t-ZTKy",
      rating: "div._3LWZlK, div.XQDdHH",
      author: "p._2sc7ZR, p._2NsDsF",
      date: "p._2sc7ZR + p, div.row._2afbiS + div.row",
      verified: "span._2mcFHG, span.YQgRqV",
      media: "div._3uDziY img, div.d5G78e img",
      sku: "meta[itemprop='sku']"
    },
    {
      name: "PRISM Simulator Sites",
      domains: ["localhost", "127.0.0.1", "prism-sim", "prism.app"],
      container: ".review-card, .review-item, [data-review], .testimonial-card",
      title: ".review-title, h4.title, .comment-title",
      text: ".review-body, .review-text, p.comment, .content",
      rating: ".review-rating, [data-rating], .stars, .rating-badge",
      author: ".reviewer-name, .author, .customer-name",
      date: ".review-date, time, .timestamp",
      verified: ".verified-badge, .badge-verified",
      batch: ".batch-code, [data-batch], .lot-number",
      media: ".review-media img, .review-photos img, .attachment img",
      sku: "[data-sku], #product-sku, .sku-value"
    },
    {
      name: "Generic E-Commerce",
      domains: ["*"],
      container: "[itemtype*='Review'], .review, .review-entry, article.comment",
      title: "[itemprop='headline'], .review-heading, h3, h4",
      text: "[itemprop='reviewBody'], .review-content, .review-description, .entry-content",
      rating: "[itemprop='ratingValue'], .rating, .score, [data-score]",
      author: "[itemprop='author'], .author-name, .reviewer",
      date: "[itemprop='datePublished'], time, .published-date",
      verified: ".verified, .buyer-status",
      media: ".review-images img, .photos img",
      sku: "[itemprop='sku'], [data-product-id]"
    }
  ];

  // Resolve active profile for current URL
  function resolveProfile() {
    const host = window.location.hostname.toLowerCase();
    for (const prof of DEFAULT_PROFILES) {
      if (prof.domains.includes("*")) continue;
      if (prof.domains.some(d => host.includes(d))) {
        return prof;
      }
    }
    return DEFAULT_PROFILES[DEFAULT_PROFILES.length - 1]; // Generic fallback
  }

  // Parse rating value to 0.5 - 5.0 scale
  function parseRating(rawText, el) {
    if (!rawText && el) {
      rawText = el.getAttribute("data-rating") || el.getAttribute("aria-label") || el.title || "";
    }
    if (!rawText) return 5.0;

    const match = rawText.match(/([0-5](?:\.[0-9]+)?)/);
    if (match) {
      let val = parseFloat(match[1]);
      if (val >= 0.5 && val <= 5.0) return Math.round(val * 2) / 2;
    }

    // Star count by elements
    if (el && el.querySelectorAll) {
      const filledStars = el.querySelectorAll(".star-filled, .fa-star, .active").length;
      if (filledStars > 0 && filledStars <= 5) return filledStars;
    }

    return 4.0; // Sensible default
  }

  // Scrape visible reviews based on active profile
  function extractReviews() {
    const profile = resolveProfile();
    const containers = Array.from(document.querySelectorAll(profile.container));
    const captured = [];

    // Fallback SKU detection
    let productSku = "SKU-AUTO-" + Math.abs(window.location.pathname.split("/").filter(Boolean).join("-").hashCode() || 101);
    const skuEl = document.querySelector(profile.sku || "#product-sku");
    if (skuEl) {
      productSku = skuEl.value || skuEl.getAttribute("content") || skuEl.innerText.trim() || productSku;
    }

    containers.forEach((card, idx) => {
      // Review Text
      const textEl = profile.text ? card.querySelector(profile.text) : null;
      const text = textEl ? textEl.innerText.trim() : card.innerText.trim().slice(0, 400);

      if (!text || text.length < 5) return; // Skip empty boilerplate cards

      // Title
      const titleEl = profile.title ? card.querySelector(profile.title) : null;
      const title = titleEl ? titleEl.innerText.trim() : null;

      // Rating
      const ratingEl = profile.rating ? card.querySelector(profile.rating) : null;
      const ratingVal = parseRating(ratingEl ? (ratingEl.innerText || ratingEl.title || ratingEl.getAttribute("aria-label")) : "", ratingEl);

      // Author
      const authorEl = profile.author ? card.querySelector(profile.author) : null;
      const authorName = authorEl ? authorEl.innerText.trim() : "Verified Customer";

      // Date
      const dateEl = profile.date ? card.querySelector(profile.date) : null;
      let reviewDate = new Date().toISOString();
      if (dateEl && dateEl.innerText) {
        const parsedD = new Date(dateEl.innerText.replace(/Reviewed in .* on /i, "").trim());
        if (!isNaN(parsedD.getTime())) {
          reviewDate = parsedD.toISOString();
        }
      }

      // Verified Buyer
      const verifiedEl = profile.verified ? card.querySelector(profile.verified) : null;
      const isVerified = !!verifiedEl;

      // Media / Photos
      const mediaList = [];
      const imgEls = profile.media ? card.querySelectorAll(profile.media) : [];
      imgEls.forEach((img, i) => {
        const src = img.src || img.getAttribute("data-src");
        if (src && !src.includes("icon") && !src.includes("pixel") && !src.includes("avatar")) {
          mediaList.push({
            media_id: `ext_med_${idx}_${i}`,
            kind: "image",
            url: src
          });
        }
      });

      // Batch Code
      let batchCode = null;
      if (profile.batch) {
        const bEl = card.querySelector(profile.batch);
        if (bEl) batchCode = bEl.innerText.trim();
      }
      if (!batchCode) {
        const batchMatch = text.match(/\b(BATCH|LOT|BCH)[-_]?[0-9]{4}[-_]?[A-Z0-9]{2,}\b/i);
        if (batchMatch) batchCode = batchMatch[0].toUpperCase();
      }

      // Assemble PRISM RawReview standard envelope
      const rawReview = {
        tenant_id: "default",
        source_id: "extension_capture",
        channel: "extension",
        kind: "review",
        source_review_id: `ext_${Date.now()}_${idx}`,
        product: {
          sku: productSku,
          name: document.title.split("|")[0].split("-")[0].trim() || "Captured Product"
        },
        rating: {
          value: ratingVal,
          scale: "5_star",
          raw_value: ratingVal
        },
        title: title,
        text: text,
        reviewed_at: reviewDate,
        author: {
          display_name: authorName,
          verified_buyer: isVerified
        },
        batch_code: batchCode,
        media: mediaList,
        provenance: {
          user_agent: navigator.userAgent,
          captured_by: "chrome_extension_mv3"
        }
      };

      captured.push(rawReview);

      // Visual feedback on page
      card.classList.add("prism-highlighted-review");
      if (!card.querySelector(".prism-captured-tag")) {
        const tag = document.createElement("div");
        tag.className = "prism-captured-tag";
        tag.innerText = "PRISM Captured";
        card.appendChild(tag);
      }
    });

    return {
      siteName: profile.name,
      reviewsCount: captured.length,
      productSku: productSku,
      reviews: captured
    };
  }

  // String hash helper for SKU auto-generation
  String.prototype.hashCode = function() {
    let hash = 0;
    for (let i = 0; i < this.length; i++) {
      hash = ((hash << 5) - hash) + this.charCodeAt(i);
      hash |= 0;
    }
    return hash;
  };

  // Inject or update in-page floating pill
  function updateFloatingPill(count, siteName) {
    let pill = document.getElementById("prism-floating-pill");
    if (!pill && count > 0) {
      pill = document.createElement("div");
      pill.id = "prism-floating-pill";
      pill.innerHTML = `
        <div id="prism-pill-dot"></div>
        <span><strong>PRISM</strong> Active &bull; <span id="prism-pill-count">${count}</span> Reviews</span>
      `;
      document.body.appendChild(pill);

      pill.addEventListener("click", () => {
        // Broadcast open request or quick capture
        chrome.runtime.sendMessage({ action: "PRISM_QUICK_CAPTURE" });
      });
    } else if (pill) {
      const countEl = document.getElementById("prism-pill-count");
      if (countEl) countEl.innerText = count;
      pill.style.display = count > 0 ? "flex" : "none";
    }
  }

  // Scan on initial page load
  function scanPage() {
    const profile = resolveProfile();
    const count = document.querySelectorAll(profile.container).length;
    detectedReviewsCount = count;
    updateFloatingPill(count, profile.name);
    return { count, siteName: profile.name };
  }

  // Listen for messages from popup or background service worker
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "DETECT_REVIEWS") {
      const info = scanPage();
      sendResponse({ status: "success", count: info.count, siteName: info.siteName });
    } else if (request.action === "CAPTURE_REVIEWS") {
      const extracted = extractReviews();
      sendResponse({ status: "success", data: extracted });
    }
    return true; // Keep message channel open for async response
  });

  // Run initial scan
  setTimeout(scanPage, 1200);
})();
