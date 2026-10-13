"""Configurações centralizadas, lidas do arquivo .env."""
import os

from dotenv import load_dotenv

load_dotenv()

SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:5000").rstrip("/")
MONITOR_TOKEN = os.getenv("MONITOR_TOKEN", "troque-por-um-token-longo")
DB_PATH = os.getenv("DB_PATH", "chamados.db")

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))
LEMBRETE_DIAS = int(os.getenv("LEMBRETE_DIAS", "2"))
RESUMO_HORA = int(os.getenv("RESUMO_HORA", "8"))
MAX_TENTATIVAS = int(os.getenv("MAX_TENTATIVAS", "5"))

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
# Destinatário padronizado: todos os alertas vão para este e-mail.
EMAIL_DESTINO = os.getenv("EMAIL_DESTINO", "rm98603@fiap.com.br")
