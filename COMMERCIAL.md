# Commercial Licensing

This addon is licensed under [GNU AGPL-3.0](LICENSE) for community use. AGPL-3.0 grants you broad freedom to use, modify, and distribute the code — **including in commercial settings** — provided you comply with the license's source-sharing requirements.

## When you need a commercial license

The AGPL-3.0 obligation that most often surprises commercial integrators is **§13 (Network Use)**: if you offer this addon (or any work derived from it) to users over a network — for example, as part of a Frappe / ERPNext hosted service — you must make the corresponding source code of your modified version available to those users.

You may need a non-AGPL commercial license if any of the following apply:

- You're integrating this addon into a **proprietary Frappe deployment you offer as a hosted service**, and you don't want to publish your full source under AGPL-3.0
- You're **bundling this addon with proprietary modules** you sell to clients, and the AGPL's copyleft would extend to your code
- Your **enterprise legal / compliance team** has flagged AGPL-3.0 dependencies as restricted, and you'd prefer a clean commercial license
- You're a **systems integrator / consultancy** deploying this for clients and want unambiguous licensing terms

If none of the above apply — for example, you're using the addon as-is in your own internal Frappe / ERPNext, or you're happy to share modifications back — **AGPL-3.0 is free and sufficient. No need to contact me.**

## Pricing

**$20 USD per site, per year.** A "site" is one Frappe site (one entry in `sites/`) where the addon is installed.

- Internal use, demo / staging, and dev/test deployments are not counted — only production sites where end users interact with the addon
- Includes free updates and bug fixes for the licensed year
- Renewal is optional but encouraged
- Volume / enterprise terms: if you're deploying across 10+ sites, open an issue and we'll work out a flat rate

## How to get a commercial license

Open a GitHub issue on this repository tagged `commercial-license` with:

- Your organization name + size (rough headcount or revenue bracket is fine)
- The Frappe deployment you'd integrate this into (community / Frappe Cloud / self-hosted / SaaS)
- Number of production sites you want to license
- Brief description of how you'd use the addon

I'll reply within a few days with a license document + payment instructions (typically wire / Wise / Stripe link).

You can also reach out via the contact info on the [@goldrag1 GitHub profile](https://github.com/goldrag1) or start a thread in [GitHub Discussions](https://github.com/goldrag1/feedback_widget/discussions).

## What a commercial license gives you

- A non-AGPL grant covering the addon for your specific use case
- Permission to integrate into proprietary deployments without source-sharing obligation
- Continued access to all upstream updates and bug fixes (same source repository, just licensed differently for you)

## Companion Odoo widget

If you also use Odoo, there's a sibling addon at [`goldrag1/odoo-feedback-widget`](https://github.com/goldrag1/odoo-feedback-widget) under the same license + pricing model. The JSONL inbox schema is shared between the two so a single AI analysis pipeline can consume feedback from both Frappe and Odoo deployments.

## Contributions

Contributions to this repository are accepted under AGPL-3.0 (the inbound license matches the outbound). If you contribute material changes and would like an arrangement that allows your contributions to flow back into your own proprietary projects, mention it in your PR — we can sort it case-by-case.
