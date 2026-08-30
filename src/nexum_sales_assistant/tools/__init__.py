"""Ferramentas determinísticas do Nexum Sales Assistant.

Cada módulo implementa o contrato da SPEC correspondente em
`docs/specs/`:

- `search_products`      → `docs/specs/search_products.md`
- `check_inventory`      → `docs/specs/check_inventory.md`
- `create_quote`         → `docs/specs/create_quote.md`
- `request_human_approval` → `docs/specs/request_human_approval.md`
- `simulate_payment`     → `docs/specs/simulate_payment.md`
- `generate_document`    → `docs/specs/generate_document.md`

Princípio (ADR-004): o LLM interpreta; as ferramentas validam,
consultam, calculam e controlam os estados. A aprovação humana é
obrigatória antes do pagamento simulado.
"""
