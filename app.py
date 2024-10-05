from flask import Flask, render_template, request, redirect, url_for, flash
from elasticsearch import Elasticsearch
from datetime import datetime
import mysql.connector
import subprocess
import time
import bcrypt
import os
import subprocess
import time
import requests
import secrets

app = Flask(__name__)

# Verifica se já existe uma secret key
if not os.getenv('FLASK_SECRET_KEY'):
    # Gerar uma chave aleatória em hexadecimal
    secret_key = secrets.token_hex(24)
    print(f'Generated secret key: {secret_key}')

    # Define a chave gerada como a chave secreta da aplicação
    app.secret_key = secret_key
    os.environ['FLASK_SECRET_KEY'] = secret_key
else:
    # Se já houver uma chave secreta definida no ambiente, usar ela
    app.secret_key = os.getenv('FLASK_SECRET_KEY')

# Configurações de conexão ao MySQL
mydb_config = {
    'host': "127.0.0.1",
    'port': "3306",
    'user': "root",
    'password': "root",
    'database': "docsnaipa"
}

# Função auxiliar para conectar ao banco de dados
def connect_to_db():
    try:
        conn = mysql.connector.connect(**mydb_config)
        if conn.is_connected():
            print("Conectado ao MySQL Server")
            return conn
    except mysql.connector.Error as err:
        print(f"Erro: {err}")
        return None

# Função para iniciar o Elasticsearch
def start_elasticsearch():
    es_path = r"C:\Users\sch_l\elasticsearch-8.15.2\bin\elasticsearch.bat"
    # Inicia o Elasticsearch em um subprocesso
    subprocess.Popen(es_path, shell=True)
    time.sleep(30)  # Aguarda o Elasticsearch iniciar

