# Demo Guide

Support Ticket Classifier Agent Built with Google ADK + Gemini 2.5
Flash + Cloud Run Gen AI Academy Hackathon • March 2026

Quick Reference

## 1. What the Agent Does

The Support Ticket Classifier Agent is an AI-powered HTTP service that
accepts a raw customer support message and returns a fully structured
classification --- instantly.

For each ticket, it returns: Category --- Billing, Technical, General,
Refund, or Account Priority --- Low, Medium, High, or Critical
Department --- the team that should handle it Recommended Action --- a
specific instruction for the support team Confidence --- how certain the
model is (low / medium / high) Summary --- a one-sentence digest of the
issue

## 2. Tech Stack

## 3. Demo Walkthrough

## 3.1 Frontend Demo (Recommended for live demo)

Open the frontend in a browser and walk through these steps:

Open https://support-ticket-agent.netlify.app in your browser. Click one
of the sample ticket buttons (e.g. billing issue) to auto-fill the text
box. Click Classify Ticket or press Cmd+Enter. The result card appears
below with all classification fields. Try a different sample
(e.g. account hacked) to show Critical priority detection.

## 3.2 API Demo (For technical judges)

Open a terminal and run the following curl commands to demonstrate the
raw API:

Billing ticket (High priority) curl -X POST
https://support-ticket-agent-741144778351.us-central1.run.app/classify
-H "Content-Type: application/json" -d '{"ticket": "My payment failed
but I was charged twice!"}'

Critical security ticket curl -X POST
https://support-ticket-agent-741144778351.us-central1.run.app/classify
-H "Content-Type: application/json" -d '{"ticket": "I think my account
was hacked, all data may be compromised!"}'

Swagger UI For an interactive API explorer, open:
https://support-ticket-agent-741144778351.us-central1.run.app/docs

## 4. Sample Tickets to Test

## 5. Hackathon Submission Checklist

Implemented using Google ADK (LlmAgent) Uses Gemini 2.5 Flash for
inference Single clearly defined task --- ticket classification and
routing Accepts HTTP POST input with JSON body Returns valid structured
JSON response Hosted on Google Cloud Run (us-central1) Publicly
accessible endpoint with --allow-unauthenticated Frontend demo hosted on
Netlify Source code available on GitHub

## 6. Architecture Overview

The system follows a simple three-layer architecture:

User submits a ticket via the Netlify frontend or directly via HTTP POST
to the Cloud Run endpoint. FastAPI receives the request and creates a
new ADK Runner session with an in-memory session service. The ADK Runner
sends the ticket text to Gemini 2.5 Flash via Vertex AI, using the
system prompt that enforces structured JSON output. Gemini returns a
classified JSON object which FastAPI validates, parses, and returns to
the caller.

## 7. Notes

A few things worth highlighting :

The agent uses a carefully engineered system prompt to enforce
deterministic JSON output from the LLM --- no post-processing regex
required. Each request creates a fresh ADK session (stateless design),
which is optimal for Cloud Run's scale-to-zero model. The Dockerfile
uses a multi-stage build to keep the final image lean. CORS is enabled
on the API so the Netlify frontend can call it directly from the browser
with no proxy needed. The /batch endpoint supports classifying up to 10
tickets in a single request.

  --------------------------------------------------------------------------------------------------------
  Frontend URL                        https://support-ticket-agent.netlify.app
  ----------------------------------- --------------------------------------------------------------------
  API Base URL                        https://support-ticket-agent-741144778351.us-central1.run.app

  GitHub Repo                         https://github.com/ecogetaway/support-ticket-agent

  API Docs                            https://support-ticket-agent-741144778351.us-central1.run.app/docs
  --------------------------------------------------------------------------------------------------------

  Layer             Technology
  ----------------- ------------------------------------
  Agent Framework   Google ADK (Agent Development Kit)
  LLM               Gemini 2.5 Flash
  API Server        FastAPI + Uvicorn
  Deployment        Google Cloud Run (us-central1)
  Container         Docker (multi-stage build)
  Frontend          Vanilla HTML/CSS/JS on Netlify
  Auth (prod)       Vertex AI via service account IAM

  -----------------------------------------------------------------------
  Type              Ticket Text       Expected Category Expected Priority
  ----------------- ----------------- ----------------- -----------------
  Billing           My payment failed Billing           High
                    but I was charged
                    twice this month.

  Technical         The app crashes   Technical         Medium
                    every time I try
                    to export a PDF.

  Critical          I cannot log in   Account           Critical
                    and think my
                    account was
                    hacked.

  Refund            I cancelled 3     Refund            Medium
                    days ago but
                    haven't received
                    my refund.

  General           How do I upgrade  General           Low
                    my plan to access
                    more features?
  -----------------------------------------------------------------------
