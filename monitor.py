"""Monitor de chamados.

Fluxo: lê a página /ti/chamados (requests + BeautifulSoup), detecta chamados
ainda não notificados e envia o alerta por e-mail (SMTP). O chamado só é
marcado como notificado depois que o envio dá certo; se falhar, o monitor
tenta de novo no próximo ciclo (até MAX_TENTATIVAS).
"""
import logging
import smtplib
import time
from datetime import date, datetime
from email.message import EmailMessage
from html import escape

import requests
from bs4 import BeautifulSoup

import config

log = logging.getLogger("monitor")

EMOJI = {"baixa": "🟢", "média": "🟡", "alta": "🟠", "crítica": "🔴"}
CAMPOS = ("aberto", "solicitante", "setor", "contato", "titulo", "detalhes",
          "equipamento", "patrimonio", "desde", "prioridade", "status")


# ---------------------------------------------------------------- leitura do site
def buscar_chamados() -> list[dict]:
    """Faz scraping da tabela de chamados da página da TI."""
    resp = requests.get(f"{config.SITE_URL}/ti/chamados", timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    chamados = []
    for linha in soup.select("table#chamados tbody tr[data-id]"):
        c = {"id": int(linha["data-id"]),
             "notificado": linha["data-notificado"] == "1",
             "lembrete": linha["data-lembrete"] or None}
        for campo in CAMPOS:
            celula = linha.select_one(f"td.{campo}")
            # Em "status" a célula também tem botões; pegamos só o primeiro texto.
            texto = next(celula.stripped_strings, "") if campo == "status" else celula.get_text("\n", strip=True)
            c[campo] = texto
        chamados.append(c)
    return chamados


def marcar(chamado_id: int, evento: str) -> None:
    """Avisa o site que o alerta ('notificado') ou lembrete ('lembrete') foi enviado."""
    requests.post(f"{config.SITE_URL}/api/chamados/{chamado_id}/marcar",
                  json={"evento": evento},
                  headers={"X-Monitor-Token": config.MONITOR_TOKEN},
                  timeout=10).raise_for_status()


# ---------------------------------------------------------------- utilitários
def dias_desde(texto: str) -> int:
    """Dias entre uma data/hora ISO ('AAAA-MM-DD...') e hoje."""
    return (date.today() - date.fromisoformat(texto[:10])).days


def bloco_chamado(c: dict) -> list[tuple[str, str]]:
    """Pares (rótulo, valor) exibidos no e-mail."""
    return [
        ("ID", f"#{c['id']}"),
        ("Aberto em", c["aberto"].replace("T", " ")),
        ("Solicitante", c["solicitante"]),
        ("Setor/local", c["setor"]),
        ("Contato", c["contato"]),
        ("Equipamento", c["equipamento"]),
        ("Patrimônio", c["patrimonio"] or "—"),
        ("Problema ocorre há", f"{dias_desde(c['desde'])} dia(s) (desde {c['desde']})"),
        ("Aberto há", f"{dias_desde(c['aberto'])} dia(s)"),
        ("Prioridade", f"{EMOJI.get(c['prioridade'], '')} {c['prioridade'].upper()}"),
        ("Status", c["status"]),
        ("Detalhes", c["detalhes"]),
    ]


def enviar_email(assunto: str, texto: str, html: str) -> None:
    """Envia e-mail (texto + HTML) via SMTP para o destinatário padronizado."""
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = assunto, config.SMTP_USER, config.EMAIL_DESTINO
    msg.set_content(texto)
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as smtp:
        smtp.starttls()
        smtp.login(config.SMTP_USER, config.SMTP_PASSWORD)
        smtp.send_message(msg)


def montar_chamado(c: dict, titulo: str) -> tuple[str, str, str]:
    """Retorna (assunto, texto, html) para um único chamado."""
    pares = bloco_chamado(c)
    assunto = f"{EMOJI.get(c['prioridade'], '')} {titulo} #{c['id']} — {c['titulo']}"
    texto = "\n".join(f"{k}: {v}" for k, v in pares)
    linhas = "".join(f"<tr><td><b>{escape(k)}</b></td><td>{escape(v).replace(chr(10), '<br>')}</td></tr>"
                     for k, v in pares)
    html = f"<h3>{escape(titulo)}: {escape(c['titulo'])}</h3><table cellpadding='6'>{linhas}</table>"
    return assunto, texto, html


# ---------------------------------------------------------------- regras
def notificar_novos(chamados: list[dict], tentativas: dict) -> None:
    for c in (c for c in chamados if not c["notificado"]):
        if tentativas.get(c["id"], 0) >= config.MAX_TENTATIVAS:
            continue  # desistiu deste chamado (zera ao reiniciar o monitor)
        try:
            enviar_email(*montar_chamado(c, "Novo chamado"))
            marcar(c["id"], "notificado")
            log.info("Chamado #%s notificado.", c["id"])
        except (smtplib.SMTPException, OSError, requests.RequestException) as e:
            tentativas[c["id"]] = tentativas.get(c["id"], 0) + 1
            log.error("Falha ao notificar #%s (tentativa %s/%s): %s",
                      c["id"], tentativas[c["id"]], config.MAX_TENTATIVAS, e)


def enviar_lembretes(chamados: list[dict]) -> None:
    """Lembra chamados abertos há LEMBRETE_DIAS ou mais, no máximo 1x por dia."""
    for c in chamados:
        if not c["notificado"] or c["status"] == "resolvido":
            continue
        if dias_desde(c["aberto"]) < config.LEMBRETE_DIAS:
            continue
        if c["lembrete"] and dias_desde(c["lembrete"]) < 1:
            continue
        try:
            enviar_email(*montar_chamado(c, "⏰ Lembrete de chamado parado"))
            marcar(c["id"], "lembrete")
            log.info("Lembrete do chamado #%s enviado.", c["id"])
        except (smtplib.SMTPException, OSError, requests.RequestException) as e:
            log.error("Falha no lembrete de #%s: %s", c["id"], e)


def enviar_resumo(chamados: list[dict], estado: dict) -> None:
    """Resumo diário dos chamados em aberto, uma vez por dia após RESUMO_HORA."""
    agora = datetime.now()
    if agora.hour < config.RESUMO_HORA or estado.get("resumo") == agora.date():
        return
    abertos = [c for c in chamados if c["status"] != "resolvido"]
    if abertos:
        texto = "\n".join(f"#{c['id']} {EMOJI.get(c['prioridade'], '')} {c['titulo']} "
                          f"({c['solicitante']}, aberto há {dias_desde(c['aberto'])} dia(s), {c['status']})"
                          for c in abertos)
        html = "<ul>" + "".join(f"<li>{escape(l)}</li>" for l in texto.split("\n")) + "</ul>"
        try:
            enviar_email(f"📋 Resumo diário: {len(abertos)} chamado(s) em aberto", texto, html)
        except (smtplib.SMTPException, OSError) as e:
            log.error("Falha no resumo diário: %s", e)
            return  # tenta de novo no próximo ciclo
    estado["resumo"] = agora.date()


# ---------------------------------------------------------------- loop principal
def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    if not (config.SMTP_USER and config.SMTP_PASSWORD):
        raise SystemExit("Configure SMTP_USER e SMTP_PASSWORD no arquivo .env")
    log.info("Monitor iniciado (intervalo %ss, destino %s).", config.POLL_INTERVAL, config.EMAIL_DESTINO)
    tentativas, estado = {}, {}
    while True:
        try:
            chamados = buscar_chamados()
            notificar_novos(chamados, tentativas)
            enviar_lembretes(chamados)
            enviar_resumo(chamados, estado)
        except requests.RequestException as e:
            log.error("Não foi possível ler o site: %s", e)
        except Exception:  # um erro inesperado não pode derrubar o monitor
            log.exception("Erro inesperado no ciclo")
        time.sleep(config.POLL_INTERVAL)


if __name__ == "__main__":
    main()
