"""Post this round's EPL model bets to the Telegram channel (Cowork session 17, 2026-10-28).
Rules from TELEGRAM_CHANNEL_HANDOFF.md (gitignored; token lives in .env as TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID).

  python scripts/telegram_post.py preview   # print the message, send nothing
  python scripts/telegram_post.py test      # send 'Test from the other sports model.'
  python scripts/telegram_post.py send      # send this round's bets (once per predict run; --force to resend)

Safety: never posts 11:25-11:40 Sat (racing card); never posts a stale round (predict older than 3 days);
records each sent round in output/paper_trading/telegram_sent.csv so a re-run does not double-post.
"""
import html, math, os, sys
from datetime import datetime, date, timedelta
from pathlib import Path
import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT)); sys.path.insert(0, str(Path(__file__).resolve().parent))
os.chdir(PROJECT)
import au_prices  # noqa: E402

LOG = PROJECT / 'output' / 'paper_trading' / 'log_ah.csv'
SENT = PROJECT / 'output' / 'paper_trading' / 'telegram_sent.csv'
MAX_LEN = 4096
MIN_CHANCE = 0.15

KEY = ('<b>KEY</b>\n'
       '<i>⚽ the match · AH = Asian handicap: a team starts with a goal head start (+) or deficit (−) · '
       '% = chance the bet comes in (a refund counts as half) · "price says → with the edge" = the bookmakers\' '
       'chance → our model\'s chance · "Worth it at" = lowest price that still pays off on the model\'s numbers</i>')

PLAIN = {0.0: 'win = win, draw = money back', 0.5: 'win or draw', -0.5: 'must win',
         0.25: 'win or draw = win (a draw pays half)', -0.25: 'must win (a draw gives half your stake back)',
         0.75: 'win or draw = win; lose by 1 = half stake lost',
         -0.75: 'win by 2+ = win; win by 1 = half win', 1.0: 'win or draw = win; lose by 1 = money back',
         -1.0: 'win by 2+ = win; win by 1 = money back', 1.5: 'win, draw or lose by 1',
         -1.5: 'win by 2 or more', 1.25: 'win or draw = win; lose by 1 = half win',
         -1.25: 'win by 2+ = win; win by 1 = half stake lost'}


def esc(s):
    return html.escape(str(s), quote=False)


def fmt_date(d):
    return datetime.strptime(str(d)[:10], '%Y-%m-%d').strftime('%a %-d %b') if os.name != 'nt' else \
        datetime.strptime(str(d)[:10], '%Y-%m-%d').strftime('%a %#d %b')


def latest_round(log):
    cur = log[log['league'] == 'EPL']
    if cur.empty:
        return None, cur
    p = cur['prediction_date'].astype(str).max()
    return p, cur[cur['prediction_date'].astype(str) == p]


def au_lookup():
    try:
        s = au_prices.read_sheet()
    except Exception:
        return {}
    out = {}
    for _, r in s.iterrows():
        prices = au_prices.effective_prices(r.to_dict())
        if prices:
            col, v = max(prices.items(), key=lambda kv: kv[1])
            out[r['key']] = (v, au_prices.BOOK_LABELS[col], float(r['break_even']))
    return out


def bet_block(r, au):
    side = str(r['bet_side'])
    team = r['home_team'] if side == 'home' else r['away_team']
    line = au_prices.bet_line(r['ah_line'], side)
    q, p = float(r['market_prob_consensus']), float(r['calib_prob'])
    if p < MIN_CHANCE:
        return None
    pp = au_prices.market_push_prob(q, r['ah_line'], side)
    be = au_prices.break_even(p, pp)
    q_score = q + pp * (0.5 - q)   # bookmakers' chance on the same basis as the model (refund = half)
    market, _ = au_prices.au_market(line)
    lines = [f"<b>{esc(r['home_team'])} v {esc(r['away_team'])}</b> · {fmt_date(r['match_date'])}",
             f"Bet: {esc(team)} AH {line:+.2f} — {esc(PLAIN.get(line, 'Asian handicap ' + format(line, '+.2f')))}",
             f"At AU bookies look for: {esc(market)}",
             f"Chance: price says {q_score:.0%} → with the edge {p:.0%}",
             f"Worth it at {be:.2f} or better"]
    key = f"{r['prediction_date']}|{r['home_team']}|{r['away_team']}"
    if key in au:
        v, book, _ = au[key]
        verdict = 'worth it' if v >= be else 'too low, skip it'
        lines.append(f"Best AU price found: {v:.2f} ({esc(book)}), {verdict}")
    else:
        lines.append(f"Best price found online: {float(r['odds_ah']):.2f}")
    return '\n'.join(lines)


