# StreamPack Jr.Jamal

Loja oficial de assinaturas de streaming em Moçambique (Netflix, Disney+ e Amazon Prime Video).

## Correr

```bash
cd streampack-jr-jamal
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abre http://127.0.0.1:5000

## Admin

- URL: http://127.0.0.1:5000/admin
- Palavra-passe: `streampack2026`

Checkout cria pedido pendente (sem pagamento online). Cumprimento manual via WhatsApp.

## Duas aplicações

- **Loja (clientes):** `python app.py` → http://127.0.0.1:5055
- **Admin (só tu):** `python admin_app.py` → http://127.0.0.1:5056/pedidos  
  Palavra-passe: `streampack2026`

Partilham a mesma base `orders.db`, mas são processos/apps separados.
