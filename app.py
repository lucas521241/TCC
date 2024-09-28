from flask import Flask, render_template, request, redirect, url_for
from elasticsearch import Elasticsearch
from datetime import datetime
import mysql.connector
import subprocess
import os
import time

app = Flask(__name__)

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

# Conexão com o Elasticsearch
es = Elasticsearch(['http://localhost:9200'])

# Rota inicial do portal
@app.route('/meu-portal')
def meu_portal():
    return render_template('meu_portal.html')

# Rota para inserir documento no Elasticsearch
@app.route('/inserir-documento', methods=['POST'])
def inserir_documento():
    identificador = request.form['identificador']
    categoria = request.form['categoria']
    autor = request.form['autor']
    email = request.form['email']
    skills = request.form['skills'].split(',')

    # Criando documento
    doc = {
        'identificador': identificador,
        'categoria': categoria,
        'autor': autor,
        'email': email,
        'skills': skills,
        'timestamp': datetime.now(),
    }

    # Inserir no Elasticsearch
    try:
        res = es.index(index="python-elasticsearch", body=doc)
        print("Documento inserido com sucesso:", res['result'])
        return redirect(url_for('meu_portal'))
    except Exception as e:
        print(f"Erro ao inserir documento: {e}")
        return "Erro ao inserir documento no Elasticsearch."

# Rota inicial para login
@app.route('/')
def login():
    return render_template('login.html')

# Rota para tratar o login
@app.route('/login', methods=['GET', 'POST'])
def login_route():
    if request.method == 'POST':
        return redirect(url_for('home'))
    return render_template('login.html')

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
    start_elasticsearch()  # Inicia o Elasticsearch ao executar o app
    app.run(debug=True)
