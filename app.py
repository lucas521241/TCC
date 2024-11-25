# Importações necessárias para o funcionamento da aplicação
# Flask é o framework principal, Flask-Login para gerenciar autenticação, dotenv para variáveis de ambiente
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import LoginManager, login_user, current_user, login_required, UserMixin
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from datetime import datetime
import mysql.connector  # Para conexão com o banco de dados MySQL
import bcrypt  # Para criptografia de senhas
import os  # Manipulação de sistema operacional e variáveis de ambiente
import secrets  # Para geração de chaves seguras
import PyPDF2  # Biblioteca para manipulação de PDFs
import logging  # Configuração de logs para depuração e auditoria
import requests  # Para realizar requisições HTTP

# Inicializando a aplicação Flask
app = Flask(__name__)

# Configuração do log
logging.basicConfig(level=logging.INFO)
file_handler = logging.FileHandler('app.log')
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)

# Pra pegar a pasta do app.py
base_dir = os.path.dirname(os.path.abspath(__file__))

# Pra construir o caminho pro arquivo .env (API)
dotenv_path = os.path.join(base_dir, "pdf_view.env")

# Carregue a variavel pro ambiente
load_dotenv(dotenv_path)

# Chave de API do OpenAI
# Usada para integração com a API do ChatGPT
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    app.logger.error("API_KEY não foi carregada. Verifique o arquivo pdf_view.env e o uso do load_dotenv.")
else:
    app.logger.info("API_KEY carregada com sucesso.")

# Configurando o Flask-Login para gerenciar autenticação de usuários
login_manager = LoginManager()
login_manager.init_app(app)  # Ligando o LoginManager à aplicação Flask
login_manager.login_view = 'login'  # Define a rota padrão de login

# Verifica se já existe uma secret key
if not os.getenv('FLASK_SECRET_KEY'):
    # Gerar uma chave aleatória em hexadecimal caso não existir
    secret_key = secrets.token_hex(24)
    print(f'Generated secret key: {secret_key}') # Apenas para debug
    # Define a chave gerada como a chave secreta da aplicação
    app.secret_key = secret_key
    os.environ['FLASK_SECRET_KEY'] = secret_key
else:
    # Caso já tiver, vai utilizar a chave secreta já configurada na aplicação
    app.secret_key = os.getenv('FLASK_SECRET_KEY')

# Configurações de conexão ao MYSQL Workbench (OBS: Precisa inicializar ele pra funcionar)
mydb_config = {
    'host': "127.0.0.1",    # host do banco
    'port': "3306",         # Porta do banco
    'user': "root",         # Usuario do banco
    'password': "root",     # senha do banco (padrão é root)
    'database': "docsnaipa" # Nome do banco (no mysql utilizar o use docsnaipa)
}

# Função auxiliar para conectar ao banco de dados no MYSQL e centralizar a lógica de conexão
def connect_to_db():
    try:
        conn = mysql.connector.connect(**mydb_config)
        if conn.is_connected():
            print("Conectado ao MySQL Server")
            return conn
    except mysql.connector.Error as err:
        # Se caso falhar a conexão, trazer um print (impressão) do que rolou
        print(f"Erro: {err}")
        return None
    
# Local para armazenar os arquivos PDF feito pelo usuário pela tela "Meu Portal"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(PROJECT_DIR, "upload_files")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'pdf'} # limitado o tipo de arquivo para PDF

# Função para pegar as categorias no banco e facilitar no formulário
def obter_categorias():
    try:
        conn = connect_to_db()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT IDENTIFIER, IDCATEGORY FROM DCCATEGORY"
        cursor.execute(query)
        categorias = cursor.fetchall()
        cursor.close()
        conn.close()
        return categorias
    except Exception as e:
        print(f"Erro ao obter categorias: {e}")
        return []

# Função pra pegar a lista de usuários no banco e passar pro formulário no html
def obter_usuarios():
    try:
        conn = connect_to_db()
        cursor = conn.cursor(dictionary=True)
        query = "SSELECT ID, NAME_USER FROM USERS"
        cursor.execute(query)
        usuarios = cursor.fetchall()
        cursor.close()
        conn.close()
        return usuarios
    except Exception as e:
        print(f"Erro ao obter usuários: {e}")
        return []


