from flask import Flask, render_template, request, jsonify, send_file
import sqlite3, smtplib, email.utils
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from weasyprint import HTML
import os, uuid

app = Flask(__name__)
DB = "transport.db"

# ---------- Mail-Sender ----------
SMTP = "smtp.gmail.com"
PORT = 587
USER = "your@gmail.com"
PASS = "yourpassword"

def send_mail(to, subj, body):
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subj
    msg["From"] = USER
    msg["To"] = to
    try:
        srv = smtplib.SMTP(SMTP, PORT)
        srv.starttls()
        srv.login(USER, PASS)
        srv.sendmail(USER, [to], msg.as_string())
        srv.quit()
        return True
    except Exception as e:
        print("Mail-Fehler:", e)
        return False

# ---------- API ----------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/buchung")
def buchung():
    return render_template("buchung.html")

@app.route("/api/buchen", methods=["POST"])
def api_buchen():
    data = request.get_json()
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    # Kunde anlegen
    c.execute("INSERT INTO kunden(name,tel,mail) VALUES (?,?,?)",
              (data["name"], data["tel"], data["mail"]))
    k_id = c.lastrowid
    # Termin
    c.execute("""INSERT INTO termine(kunde_id,datum,zeit,abfahrt,ziel,preis)
                 VALUES (?,?,?,?,?,?)""",
              (k_id, data["datum"], data["zeit"], data["abfahrt"], data["ziel"], data["preis"]))
    conn.commit(); conn.close()
    # Mail-Bestätigung
    body = f"Hallo {data['name']},\nIhr Transport ist gebucht am {data['datum']} um {data['zeit']} Uhr.\nStrecke: {data['abfahrt']} → {data['ziel']}\nPreis: {data['preis']} €\n\nMit freundlichen Grüßen\nIhre Transport-Firma"
    send_mail(data["mail"], "Buchungsbestätigung", body)
    return jsonify({"ok": True})

@app.route("/api/rechnung/<int:tid>")
def api_rechnung(tid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    row = c.execute("""SELECT t.datum,t.zeit,t.abfahrt,t.ziel,t.preis,k.name,k.mail
                       FROM termine t JOIN kunden k ON t.kunde_id = k.id
                       WHERE t.id=?""", (tid,)).fetchone()
    conn.close()
    if not row: return "Termin nicht gefunden", 404
    datum, zeit, abf, ziel, preis, name, mail = row
    html_code = f"""
    <html>
      <head><meta charset="utf-8"><title>Rechnung</title></head>
      <body style="font-family:Arial,sans-serif;margin:40px;">
        <h1 style="color:#c53030">Rechnung</h1>
        <p>Kunde: {name}<br>Datum: {datum} {zeit} Uhr<br>Strecke: {abf} → {ziel}</p>
        <hr>
        <p style="font-size:20px;font-weight:bold;">Preis: {preis} €</p>
      </body>
    </html>"""
    pdf_path = f"invoices/RE{tid}.pdf"
    HTML(string=html_code).write_pdf(pdf_path)
    return send_file(pdf_path, as_attachment=True)

# ---------- Reminder-Job ----------
from apscheduler.schedulers.background import BackgroundScheduler
def reminder_job():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    rows = c.execute("""SELECT t.id,t.zeit,k.name,k.mail
                        FROM termine t JOIN kunden k ON t.kunde_id = k.id
                        WHERE t.datum=? AND t.reminder_sent=0""", (tomorrow,)).fetchall()
    for tid, zeit, name, mail in rows:
        body = f"Hallo {name},\nerinnerung an Ihren Transport morgen ({tomorrow}) um {zeit} Uhr."
        if send_mail(mail, "Erinnerung – Transport morgen", body):
            c.execute("UPDATE termine SET reminder_sent=1 WHERE id=?", (tid,))
    conn.commit(); conn.close()

sched = BackgroundScheduler(daemon=True)
sched.add_job(reminder_job, "interval", minutes=60)
sched.start()

if __name__ == "__main__":
    os.makedirs("invoices", exist_ok=True)
    app.run(debug=True)