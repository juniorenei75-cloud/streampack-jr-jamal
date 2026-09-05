"""
StreamPack Jr.Jamal — loja de pacotes de streaming (Moçambique).
Fluxo: nome/apelido → transferência → comprovativo → WhatsApp.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone, timedelta
from functools import wraps
from pathlib import Path
from urllib.parse import quote
from werkzeug.utils import secure_filename

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "orders.db"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
ADMIN_PASSWORD = "streampack2026"
PLATFORM_LOGOS = {
    "Netflix": "img/netflix.svg",
    "Disney+": "img/disney-plus.svg",
    "Amazon Prime Video": "img/prime-video.svg",
}

MERCHANT_WHATSAPP = "258849053340"  # abre WhatsApp do comerciante
ALLOWED_RECEIPT = {".png", ".jpg", ".jpeg", ".webp", ".pdf", ".gif"}
MAX_RECEIPT_BYTES = 8 * 1024 * 1024

PAYMENT_METHODS = [
    {
        "id": "mola",
        "name": "Mola",
        "logo": "img/mola.svg",
        "number": "867941110",
        "hint": "Transferência Mola",
    },
    {
        "id": "millennium_bim",
        "name": "Millennium BIM",
        "logo": "img/millennium-bim.svg",
        "number": "000100000068702704257",
        "hint": "Transferência bancária",
    },
]

MOZ_TZ = timezone(timedelta(hours=2))




SERIES_RECS = [
    {"title": "Stranger Things", "year": "5.ª temporada", "tag": "Ficção · Mistério", "blurb": "O fim da saga em Hawkins — ideal para maratonar.", "platform": "Netflix", "poster": "img/posters/stranger-things.png"},
    {"title": "The Boys", "year": "Nova temporada", "tag": "Ação · Sátira", "blurb": "Super-heróis corruptos e muita adrenalina.", "platform": "Amazon Prime Video", "poster": "img/posters/the-boys.png"},
    {"title": "The Lord of the Rings: The Rings of Power", "year": "Em destaque", "tag": "Fantasia", "blurb": "A Terra Média antes do Senhor dos Anéis.", "platform": "Amazon Prime Video", "poster": "img/posters/rings-of-power.png"},
    {"title": "Wednesday", "year": "Nova temporada", "tag": "Mistério · Humor", "blurb": "Wednesday Addams na Nevermore Academy.", "platform": "Netflix", "poster": "img/posters/wednesday.png"},
    {"title": "Reacher", "year": "Em alta", "tag": "Ação · Crime", "blurb": "Jack Reacher resolve casos à força.", "platform": "Amazon Prime Video", "poster": "img/posters/reacher.png"},
    {"title": "Squid Game", "year": "Sucesso global", "tag": "Drama · Thriller", "blurb": "Jogos mortais e tensão até ao fim.", "platform": "Netflix", "poster": "img/posters/squid-game.png"},
    {"title": "The Mandalorian", "year": "Em destaque", "tag": "Ação · Star Wars", "blurb": "Aventuras no universo Star Wars.", "platform": "Disney+", "poster": "img/posters/mandalorian.png"},
    {"title": "Loki", "year": "Em destaque", "tag": "Marvel · Fantasia", "blurb": "O Deus da Traição pelo multiverso.", "platform": "Disney+", "poster": "img/posters/loki.png"},
]


PRODUCTS = {
    "netflix": {
        "id": "netflix",
        "name": "Netflix",
        "tagline": "Filmes, séries e originais exclusivos",
        "description": (
            "Acesso à biblioteca Netflix com séries originais, filmes "
            "e documentários. Ideal para maratonas em família ou solo."
        ),
        "accent": "#E50914",
        "accent_soft": "rgba(229, 9, 20, 0.18)",
        "icon": "N",
        "logo": "img/netflix.svg",
        "plans": [
            {"id": "1m", "label": "1 mês", "months": 1, "price_mzn": 350},
            {"id": "2m", "label": "2 meses", "months": 2, "price_mzn": 700},
            {"id": "3m", "label": "3 meses", "months": 3, "price_mzn": 1050},
            {"id": "6m", "label": "6 meses", "months": 6, "price_mzn": 2100},
            {"id": "1y", "label": "1 ano", "months": 12, "price_mzn": 4200},
        ],
    },
    "disney": {
        "id": "disney",
        "name": "Disney+",
        "tagline": "Marvel, Star Wars, Pixar e mais",
        "description": (
            "Disney+ com filmes e séries da Disney, Pixar, Marvel, "
            "Star Wars e National Geographic."
        ),
        "accent": "#113CCF",
        "accent_soft": "rgba(17, 60, 207, 0.18)",
        "icon": "D+",
        "logo": "img/disney-plus.svg",
        "plans": [
            {"id": "1m", "label": "1 mês", "months": 1, "price_mzn": 350},
            {"id": "2m", "label": "2 meses", "months": 2, "price_mzn": 700},
            {"id": "3m", "label": "3 meses", "months": 3, "price_mzn": 1050},
            {"id": "6m", "label": "6 meses", "months": 6, "price_mzn": 2100},
            {"id": "1y", "label": "1 ano", "months": 12, "price_mzn": 4200},
        ],
    },
    "prime": {
        "id": "prime",
        "name": "Amazon Prime Video",
        "tagline": "Streaming de cinema e séries",
        "description": (
            "Amazon Prime Video com filmes, séries e exclusivos. "
            "Entretenimento para ver onde e quando quiser."
        ),
        "accent": "#00A8E1",
        "accent_soft": "rgba(0, 168, 225, 0.18)",
        "icon": "Pv",
        "logo": "img/prime-video.svg",
        "plans": [
            {"id": "1m", "label": "1 mês", "months": 1, "price_mzn": 350},
            {"id": "2m", "label": "2 meses", "months": 2, "price_mzn": 700},
            {"id": "3m", "label": "3 meses", "months": 3, "price_mzn": 1050},
            {"id": "6m", "label": "6 meses", "months": 6, "price_mzn": 2100},
            {"id": "1y", "label": "1 ano", "months": 12, "price_mzn": 4200},
        ],
    },
}



app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "streampack-jr-jamal-dev-secret-2026")
app.config["MAX_CONTENT_LENGTH"] = MAX_RECEIPT_BYTES


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            phone TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            notes TEXT,
            items_json TEXT NOT NULL,
            total_mzn INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'awaiting_payment',
            payment_method TEXT,
            receipt_path TEXT
        )
        """
    )
    db.commit()
    db.close()