# Função para pegar os documentos existentes no banco e que são ativos (current)
def obter_documentos():
    try:
        conn = connect_to_db()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT IDDOCUMENT, CDDOCUMENT FROM DCDOCUMENT WHERE CURRENT = 1"
        cursor.execute(query)
        documentos = cursor.fetchall()
        cursor.close()
        conn.close()
        return documentos
    except Exception as e:
        # Se der erro, printar o erro e retornar vazio
        print(f"Erro ao obter documentos: {e}")
        return []

# Função para pegar o texto do PDF e depois jogar pra API do chatGPT (resumir PDF) no chatGPT
def extract_text_from_pdf(pdf_path):
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ''
            # Log para verificar se o PDF foi lido corretamente
            if not reader.pages:
                app.logger.error(f"PDF {pdf_path} não possui páginas ou não pode ser lido.")
                return ''

            # Aqui ele vai pegar e verificar todas as páginas do PDF
            for page_num, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ''
                if not page_text:
                    app.logger.warning(f"Texto da página {page_num} do PDF {pdf_path} está vazio.")
                text += page_text
            app.logger.info(f"Texto extraído do PDF {pdf_path} com sucesso.")
            return text
    except Exception as e:
        app.logger.error(f"Erro ao tentar extrair texto do PDF {pdf_path}: {e}")
        return ''

# Função para verificar se o arquivo que foi feito upload é PDF (só um check a mais)
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']    


# Configuração básica do logger que estamos usando pra pegar e registrar e armazenar erros/registros importantes da aplicação
logging.basicConfig(filename='app.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Rota onde a aplicação se inicializa, no caso, sempre vai jogar pra tela de login...
@app.route('/')
def login():
    return render_template('login.html')

# Rota de login
@app.route('/login', methods=['GET', 'POST'])
def login_route():
    if request.method == 'POST': # Verificar se é requisição POST que seria pra envio de dados
        login_user_value = request.form['login']  # Recebe valor do login digitado
        password = request.form['senha']          # Reecebe o valor da senha digitada

        # Conecta no banco de dados MYSQL
        conn = connect_to_db()
        cursor = conn.cursor(dictionary=True)

        # Consulta pra verificar se o login está correto
        cursor.execute("SELECT * FROM USERS WHERE LOGIN_USER = %s", (login_user_value,))  
        user = cursor.fetchone()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['PASSWORD'].encode('utf-8')):
            user_obj = User(user['ID'], user['NAME_USER'])
            login_user(user_obj)  # autentica e realiza o login do usuário
            flash("Login bem-sucedido!", "success")
            return redirect(url_for('home')) # Redireciona pra tela home (página principal)
        else:
            flash("Usuário ou senha incorretos!", "danger") # caso der problema, dar um alerta

        # Fecha a conexão com o banco de dados MYSQL
        cursor.close()
        conn.close()

    # Exibie a página de login em caso de requisição tipo GET ou erro no login
    return render_template('login.html')

# Página inicial após login
@app.route('/home', methods=['GET'])
@login_required # Irá garantir pra que apenas os usuários logados possam acessar
def home():
    return render_template('home.html')

# Classe de usuário para Flask-Login
class User(UserMixin):
    def __init__(self, id, name_user):
        self.id = id
        self.name_user = name_user

# Função pra carregamento do usuário Flask-Login
@login_manager.user_loader
def load_user(user_id):
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)

    # Consulta os dados do usuário
    cursor.execute("SELECT * FROM USERS WHERE ID = %s", (user_id,))
    user_data = cursor.fetchone()

    # Fecha a conexão
    cursor.close()
    conn.close()

    # Se encontrado, retorna o ID e o nome do usuário
    if user_data:
        return User(user_data['ID'], user_data['NAME_USER'])
    return None

# Rota para a página de registro
@app.route('/cadastro', methods=['GET', 'POST'])
def register_route():
    if request.method == 'POST': # Verifica se é requisição POST (envio de dados)
        login_user = request.form['login']  # pega o valor do login digitado no formulário
        password = request.form['senha']    # pega o valor da senha digitada no formulário
        name_user = request.form['nome']    # pega o valor do nome digitado no formulário

        # Criptografar a senha digitada usando o brcrypt
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Se conecta no banco
        conn = connect_to_db()
        cursor = conn.cursor()

        # Insere os dados que foram digitados pelo usuário no formulário no banco de daos
        cursor.execute("INSERT INTO USERS (LOGIN_USER, PASSWORD, NAME_USER) VALUES (%s, %s, %s)",
                       (login_user, hashed_password, name_user))
        conn.commit() # Salva as alterações no banco

        # Fecha a conexão com o banco de dados
        cursor.close()
        conn.close()

        flash('Usuário registrado com sucesso! Você pode fazer login agora.')
        return redirect(url_for('login_route')) # retorna pra página de login

    # Caso a requisição for tipo GET, retorna pro cadastro
    return render_template('cadastro.html')

