"""Acesso ao banco SQLite (biblioteca padrão, sem dependências extras)."""
import sqlite3
from contextlib import closing
from datetime import datetime

import config

PRIORIDADES = ("baixa", "média", "alta", "crítica")
STATUS = ("novo", "em andamento", "resolvido")


def _conectar() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def init_db() -> None:
    """Cria a tabela de chamados, se ainda não existir."""
    with closing(_conectar()) as conn, conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS chamados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aberto_em TEXT NOT NULL,
                solicitante TEXT NOT NULL,
                titulo TEXT NOT NULL,
                detalhes TEXT NOT NULL,
                equipamento TEXT NOT NULL,
                patrimonio TEXT,
                setor TEXT NOT NULL,
                contato TEXT NOT NULL,
                prioridade TEXT NOT NULL,
                desde TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'novo',
                notificado INTEGER NOT NULL DEFAULT 0,
                ultimo_lembrete TEXT
            )"""
        )


def criar_chamado(d: dict) -> int:
    """Grava um chamado novo; ID e data/hora de abertura são automáticos."""
    with closing(_conectar()) as conn, conn:
        cur = conn.execute(
            """INSERT INTO chamados (aberto_em, solicitante, titulo, detalhes,
               equipamento, patrimonio, setor, contato, prioridade, desde)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (_agora(), d["solicitante"], d["titulo"], d["detalhes"],
             d["equipamento"], d["patrimonio"], d["setor"], d["contato"],
             d["prioridade"], d["desde"]),
        )
        return cur.lastrowid


def listar(status: str | None = None) -> list[sqlite3.Row]:
    sql, params = "SELECT * FROM chamados", ()
    if status in STATUS:
        sql, params = sql + " WHERE status = ?", (status,)
    with closing(_conectar()) as conn:
        return conn.execute(sql + " ORDER BY id DESC", params).fetchall()


def atualizar_status(chamado_id: int, status: str) -> None:
    with closing(_conectar()) as conn, conn:
        conn.execute("UPDATE chamados SET status = ? WHERE id = ?", (status, chamado_id))


def marcar(chamado_id: int, evento: str) -> None:
    """Registra que o alerta ('notificado') ou o lembrete ('lembrete') foi enviado."""
    campo = {"notificado": "notificado = 1", "lembrete": "ultimo_lembrete = ?"}[evento]
    params = (_agora(), chamado_id) if evento == "lembrete" else (chamado_id,)
    with closing(_conectar()) as conn, conn:
        conn.execute(f"UPDATE chamados SET {campo} WHERE id = ?", params)
