from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import LoginManager, login_user, current_user, login_required, UserMixin
from datetime import datetime
from werkzeug.utils import secure_filename
import mysql.connector
import bcrypt
import os
import secrets
import PyPDF2
import requests

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
    
# Diretório para armazenar os arquivos PDF
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(PROJECT_DIR, "upload_files")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
API_KEY = "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"

# Função para extrair texto do PDF e posteriormente jogar pra API do chatGPT (resumir PDF)
def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ''
        for page in reader.pages:
            text += page.extract_text() or ''
        return text

# Função para verificar se o arquivo que foi feito upload é PDF
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']    

# Rota inicial do portal
@app.route('/meu-portal')
def meu_portal():
    # Conectar ao banco de dados
    conn = connect_to_db()
    if conn is None:
        return "Erro ao conectar ao banco de dados."
    
    cursor = conn.cursor(dictionary=True)

    # Buscar categorias existentes no banco de dados
    cursor.execute("SELECT IDCATEGORY, IDENTIFIER FROM DCCATEGORY")
    categorias = cursor.fetchall()

    # Buscar documentos existentes no banco de dados
    cursor.execute("SELECT CDDOCUMENT, IDDOCUMENT FROM DCDOCUMENT WHERE CURRENT = 1")
    documentos = cursor.fetchall()

    # Fechar a conexão
    cursor.close()
    conn.close()

    # Passar as categorias e documentos para o template
    return render_template('meu_portal.html', categorias=categorias, documentos=documentos)

# Rota para tarefas pendentes
@app.route('/minhas-tarefas-pendentes')
def minhas_tarefas_pendentes():
    # Conectar ao banco de dados
    conn = connect_to_db()
    if conn is None:
        return "Erro ao conectar ao banco de dados."
    
    cursor = conn.cursor(dictionary=True)

    # Buscar tarefas existentes no banco de dados
    cursor.execute("""
        SELECT 
            WA.id, 
            W.form_id, 
            W.status AS workflow_status, 
            W.tipo_workflow
        FROM 
            WORKFLOW_ATIVIDADES WA
        INNER JOIN 
            WORKFLOW W ON WA.workflow_id = W.id
        WHERE 
            WA.status = 'PENDENTE'
    """)
    tarefas = cursor.fetchall()

    print(f"Tarefas retornadas: {tarefas}")

    # Fechar a conexão
    cursor.close()
    conn.close()

    # Passar as tarefas para o template
    return render_template('minhas_tarefas.html', tarefas=tarefas)


