from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, current_user, login_required, UserMixin
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


# Configurar o Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Rota de login

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
    if es is None:
        start_elasticsearch()
        initialize_elasticsearch()

    identificador = request.form['identificador']
    nome_documento = request.form['nome_documento']
    categoria = request.form['categoria']
    autor = request.form['autor']
    doc = {
        'identificador': identificador,
        'nome_documento': nome_documento,
        'categoria': categoria,
        'autor': autor,
        'timestamp': datetime.now(),
    }

    # Inserção no Elasticsearch
    try:
        res = es.index(index="python-elasticsearch", body=doc)
        print("Documento inserido no Elasticsearch com sucesso:", res['result'])
    except Exception as e:
        print(f"Erro ao inserir documento no Elasticsearch: {e}")
        return "Erro ao inserir documento no Elasticsearch."
    
    # Inserção no MySQL e criação do workflow
    try:
        conn = connect_to_db()
        cursor = conn.cursor()

        query_insert_documento = """
        INSERT INTO DCDOCUMENT (IDDOCUMENT, NMDOCUMENT, CATEGORY, REDATOR, REVISION, CURRENT)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query_insert_documento, (identificador, nome_documento, categoria, autor, 0, 2))
        
        # Criar um novo Workflow no MySQL
        cursor.execute("""
            INSERT INTO WORKFLOW (form_id, status) VALUES (%s, 'PENDENTE')
        """, (identificador,))
        workflow_id = cursor.lastrowid
        
        # Definir usuários aprovadores
        usuarios_aprovadores = [1, 2]  # IDs dos usuários aprovadores
        for usuario_id in usuarios_aprovadores:
            cursor.execute("""
                INSERT INTO WORKFLOW_ATIVIDADES (workflow_id, usuario_id, status)
                VALUES (%s, %s, 'PENDENTE')
            """, (workflow_id, usuario_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Documento e Workflow criados no banco de dados com sucesso.")
    except Exception as e:
        print(f"Erro ao inserir documento e criar workflow no banco de dados: {e}")
        return "Erro ao inserir documento e criar workflow no banco de dados."

    return redirect(url_for('meu_portal'))

# Rota inicial para login
@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login_route():
    if request.method == 'POST':
        login_user_value = request.form['login']  # Renomeie esta variável
        password = request.form['senha']

        conn = connect_to_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM USERS WHERE LOGIN_USER = %s", (login_user_value,))  # Use a nova variável
        user = cursor.fetchone()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['PASSWORD'].encode('utf-8')):
            user_obj = User(user['ID'], user['NAME_USER'])
            login_user(user_obj)  # Autentica o usuário
            flash("Login bem-sucedido!", "success")
            return redirect(url_for('home'))
        else:
            flash("Usuário ou senha incorretos!", "danger")

        cursor.close()
        conn.close()

    return render_template('login.html')

# Classe de usuário para Flask-Login
class User(UserMixin):
    def __init__(self, id, name_user):
        self.id = id
        self.name_user = name_user

@login_manager.user_loader
def load_user(user_id):
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM USERS WHERE ID = %s", (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    conn.close()

    # Verifique o conteúdo de user_data
    print(user_data)  # Para verificar se o retorno inclui o campo 'id'
    
    if user_data:
        return User(user_data['ID'], user_data['NAME_USER'])  # Use 'ID' com maiúscula para corresponder à tabela
    return None

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
    usuario_id = 1  # ID do usuário logado (obter dinamicamente após implementação de autenticação)
    
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.id, a.status, w.form_id, w.status as workflow_status
        FROM WORKFLOW_ATIVIDADES a
        JOIN WORKFLOW w ON a.workflow_id = w.id
        WHERE a.usuario_id = %s AND a.status = 'PENDENTE'
    """, (usuario_id,))
    tarefas = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('minhas_tarefas.html', tarefas=tarefas)

# Rota para aprovar ou reprovar documentos (Workflow)
@app.route('/aprovar_reprovar/<int:atividade_id>', methods=['POST'])
def aprovar_reprovar(atividade_id):
    status = request.form['status']
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE WORKFLOW_ATIVIDADES
        SET status = %s, atualizado_em = %s
        WHERE id = %s
    """, (status, datetime.now(), atividade_id))
    
    cursor.execute("""
        SELECT workflow_id FROM WORKFLOW_ATIVIDADES WHERE id = %s
    """, (atividade_id,))
    workflow_id = cursor.fetchone()['workflow_id']
    
    cursor.execute("""
        SELECT COUNT(*) as pendentes FROM WORKFLOW_ATIVIDADES WHERE workflow_id = %s AND status = 'PENDENTE'
    """, (workflow_id,))
    pendentes = cursor.fetchone()['pendentes']

    if pendentes == 0:
        cursor.execute("""
            SELECT COUNT(*) as aprovadas FROM WORKFLOW_ATIVIDADES WHERE workflow_id = %s AND status = 'APROVADO'
        """, (workflow_id,))
        aprovadas = cursor.fetchone()['aprovadas']
        
        novo_status = 'APROVADO' if aprovadas > 0 else 'REPROVADO'
        cursor.execute("""
            UPDATE WORKFLOW SET status = %s WHERE id = %s
        """, (novo_status, workflow_id))

    conn.commit()
    cursor.close()
    conn.close()
    
    flash(f'Atividade {status} com sucesso!')
    return redirect(url_for('minhas_tarefas'))


# Rota para a pesquisa de documentos
@app.route('/pesquisa_documentos', methods=['GET'])
def pesquisa_documentos():
    global es

    # Iniciar o Elasticsearch, se ainda não estiver iniciado
    if es is None:
        start_elasticsearch()
        initialize_elasticsearch()

    # Receber o termo de busca do formulário
    termo_busca = request.args.get('document')

    # Realizar busca no Elasticsearch
    resultado_busca = es.search(
        index="nome_do_indice",
        body={
            "query": {
                "match": {
                    "conteudo": termo_busca
                }
            }
        }
    )

    # Extrair e formatar os resultados da busca
    documentos = [hit['_source'] for hit in resultado_busca['hits']['hits']]

    # Renderizar o template com os resultados
    return render_template('pesquisa_documentos.html', documentos=documentos)


# Rota para página de configurações
@app.route('/configuracoes')
def configuracoes():
    return render_template('configuracoes.html')

# Executar o app Flask
if __name__ == '__main__':
    app.run(debug=True)
