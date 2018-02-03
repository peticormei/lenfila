from flask import Flask
from flask_restful import Api, Resource, marshal, reqparse
from templates_respostas import *
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
api = Api(app)

uri_database = "mysql://root:root@localhost:3306/len(fila)"
app.config['SQLALCHEMY_DATABASE_URI'] = uri_database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class HistoricoTamanhosBase(db.Model):

    __tablename__ = 'historico'

    id = db.Column(db.Integer, primary_key=True)
    checkpointAtingido = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.Integer, nullable=False)

    def __init__(self, checkpointRegistro, timestampRegistro):

        self.checkpointAtingido = checkpointRegistro
        self.timestamp = timestampRegistro

class HistoricoTamanhos(Resource):

    def __init__(self):

        self.parser = reqparse.RequestParser()
        self.parser.add_argument('checkpointAtingido', type=int, required = True,
                                 help='Value cannot be converted', location = 'json')
        self.parser.add_argument('timestamp', type=int, required = True,
                                 help='Value cannot be converted', location = 'json')

        super(HistoricoTamanhos, self).__init__()

    def get(self):
        pass

    def post(self):

        tamanhoCalculado = self.parser.parse_args()

        checkpointAtingido = tamanhoCalculado["checkpointAtingido"]
        timestamp = tamanhoCalculado["timestamp"]

        novoRegistro = HistoricoTamanhosBase(checkpointAtingido, timestamp)
        db.session.add(novoRegistro)
        db.session.commit()

class TamanhoAtual(Resource):

    def get(self):

        tamanhoAtual = HistoricoTamanhosBase.query.order_by(HistoricoTamanhosBase.id.desc()).first()
        return {'tamanhoAtual': marshal(tamanhoAtual, camposTamanhoAtual)}

api.add_resource(HistoricoTamanhos, '/api/tamanhos', endpoint = 'tamanhos')
api.add_resource(TamanhoAtual, '/api/tamanho', endpoint = 'tamanhoAtual')

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
