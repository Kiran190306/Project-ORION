# Privacy Policy & Data Disclosure

**Document Version:** 1.0
**Effective Date:** 2026-09-22
**Status:** Draft for legal review — requires qualified legal counsel review prior to commercial launch.

---

### Internal Implementation Notice
> This document describes the actual, factual technical data collection and storage behaviors of Project ORION during Public Beta. It does not fabricate statutory certifications (such as certified GDPR or CCPA compliance). Comprehensive data protection officer appointments, formal jurisdictional representations, and cross-border transfer mechanisms are subject to external legal counsel review.

---

### 1. Overview & Scope
Project ORION ("the Platform") is committed to transparent information practices. This Privacy Policy details the categories of personal data collected, technical operational logs stored, browser storage mechanisms utilized, and the third-party infrastructure providers involved in delivering the Platform.

### 2. Information We Collect
We collect only information necessary to authenticate users, enforce multi-tenant isolation, mitigate automated system abuse, and maintain operational stability:

- **Account Information:** When you register, we collect your `username`, `email address`, and a salted hash of your password (`bcrypt`). We do not store plaintext passwords.
- **Organization & Role Data:** Tenant organization name, custom slug, member invitations, and assigned roles (`OWNER`, `ADMIN`, `TRADER`, `VIEWER`).
- **Security & Lifecycle Data:** Ephemeral single-use cryptographic token hashes (`SHA-256`) for password recovery and email verification; timestamps of password modifications for session revocation.
- **Abuse Defense Telemetry:** When accessing public APIs, client IP addresses are processed by an in-memory sliding-window counter in Redis to mitigate brute-force attacks. Raw IP addresses are not permanently stored in legal consent tables.
- **Simulated Trading Activity:** Paper trading accounts, paper orders, simulated execution fills, positions, strategy parameters, backtest tearsheets, and walk-forward optimization runs.
- **Audit Records:** Immutable system audit logs recording tenant-level administrative events (e.g. member invitations, role changes, billing plan transitions, legal document acceptances).

### 3. Browser Storage & Cookie Disclosure
- **Zero Tracking Cookies:** Project ORION does **not** use persistent advertising cookies, marketing pixels, or third-party web beacons.
- **Ephemeral Session Storage:** The Platform utilizes HTML5 `sessionStorage` strictly to maintain your authenticated session:
  - `orion_access_token`: Cryptographic JWT bearer token granting API access for your current browser tab.
  - `orion_active_org_id`: UUID of your currently selected tenant organization.
  Both items are destroyed when you log out or close your browser tab.
- **Zero LocalStorage / IndexedDB:** The web application does not persist tracking or profile data in `localStorage` or `IndexedDB`.

### 4. Third-Party Infrastructure Processors
To deliver the cloud-hosted platform, Project ORION interfaces with the following infrastructure providers:
- **Cloud Infrastructure Hosting:** Hosted on containerized cloud infrastructure provided by **Render**, utilizing managed PostgreSQL and Redis databases.
- **Payment Processing (Test Mode):** Commercial billing is integrated with **Stripe** operating strictly in **Test Mode** (`sk_test_...`). No live payment cards or live financial accounts are debited.
- **Market Data Feeds:** Quantitative market pricing data is retrieved from external market data providers (e.g., **TwelveData**).
- **Broker Sandbox:** Connections to external broker practice environments (e.g., **OANDA v20 Practice Sandbox**) use client-supplied sandbox credentials encrypted at rest with AES-256-GCM.

*(Third-party subprocessor agreements and formal Data Processing Addenda (DPAs) require external legal counsel review before public commercial launch.)*

### 5. Data Retention & Deletion
- **Database Records:** Account, organization, and simulated trading data remain stored in the platform database for the duration of the account lifecycle. *(Automated data retention and purging policies across subscription tiers require formal product/legal decision.)*
- **Account Deactivation:** In accordance with Phase 1 hardening, deactivated user accounts fail closed and prevent session creation.

### 6. International Transfers & Jurisdictional Compliance
The Platform is accessible over the public Internet. Depending on your location, your information may be processed in cloud hosting facilities located in the United States or the European Union. *(Jurisdictional legal review required before public commercial launch to establish formal Standard Contractual Clauses or regional data residency compliance.)*

### 7. Contact Information
For questions regarding technical data handling or to request deletion of your beta testing account, contact the platform administrators via designated support channels. *(Formal legal contact address and Data Protection Officer designation require final corporate incorporation.)*
