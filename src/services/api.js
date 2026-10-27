// PRISM Frontend API Service connecting to the backend

const API_BASE = '/api';

/**
 * Authenticate with the backend
 */
export async function loginUser(employeeId, password) {
  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ employee_id: employeeId, password }),
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn('[API] Backend login error, using local resolution:', err);
  }
  return null;
}

/**
 * Fetch current authenticated user
 */
export async function fetchCurrentUser() {
  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      credentials: 'include',
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn('[API] Could not fetch /auth/me:', err);
  }
  return null;
}

/**
 * Fetch dashboard data for a given product
 */
export async function fetchDashboardData(productId) {
  try {
    const res = await fetch(`${API_BASE}/dashboard/${productId}`, {
      credentials: 'include',
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn(`[API] Could not fetch dashboard for ${productId}:`, err);
  }
  return null;
}

/**
 * Fetch all alerts / serious complaints
 */
export async function fetchAlerts() {
  try {
    const res = await fetch(`${API_BASE}/alerts`, {
      credentials: 'include',
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn('[API] Could not fetch alerts:', err);
  }
  return null;
}

/**
 * Fetch leaderboard of all products
 */
export async function fetchLeaderboard() {
  try {
    const res = await fetch(`${API_BASE}/dashboard/all`, {
      credentials: 'include',
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn('[API] Could not fetch leaderboard:', err);
  }
  return null;
}

/**
 * Fetch paginated reviews for a given product
 */
export async function fetchReviews(productId, { page = 1, limit = 20, feature, sentiment, platform } = {}) {
  try {
    const params = new URLSearchParams({ page: String(page), limit: String(limit) });
    if (feature) params.append('feature', feature);
    if (sentiment) params.append('sentiment', sentiment);
    if (platform) params.append('platform', platform);

    const res = await fetch(`${API_BASE}/reviews/${productId}?${params.toString()}`, {
      credentials: 'include',
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn(`[API] Could not fetch reviews for ${productId}:`, err);
  }
  return { reviews: [], total: 0, page: 1 };
}

/**
 * Generate PDF report for product
 */
export async function generateReport(productId, platform = 'all') {
  try {
    const res = await fetch(`${API_BASE}/reports/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ product_id: productId, platform }),
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn('[API] Could not generate report:', err);
  }
  return null;
}

/**
 * Ingest a new review (used by simulation or test runner)
 */
export async function ingestReview(payload) {
  const res = await fetch(`${API_BASE}/reviews/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return await res.json();
}

/**
 * Check backend health
 */
export async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    return { status: 'offline', error: err.message };
  }
  return { status: 'offline' };
}

/**
 * Fetch 6-7 RAG diagnostic survey questions and memory processing trace
 */
export async function fetchSurveyPreview(productId = 'prod_001') {
  try {
    const res = await fetch(`${API_BASE}/survey/preview/${productId}`, {
      credentials: 'include',
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn(`[API] Could not fetch survey preview for ${productId}:`, err);
  }
  return null;
}