# Rota inicial do portal de inicialização de processos (cadastro, revisão e cancelamento de documentos)
@app.route('/meu-portal')
def meu_portal():
    # Se conectar ao banco de dados
    conn = connect_to_db()
    if conn is None:
        return "Erro ao conectar ao banco de dados."
    cursor = conn.cursor(dictionary=True)

    # Busca as categorias de documento no banco de dados
    cursor.execute("SELECT IDCATEGORY, IDENTIFIER FROM DCCATEGORY")
    categorias = cursor.fetchall()

    # Busca os usuários pra aprovação
    cursor.execute("SELECT ID, NAME_USER FROM USERS")
    usuarios = cursor.fetchall()

    # Busca documentos ativos (current = 1) no banco de dados
    cursor.execute("SELECT CDDOCUMENT, IDDOCUMENT FROM DCDOCUMENT WHERE CURRENT = 1")
    documentos = cursor.fetchall()

    # Fecha a conexão com o banco de dados
    cursor.close()
    conn.close()

    # Passa as categorias e os documentos pro template
    return render_template('meu_portal.html', categorias=categorias, usuarios=usuarios, documentos=documentos)

# Rota para inserir documento no banco e o PDF que foi anexado
@app.route('/inserir-documento', methods=['GET', 'POST'])
def inserir_documento():
    if request.method == 'POST': # Verifica se é requisição post
        print(request.form)  # Linha para depuração

        # Obtenha os dados do formulário com tratamento para chaves ausentes
        identificador = request.form.get('identificadorCriacao')        # Pega o valor digitado no formulário e salva na variavel identificador
        nome_documento = request.form.get('nome_documentoCriacao')      # Pega o valor digitado no formulário e salva na variavel nome_documento
        category = request.form.get('categoriaCriacao')                 # Pega o valor digitado no formulário e salva na variavel category
        usuario_aprovador = request.form.get('usuario_aprovador')       # Pega o ID do usuário selecionado para aprovação
        autor = request.form.get('autor')                               # Pega o valor digitado no formulário e salva na variavel autor
        solicitante = request.form.get('autor')                         # Pega o valor digitado no formulário e salva na variavel solicitante
        motivo = request.form.get('motivo')                             # Pega o valor digitado no formulário e salva na variavel motivo
        current_status = 2  # Por padrão é 2, depois se for aprovado vira 1

        # Verifica se todos os campos obrigatórios foram preenchidos
        if not identificador or not nome_documento or not category or not autor:
            flash("Todos os campos são obrigatórios.", "danger")
            return redirect(request.url)

        # Verifica se o arquivo PDF foi anexado e se também é um PDF
        if 'file' not in request.files:
            flash("Nenhum arquivo enviado.")
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash("Nenhum arquivo selecionado.")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            # Se foi feito corretamente a anexação e é PDF ele salva na pasta o arquivo
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Se conecta no banco e faz as inserções dos dados
            try:
                conn = connect_to_db()
                cursor = conn.cursor()

                # Insere o documento no banco de dados
                query_insert_documento = """
                INSERT INTO DCDOCUMENT (IDDOCUMENT, NMDOCUMENT, CATEGORY, REVISION, CURRENT, REDATOR, STATUS)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query_insert_documento, (identificador, nome_documento, category, 0, current_status, autor, 'EMISSÃO'))
                cddocument = cursor.lastrowid  # Pega o último CDDOCUMENT que foi gerado no banco

                # Associa o arquivo PDF no documento
                query_insert_file = """
                INSERT INTO DCFILE (FILENAME, FILEPATH, CDDOCUMENT)
                VALUES (%s, %s, %s)
                """
                cursor.execute(query_insert_file, (filename, filepath, cddocument))

                # Cria um novo Workflow que terá que ser aprovado
                cursor.execute(""" 
                    INSERT INTO WORKFLOW (form_id, status, MOTIVO ,tipo_workflow, solicitante) VALUES (%s, 'PENDENTE', %s, 'criação', %s)
                """, (identificador, motivo, solicitante))
                workflow_id = cursor.lastrowid

                # Insere a atividade pro usuário conforme formulário
                cursor.execute(""" 
                    INSERT INTO WORKFLOW_ATIVIDADES (workflow_id, usuario_id, status)
                    VALUES (%s, %s, 'PENDENTE')
                """, (workflow_id, usuario_aprovador))

                conn.commit() # Comita as inserções no banco e mostra uma mensagem de sucesso
                flash("Documento e arquivo PDF inseridos com sucesso!", "success")

            except Exception as e:
                print(f"Erro ao inserir documento e arquivo: {e}")
                flash("Erro ao inserir documento e arquivo no banco de dados.", "danger")
                conn.rollback()  # Se der erro, ele dá um rollback no banco
            finally:
                # Fecha a conexão com o banco
                cursor.close()
                conn.close()
        else:
            flash("Apenas arquivos PDF são permitidos.", "danger")

    return redirect(url_for('meu_portal'))  # Após finalizar tudo, direciona pra tela Meu Portal

# Rota para revisar documento
@app.route('/revisar-documento', methods=['GET', 'POST'])
def revisar_documento():
    if request.method == 'GET': # Verifica se é método GET
        categorias = obter_categorias() # Pega da função obter categoria e salva na variável categorias
        documentos = obter_documentos() # Pega da função obter categoria e salva na variável documentos
        return render_template('meu_portal.html', categorias=categorias, documentos=documentos)

    if request.method == 'POST': # Verifica se é método POST
        identificador = request.form['identificador']       # Pega o valor digitado no formulário e salva na variavel identificador
        nome_documento = request.form['nome_documento']     # Pega o valor digitado no formulário e salva na variavel nome_documento
        category = request.form['categoria']                # Pega o valor digitado no formulário e salva na variavel category
        usuario_aprovador = request.form.get('usuario_aprovador')       # Pega o ID do usuário selecionado para aprovação
        autor = request.form.get('autor')                   # Pega o valor digitado no formulário e salva na variavel autor
        motivo = request.form('motivo')                     # Pega o valor digitado no formulário e salva na variavel motivo
        solicitante = request.form.get('autor')             # Pega o valor digitado no formulário e salva na variavel solicitante

        # Verifica se tem arquivo e é PDF
        if 'pdf_file' not in request.files:
            flash("Nenhum arquivo enviado.")
            return redirect(request.url)

        file = request.files['pdf_file']
        if file.filename == '':
            flash("Nenhum arquivo selecionado.")
            return redirect(request.url)

        if not (file and allowed_file(file.filename)):
            flash("Apenas arquivos PDF são permitidos.", "danger")
            return redirect(request.url)

         # Salva o arquivo PDF na pasta local
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # Atualiza os registro no banco (se conectando)
            conn = connect_to_db()
            cursor = conn.cursor(dictionary=True)

            # Faz um select dos campos do DCDOCUMENT e trás só oque é ativo (CURRENT = 1 )
            query_select_documento = """
            SELECT * FROM DCDOCUMENT
            WHERE IDDOCUMENT = %s AND CURRENT = 1
            """
            cursor.execute(query_select_documento, (identificador,))
            documento = cursor.fetchone()

            if documento:
                nova_revisao = documento['REVISION'] + 1 # Faz isso pra colocar o novo numero da revisão do documento (anterior +1)
                
                # Query pra inserir os dados do documento no banco, conforme formulário e outros
                query_insert_documento = """
                INSERT INTO DCDOCUMENT (IDDOCUMENT, NMDOCUMENT, CATEGORY, REVISION, CURRENT, REDATOR, STATUS)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query_insert_documento, (identificador, nome_documento, category, nova_revisao, 1, autor, 'REVISÃO')) # Executa o SQL
                cddocument = cursor.lastrowid # pega o ultimo CDDOCUMENT gerado

                # Insere no DCFILE as paradas do documento e o numero gerado do CDDOCUMENT
                query_insert_file = """
                INSERT INTO DCFILE (FILENAME, FILEPATH, CDDOCUMENT)
                VALUES (%s, %s, %s)
                """
                cursor.execute(query_insert_file, (filename, filepath, cddocument)) # Executa o SQL

                # Faz um update do documento e insere como status 2 (inativo) pra somente quando aprovado ele ficar como ativo (CURRENT = 1)
                query_update_documento = """
                UPDATE DCDOCUMENT
                SET CURRENT = 2
                WHERE CDDOCUMENT = %s
                """
                cursor.execute(query_update_documento, (documento['CDDOCUMENT'],)) # Executa o SQL

                cursor.execute(""" 
                    INSERT INTO WORKFLOW (form_id, status, MOTIVO ,tipo_workflow, solicitante) VALUES (%s, 'PENDENTE', %s, 'revisão', %s)
                """, (identificador, motivo, solicitante))
                workflow_id = cursor.lastrowid
                
                # Insere a atividade pro usuário conforme formulário
                cursor.execute(""" 
                    INSERT INTO WORKFLOW_ATIVIDADES (workflow_id, usuario_id, status)
                    VALUES (%s, %s, 'PENDENTE')
                """, (workflow_id, usuario_aprovador))

                # Fecha a conexão com o banco de dados
                conn.commit()
                cursor.close()
                conn.close()
                flash("Revisão do documento e upload do PDF registrados com sucesso.", "success")
            else:
                print(f"Documento com ID {identificador} não encontrado.")
                flash("Documento não encontrado.", "danger")
                return redirect(request.url)
        except Exception as e:
            print(f"Erro ao iniciar revisão: {e}")
            flash("Erro ao iniciar revisão.", "danger")
            return redirect(url_for('meu_portal'))

        return redirect(url_for('meu_portal'))


