"""
StreamPack Jr.Jamal — painel ADMIN (app separado da loja).
Corre em porta diferente (5056 local / $PORT em produção).
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from functools import wraps
from pathlib import Path

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

from shared_config import ADMIN_PASSWORD, BASE_DIR, DB_PATH, UPLOAD_DIR, MOZ_TZ_HOURS

MOZ_TZ = timezone(timedelta(hours=MOZ_TZ_HOURS))

app = Flask(__name__)
app.secret_key = os.environ.get("ADMIN_SECRET_KEY", "streampack-admin-secret-2026")


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def format_mzn(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + " MZN"


@app.context_processor
def inject_globals():
    return {"format_mzn": format_mzn, "brand": "StreamPack Admin"}


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_ok"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@app.route("/")
def root():
    return redirect(url_for("admin"))


@app.route("/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_ok"):
        return redirect(url_for("admin"))
    if request.method == "POST":
        if request.form.get("password", "") == ADMIN_PASSWORD:
            session["admin_ok"] = True
            return redirect(request.args.get("next") or url_for("admin"))
        flash("Palavra-passe incorreta.", "error")
    return render_template("admin_login.html")


@app.route("/logout")
def admin_logout():
    session.pop("admin_ok", None)
    flash("Sessão terminada.", "success")
    return redirect(url_for("admin_login"))


@app.route("/pedidos")
@admin_required
def admin():
    rows = get_db().execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    orders = []
    for row in rows:
        o = dict(row)
        o["items"] = json.loads(o["items_json"])
        try:
            dt = datetime.fromisoformat(o["created_at"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            o["created_display"] = dt.astimezone(MOZ_TZ).strftime("%d/%m/%Y %H:%M")
        except Exception:
            o["created_display"] = o["created_at"]
        orders.append(o)
    return render_template("admin.html", orders=orders)


@app.route("/pedido/<order_id>/estado", methods=["POST"])
@admin_required
def admin_set_status(order_id):
    status = request.form.get("status", "")
    if status not in ("awaiting_payment", "awaiting_confirmation", "paid", "delivered", "pending"):
        flash("Estado inválido.", "error")
        return redirect(url_for("admin"))
    cur = get_db().execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    get_db().commit()
    if cur.rowcount:
        flash(f"Pedido {order_id} atualizado.", "success")
    else:
        flash("Pedido não encontrado.", "error")
    return redirect(url_for("admin"))


@app.route("/comprovativo/<order_id>")
@admin_required
def admin_receipt(order_id):
    row = get_db().execute("SELECT receipt_path FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not row or not row["receipt_path"]:
        flash("Comprovativo não encontrado.", "error")
        return redirect(url_for("admin"))
    return send_from_directory(UPLOAD_DIR, row["receipt_path"], as_attachment=False)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5056"))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
