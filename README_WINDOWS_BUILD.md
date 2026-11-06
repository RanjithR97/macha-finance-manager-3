# Macha Finance Manager — Windows build package

This package refreshes the desktop interface with a video-inspired ERP layout: dark left navigation, white workspace, dashboard cards, structured forms and tables. It keeps the original upfront-interest / fixed collection-target model.

## Included modules
- Dashboard: customer, active-loan, disbursement, today's collection, outstanding and account balances.
- Customer registration and customer list.
- Loan creation with upfront-interest calculation preview, charges, net disbursement and daily collection target.
- Daily collections with receipt numbers and payment references.
- Investor contribution ledger and investor/company/lending account balances.
- Linked transfers between investor, company, lending, interest and other ledgers.
- Interest ledger view and Excel export / local database backup.

## Build the Windows installer
The GitHub Actions workflow `.github/workflows/build-windows.yml` builds the Windows executable and Inno Setup installer. Upload/replace the package files in your existing GitHub repository, commit, then open **Actions** and run the Windows build workflow. Download the generated artifact from the completed run.

## Important before live financial use
This remains a local single-PC prototype. It is not yet a production-ready multi-user lending platform. The current SQLite database is local; user authentication/roles, shared PostgreSQL deployment, encrypted Aadhaar/PAN storage, audit-log immutability, cheque-clearance workflow, and full double-entry accounting still require implementation and testing. Do not enter real Aadhaar/PAN data until encryption and access controls are implemented. Keep verified database backups.

The rate field is used as a one-time upfront percentage against the gross loan amount in this model (the existing API property is named `monthly_rate_pct` for compatibility; it is not a reducing-balance monthly EMI rate). Daily collection is `gross loan amount / collection days`, rounded by the UI for display. The loan closes when the full collection target is received.