# Rota para iniciar um cancelamento
@app.route('/iniciar-cancelamento', methods=['POST'])
def iniciar_cancelamento():
    identificador = request.form['identificador']               # Pega o valor digitado no formulário e salva na variavel identificador
    usuario_aprovador = request.form.get('usuario_aprovador')   # Pega o ID do usuário selecionado para aprovação
    motivo = request.form['motivo']                             # Pega o valor digitado no formulário e salva na variavel motivo
    solicitante = request.form.get('autor')                     # Pega o valor digitado no formulário e salva na variavel solicitante

    try:
        # Se conecta no banco
        conn = connect_to_db()
        cursor = conn.cursor()

        # Inseri um novo workflow para o cancelamento
        cursor.execute(""" 
            INSERT INTO WORKFLOW (form_id, status, motivo, tipo_workflow, solicitante) VALUES (%s, 'PENDENTE', %s, 'cancelamento', %s)
        """, (identificador, motivo, solicitante))
        workflow_id = cursor.lastrowid
        
        # Insere a atividade pro usuário conforme formulário
        cursor.execute(""" 
            INSERT INTO WORKFLOW_ATIVIDADES (workflow_id, usuario_id, status)
            VALUES (%s, %s, 'PENDENTE')
        """, (workflow_id, usuario_aprovador))

        # Comita as inserções e fecha a conexão com o banco de dados
        conn.commit()
        cursor.close()
        conn.close()
        print("Cancelamento do documento pendente de aprovação.")
    except Exception as e:
        # Caso der um erro, printar o erro
        print(f"Erro ao iniciar cancelamento: {e}")
        return "Erro ao iniciar cancelamento."

    return redirect(url_for('meu_portal'))