# Verifica se o Elasticsearch está rodando
def check_elasticsearch():
    try:
        response = requests.get('http://localhost:9200')
        if response.status_code == 200:
            print("Elasticsearch iniciado com sucesso!")
            return True
        else:
            print(f"Elasticsearch não respondeu corretamente. Código: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("Não foi possível conectar ao Elasticsearch. Verifique se ele foi iniciado corretamente.")
        return False

# Conexão com o Elasticsearch (defina globalmente)
es = None

def initialize_elasticsearch():
    global es
    if check_elasticsearch():
        es = Elasticsearch(['http://localhost:9200'])
        print("Conexão com Elasticsearch estabelecida.")
    else:
        print("Erro ao estabelecer conexão com o Elasticsearch.")

# Rota inicial do portal
@app.route('/meu-portal')
def meu_portal():
    global es

    # Iniciar o Elasticsearch, se não estiver iniciado
    if es is None:
        start_elasticsearch()
        initialize_elasticsearch()

    # Conectar ao banco de dados
    conn = connect_to_db()
    if conn is None:
        return "Erro ao conectar ao banco de dados."
    cursor = conn.cursor(dictionary=True)

    # Buscar categorias existentes no banco de dados
    cursor.execute("SELECT IDCATEGORY, NAME FROM DCCATEGORY")
    categorias = cursor.fetchall()

    # Fechar a conexão
    cursor.close()
    conn.close()

    # Passar as categorias para o template
    return render_template('meu_portal.html', categorias=categorias)

# Rota para inserir documento no Elasticsearch e MYSQL
@app.route('/inserir-documento', methods=['POST'])
def inserir_documento():
    global es

    # Iniciar o Elasticsearch, se não estiver iniciado
    if es is None:
        start_elasticsearch()
        initialize_elasticsearch()

    identificador = request.form['identificador']
    nome_documento = request.form['nome_documento']
    categoria = request.form['categoria']
    autor = request.form['autor']

    # Criando documento
    doc = {
        'identificador': identificador,
        'nome_documento': nome_documento,
        'categoria': categoria,
        'autor': autor,
        'timestamp': datetime.now(),
    }

    # Inserir no Elasticsearch
    try:
        res = es.index(index="python-elasticsearch", body=doc)
        print("Documento inserido no Elasticsearch com sucesso:", res['result'])
    except Exception as e:
        print(f"Erro ao inserir documento no Elasticsearch: {e}")
        return "Erro ao inserir documento no Elasticsearch."
    
    # Inserir o documento no banco de dados MySQL
    try:
        conn = connect_to_db()
        if conn is None:
            return "Erro ao conectar ao banco de dados."

        cursor = conn.cursor()

        query_insert_documento = """
        INSERT INTO DCDOCUMENT (IDDOCUMENT, NMDOCUMENT, CATEGORY, REDATOR, REVISION, CURRENT)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query_insert_documento, (identificador, nome_documento, categoria, autor, 0, 2))  # REVISION = 0, CURRENT = 2
        conn.commit()

        cursor.close()
        conn.close()

        print("Documento inserido no banco de dados com sucesso.")
    except Exception as e:
        print(f"Erro ao inserir documento no banco de dados: {e}")
        return "Erro ao inserir documento no banco de dados."

    # Redireciona de volta ao portal após inserção no Elasticsearch e no MySQL
    return redirect(url_for('meu_portal'))

# Rota inicial para login
@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login_route():
    if request.method == 'POST':
        login_user = request.form['login']  # Captura o usuário do campo do HTML /login
        password = request.form['senha']  # Captura a senha do campo do HTML /login

        conn = connect_to_db()
        cursor = conn.cursor(dictionary=True)

        # Verifica se o usuário existe
        cursor.execute("SELECT * FROM USERS WHERE LOGIN_USER = %s", (login_user,))
        user = cursor.fetchone()

        if user:
            # Compara a senha inserida com a senha armazenada (hash)
            if bcrypt.checkpw(password.encode('utf-8'), user['PASSWORD'].encode('utf-8')):
                flash("Login bem-sucedido!", "success")
                return redirect(url_for('home'))
            else:
                flash("Senha incorreta!", "danger")
        else:
            flash("Usuário não encontrado!", "danger")

        cursor.close()
        conn.close()

    return render_template('login.html')

# Rota para a página de registro
@app.route('/cadastro', methods=['GET', 'POST'])
def register_route():
    if request.method == 'POST':
        login_user = request.form['login']
        password = request.form['senha']
        name_user = request.form['nome']

        # Criptografar a senha
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        conn = connect_to_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO USERS (LOGIN_USER, PASSWORD, NAME_USER) VALUES (%s, %s, %s)",
                       (login_user, hashed_password, name_user))
        conn.commit()
        cursor.close()
        conn.close()

        flash('Usuário registrado com sucesso! Você pode fazer login agora.')
        return redirect(url_for('login_route'))

    return render_template('cadastro.html')

# Página inicial após login
@app.route('/home', methods=['GET'])
def home():
    return render_template('home.html')

# Rota para exibir tarefas
@app.route('/minhas-tarefas')
def minhas_tarefas():
    return render_template('minhas_tarefas.html')

# Rota para a pesquisa de documentos
@app.route('/pesquisa-documentos')
def pesquisa_documentos():
    global es

    # Iniciar o Elasticsearch, se não estiver iniciado
    if es is None:
        start_elasticsearch()
        initialize_elasticsearch()

    query = request.args.get('document')
    conn = connect_to_db()
    if conn:
        print("Conexão ativa, realizando consulta...")
        try:
            mycursor = conn.cursor()
            mycursor.execute("SELECT iddocument, nmdocument FROM dcdocument WHERE iddocument = %s OR nmdocument LIKE %s", (query, '%' + query + '%'))
            resultados = mycursor.fetchall()
            mycursor.close()
            return render_template('pesquisa_documentos.html', dados=resultados)
        except mysql.connector.Error as err:
            print(f"Erro ao consultar o banco de dados: {err}")
            return "Erro ao consultar o banco de dados."
        finally:
            conn.close()
            print("Conexão com o MySQL foi encerrada.")
    else:
        print("Falha na conexão com o banco de dados.")
        return "Erro ao conectar ao banco de dados."

# Rota para página de configurações
@app.route('/configuracoes')
def configuracoes():
    return render_template('configuracoes.html')

# Executar o app Flask
if __name__ == '__main__':
    app.run(debug=True)
