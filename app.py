from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)

# Configurações de conexão ao MySQL
mydb_config = {
    'host': "127.0.0.1",        # Nome do servidor ou IP
    'user': "root",             # Usuário MySQL
    'password': "root",         # Senha MySQL
    'database': "docsnaipa" # Nome do banco de dados
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


# Rota inicial para login
@app.route('/')
def login():
    return render_template('login.html')


# Rota para tratar o login
@app.route('/login', methods=['GET', 'POST'])
def login_route():
    if request.method == 'POST':
        # Aqui você pode adicionar a lógica de autenticação, por exemplo, verificando o usuário no banco
        return redirect(url_for('home'))  # Redireciona para a rota 'home'
    return render_template('login.html')


# Página inicial após login
@app.route('/home', methods=['GET'])
def home():
    return render_template('home.html')


# Rota para exibir tarefas
@app.route('/minhas-tarefas')
def minhas_tarefas():
    return render_template('minhas_tarefas.html')


# Rota para exibir o portal do usuário
@app.route('/meu-portal')
def meu_portal():
    return render_template('meu_portal.html')


# Rota para a pesquisa de documentos
@app.route('/pesquisa-documentos')
def pesquisa_documentos():
    conn = connect_to_db()
    if conn:
        try:
            # Criar um cursor e realizar consulta no banco de dados
            mycursor = conn.cursor()
            mycursor.execute("SELECT * FROM dcdocument")
            resultados = mycursor.fetchall()

            # Fechar o cursor
            mycursor.close()

            return render_template('pesquisa_documentos.html', dados=resultados)

        except mysql.connector.Error as err:
            print(f"Erro ao consultar o banco de dados: {err}")
            return "Erro ao consultar o banco de dados."
        
        finally:
            # Fechar a conexão
            conn.close()
            print("Conexão com o MySQL foi encerrada.")
    else:
        return "Erro ao conectar ao banco de dados."


# Rota para página de configurações
@app.route('/configuracoes')
def configuracoes():
    return render_template('configuracoes.html')


# Executar o app Flask
if __name__ == '__main__':
    app.run(debug=True)