# Rota para exibir tarefas pendentes do usuário logado
@app.route('/minhas-tarefas')
def minhas_tarefas():
    usuario_id = getattr(current_user, 'id', None)  # Obtém o ID do usuário que tá logado
    
    # Conecta com o banco de dados
    conn = connect_to_db()
    if conn is None:
        # Caso der erro, logar isso nos logs da aplicação
        app.logger.info("Erro ao conectar ao banco de dados.")
        return "Erro ao conectar ao banco de dados."
    cursor = conn.cursor(dictionary=True)

    # Faz uma consulta com o filtro do usuário e atividades pendentes
    if usuario_id:
        cursor.execute("""
            SELECT 
                WA.id, 
                W.form_id, 
                W.status AS workflow_status, 
                W.tipo_workflow,
                W.MOTIVO AS motivo,
                W.solicitante AS solicitante
            FROM 
                WORKFLOW_ATIVIDADES WA
            INNER JOIN 
                WORKFLOW W ON WA.workflow_id = W.id
            WHERE 
                WA.status = 'PENDENTE' AND WA.usuario_id = %s AND W.tipo_workflow IS NOT NULL
        """, (usuario_id,))
    else:
        cursor.execute("""
            SELECT 
                WA.id, 
                W.form_id, 
                W.status AS workflow_status, 
                W.tipo_workflow,
                W.MOTIVO AS motivo,
                W.solicitante AS solicitante
            FROM 
                WORKFLOW_ATIVIDADES WA
            INNER JOIN 
                WORKFLOW W ON WA.workflow_id = W.id
            WHERE 
                WA.status = 'PENDENTE' AND AND W.tipo_workflow IS NOT NULL
        """)
    
    tarefas = cursor.fetchall()

    # Loga os erros ou retorna as atividades se der sucesso
    if not tarefas:
        app.logger.info("Nenhuma tarefa pendente encontrada.")
    else:
        app.logger.info(f"Tarefas retornadas: {tarefas}")

    # Fecha a conexão com o banco
    cursor.close()
    conn.close()

    # Traz as atividades (tarefas) pro template das Minhas Tarefas, de acordo com o usuário logado
    return render_template('minhas_tarefas.html', tarefas=tarefas)

