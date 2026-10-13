# Chamados de TI — alerta automático por e-mail

Usuário abre o chamado em uma página HTML; o monitor Python lê a página da TI
(requests + BeautifulSoup) e envia o alerta por e-mail para `rm98603@fiap.com.br`.

## Como rodar (Python 3.10+)
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # preencha SMTP_USER, SMTP_PASSWORD e MONITOR_TOKEN
python app.py               # terminal 1: site em http://127.0.0.1:5000
python monitor.py           # terminal 2: monitor
```
- Formulário do usuário: `http://127.0.0.1:5000/`
- Painel da TI: `http://127.0.0.1:5000/ti/chamados`

## E-mail (Gmail)
Ative a verificação em duas etapas e crie uma **senha de app**; use-a em `SMTP_PASSWORD`.

## O que o alerta traz
ID e data/hora (automáticos), solicitante, setor, contato, equipamento, patrimônio,
há quantos dias o problema ocorre, há quantos dias o chamado está aberto, prioridade
(🟢🟡🟠🔴), status e detalhes. Também há lembrete diário de chamados parados
(`LEMBRETE_DIAS`) e resumo diário (`RESUMO_HORA`).

## Confiabilidade
O chamado só é marcado como notificado após o e-mail ser enviado. Se falhar,
o monitor tenta no próximo ciclo (até `MAX_TENTATIVAS`) e registra tudo em log.

## Equipe

| Integrante        | RM      |
| ----------------- | ------- |
| David Denunci     | RM98603 |
| Fernando Popolili | RM99919 |
| Lucas de Toledo   | RM97913 |
| Matheus Zanardi   | RM98832 |
| Augusto Milreu    | RM98245 |