# Rota para inserir documento no banco e PDF
@app.route('/inserir-documento', methods=['GET', 'POST'])
def inserir_documento():
    if request.method == 'POST':
        print(request.form)  # Linha para depuração

        # Obtenha os dados do formulário com tratamento para chaves ausentes
        identificador = request.form.get('identificadorCriacao')
        nome_documento = request.form.get('nome_documentoCriacao')
        category = request.form.get('categoriaCriacao')
        autor = request.form.get('autor')
        solicitante = request.form.get('autor')
        motivo = request.form.get('motivo')
        current_status = 2  # Por padrão é 2, depois se aprovado vira 1

        # Verifica se todos os campos obrigatórios estão preenchidos
        if not identificador or not nome_documento or not category or not autor:
            flash("Todos os campos são obrigatórios.", "danger")
            return redirect(request.url)

        # Verifica se tem arquivo e está em PDF
        if 'file' not in request.files:
            flash("Nenhum arquivo enviado.")
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash("Nenhum arquivo selecionado.")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Inserção no banco MySQL
            try:
                conn = connect_to_db()
                cursor = conn.cursor()

                query_insert_documento = """
                INSERT INTO DCDOCUMENT (IDDOCUMENT, NMDOCUMENT, CATEGORY, REVISION, CURRENT, REDATOR, STATUS)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query_insert_documento, (identificador, nome_documento, category, 0, current_status, autor, 'EMISSÃO'))
                cddocument = cursor.lastrowid  # Pega o último ID gerado automaticamente

                # Associa o arquivo PDF no documento da tabela DCFILE
                query_insert_file = """
                INSERT INTO DCFILE (FILENAME, FILEPATH, CDDOCUMENT)
                VALUES (%s, %s, %s)
                """
                cursor.execute(query_insert_file, (filename, filepath, cddocument))

                # Criar um novo Workflow no banco MySQL
                cursor.execute(""" 
                    INSERT INTO WORKFLOW (form_id, status, MOTIVO ,tipo_workflow, solicitante) VALUES (%s, 'PENDENTE', %s, 'criação', %s)
                """, (identificador, motivo, solicitante))
                workflow_id = cursor.lastrowid

                # Definir usuário aprovador 
                usuario_aprovador = 1  # ID do usuário aprovador
                cursor.execute(""" 
                    INSERT INTO WORKFLOW_ATIVIDADES (workflow_id, usuario_id, status)
                    VALUES (%s, %s, 'PENDENTE')
                """, (workflow_id, usuario_aprovador))

                conn.commit()
                flash("Documento e arquivo PDF inseridos com sucesso!", "success")
            except Exception as e:
                print(f"Erro ao inserir documento e arquivo: {e}")
                flash("Erro ao inserir documento e arquivo no banco de dados.", "danger")
                conn.rollback()  # Rollback em caso de erro
            finally:
                cursor.close()
                conn.close()
        else:
            flash("Apenas arquivos PDF são permitidos.", "danger")

    return redirect(url_for('meu_portal'))  # Redireciona após o processamento


# Rota para revisar documento
@app.route('/revisar-documento', methods=['GET', 'POST'])
def revisar_documento():
    if request.method == 'GET':
        categorias = obter_categorias()
        documentos = obter_documentos()
        return render_template('meu_portal.html', categorias=categorias, documentos=documentos)

    if request.method == 'POST':
        identificador = request.form['identificador']
        nome_documento = request.form['nome_documento']
        category = request.form['categoria']
        autor = request.form.get('autor')
        motivo = request.form('motivo')
        solicitante = request.form.get('autor')

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

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            conn = connect_to_db()
            cursor = conn.cursor(dictionary=True)

            query_select_documento = """
            SELECT * FROM DCDOCUMENT
            WHERE IDDOCUMENT = %s AND CURRENT = 1
            """
            cursor.execute(query_select_documento, (identificador,))
            documento = cursor.fetchone()

            if documento:
                nova_revisao = documento['REVISION'] + 1
                query_insert_documento = """
                INSERT INTO DCDOCUMENT (IDDOCUMENT, NMDOCUMENT, CATEGORY, REVISION, CURRENT, REDATOR, STATUS)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query_insert_documento, (identificador, nome_documento, category, nova_revisao, 1, autor, 'REVISÃO'))
                cddocument = cursor.lastrowid

                query_insert_file = """
                INSERT INTO DCFILE (FILENAME, FILEPATH, CDDOCUMENT)
                VALUES (%s, %s, %s)
                """
                cursor.execute(query_insert_file, (filename, filepath, cddocument))

                query_update_documento = """
                UPDATE DCDOCUMENT
                SET CURRENT = 2
                WHERE CDDOCUMENT = %s
                """
                cursor.execute(query_update_documento, (documento['CDDOCUMENT'],))

                cursor.execute(""" 
                    INSERT INTO WORKFLOW (form_id, status, MOTIVO ,tipo_workflow, solicitante) VALUES (%s, 'PENDENTE', %s, 'revisão', %s)
                """, (identificador, motivo, solicitante))
                workflow_id = cursor.lastrowid

                usuario_aprovador = 1
                cursor.execute(""" 
                    INSERT INTO WORKFLOW_ATIVIDADES (workflow_id, usuario_id, status)
                    VALUES (%s, %s, 'PENDENTE')
                """, (workflow_id, usuario_aprovador))

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


# Função para obter as categorias
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

# Função para obter os documentos
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
        print(f"Erro ao obter documentos: {e}")
        return []