# Rota pra visualizar as tarefas de acordo com o ID dela
@app.route('/visualizar_pdf/<int:tarefa_id>', methods=['GET'])
def visualizar_pdf(tarefa_id):
    # Log para verificar o ID da tarefa
    app.logger.info(f"Visualizando PDF para a tarefa com ID: {tarefa_id}")

    # Conecta ao banco de dados
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    
    # Consulta para pegar o CDDOCUMENT e FILENAME baseado no ID da tarefa
    cursor.execute("""
        SELECT D.CDDOCUMENT, F.FILENAME
        FROM DCDOCUMENT D
        INNER JOIN DCFILE F ON D.CDDOCUMENT = F.CDDOCUMENT
        INNER JOIN WORKFLOW W ON D.IDDOCUMENT = W.form_id
        INNER JOIN WORKFLOW_ATIVIDADES WA ON WA.workflow_id = W.id
        WHERE WA.id = %s
    """, (tarefa_id,))

    pdf_data = cursor.fetchone()

    # Log para verificar o resultado da consulta SQL
    if pdf_data:
        app.logger.info(f"PDF encontrado: CDDOCUMENT={pdf_data['CDDOCUMENT']}, FILENAME={pdf_data['FILENAME']}")
    else:
        app.logger.warning(f"Nenhum PDF encontrado para o ID da tarefa: {tarefa_id}")

    # Fecha a conexão com o banco de dados
    cursor.close()
    conn.close()

    # Se não tiver PDF (arquivo) dá erro
    if not pdf_data:
        return jsonify({"error": "PDF não encontrado"}), 404

    # Pega o caminho completo do arquivo PDF na pasta local
    pdf_filename = pdf_data['FILENAME']
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)

    # Verifica se o arquivo existe antes de salvar
    if not os.path.exists(pdf_path):
        return jsonify({"error": f"Arquivo {pdf_filename} não encontrado no diretório."}), 404

    # Retorna o PDF pro usuário
    return send_from_directory(app.config['UPLOAD_FOLDER'], pdf_filename)