def build_messages(log, au=None):
    au = au_lookup() if au is None else au
    pdate, rnd = latest_round(log)
    if pdate is None:
        return pdate, []
    flagged = rnd[rnd['bet_flag'].astype(str) == 'True'].sort_values('match_date')
    d0, d1 = rnd['match_date'].min(), rnd['match_date'].max()
    span = fmt_date(d0) if d0 == d1 else f'{fmt_date(d0)} to {fmt_date(d1)}'
    head = f'⚽ <b>EPL — {span}</b>'
    blocks = [b for b in (bet_block(r, au) for _, r in flagged.iterrows()) if b]
    if not blocks:
        body = [head, f'No bets this round. The model found no edge worth betting in {len(rnd)} matches.']
    else:
        body = [head, f'{len(blocks)} bet(s) from {len(rnd)} matches.'] + blocks
    msgs, cur = [], KEY
    for part in body:
        cand = cur + '\n\n' + part
        if len(cand) > MAX_LEN:
            msgs.append(cur); cur = KEY + '\n\n' + part
        else:
            cur = cand
    msgs.append(cur)
    return pdate, msgs


def creds():
    try:
        from dotenv import load_dotenv; load_dotenv(PROJECT / '.env')
    except ImportError:
        for line in (PROJECT / '.env').read_text(encoding='utf-8').splitlines():
            if '=' in line:
                k, v = line.split('=', 1); os.environ.setdefault(k.strip(), v.strip())
    tok, cid = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
    if not tok or not cid:
        raise SystemExit('ERROR: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID missing from .env')
    return tok, int(cid)


def post(text):
    import requests
    tok, cid = creds()
    r = requests.post(f'https://api.telegram.org/bot{tok}/sendMessage',
                      json={'chat_id': cid, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': True},
                      timeout=30)
    body = r.json()
    if not body.get('ok'):
        raise RuntimeError(f"Telegram refused the message: {body.get('description')}")


def racing_window(now):
    return now.weekday() == 5 and (now.hour, now.minute) >= (11, 25) and (now.hour, now.minute) <= (11, 40)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    now = datetime.now()
    if mode == 'test':
        post('Test from the other sports model.'); print('Test message sent.'); return 0
    log = pd.read_csv(LOG)
    pdate, msgs = build_messages(log)
    if mode == 'preview':
        for m in msgs:
            print(m); print('-' * 60)
        return 0
    if mode != 'send':
        print('mode must be preview, test or send'); return 1
    if pdate is None:
        print('No EPL rows in the log - nothing sent.'); return 1
    if (date.today() - datetime.strptime(pdate, '%Y-%m-%d').date()).days > 3:
        print(f'Latest predict run is {pdate} - stale (predict failed?). Nothing sent.'); return 1
    sent = pd.read_csv(SENT, dtype=str) if SENT.exists() else pd.DataFrame(columns=['prediction_date', 'sent_at', 'messages'])
    if pdate in set(sent.prediction_date) and '--force' not in sys.argv:
        print(f'Round {pdate} already posted - nothing sent (use --force to resend).'); return 0
    if racing_window(now):
        print('Inside the Saturday 11:25-11:40 racing window - nothing sent.'); return 1
    for m in msgs:
        post(m)
    sent = pd.concat([sent, pd.DataFrame([{'prediction_date': pdate, 'sent_at': now.isoformat(timespec='minutes'),
                                           'messages': len(msgs)}])], ignore_index=True)
    sent.to_csv(SENT, index=False)
    print(f'Posted round {pdate}: {len(msgs)} message(s).')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except RuntimeError as e:
        print(f'ERROR: {e}'); sys.exit(2)
