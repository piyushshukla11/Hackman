const nodemailer = require('nodemailer');

function getBaseUrl() {
  return (process.env.SURVEY_BASE_URL || 'http://localhost:5000').replace(/\/$/, '');
}

function escapeHtml(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Renders the email body sent to Gmail/email clients.
 * Email clients strictly block <form> and <input> submissions inside emails.
 * This email presents clear preview cards and prominent action buttons to
 * open the interactive web survey or Google Docs format.
 */
function buildSurveyEmailHtml(surveyId, productName, questions) {
  const base = getBaseUrl();
  const webSurveyUrl = `${base}/api/survey/${surveyId}`;
  const gdocUrl = `${base}/api/survey/gdoc/${surveyId}`;

  const qList = Array.isArray(questions) && questions.length > 0 ? questions : [
    { question: 'Additional feedback on your experience', type: 'text', processing_note: 'General consumer feedback' }
  ];

  const questionsPreview = qList.map((item, i) => {
    const label = escapeHtml(item.question);
    const note = item.processing_note ? `<div style="font-size:11px;color:#0d9488;margin-top:3px;font-family:monospace">⚡ Root Cause Note: ${escapeHtml(item.processing_note)}</div>` : '';
    const src = item.grounded_data_source ? `<div style="font-size:11px;color:#64748b;margin-top:2px;font-family:monospace">📌 Grounded In: ${escapeHtml(item.grounded_data_source)}</div>` : '';

    return `<div style="margin-bottom:12px;padding:12px 14px;background:#f8fafc;border-left:3px solid #0d9488;border-radius:6px">
      <div style="font-size:11px;font-weight:700;color:#0d9488;text-transform:uppercase;font-family:monospace">Question ${i + 1} of ${qList.length}</div>
      <div style="font-size:13px;font-weight:600;color:#1e293b;margin-top:2px">${label}</div>
      ${note}
      ${src}
    </div>`;
  }).join('');

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Quality Investigation Follow-Up — ${escapeHtml(productName)}</title>
</head>
<body style="margin:0;padding:24px 12px;background:#f1f5f9;color:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif">
  <div style="max-width:620px;margin:0 auto;background:#ffffff;padding:32px 24px;border-radius:16px;box-shadow:0 4px 20px -2px rgba(0,0,0,0.06);border:1px solid #e2e8f0">
    
    <!-- Branding Header -->
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:16px">
      <span style="background:#0f172a;color:#f8fafc;padding:4px 10px;border-radius:6px;font-size:11px;font-weight:700;font-family:monospace;letter-spacing:0.04em">PRISM RAG FORENSICS</span>
      <span style="background:#ccfbf1;color:#0f766e;border:1px solid #99f6e4;padding:4px 8px;border-radius:6px;font-size:11px;font-weight:600">Adaptive Customer Verification</span>
    </div>

    <h1 style="font-size:20px;font-weight:700;color:#0f172a;margin:0 0 10px;line-height:1.3">
      Quick follow-up regarding your experience with <strong>${escapeHtml(productName)}</strong>
    </h1>

    <p style="font-size:14px;line-height:1.6;color:#475569;margin:0 0 20px">
      Our quality engineering team flagged a reported issue with your recent purchase. To help our engineers isolate the physical or firmware root cause, our RAG diagnostic system prepared <strong>${qList.length} quick questions</strong>.
    </p>

    <!-- Prominent Action Buttons -->
    <div style="background:#f0fdfa;border:1px solid #99f6e4;border-radius:12px;padding:20px;margin-bottom:24px;text-align:center">
      <div style="font-size:13px;font-weight:700;color:#0f766e;text-transform:uppercase;letter-spacing:0.04em;margin-bottom:12px">
        📱 Works on Phone & Computer (Choose Your View):
      </div>

      <div style="margin-bottom:12px">
        <a href="${escapeHtml(webSurveyUrl)}" target="_blank" style="display:inline-block;width:90%;max-width:340px;background:#0f172a;color:#ffffff;padding:15px 24px;border-radius:10px;font-size:16px;font-weight:700;text-decoration:none;box-shadow:0 4px 12px rgba(15,23,42,0.18)">
          👉 Open Mobile Web Survey
        </a>
      </div>

      <div style="margin-bottom:12px">
        <a href="${escapeHtml(gdocUrl)}" target="_blank" style="display:inline-block;width:90%;max-width:340px;background:#1a73e8;color:#ffffff;padding:13px 24px;border-radius:10px;font-size:15px;font-weight:600;text-decoration:none;box-shadow:0 4px 12px rgba(26,115,232,0.18)">
          📄 Open in Google Docs Format
        </a>
      </div>

      <div style="margin-top:14px;padding:10px;background:#ffffff;border-radius:8px;border:1px dashed #cbd5e1;font-size:12px;color:#334155;line-height:1.5">
        💡 <strong>Prefer to reply here?</strong> You can also just hit <strong>Reply</strong> to this email and type your answers (1 to ${qList.length}).
      </div>
    </div>

    <!-- Questions Overview -->
    <div style="margin-bottom:24px">
      <div style="font-size:12px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:10px">
        Questions Prepared by RAG Model (${qList.length} Failure-Isolation Steps):
      </div>
      ${questionsPreview}
    </div>

    <!-- Direct fallback link -->
    <div style="padding-top:16px;border-top:1px solid #e2e8f0;font-size:12px;color:#64748b;line-height:1.5">
      If the buttons do not open, copy and paste this link into your browser:<br>
      <a href="${escapeHtml(webSurveyUrl)}" style="color:#0d9488;word-break:break-all">${escapeHtml(webSurveyUrl)}</a>
    </div>

    <div style="margin-top:24px;text-align:center;font-size:11px;color:#94a3b8;font-family:monospace">
      PRISM Closed-Loop Quality Intelligence • DPDP Compliant
    </div>
  </div>
</body>
</html>`;
}

/**
 * Renders the standalone web survey page (opened in browser when clicking link).
 * Full interactive forms work 100% in the browser.
 */
function buildSurveyFormHtml(surveyId, productName, questions) {
  const base = getBaseUrl();
  const action = `${base}/api/survey/respond/${surveyId}`;
  const gdocUrl = `${base}/api/survey/gdoc/${surveyId}`;
  const qList = Array.isArray(questions) && questions.length > 0 ? questions : [
    { question: 'Additional feedback', type: 'text', processing_note: 'General consumer feedback' }
  ];

  const blocks = qList.map((item, i) => {
    const label = escapeHtml(item.question);
    const note = item.processing_note ? `<div style="font-size:11px;color:#0d9488;margin-top:4px;font-family:monospace;background:#f0fdfa;padding:4px 8px;border-radius:4px;display:inline-block">⚡ RAG Isolation: ${escapeHtml(item.processing_note)}</div>` : '';
    const src = item.grounded_data_source ? `<div style="font-size:11px;color:#64748b;margin-top:3px;font-family:monospace">📌 Grounded in: ${escapeHtml(item.grounded_data_source)}</div>` : '';
    let inputs = '';
    if (item.type === 'rating') {
      inputs = [1, 2, 3, 4, 5]
        .map(
          (n, ri) =>
            `<label style="margin-right:12px;display:inline-flex;align-items:center;gap:4px;cursor:pointer;font-size:14px;color:#334155"><input type="radio" name="q${i}" value="${n}" ${ri === 0 ? 'required' : ''}> ★ ${n}</label>`
        )
        .join('');
    } else if (item.type === 'yesno') {
      inputs =
        `<label style="margin-right:16px;display:inline-flex;align-items:center;gap:6px;cursor:pointer;font-size:14px;color:#334155"><input type="radio" name="q${i}" value="Yes" required> Yes</label>` +
        `<label style="display:inline-flex;align-items:center;gap:6px;cursor:pointer;font-size:14px;color:#334155"><input type="radio" name="q${i}" value="No"> No</label>`;
    } else {
      inputs = `<input type="text" name="q${i}" placeholder="Enter specific observations..." required style="width:100%;max-width:100%;padding:10px 12px;border:1px solid #cbd5e1;border-radius:8px;font-size:14px;box-sizing:border-box;outline:none" />`;
    }
    return `<div style="margin-bottom:24px;padding:18px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
    <span style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:#0d9488;background:#ccfbf1;padding:2px 6px;border-radius:4px;font-family:monospace">Question ${i + 1} of ${qList.length}</span>
  </div>
  <div style="font-weight:600;margin-bottom:6px;font-size:14px;color:#0f172a;line-height:1.4">${label}</div>
  ${note}
  ${src}
  <div style="margin-top:12px">${inputs}</div>
</div>`;
  }).join('\n');

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PRISM RAG Diagnostic Survey — ${escapeHtml(productName)}</title>
</head>
<body style="margin:0;padding:32px 16px;background:#f1f5f9;color:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
  <div style="max-width:680px;margin:0 auto;background:#ffffff;padding:32px 24px;border-radius:16px;box-shadow:0 4px 20px -2px rgba(0,0,0,0.06);border:1px solid #e2e8f0">
    <div style="display:flex;align-items:center;justify-content:between;flex-wrap:wrap;gap:10px;margin-bottom:12px">
      <div style="display:flex;align-items:center;gap:8px">
        <span style="background:#0f172a;color:#f8fafc;padding:3px 10px;border-radius:6px;font-size:11px;font-weight:700;font-family:monospace;letter-spacing:0.04em">PRISM RAG ENGINE</span>
        <span style="background:#ccfbf1;color:#0f766e;border:1px solid #99f6e4;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:600">Simulation Memory Ingested • 500 Reviews</span>
      </div>
      <a href="${escapeHtml(gdocUrl)}" style="display:inline-flex;align-items:center;gap:6px;background:#f1f5f9;color:#1a73e8;border:1px solid #cbd5e1;padding:4px 10px;border-radius:6px;font-size:12px;font-weight:600;text-decoration:none">
        📄 View as Google Doc
      </a>
    </div>

    <h1 style="font-size:22px;font-weight:700;margin:0 0 8px;color:#0f172a">Technical Root-Cause Diagnostic Survey</h1>
    <p style="font-size:13px;line-height:1.5;color:#475569;margin:0 0 24px">
      We are investigating reported hardware anomalies for <strong>${escapeHtml(productName)}</strong>. The questions below were synthesized by the PRISM RAG forensic model using multi-platform reviews (Amazon, Flipkart, JioMart, Brand Direct, Steam) and hardware engineering schematics.
    </p>
    <form method="post" action="${escapeHtml(action)}" enctype="application/x-www-form-urlencoded">
${blocks}
      <button type="submit" style="margin-top:12px;padding:14px 28px;font-size:15px;font-weight:700;background:#0f172a;color:#fff;border:none;border-radius:10px;cursor:pointer;width:100%;transition:background 0.2s">Submit Diagnostic Telemetry</button>
    </form>
    <div style="margin-top:20px;text-align:center;font-size:11px;color:#94a3b8;font-family:monospace">
      PRISM AI Closed-Loop Forensic Ingestion • DPDP & Privacy Compliant
    </div>
  </div>
</body>
</html>`;
}

/**
 * Renders the survey in Google Docs layout, complete with Docs styling,
 * 1-click clipboard export, and direct link to open https://docs.google.com/document/create
 */
function buildGoogleDocsHtml(surveyId, productName, questions, respondentEmail) {
  const base = getBaseUrl();
  const action = `${base}/api/survey/respond/${surveyId}`;
  const webUrl = `${base}/api/survey/${surveyId}`;

  const qList = Array.isArray(questions) && questions.length > 0 ? questions : [
    { question: 'Additional feedback on your experience', type: 'text', processing_note: 'General consumer feedback' }
  ];

  // Plain text export for 1-click Google Docs paste
  const plainTextDoc = `VOYAGE QUALITY ASSURANCE — CUSTOMER DIAGNOSTIC FEEDBACK
Product: ${productName}
Investigation ID: ${surveyId}
Respondent: ${respondentEmail || 'Consenting Reviewer'}
Date: ${new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
Grounding Source: PRISM RAG Simulation Memory Bank (500 Reviews across Amazon, Flipkart, JioMart, Brand Store, Steam)

─────────────────────────────────────────────────────────────────────────────
DIAGNOSTIC QUESTIONS FOR ROOT-CAUSE ISOLATION
─────────────────────────────────────────────────────────────────────────────

${qList.map((item, i) => {
  let formatHint = '';
  if (item.type === 'rating') formatHint = '[Rating Scale: 1 (Very Poor) to 5 (Excellent)]';
  else if (item.type === 'yesno') formatHint = '[Options: [  ] Yes    [  ] No]';
  else formatHint = '[Format: Short descriptive response]';

  return `Question ${i + 1} of ${qList.length}:
${item.question}
${item.grounded_data_source ? `• Grounded In: ${item.grounded_data_source}` : ''}
${item.processing_note ? `• Telemetry Note: ${item.processing_note}` : ''}
${formatHint}

Your Response:
_____________________________________________________________________________
`;
}).join('\n')}

─────────────────────────────────────────────────────────────────────────────
Thank you for your verification telemetry.`;

  const questionRows = qList.map((item, i) => {
    let inputBlock = '';
    if (item.type === 'rating') {
      inputBlock = `<div style="margin-top:8px">
        <span style="font-size:12px;color:#5f6368;margin-right:8px">Rating:</span>
        ${[1, 2, 3, 4, 5].map((n, ri) => `
          <label style="margin-right:12px;font-size:13px;cursor:pointer">
            <input type="radio" name="q${i}" value="${n}" ${ri === 0 ? 'required' : ''}> ★ ${n}
          </label>
        `).join('')}
      </div>`;
    } else if (item.type === 'yesno') {
      inputBlock = `<div style="margin-top:8px">
        <label style="margin-right:18px;font-size:13px;cursor:pointer">
          <input type="radio" name="q${i}" value="Yes" required> [  ] Yes
        </label>
        <label style="font-size:13px;cursor:pointer">
          <input type="radio" name="q${i}" value="No"> [  ] No
        </label>
      </div>`;
    } else {
      inputBlock = `<div style="margin-top:8px">
        <input type="text" name="q${i}" required placeholder="Type your answer here..." style="width:100%;border:none;border-bottom:1.5px solid #bdc1c6;padding:6px 0;font-size:14px;font-family:Arial,sans-serif;outline:none" />
      </div>`;
    }

    return `<div style="margin-bottom:28px">
      <div style="font-weight:700;font-size:14px;color:#202124;margin-bottom:4px">
        ${i + 1}. ${escapeHtml(item.question)}
      </div>
      ${item.grounded_data_source ? `<div style="font-size:11px;color:#5f6368;font-family:monospace">📌 RAG Spec Grounding: ${escapeHtml(item.grounded_data_source)}</div>` : ''}
      ${item.processing_note ? `<div style="font-size:11px;color:#0d9488;font-family:monospace">⚡ Failure Mode: ${escapeHtml(item.processing_note)}</div>` : ''}
      ${inputBlock}
    </div>`;
  }).join('');

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Google Docs — [PRISM QA] Diagnostic Survey — ${escapeHtml(productName)}</title>
  <style>
    body {
      margin: 0;
      padding: 0;
      background: #f8f9fa;
      color: #202124;
      font-family: Arial, sans-serif;
    }
    .gdoc-header {
      background: #ffffff;
      border-bottom: 1px solid #dadce0;
      padding: 10px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .gdoc-logo-area {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .gdoc-icon {
      width: 32px;
      height: 38px;
      background: #4285f4;
      border-radius: 4px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: bold;
      font-size: 18px;
    }
    .gdoc-title {
      font-size: 18px;
      font-weight: 500;
      color: #202124;
    }
    .gdoc-actions {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .btn-action {
      background: #1a73e8;
      color: #ffffff;
      border: none;
      border-radius: 6px;
      padding: 8px 16px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: background 0.2s;
    }
    .btn-action:hover {
      background: #1557b0;
    }
    .btn-secondary {
      background: #ffffff;
      color: #3c4043;
      border: 1px solid #dadce0;
    }
    .btn-secondary:hover {
      background: #f1f3f4;
    }
    .paper-sheet {
      max-width: 780px;
      margin: 28px auto 60px;
      background: #ffffff;
      padding: 60px 54px;
      box-shadow: 0 1px 3px 0 rgba(60,64,67,.3), 0 4px 8px 3px rgba(60,64,67,.15);
      border-radius: 2px;
      min-height: 900px;
      box-sizing: border-box;
    }
    .doc-meta {
      border-bottom: 2px solid #202124;
      padding-bottom: 16px;
      margin-bottom: 28px;
    }
    .doc-badge {
      display: inline-block;
      background: #e8f0fe;
      color: #1967d2;
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
      margin-bottom: 8px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
  </style>
</head>
<body>
  <!-- Google Docs Toolbar Header -->
  <div class="gdoc-header">
    <div class="gdoc-logo-area">
      <div class="gdoc-icon">📄</div>
      <div>
        <div class="gdoc-title">[PRISM QA] Diagnostic Survey — ${escapeHtml(productName)}</div>
        <div style="font-size:11px;color:#5f6368">File &bull; Edit &bull; View &bull; PRISM RAG Simulation Memory Form</div>
      </div>
    </div>
    <div class="gdoc-actions">
      <button class="btn-action btn-secondary" onclick="copyDocumentToClipboard()">
        📋 Copy Text for Google Docs
      </button>
      <a href="https://docs.google.com/document/create" target="_blank" class="btn-action">
        🚀 Open Blank Google Doc
      </a>
      <a href="${escapeHtml(webUrl)}" class="btn-action btn-secondary">
        🌐 Switch to Web View
      </a>
    </div>
  </div>

  <!-- Document Paper Canvas -->
  <div class="paper-sheet">
    <div class="doc-meta">
      <span class="doc-badge">Voyage Quality Assurance Forensic Survey</span>
      <h1 style="font-size:24px;font-weight:700;margin:4px 0 8px;color:#202124">
        Technical Root-Cause Diagnostic Document
      </h1>
      <div style="font-size:13px;color:#5f6368;line-height:1.6">
        <strong>Product:</strong> ${escapeHtml(productName)}<br>
        <strong>Investigation ID:</strong> <code>${escapeHtml(surveyId)}</code><br>
        <strong>Respondent:</strong> ${escapeHtml(respondentEmail || 'Consenting Reviewer')}<br>
        <strong>Grounded Knowledge:</strong> RAG Memory Bank (500 reviews across Amazon, Flipkart, JioMart, Brand Direct, Steam)
      </div>
    </div>

    <p style="font-size:13px;line-height:1.6;color:#3c4043;margin-bottom:24px">
      Please review and fill out the 7 diagnostic items below. You can either type your answers directly into this form and click <strong>Submit Telemetry</strong>, or click <strong>Copy Text for Google Docs</strong> above and paste it into Google Drive.
    </p>

    <form method="post" action="${escapeHtml(action)}" enctype="application/x-www-form-urlencoded">
      ${questionRows}
      <div style="margin-top:36px;border-top:1px solid #dadce0;padding-top:20px;text-align:right">
        <button type="submit" class="btn-action" style="padding:12px 28px;font-size:15px;background:#1a73e8;border-radius:8px">
          ✓ Submit Telemetry to PRISM Pipeline
        </button>
      </div>
    </form>
  </div>

  <textarea id="raw-doc-text" style="position:fixed;top:-9999px;left:-9999px">${escapeHtml(plainTextDoc)}</textarea>

  <script>
    function copyDocumentToClipboard() {
      const textarea = document.getElementById('raw-doc-text');
      textarea.select();
      document.execCommand('copy');
      alert('✓ Document text copied to clipboard! You can now paste it directly into your Google Doc.');
    }
  </script>
</body>
</html>`;
}

let transporter;

/** Gmail App Passwords are 16 chars; users often paste with spaces — strip all whitespace. */
function smtpAuth() {
  const user = (process.env.SMTP_USER || '').trim();
  const pass = (process.env.SMTP_PASS || '').replace(/\s+/g, '');
  return { user, pass };
}

function getTransporter() {
  if (!transporter) {
    const { user, pass } = smtpAuth();
    transporter = nodemailer.createTransport({
      service: 'gmail',
      auth: { user, pass },
    });
  }
  return transporter;
}

/** Call after .env reload if you change SMTP without restarting (tests). */
function resetTransporter() {
  transporter = null;
}

async function sendSurveyEmail(to, surveyId, productName, questions) {
  // Use buildSurveyEmailHtml to guarantee Gmail compatibility with buttons
  const html = buildSurveyEmailHtml(surveyId, productName, questions);
  const { user } = smtpAuth();
  if (!user) {
    throw new Error('SMTP_USER is not set');
  }
  const transport = getTransporter();
  const subject = `Action Required: Quick follow-up on your review of ${productName} (45 seconds)`;
  await transport.sendMail({
    from: `"PRISM Quality Engineering" <${user}>`,
    to,
    subject,
    html,
  });
}

module.exports = {
  sendSurveyEmail,
  buildSurveyFormHtml,
  buildSurveyEmailHtml,
  buildGoogleDocsHtml,
  getBaseUrl,
  resetTransporter,
  smtpAuth,
};