# Rota para iniciar um cancelamento
@app.route('/iniciar-cancelamento', methods=['POST'])
def iniciar_cancelamento():
    identificador = request.form['identificador']
    motivo = request.form['motivo']
    solicitante = request.form.get('autor')

    try:
        conn = connect_to_db()
        cursor = conn.cursor()

        # Inserir uma nova entrada no workflow para o cancelamento com o motivo
        cursor.execute(""" 
            INSERT INTO WORKFLOW (form_id, status, motivo, tipo_workflow, solicitante) VALUES (%s, 'PENDENTE', %s, 'cancelamento', %s)
        """, (identificador, motivo, solicitante))
        workflow_id = cursor.lastrowid
        
        # Definir usuário aprovador
        usuario_aprovador = 1
        cursor.execute(""" 
            INSERT INTO WORKFLOW_ATIVIDADES (workflow_id, usuario_id, status)
            VALUES (%s, %s, 'PENDENTE')
        """, (workflow_id, usuario_aprovador))
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Cancelamento do documento pendente de aprovação.")
    except Exception as e:
        print(f"Erro ao iniciar cancelamento: {e}")
        return "Erro ao iniciar cancelamento."

    return redirect(url_for('meu_portal'))


# Rota inicial para login
@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login_route():
    if request.method == 'POST':
        login_user_value = request.form['login']  
        password = request.form['senha']

        conn = connect_to_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM USERS WHERE LOGIN_USER = %s", (login_user_value,))  
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

    if user_data:
        return User(user_data['ID'], user_data['NAME_USER'])
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
@login_required
def home():
    return render_template('home.html')

# Rota para exibir tarefas
@app.route('/minhas-tarefas')
def minhas_tarefas():
    usuario_id = current_user.id  # ID do usuário logado
    
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

# Rota para aprovar ou reprovar tarefas de criação
@app.route('/aprovar_reprovar/<int:atividade_id>', methods=['POST'])
def aprovar_reprovar(atividade_id):
    status = request.form['status']
    conn = connect_to_db()
    cursor = conn.cursor()
    
    # Atualiza o status da atividade
    cursor.execute(""" 
        UPDATE WORKFLOW_ATIVIDADES
        SET status = %s, atualizado_em = %s
        WHERE id = %s
    """, (status, datetime.now(), atividade_id))
    
    # Obtém o workflow_id relacionado à atividade
    cursor.execute(""" 
        SELECT workflow_id FROM WORKFLOW_ATIVIDADES WHERE id = %s
    """, (atividade_id,))
    workflow_id = cursor.fetchone()[0]

    # Verifica quantas atividades estão pendentes
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
        
        # Atualiza o status do workflow
        novo_status = 'APROVADO' if aprovadas > 0 else 'REPROVADO'
        cursor.execute(""" 
            UPDATE WORKFLOW SET status = %s WHERE id = %s
        """, (novo_status, workflow_id))

        # Obtém o tipo de workflow (criação, revisão ou cancelamento)
        cursor.execute(""" 
            SELECT form_id, tipo_workflow FROM WORKFLOW WHERE id = %s
        """, (workflow_id,))
        workflow = cursor.fetchone()
        form_id = workflow[0]
        tipo_workflow = workflow[1]

        if novo_status == 'APROVADO':
            if tipo_workflow == 'criação':
                # Atualiza o CURRENT e STATUS do documento para criação
                cursor.execute("""
                    UPDATE DCDOCUMENT SET CURRENT = 1, STATUS = 'HOMOLOGADO' WHERE IDDOCUMENT = %s
                """, (form_id,))
            elif tipo_workflow == 'revisão':
                # Atualiza o CURRENT e STATUS do documento para revisão
                cursor.execute("""
                    UPDATE DCDOCUMENT SET CURRENT = 1, STATUS = 'HOMOLOGADO' WHERE IDDOCUMENT = %s
                """, (form_id,))
                # Atualiza o documento antigo para CURRENT = 2
                cursor.execute("""
                    UPDATE DCDOCUMENT SET CURRENT = 2 WHERE IDDOCUMENT = %s AND CURRENT = 1
                """, (form_id,))
            elif tipo_workflow == 'cancelamento':
                # Atualiza o CURRENT e STATUS do documento para cancelamento
                cursor.execute("""
                    UPDATE DCDOCUMENT SET CURRENT = 2, STATUS = 'CANCELADO' WHERE IDDOCUMENT = %s
                """, (form_id,))

    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('meu_portal'))