def migrate_db():
    db = sqlite3.connect(DB_PATH)
    cols = {r[1] for r in db.execute("PRAGMA table_info(orders)").fetchall()}
    alters = {
        "first_name": "ALTER TABLE orders ADD COLUMN first_name TEXT",
        "last_name": "ALTER TABLE orders ADD COLUMN last_name TEXT",
        "payment_method": "ALTER TABLE orders ADD COLUMN payment_method TEXT",
        "receipt_path": "ALTER TABLE orders ADD COLUMN receipt_path TEXT",
    }
    for col, sql in alters.items():
        if col not in cols:
            db.execute(sql)
    db.commit()
    db.close()


def format_mzn(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + " MZN"


def get_plan(product_id: str, plan_id: str) -> dict | None:
    product = PRODUCTS.get(product_id)
    if not product:
        return None
    for plan in product["plans"]:
        if plan["id"] == plan_id:
            return plan
    return None


def cart_items():
    raw = session.get("cart", [])
    items = []
    for entry in raw:
        product = PRODUCTS.get(entry.get("product_id"))
        plan = get_plan(entry.get("product_id", ""), entry.get("plan_id", ""))
        qty = int(entry.get("qty", 1) or 1)
        if not product or not plan or qty < 1:
            continue
        line_total = plan["price_mzn"] * qty
        items.append(
            {
                "product_id": product["id"],
                "product_name": product["name"],
                "accent": product["accent"],
                "plan_id": plan["id"],
                "plan_label": plan["label"],
                "unit_price": plan["price_mzn"],
                "qty": qty,
                "line_total": line_total,
            }
        )
    return items


def cart_total(items=None) -> int:
    if items is None:
        items = cart_items()
    return sum(i["line_total"] for i in items)


def cart_count() -> int:
    return sum(i["qty"] for i in cart_items())


def load_order(order_id: str) -> dict | None:
    row = get_db().execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not row:
        return None
    order = dict(row)
    order["items"] = json.loads(order["items_json"])
    return order


def payment_label(method_id: str | None) -> str:
    for pm in PAYMENT_METHODS:
        if pm["id"] == method_id:
            return pm["name"]
    return method_id or "—"


def build_whatsapp_link(order: dict, *, ask_receipt: bool = True) -> str:
    full_name = f"{order.get('first_name') or ''} {order.get('last_name') or ''}".strip()
    lines = [
        "Olá! Segue o meu pedido StreamPack Jr.Jamal.",
        f"Pedido: {order['id']}",
        f"Nome: {full_name or order['customer_name']}",
        f"Total a pagar: {format_mzn(order['total_mzn'])}",
    ]
    method = payment_label(order.get("payment_method"))
    if method and method != "—":
        lines.append(f"Método: {method}")
    lines.append("Pacote(s):")
    for i in order["items"]:
        lines.append(
            f"- {i['product_name']} · {i['plan_label']} × {i['qty']} = {format_mzn(i['line_total'])}"
        )
    if order.get("phone"):
        lines.append(f"Meu WhatsApp: {order['phone']}")
    if order.get("email"):
        lines.append(f"Email: {order['email']}")
    text = "\n".join(lines)
    return f"https://wa.me/{MERCHANT_WHATSAPP}?text={quote(text)}"



@app.context_processor
def inject_globals():
    return {
        "brand": "StreamPack Jr.Jamal",
        "cart_count": cart_count(),
        "format_mzn": format_mzn,
        "products": PRODUCTS,
        "payment_methods": PAYMENT_METHODS,
        "platform_logos": PLATFORM_LOGOS,
    }




@app.route("/")
def index():
    return render_template(
        "index.html",
        products=list(PRODUCTS.values()),
        series_recs=SERIES_RECS,
    )


@app.route("/produto/<product_id>")
def product_detail(product_id):
    product = PRODUCTS.get(product_id)
    if not product:
        flash("Produto não encontrado.", "error")
        return redirect(url_for("index"))
    return render_template("product.html", product=product)


@app.route("/carrinho")
def cart_view():
    items = cart_items()
    return render_template(
        "cart.html",
        items=items,
        total=cart_total(items),
        products=PRODUCTS,
    )


@app.route("/carrinho/adicionar", methods=["POST"])
def cart_add():
    product_id = request.form.get("product_id", "")
    plan_id = request.form.get("plan_id", "")
    try:
        qty = max(1, min(20, int(request.form.get("qty", 1))))
    except ValueError:
        qty = 1
    if not get_plan(product_id, plan_id):
        flash("Plano inválido.", "error")
        return redirect(url_for("index"))
    cart = session.get("cart", [])
    found = False
    for entry in cart:
        if entry.get("product_id") == product_id and entry.get("plan_id") == plan_id:
            entry["qty"] = min(20, int(entry.get("qty", 1)) + qty)
            found = True
            break
    if not found:
        cart.append({"product_id": product_id, "plan_id": plan_id, "qty": qty})
    session["cart"] = cart
    flash("Adicionado ao carrinho.", "success")
    return redirect(url_for("cart_view"))


@app.route("/carrinho/atualizar", methods=["POST"])
def cart_update():
    product_id = request.form.get("product_id", "")
    plan_id = request.form.get("plan_id", "")
    action = request.form.get("action", "update")
    cart = session.get("cart", [])
    new_cart = []
    for entry in cart:
        if entry.get("product_id") == product_id and entry.get("plan_id") == plan_id:
            if action == "remove":
                continue
            if action == "set_plan":
                new_plan = request.form.get("new_plan_id", plan_id)
                if get_plan(product_id, new_plan):
                    merged = False
                    for other in new_cart:
                        if other.get("product_id") == product_id and other.get("plan_id") == new_plan:
                            other["qty"] = min(20, int(other.get("qty", 1)) + int(entry.get("qty", 1)))
                            merged = True
                            break
                    if not merged:
                        entry = dict(entry)
                        entry["plan_id"] = new_plan
                        new_cart.append(entry)
                    continue
            try:
                qty = int(request.form.get("qty", entry.get("qty", 1)))
            except ValueError:
                qty = 1
            qty = max(1, min(20, qty))
            entry = dict(entry)
            entry["qty"] = qty
            new_cart.append(entry)
        else:
            new_cart.append(entry)
    session["cart"] = new_cart
    flash("Carrinho atualizado.", "success")
    return redirect(url_for("cart_view"))


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items = cart_items()
    if not items:
        flash("O carrinho está vazio.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        first_name = (request.form.get("first_name") or "").strip()
        last_name = (request.form.get("last_name") or "").strip()
        name = f"{first_name} {last_name}".strip()
        errors = []
        if len(first_name) < 2:
            errors.append("Indique o seu nome.")
        if len(last_name) < 2:
            errors.append("Indique o seu apelido.")
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "checkout.html",
                items=items,
                total=cart_total(items),
                form={"first_name": first_name, "last_name": last_name},
            )

        order_id = "SP-" + secrets.token_hex(4).upper()
        now = datetime.now(timezone.utc).isoformat()
        payload = [
            {
                "product_id": i["product_id"],
                "product_name": i["product_name"],
                "plan_id": i["plan_id"],
                "plan_label": i["plan_label"],
                "unit_price": i["unit_price"],
                "qty": i["qty"],
                "line_total": i["line_total"],
            }
            for i in items
        ]
        total = cart_total(items)
        db = get_db()
        db.execute(
            """
            INSERT INTO orders
            (id, created_at, customer_name, first_name, last_name, phone, email, notes,
             items_json, total_mzn, status)
            VALUES (?, ?, ?, ?, ?, '', '', NULL, ?, ?, 'awaiting_payment')
            """,
            (order_id, now, name, first_name, last_name, json.dumps(payload, ensure_ascii=False), total),
        )
        db.commit()
        session["cart"] = []
        return redirect(url_for("payment", order_id=order_id))

    return render_template(
        "checkout.html",
        items=items,
        total=cart_total(items),
        form={"first_name": "", "last_name": ""},
    )


@app.route("/pagamento/<order_id>", methods=["GET", "POST"])
def payment(order_id):
    order = load_order(order_id)
    if not order:
        flash("Pedido não encontrado.", "error")
        return redirect(url_for("index"))
    if order["status"] not in ("awaiting_payment", "awaiting_confirmation"):
        return redirect(url_for("sent", order_id=order_id))

    if request.method == "POST":
        method = request.form.get("payment_method", "")
        if method not in {pm["id"] for pm in PAYMENT_METHODS}:
            flash("Escolhe Mola ou Millennium BIM.", "error")
            return render_template("payment.html", order=order, whatsapp_url=build_whatsapp_link(order))
        get_db().execute(
            "UPDATE orders SET payment_method = ? WHERE id = ?",
            (method, order_id),
        )
        get_db().commit()
        return redirect(url_for("receipt_upload", order_id=order_id))

    return render_template("payment.html", order=order, whatsapp_url=build_whatsapp_link(order))


@app.route("/comprovativo/<order_id>", methods=["GET", "POST"])
def receipt_upload(order_id):
    order = load_order(order_id)
    if not order:
        flash("Pedido não encontrado.", "error")
        return redirect(url_for("index"))
    if order["status"] == "awaiting_payment" and not order.get("payment_method"):
        return redirect(url_for("payment", order_id=order_id))

    if request.method == "POST":
        phone = (request.form.get("phone") or "").strip()
        email = (request.form.get("email") or "").strip()
        notes = (request.form.get("notes") or "").strip()
        method = request.form.get("payment_method") or order.get("payment_method") or ""
        f = request.files.get("receipt")

        errors = []
        if len(phone) < 8:
            errors.append("Indique um WhatsApp/telefone válido.")
        if "@" not in email or "." not in email:
            errors.append("Indique um email válido.")
        if method not in {pm["id"] for pm in PAYMENT_METHODS}:
            errors.append("Indique o método de pagamento.")
        if not f or not f.filename:
            errors.append("Carregue o comprovativo da transferência.")
        else:
            ext = Path(f.filename).suffix.lower()
            if ext not in ALLOWED_RECEIPT:
                errors.append("Comprovativo: use PNG, JPG, WEBP ou PDF.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "receipt.html",
                order=order,
                whatsapp_url=build_whatsapp_link(order),
                form={"phone": phone, "email": email, "notes": notes, "payment_method": method},
            )

        safe = secure_filename(f.filename) or "comprovativo"
        fname = f"{order_id}_{secrets.token_hex(4)}{Path(safe).suffix.lower()}"
        dest = UPLOAD_DIR / fname
        f.save(dest)

        get_db().execute(
            """
            UPDATE orders
            SET phone = ?, email = ?, notes = ?, payment_method = ?,
                receipt_path = ?, status = 'awaiting_confirmation'
            WHERE id = ?
            """,
            (phone, email, notes or None, method, fname, order_id),
        )
        get_db().commit()
        return redirect(url_for("sent", order_id=order_id))

    return render_template(
        "receipt.html",
        order=order,
        whatsapp_url=build_whatsapp_link(order),
        form={
            "phone": order.get("phone") or "",
            "email": order.get("email") or "",
            "notes": order.get("notes") or "",
            "payment_method": order.get("payment_method") or "",
        },
    )


@app.route("/enviado/<order_id>")
def sent(order_id):
    order = load_order(order_id)
    if not order:
        flash("Pedido não encontrado.", "error")
        return redirect(url_for("index"))
    wa = build_whatsapp_link(order)
    return render_template("sent.html", order=order, whatsapp_url=wa)


@app.route("/confirmacao/<order_id>")
def confirmation(order_id):
    order = load_order(order_id)
    if not order:
        flash("Pedido não encontrado.", "error")
        return redirect(url_for("index"))
    if order["status"] == "awaiting_payment":
        return redirect(url_for("payment", order_id=order_id))
    if not order.get("receipt_path"):
        return redirect(url_for("receipt_upload", order_id=order_id))
    return redirect(url_for("sent", order_id=order_id))



init_db()
migrate_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5055"))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
