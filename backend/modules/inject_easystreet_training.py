"""Inject EasyStreet training data into Sovereign Omega."""
import json

TRAINING_PAIRS = [
    ("What is EasyStreet?",
     "EasyStreet (AEGIS Audits) is a fully autonomous smart contract security audit platform live at https://aegisaudits.com. It runs 8-gate VERITAS verification on Solidity contracts in 1.7 seconds, generates PDF reports, accepts Stripe LIVE payments (Scout $299, Shield $999, Sovereign $4999), and runs 6 autonomous growth bots 24/7 on Google Cloud Run. Monthly cost ~$55, revenue potential $8,400-$27,600/month."),

    ("How do I check EasyStreet status?",
     "Health check: curl https://aegisaudits.com/health. Growth suite status: curl https://aegisaudits.com/growth/status -H 'X-Growth-Secret: easystreet_aegis_2026'. Cloud Run logs: gcloud run services logs read easystreet --region us-central1 --limit=50. Scheduler jobs: gcloud scheduler jobs list --location us-central1."),

    ("What are the EasyStreet growth bots?",
     "6 bots run 24/7: (1) Chain Sniper - scans ETH/Base/ARB/OPT/POLY mainnets every 1 min for new contract deployments via dRPC, 50 blocks per poll. (2) GitHub Scanner - scans trending Solidity repos daily at 9AM CT. (3) Exploit Monitor - monitors rekt.news + DefiLlama every 15 min. (4) Email Drip - 4-email nurture via Gmail SMTP every 6 hours. (5) Case Study Generator - SEO pages weekly Sunday 3AM. (6) Community Bot - Discord AegisAudits-Bot#1713, always-on, keyword triggers."),

    ("How much does EasyStreet cost to run?",
     "~$55/month total: ~$50 dRPC (chain sniper mainnet scanning, $49 balance = ~1 month), ~$5-10 Discord bot (always-on Cloud Run min-instances=1), ~$0 main Cloud Run (free tier), ~$0 Cloud Scheduler (free tier), $0 Gmail SMTP."),

    ("How do I trigger EasyStreet growth modules manually?",
     "POST to https://aegisaudits.com/growth/run/<module> with header X-Growth-Secret: easystreet_aegis_2026 and Content-Type: application/json with body {}. Available modules: chain_sniper, exploit_monitor, github_scanner, drip_scheduler, case_studies."),

    ("What is the EasyStreet Discord?",
     "Discord server invite: https://discord.gg/bVZXUYwG. Bot: AegisAudits-Bot#1713 running on always-on Cloud Run service 'aegis-discord-bot'. Responds to /audit command and security keywords ('audit', 'is this safe', 'vulnerability'). Token env var: DISCORD_BOT_TOKEN."),

    ("How do I redeploy EasyStreet?",
     "Full redeploy: cd modules/easystreet && gcloud run deploy easystreet --source . --region us-central1 --allow-unauthenticated. Env var only (no rebuild): gcloud run services update easystreet --region us-central1 --update-env-vars KEY=VALUE. Discord bot: gcloud run services update aegis-discord-bot --region us-central1 --update-env-vars RESTART_TRIGGER=<timestamp>."),

    ("What chains does EasyStreet chain sniper monitor?",
     "5 EVM mainnets: Ethereum (chain 1), Base (chain 8453), Arbitrum One (chain 42161), Optimism (chain 10), Polygon (chain 137). All via dRPC authenticated RPC at lb.drpc.org. Scans 50 blocks per poll, every 1 minute via Cloud Scheduler."),

    ("Where is EasyStreet deployed?",
     "Google Cloud Run, project project-veritas-488104, region us-central1. Main service: easystreet. Discord bot service: aegis-discord-bot. Domain: aegisaudits.com (Google-managed SSL). Server: Gunicorn 2 workers, 120s timeout. Container: Python 3.11-slim + solc 0.8.19 + Slither."),

    ("What are the EasyStreet Cloud Scheduler jobs?",
     "5 jobs in us-central1: easystreet-chain-sniper (every 1 min), easystreet-exploit-monitor (every 15 min), easystreet-github-scanner (daily 9AM), easystreet-drip-scheduler (every 6 hours), easystreet-case-studies (weekly Sunday 3AM). All use America/Chicago timezone and X-Growth-Secret header."),

    ("What are the EasyStreet environment variables?",
     "Cloud Run env vars: STRIPE_SECRET_KEY (sk_live_...), STRIPE_PUBLISHABLE_KEY (pk_live_...), GROWTH_SECRET (easystreet_aegis_2026), GITHUB_TOKEN, DRPC_API_KEY, SMTP_HOST (smtp.gmail.com), SMTP_PORT (587), SMTP_USER (RJ@AegisAudits.com), SMTP_PASS, FROM_EMAIL, DISCORD_BOT_TOKEN, TELEGRAM_BOT_TOKEN, EASYSTREET_URL."),

    ("What is the EasyStreet revenue model?",
     "Three pricing tiers via Stripe LIVE: Scout $299 (single contract audit), Shield $999/month (unlimited audits + monitoring), Sovereign $4,999 (full protocol + ALD compliance). Growth bots generate leads autonomously. Chain sniper finds mainnet deployers, GitHub scanner finds vulnerable repos, exploit monitor positions brand after DeFi hacks, email drip nurtures free users, case studies drive SEO, Discord bot catches security keywords."),

    ("How do I troubleshoot EasyStreet?",
     "Chain sniper 0 deployments: Normal, not every block has creations. Check dRPC balance at app.drpc.org. 500 errors: Check logs with gcloud run services logs read easystreet --region us-central1 --limit=20. Discord bot offline: Check aegis-discord-bot logs, restart with env var update. Email not sending: Check /growth/status -> smtp_configured. Stripe issues: Verify sk_live keys with gcloud run services describe."),

    ("What is the EasyStreet ops manual?",
     "Full operations manual at modules/easystreet/EASYSTREET_OPS_MANUAL.md. Contains: all API endpoints, monitoring commands, Cloud Scheduler config, bot descriptions, env vars, file structure, pricing, Discord info, cost breakdown, revenue projections, and troubleshooting guide."),
]

TARGET = r"C:\Users\rlope\.gemini\antigravity\scratch\VERITAS_COMMAND_CENTER\training_data.jsonl"

with open(TARGET, "a", encoding="utf-8") as f:
    for q, a in TRAINING_PAIRS:
        f.write(json.dumps({"role": "user", "content": q}) + "\n")
        f.write(json.dumps({"role": "assistant", "content": a}) + "\n")

print(f"Injected {len(TRAINING_PAIRS)} EasyStreet training pairs into training_data.jsonl")