# Rota para a pesquisa de documentos
@app.route('/pesquisa_documentos', methods=['GET'])
def pesquisa_documentos():
    # Receber o termo de busca do formulário
    termo_busca = request.args.get('document')

    # Buscar documentos no MySQL
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT D.IDDOCUMENT AS iddocument, D.NMDOCUMENT AS nmdocument, C.IDENTIFIER AS category, 
            D.DOCUMENT_DATE_PUBLISH AS document_date_publish, D.REDATOR AS redator, F.CDDOCUMENT AS cddocument, F.FILEPATH AS filepath
        FROM DCDOCUMENT D
        INNER JOIN DCCATEGORY C ON D.CATEGORY = C.IDCATEGORY
        INNER JOIN DCFILE F ON D.IDDOCUMENT = F.CDDOCUMENT
        WHERE D.CURRENT = 1 AND (D.NMDOCUMENT LIKE %s OR D.IDDOCUMENT LIKE %s OR C.IDENTIFIER LIKE %s OR D.REDATOR LIKE %s)
    """, ('%' + termo_busca + '%', '%' + termo_busca + '%', '%' + termo_busca + '%', '%' + termo_busca + '%'))

    documentos = cursor.fetchall()
    cursor.close()
    conn.close()

    # Renderizar o template com os resultados
    mensagem = ""
    if not documentos:
        mensagem = "Nenhum documento encontrado."

    return render_template('pesquisa_documentos.html', documentos=documentos, mensagem=mensagem)

# Rota para visualizar o PDF
@app.route('/view_pdf/<int:doc_id>', methods=['GET'])
def view_pdf(doc_id):
    # Conectar ao banco de dados
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    
    # Consulta para obter o nome do arquivo pelo CDDOCUMENT
    cursor.execute("SELECT FILENAME FROM DCFILE WHERE CDDOCUMENT = %s", (doc_id,))
    file_data = cursor.fetchone()
    cursor.close()
    conn.close()

    if not file_data:
        return jsonify({"error": "PDF não encontrado"}), 404

    # Define o nome do arquivo PDF
    pdf_filename = file_data['FILENAME']
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)

    # Verifica se o arquivo existe antes de tentar enviá-lo
    if not os.path.exists(pdf_path):
        return jsonify({"error": f"Arquivo {pdf_filename} não encontrado no diretório."}), 404

    # Retorna o arquivo PDF ao usuário usando o caminho correto
    return send_from_directory(app.config['UPLOAD_FOLDER'], pdf_filename)


# Rota para resumir o PDF usando a API do ChatGPT
@app.route('/summarize_pdf/<int:doc_id>', methods=['GET'])
def summarize_pdf(doc_id):
    # Consulta ao banco de dados
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT FILENAME FROM DCFILE WHERE CDDOCUMENT = %s", (doc_id,))
    file_data = cursor.fetchone()
    cursor.close()
    conn.close()

    if not file_data:
        return jsonify({"error": "PDF não encontrado"}), 404

    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], file_data['FILENAME'])
    pdf_text = extract_text_from_pdf(pdf_path)

    # Chamar API do ChatGPT
    response = requests.post(
        "https://api.openai.com/v1/engines/davinci-codex/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "prompt": f"Resuma o seguinte texto:\n{pdf_text}",
            "max_tokens": 150
        }
    )
    summary = response.json().get('choices', [{}])[0].get('text', 'Erro ao resumir o PDF')

    return jsonify({"summary": summary})


# Executar o app Flask
if __name__ == '__main__':
    app.run(debug=True)
