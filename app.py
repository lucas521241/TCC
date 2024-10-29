from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, current_user, login_required, UserMixin
from datetime import datetime
import mysql.connector
import bcrypt
import os
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

    # Fechar a conexão
    cursor.close()
    conn.close()

    # Passar as tarefas para o template
    return render_template('minhas_tarefas.html', tarefas=tarefas)


# Rota para inserir documento no MySQL
@app.route('/inserir-documento', methods=['POST'])
def inserir_documento():
    identificador = request.form['identificador']  # IDDOCUMENT como string
    nome_documento = request.form['nome_documento']
    category = request.form['categoria'] 
    autor = current_user.name_user  # Redator é o nome do usuário logado
    
    # Defina o valor padrão para CURRENT
    current_status = 2 

    # Inserção no MySQL
    try:
        conn = connect_to_db()
        cursor = conn.cursor()

        query_insert_documento = """
        INSERT INTO DCDOCUMENT (IDDOCUMENT, NMDOCUMENT, CATEGORY, REVISION, CURRENT, REDATOR, STATUS)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query_insert_documento, (identificador, nome_documento, category, 0, current_status, autor, 'EMISSÃO'))
        
        # Criar um novo Workflow no MySQL
        cursor.execute(""" 
            INSERT INTO WORKFLOW (form_id, status) VALUES (%s, 'PENDENTE')
        """, (identificador,))
        workflow_id = cursor.lastrowid
        
        # Definir usuário aprovador 
        usuario_aprovador = 1  # ID do usuário aprovador
        cursor.execute(""" 
            INSERT INTO WORKFLOW_ATIVIDADES (workflow_id, usuario_id, status)
            VALUES (%s, %s, 'PENDENTE')
        """, (workflow_id, usuario_aprovador))
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Documento e Workflow criados no banco de dados com sucesso.")
    except Exception as e:
        print(f"Erro ao inserir documento e criar workflow no banco de dados: {e}")
        return "Erro ao inserir documento e criar workflow no banco de dados."

    return redirect(url_for('meu_portal'))

# Rota para iniciar uma revisão
@app.route('/revisar-documento', methods=['POST'])
def revisar_documento():
    identificador = request.form['identificador']
    nome_documento = request.form['nome_documento']
    category = request.form['categoria']
    autor = current_user.name_user

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
            INSERT INTO DCDOCUMENT (IDDOCUMENT, NMDOCUMENT, CATEGORY, REVISION, CURRENT, REDATOR, STATUS, DCREVISION)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query_insert_documento, (identificador, nome_documento, category, nova_revisao, 1, autor, 'REVISÃO', nova_revisao))
            
            query_update_documento = """
            UPDATE DCDOCUMENT
            SET CURRENT = 2
            WHERE CDDOCUMENT = %s
            """
            cursor.execute(query_update_documento, (documento['CDDOCUMENT'],))
            
            # Inserir uma nova entrada no workflow para a revisão
            cursor.execute(""" 
                INSERT INTO WORKFLOW (form_id, status, tipo_workflow) VALUES (%s, 'PENDENTE', 'revisão')
            """, (identificador,))
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
            print("Revisão iniciada com sucesso.")
        else:
            print("Documento não encontrado.")
            return "Documento não encontrado."
    except Exception as e:
        print(f"Erro ao iniciar revisão: {e}")
        return "Erro ao iniciar revisão."

    return redirect(url_for('meu_portal'))


# Rota para iniciar um cancelamento
@app.route('/iniciar-cancelamento', methods=['POST'])
def iniciar_cancelamento():
    identificador = request.form['identificador']
    motivo = request.form['motivo']

    try:
        conn = connect_to_db()
        cursor = conn.cursor()

        # Inserir uma nova entrada no workflow para o cancelamento com o motivo
        cursor.execute(""" 
            INSERT INTO WORKFLOW (form_id, status, motivo, tipo_workflow) VALUES (%s, 'PENDENTE', %s, 'cancelamento')
        """, (identificador, motivo))
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
            D.DOCUMENT_DATE_PUBLISH AS document_date_publish, D.REDATOR AS redator
        FROM DCDOCUMENT D
        JOIN DCCATEGORY C ON D.CATEGORY = C.IDCATEGORY
        WHERE D.CURRENT = 1 AND D.NMDOCUMENT LIKE %s OR D.IDDOCUMENT LIKE %s OR C.IDENTIFIER LIKE %s OR D.REDATOR LIKE %s
    """, ('%' + termo_busca + '%', '%' + termo_busca + '%', '%' + termo_busca + '%', '%' + termo_busca + '%'))
    documentos = cursor.fetchall()
    cursor.close()
    conn.close()


    # Renderizar o template com os resultados
    mensagem = ""
    if not documentos:
        mensagem = "Nenhum documento encontrado."

    return render_template('pesquisa_documentos.html', documentos=documentos, mensagem=mensagem)



# Rota para página de configurações
@app.route('/configuracoes')
def configuracoes():
    return render_template('configuracoes.html')

# Executar o app Flask
if __name__ == '__main__':
    app.run(debug=True)
