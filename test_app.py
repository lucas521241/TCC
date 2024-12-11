import pytest
import os
from app import app, connect_to_db, extrair_texto_pdf, obter_categorias, obter_documentos, obter_usuarios
from flask import url_for

# Configuração do pytest para criar um cliente de teste
@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# 1. Testes de rotas principais
def test_login_route(client):
    response = client.get('/login')
    assert response.status_code == 200

def test_home_route_requires_auth(client):
    response = client.get('/home')
    assert response.status_code == 302  # Redireciona para /login
    assert '/login' in response.headers['Location']

def test_meu_portal_route(client):
    response = client.get('/meu-portal')
    assert response.status_code == 200

def test_inserir_documento_route(client):
    response = client.post('/inserir-documento', data={}, follow_redirects=True)
    assert response.status_code == 200

# 2. Testes de funções auxiliares
def test_connect_to_db():
    conn = connect_to_db()
    assert conn is not None
    conn.close()

def test_obter_categorias():
    categorias = obter_categorias()
    assert isinstance(categorias, list)

def test_obter_usuarios():
    usuarios = obter_usuarios()
    assert isinstance(usuarios, list)

def test_obter_documentos():
    documentos = obter_documentos()
    assert isinstance(documentos, list)

def test_extrair_texto_pdf():
    sample_pdf = os.path.join(os.path.dirname(__file__), 'sample.pdf')
    with open(sample_pdf, 'wb') as f:
        f.write(b"%PDF-1.4\n...")  # Um exemplo simples de um arquivo PDF
    texto = extrair_texto_pdf(sample_pdf)
    assert texto.strip() != ""
    os.remove(sample_pdf)

# 3. Testes de rotas específicas
def test_visualizar_pdf(client):
    response = client.get('/visualizar_pdf/1')
    assert response.status_code in [200, 404]  # Depende se o arquivo PDF existe

def test_summarize_pdf(client):
    response = client.get('/summarize_pdf/1')
    assert response.status_code in [200, 404]

def test_download_pdf(client):
    response = client.get('/download_pdf/1')
    assert response.status_code in [200, 404]

# 4. Testes para workflows
def test_minhas_tarefas(client):
    response = client.get('/minhas-tarefas')
    assert response.status_code == 200

def test_aprovar_reprovar(client):
    data = {"status": "APROVADO"}
    response = client.post('/aprovar_reprovar/1', data=data, follow_redirects=True)
    assert response.status_code == 200

# 5. Teste de inserção no banco
def test_inserir_documento(client):
    data = {
        'identificadorCriacao': '123',
        'nome_documentoCriacao': 'Teste Documento',
        'categoriaCriacao': '1',
        'usuario_aprovador': '1',
        'autor': 'Autor Teste',
        'motivo': 'Motivo Teste'
    }
    response = client.post('/inserir-documento', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Documento e arquivo PDF inseridos com sucesso!" in response.data
