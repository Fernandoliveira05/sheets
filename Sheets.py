import gspread  # Biblioteca para manipularmos o Google Sheets
from google.oauth2.service_account import Credentials  # Importando o uso das credenciais
import psycopg2  # Biblioteca para termos acesso ao PostgreSQL
from psycopg2.extras import execute_values  # Importando uma função da biblioteca para extrairmos os valores
from time import sleep  # Para introduzir atrasos no loop
import os  # Manipulação de variáveis de ambiente
import datetime  # Para manipular dados de tempo

# Configuração do Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = './Apontar.json'  # Substitua pelo caminho do arquivo de credenciais
SPREADSHEET_ID = '1gGsG63QDT_7p7V0SLvyRM78U_fE0VqfmWggltiWKSKU'

# Configuração de acesso ao Google Sheets
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(credentials)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

# Conexão ao banco de dados PostgreSQL
try:
    db = psycopg2.connect(
        host=os.getenv("DB_HOST", "dpg-cu2km11u0jms73dai7f0-a.oregon-postgres.render.com"),
        user=os.getenv("DB_USER", "originei_contatos_y7vy_user"),
        password=os.getenv("DB_PASSWORD", "jJ1sDPZlv9ptrp6vwJ0Rk3jGFG2jgmY7"),
        database=os.getenv("DB_NAME", "originei_contatos_y7vy"),
        port=os.getenv("DB_PORT", "5432")
    )
    cursor = db.cursor()
    print("[INFO] Conexão com o banco de dados estabelecida com sucesso.")
except Exception as e:
    print(f"[ERRO] Falha ao conectar ao banco de dados: {e}")
    exit(1)

def get_last_synced_id():
    """
    Obtém o último ID sincronizado a partir da planilha.
    Presume que o ID está na primeira coluna da planilha.
    """
    rows = sheet.get_all_values()
    if len(rows) > 1:
        last_row = rows[-1]  # Obtém a última linha preenchida
        print(f"[INFO] Última linha na planilha: {last_row}")
        try:
            return int(last_row[0])  # Presume que o ID está na primeira coluna
        except ValueError:
            print("[ERRO] O último valor na coluna de ID não é válido.")
            return 0
    return 0

def add_headers():
    """
    Adiciona os cabeçalhos das colunas à planilha se estiver vazia.
    """
    try:
        a1_value = sheet.acell('A1').value
        if a1_value is None:
            print("[INFO] Planilha vazia. Obtendo cabeçalhos do banco de dados...")
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")
            headers = [col[0] for col in cursor.fetchall()]
            if headers:
                sheet.update('A1', [headers])
                print("[INFO] Cabeçalhos adicionados à planilha.")
            else:
                print("[ERRO] Nenhum cabeçalho foi retornado do banco de dados.")
        else:
            print(f"[INFO] Cabeçalhos já existentes: {a1_value}")
    except Exception as e:
        print(f"[ERRO] Falha ao adicionar cabeçalhos: {e}")

def get_unsynced_rows(last_synced_id):
    """
    Obtém as linhas do banco de dados com ID maior que o último ID sincronizado.
    """
    try:
        query = "SELECT * FROM users WHERE id > %s ORDER BY id ASC"
        cursor.execute(query, (last_synced_id,))
        rows = cursor.fetchall()

        unsynced_rows = []
        for row in rows:
            processed_row = [
                col.isoformat() if isinstance(col, datetime.datetime) else
                str(col) if isinstance(col, datetime.timedelta) else
                col
                for col in row
            ]
            unsynced_rows.append(processed_row)
        print(f"[INFO] Linhas não sincronizadas obtidas: {unsynced_rows}")
        return unsynced_rows
    except Exception as e:
        print(f"[ERRO] Falha ao buscar linhas não sincronizadas: {e}")
        return []

def sync_db_to_sheet():
    """
    Sincroniza incrementalmente novas linhas do banco de dados para a planilha.
    """
    try:
        add_headers()
        last_synced_id = get_last_synced_id()
        print(f"[INFO] Último ID sincronizado: {last_synced_id}")

        unsynced_rows = get_unsynced_rows(last_synced_id)
        if unsynced_rows:
            for row in unsynced_rows:
                sheet.append_row(row)
                print(f"[INFO] Linha sincronizada: {row}")
            print("[INFO] Sincronização concluída com sucesso.")
        else:
            print("[INFO] Nenhuma nova linha para sincronizar.")
    except Exception as e:
        print(f"[ERRO] Falha ao sincronizar banco -> planilha: {e}")

try:
    while True:
        print("[INFO] Iniciando sincronização...")
        sync_db_to_sheet()
        print("[INFO] Aguardando próxima execução...")
        sleep(5)
except KeyboardInterrupt:
    print("[INFO] Sincronização interrompida pelo usuário.")
except Exception as e:
    print(f"[ERRO] Erro inesperado: {e}")
finally:
    cursor.close()
    db.close()
    print("[INFO] Conexão com o banco de dados encerrada.")
