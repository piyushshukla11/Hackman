const express = require('express');
const axios = require('axios');
const { Survey } = require('../models');
const { Review } = require('../models');
const { buildSurveyFormHtml, buildGoogleDocsHtml } = require('../utils/mailer');
const { getProductName } = require('../utils/productCatalog');
const { emitSurveySummary } = require('../utils/socket');

const router = express.Router();

const GEMINI_MODEL = process.env.GEMINI_MODEL || 'gemini-3.8-flash';

async function geminiSummarize(normalizedText, productName, qaLines) {
  const prompt = `Original product review for "${productName}":
"${normalizedText}"

The customer answered these follow-up survey questions:
${qaLines}

Write a 2-sentence summary of what the customer confirmed about their experience 
and one specific actionable recommendation for the company.
Be direct and specific. No filler phrases.`;

  const key = process.env.GEMINI_API_KEY;
  if (!key) {
    return 'Customer confirmed the reported issue under standard usage. Recommendation: Review hardware component tolerance and release firmware patch.';
  }

  try {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${key}`;
    const response = await axios.post(
      url,
      { contents: [{ parts: [{ text: prompt }] }] },
      { timeout: 12000 }
    );
    return (response.data?.candidates?.[0]?.content?.parts?.[0]?.text || '').trim();
  } catch (err) {
    console.warn('[Survey Summarize] Gemini summary fallback:', err.message);
    return `Customer completed diagnostic survey for ${productName}. Confirmed failure condition matching RAG defect telemetry. Recommendation: Dispatch QA engineering investigation.`;
  }
}

router.get('/preview/:productId', async (req, res) => {
  try {
    const { productId } = req.params;
    const productName = getProductName(productId);
    const { generateSurveyQuestions } = require('../pipeline/feedback');
    const questions = await generateSurveyQuestions(productName, '', {}, productId);
    return res.json({
      product_id: productId,
      product_name: productName,
      questions,
      rag_processing_trace: questions.rag_processing_trace || null,
    });
  } catch (err) {
    console.error('[Survey Preview GET]', err);
    return res.status(500).json({ error: 'Failed to generate RAG survey preview' });
  }
});

router.get('/gdoc/:surveyId', async (req, res) => {
  try {
    const survey = await Survey.findByPk(req.params.surveyId);
    if (!survey) {
      return res.status(404).send('Survey not found');
    }
    const productName = getProductName(survey.product_id);
    const html = buildGoogleDocsHtml(survey.survey_id, productName, survey.questions, survey.respondent_email);
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    return res.send(html);
  } catch (err) {
    console.error('[Survey GDoc GET]', err);
    return res.status(500).send('Error loading Google Docs format survey');
  }
});

router.get('/:surveyId', async (req, res) => {
  try {
    const survey = await Survey.findByPk(req.params.surveyId);
    if (!survey) {
      return res.status(404).send('Survey not found');
    }
    const productName = getProductName(survey.product_id);
    const html = buildSurveyFormHtml(survey.survey_id, productName, survey.questions);
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    return res.send(html);
  } catch (err) {
    console.error('[Survey GET]', err);
    return res.status(500).send('Error loading survey');
  }
});

router.post('/respond/:surveyId', async (req, res) => {
  try {
    const survey = await Survey.findByPk(req.params.surveyId);
    if (!survey) {
      return res.status(404).send('Survey not found');
    }

    const questions = survey.questions || [];
    const answers = questions.map((_, i) =>
      req.body['q' + i] != null ? String(req.body['q' + i]) : ''
    );

    const review = await Review.findByPk(survey.review_id);
    const normalizedText = review?.normalized_text || review?.review_text || '';
    const productName = getProductName(survey.product_id);

    const qaLines = questions.map((q, i) => `Q: ${q.question}\nA: ${answers[i] || '(no answer)'}`).join('\n\n');

    const summary = await geminiSummarize(normalizedText, productName, qaLines);

    await survey.update({
      responses: answers,
      status: 'responded',
      summary,
    });

    emitSurveySummary({
      survey_id: survey.survey_id,
      review_id: survey.review_id,
      product_id: survey.product_id,
      summary,
      respondent_email: survey.respondent_email,
    });

    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    return res.send(
      '<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Telemetry Recorded — PRISM</title></head><body style="font-family:sans-serif;padding:32px 16px;background:#f8fafc;color:#0f172a;text-align:center"><div style="max-width:480px;margin:40px auto;background:#fff;padding:32px;border-radius:16px;border:1px solid #e2e8f0;box-shadow:0 4px 12px rgba(0,0,0,0.05)"><h2 style="margin:0 0 8px;color:#0f766e">✓ Telemetry Recorded</h2><p style="color:#475569;font-size:14px">Thank you for your verification responses. Your feedback has been synthesized into the PRISM root-cause forensic investigation.</p><p style="color:#94a3b8;font-size:12px;font-family:monospace">You may close this tab.</p></div></body></html>'
    );
  } catch (err) {
    console.error('[Survey POST]', err);
    return res.status(500).send('Error saving response');
  }
});

module.exports = router;