# Rota para aprovar ou reprovar as tarefas de criação do documento (método POST)
@app.route('/aprovar_reprovar/<int:atividade_id>', methods=['POST'])
def aprovar_reprovar(atividade_id):
    status = request.form['status'] # Salva na variavel status o valor do STATUS no formulário

    # Conecta com o banco de dados
    conn = connect_to_db() 
    cursor = conn.cursor()
    
    # Atualiza o status da atividade através do UPDATE (SQL)
    cursor.execute(""" 
        UPDATE WORKFLOW_ATIVIDADES
        SET status = %s, atualizado_em = %s
        WHERE id = %s
    """, (status, datetime.now(), atividade_id))
    
    # Pega o workflow_id que está relacionado na atividade do usuário
    cursor.execute(""" 
        SELECT workflow_id FROM WORKFLOW_ATIVIDADES WHERE id = %s
    """, (atividade_id,))
    workflow_id = cursor.fetchone()[0]

    # Faz um COUNT pra saber quantas atividades estão pendentes
    cursor.execute(""" 
        SELECT COUNT(*) as pendentes FROM WORKFLOW_ATIVIDADES WHERE workflow_id = %s AND status = 'PENDENTE'
    """, (workflow_id,))
    pendentes = cursor.fetchone()[0]

    if pendentes == 0:
        # Verifica quantas atividades estão aprovadas
        cursor.execute(""" 
            SELECT COUNT(*) as aprovadas FROM WORKFLOW_ATIVIDADES WHERE workflow_id = %s AND status = 'APROVADO'
        """, (workflow_id,))
        aprovadas = cursor.fetchone()[0]
        
        # Atualiza o status do workflow de acordo com o novo_status
        novo_status = 'APROVADO' if aprovadas > 0 else 'REPROVADO'
        cursor.execute(""" 
            UPDATE WORKFLOW SET status = %s WHERE id = %s
        """, (novo_status, workflow_id))

        # Consulta o tipo de workflow (criação, revisão ou cancelamento) através de um SQL (banco de dados)
        cursor.execute(""" 
            SELECT form_id, tipo_workflow FROM WORKFLOW WHERE id = %s
        """, (workflow_id,))
        workflow = cursor.fetchone()
        form_id = workflow[0]
        tipo_workflow = workflow[1]

        if novo_status == 'APROVADO':
            if tipo_workflow == 'criação':
                # Atualiza o CURRENT, data de publicação e STATUS do documento se for criação
                cursor.execute("""
                    UPDATE DCDOCUMENT SET CURRENT = 1, STATUS = 'HOMOLOGADO', DOCUMENT_DATE_PUBLISH = NOW() WHERE IDDOCUMENT = %s
                """, (form_id,))
            elif tipo_workflow == 'revisão':
                # Atualiza o CURRENT, data de publicação e STATUS do documento se for revisão
                cursor.execute("""
                    UPDATE DCDOCUMENT SET CURRENT = 1, STATUS = 'HOMOLOGADO', DOCUMENT_DATE_PUBLISH = NOW() WHERE IDDOCUMENT = %s
                """, (form_id,))
                # Atualiza o documento antigo para CURRENT = 2 (pois está agora desativado para uma nova versão)
                cursor.execute("""
                    UPDATE DCDOCUMENT SET CURRENT = 2 WHERE IDDOCUMENT = %s AND CURRENT = 1
                """, (form_id,))
            elif tipo_workflow == 'cancelamento':
                # Atualiza o CURRENT e STATUS do documento para cancelado, visto que foi aprovado o cancelamento
                cursor.execute("""
                    UPDATE DCDOCUMENT SET CURRENT = 2, STATUS = 'CANCELADO' WHERE IDDOCUMENT = %s
                """, (form_id,))

    # Comita as alteração e fecha a conexão com o banco de dados
    conn.commit()
    cursor.close()
    conn.close()
    
    # Retorna para o Meu Portal
    return redirect(url_for('meu_portal'))

# Rota para a pesquisa de documentos
@app.route('/pesquisa_documentos', methods=['GET'])
def pesquisa_documentos(): 
    termo_busca = request.args.get('document') # De acordo com o valor digitado pelo usuário salva no termo_busca

    # Adiciona um log para verificar o termo de busca
    if not termo_busca:
        return "Erro: Termo de busca não fornecido.", 400

    # Conecta com o banco de dados
    conn = connect_to_db()
    if conn is None:
        return "Erro ao conectar ao banco de dados.", 500

    cursor = conn.cursor(dictionary=True)
    
    # Adiciona um log para ver a consulta SQL que está sendo executada pelo banco
    print(f"Consultando documentos com o termo: {termo_busca}")
    
    # Faz um select (consulta) de acordo com o termo busca em uma lista de documentos
    cursor.execute("""
        SELECT D.IDDOCUMENT AS iddocument, D.NMDOCUMENT AS nmdocument, C.IDENTIFIER AS category, 
            D.DOCUMENT_DATE_PUBLISH AS document_date_publish, D.REDATOR AS redator, D.CDDOCUMENT AS cddocument, F.FILEPATH AS filepath
        FROM DCDOCUMENT D
        INNER JOIN DCCATEGORY C ON D.CATEGORY = C.IDCATEGORY
        LEFT JOIN DCFILE F ON D.IDDOCUMENT = F.CDDOCUMENT
        WHERE D.CURRENT = 1 
        AND (D.NMDOCUMENT LIKE %s OR D.IDDOCUMENT LIKE %s OR C.IDENTIFIER LIKE %s OR D.REDATOR LIKE %s)
    """, ('%' + termo_busca + '%', '%' + termo_busca + '%', '%' + termo_busca + '%', '%' + termo_busca + '%'))

    documentos = cursor.fetchall()
    
    # Verifica se o banco de dados retornou algum resultado
    print(f"Documentos encontrados: {documentos}")

    # Fecha a conexão com o banco de dados
    cursor.close()
    conn.close()

    # Renderiza no template os resultados da pesquisa
    mensagem = ""
    if not documentos:
        mensagem = "Nenhum documento encontrado."

    return render_template('pesquisa_documentos.html', documentos=documentos, mensagem=mensagem)

