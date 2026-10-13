"""Site de chamados: formulário para o usuário e listagem para a TI."""
import hmac
from datetime import date

from flask import Flask, abort, jsonify, redirect, render_template, request, url_for

import config
import database as db

app = Flask(__name__)
CAMPOS = ("solicitante", "titulo", "detalhes", "equipamento", "patrimonio",
          "setor", "contato", "prioridade", "desde")
OPCIONAIS = {"patrimonio"}


@app.route("/", methods=["GET", "POST"])
def abrir_chamado():
    erro, form = None, {}
    if request.method == "POST":
        form = {c: request.form.get(c, "").strip() for c in CAMPOS}
        faltando = [c for c in CAMPOS if not form[c] and c not in OPCIONAIS]
        if faltando:
            erro = "Preencha todos os campos obrigatórios."
        elif form["prioridade"] not in db.PRIORIDADES:
            erro = "Prioridade inválida."
        elif form["desde"] > date.today().isoformat():
            erro = "A data de início do problema não pode ser futura."
        else:
            chamado_id = db.criar_chamado(form)
            return redirect(url_for("sucesso", chamado_id=chamado_id))
    return render_template("abrir_chamado.html", erro=erro, form=form,
                           prioridades=db.PRIORIDADES, hoje=date.today().isoformat())


@app.route("/sucesso/<int:chamado_id>")
def sucesso(chamado_id: int):
    return render_template("sucesso.html", chamado_id=chamado_id)


@app.route("/ti/chamados")
def lista():
    """Página da TI. O monitor também lê esta página (BeautifulSoup)."""
    filtro = request.args.get("status")
    return render_template("lista.html", chamados=db.listar(filtro),
                           status_opcoes=db.STATUS, filtro=filtro)


@app.route("/ti/chamados/<int:chamado_id>/status", methods=["POST"])
def mudar_status(chamado_id: int):
    novo = request.form.get("status", "")
    if novo not in db.STATUS:
        abort(400)
    db.atualizar_status(chamado_id, novo)
    return redirect(request.referrer or url_for("lista"))


@app.route("/api/chamados/<int:chamado_id>/marcar", methods=["POST"])
def marcar(chamado_id: int):
    """Endpoint usado pelo monitor após enviar o e-mail (protegido por token)."""
    token = request.headers.get("X-Monitor-Token", "")
    if not hmac.compare_digest(token, config.MONITOR_TOKEN):
        abort(403)
    evento = (request.get_json(silent=True) or {}).get("evento")
    if evento not in ("notificado", "lembrete"):
        abort(400)
    db.marcar(chamado_id, evento)
    return jsonify(ok=True)


if __name__ == "__main__":
    db.init_db()
    app.run(debug=False)
