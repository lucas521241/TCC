from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/home', methods=['GET'])
def home():
    return render_template('home.html')

@app.route('/minhas-tarefas')
def minhas_tarefas():
    return render_template('minhas_tarefas.html')

@app.route('/meu-portal')
def meu_portal():
    return render_template('meu_portal.html')

@app.route('/pesquisa-documentos')
def pesquisa_documentos():
    return render_template('pesquisa_documentos.html')

@app.route('/configuracoes')
def configuracoes():
    return render_template('configuracoes.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Aqui você pode adicionar a lógica de autenticação
        return redirect(url_for('home'))
    return render_template('login.html')


if __name__ == '__main__':
    app.run(debug=True)