# Rota para visualizar o PDF na pesquisa
@app.route('/view_pdf/<int:doc_id>', methods=['GET']) # Método da requisição tipo GET
def view_pdf(doc_id):
    # Conectar ao banco de dados
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    
    # Consulta para pegar o nome do arquivo atrvés do CDDOCUMENT
    cursor.execute("SELECT FILENAME FROM DCFILE WHERE CDDOCUMENT = %s", (doc_id,))
    file_data = cursor.fetchone()

    # Fecha a conexão com o banco de dados
    cursor.close()
    conn.close()

    # Verifica se encontrou um arquivo para o CDDOCUMENT consultado
    if not file_data:
        app.logger.warning(f"PDF não encontrado no banco de dados para o CDDOCUMENT: {doc_id}")
        return jsonify({"error": "PDF não encontrado"}), 404

    # Define o caminho completo do arquivo PDF
    pdf_filename = file_data['FILENAME']
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)

    # Verifica se o arquivo existe na pasta local dos PDF armazenado
    if not os.path.exists(pdf_path):
        app.logger.warning(f"Arquivo {pdf_filename} não encontrado no diretório: {app.config['UPLOAD_FOLDER']}")
        return jsonify({"error": f"Arquivo {pdf_filename} não encontrado no diretório."}), 404

    # Retorna o arquivo PDF ao usuário usando o caminho correto
    return send_from_directory(app.config['UPLOAD_FOLDER'], pdf_filename)


# Rota para resumir o PDF usando a API do ChatGPT
@app.route('/summarize_pdf/<int:doc_id>', methods=['GET'])
def summarize_pdf(doc_id):
    try:
        # Conecta com o banco de dados
        conn = connect_to_db()
        cursor = conn.cursor(dictionary=True)

        # Faz uma consulta para pegar o nome do arquivo na tabela DCFILE
        cursor.execute("SELECT FILENAME FROM DCFILE WHERE CDDOCUMENT = %s", (doc_id,))
        file_data = cursor.fetchone()

        # Fecha a conexão com o banco de dados
        cursor.close()
        conn.close()

        # Verifica se o arquivo foi encontrado no banco de dados
        if not file_data:
            app.logger.error(f"Nenhum PDF encontrado para o documento com CDDOCUMENT {doc_id}.")
            return jsonify({"error": "PDF não encontrado"}), 404

        # Define o caminho do PDF
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], file_data['FILENAME'])
        if not os.path.exists(pdf_path):
            app.logger.error(f"O arquivo PDF {pdf_path} não existe.")
            return jsonify({"error": "Arquivo PDF não encontrado no servidor"}), 404

        # Extrai texto do PDF
        pdf_text = extract_text_from_pdf(pdf_path)
        if not pdf_text.strip():
            app.logger.error(f"Texto do PDF {pdf_path} está vazio ou não pôde ser extraído.")
            return jsonify({"error": "Não foi possível extrair o texto do PDF"}), 500

        # Faz a requisição para a API do ChatGPT
        response = requests.post(
            "https://api.openai.com/v1/chat/completions", 
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "Bora dale."},
                    {"role": "user", "content": f"Resuma pra mim o seguinte texto:\n{pdf_text}"}
                ],
                "max_tokens": 150  # Limite de tokens no resumo
            }
        )

        # Processa a resposta da API
        if response.status_code != 200:
            app.logger.error(f"Erro na chamada da API do ChatGPT: {response.text}")
            return jsonify({"error": "Erro ao comunicar com a API do ChatGPT"}), 500

        summary = response.json().get('choices', [{}])[0].get('message', {}).get('content', '').strip()
        if not summary:
            app.logger.warning(f"Resumo vazio retornado pela API do ChatGPT para o documento {doc_id}.")
            return jsonify({"error": "Não foi possível resumir o texto do PDF"}), 500

        app.logger.info(f"Resumo gerado com sucesso para o documento {doc_id}.")
        return jsonify({"summary": summary})

    except Exception as e:
        app.logger.error(f"Erro na rota /summarize_pdf para o documento {doc_id}: {e}")
        return jsonify({"error": "Erro interno no servidor"}), 500


# Executar o app Flask
if __name__ == '__main__':
    app.run(debug=True)
