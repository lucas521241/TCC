from elasticsearch import Elasticsearch
from datetime import datetime

# Decodificar a API
import base64

api_key = 'YXFhZ09KSUJqQjRnOUlkTmRvZFU6NnRoaUtMOTNUTUtSeEJVdEt2YTFWdw=='
decoded_api_key = base64.b64decode(api_key).decode('utf-8')
print(f'API Decoded: {decoded_api_key}')

# Conectar ao Elasticsearch
es = Elasticsearch(
    ['https://seu-endereco-elasticsearch.com'],
    http_auth=('aqagOJIBjB4g9IdNdodU', '6thiKL93TMKRxBUtKva1Vw')
)

# Documento a ser enviado ao Elasticsearch
doc = {
    'identificador': 'WPS-0 PT',
    'categoria': 'WPS',
    'autor': 'Lucas Josue Schneider',
    'titulo':'Teste',
    'Skills': ['Python', 'Elasticsearch', 'Security'],
    'timestamp': datetime.now(),
}

# Indexando o documento no Elasticsearch
response = es.index(index="docsnaipa", document=doc)
print(response)
