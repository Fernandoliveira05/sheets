from flask import Flask, jsonify
import gspread
from google.oauth2.service_account import Credentials
import psycopg2
from psycopg2.extras import execute_values
import os
import datetime
from threading import Thread
from time import sleep

app = Flask(__name__)

# Configuração do Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = './Apontar.json'  # Substitua pelo caminho do arquivo de credenciais
SPREADSHEET_ID = '1gGsG63QDT_7p7V0SLvyRM78U_fE0VqfmWggltiWKSKU'

credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(credentials)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

# Conexão ao banco de dados PostgreSQL
db = psycopg2.connect(
    host=os.getenv("DB_HOST", "dpg-cu2km11u0jms73dai7f0-a.oregon-postgres.render.com"),
    user=os.getenv("DB_USER", "originei_contatos_y7vy_user"),
    password=os.getenv("DB_PASSWORD", "jJ1sDPZlv9ptrp6vwJ0Rk3jGFG2jgmY7"),
    database=os.getenv("DB_NAME", "originei_contatos_y7vy"),
    port=os.getenv("DB_PORT", "5432")
)
cursor = db.cursor()

# Função para obter o último ID sincronizado
def get_last_synced_id():
    rows = sheet.get_all_values()
    if len(rows) > 1:
        last_row = rows[-1]
        try:
            return int(last_row[0])
        except ValueError:
            return 0
    return 0

# Função para sincronizar com o Google Sheets
def sync_db_to_sheet():
    try:
        last_synced_id = get_last_synced_id()
        cursor.execute("SELECT * FROM users WHERE id > %s ORDER BY id ASC", (last_synced_id,))
        rows = cursor.fetchall()

        for row in rows:
            processed_row = [
                col.isoformat() if isinstance(col, datetime.datetime) else
                str(col) if isinstance(col, datetime.timedelta) else
                col
                for col in row
            ]
            sheet.append_row(processed_row)
        return {"message": "Sincronização concluída", "rows_synced": len(rows)}
    except Exception as e:
        return {"error": str(e)}

# Endpoint manual de sincronização
@app.route('/sync', methods=['POST'])
def manual_sync():
    result = sync_db_to_sheet()
    return jsonify(result)

# Endpoint para verificar o status da API
@app.route('/status', methods=['GET'])
def status():
    return jsonify({"message": "API está funcionando!"})

# Loop contínuo para sincronização automática
def auto_sync(interval=5):
    while True:
        print("[INFO] Iniciando sincronização automática...")
        result = sync_db_to_sheet()
        print("[INFO] Resultado da sincronização automática:", result)
        sleep(interval)

# Inicializa o servidor Flask e a sincronização automática
if __name__ == '__main__':
    # Inicia o loop de sincronização automática em uma thread separada
    thread = Thread(target=auto_sync, args=(5,))
    thread.daemon = True  # Permite encerrar o loop quando o programa for finalizado
    thread.start()

    # Inicia o servidor Flask
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
