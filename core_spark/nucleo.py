import sys
from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from mqtt import MQTTUtils
import httplib, json, time

def mediaSinais(lista):
    quantidade = len(lista)
    soma = sum(lista)
    media = soma/quantidade
    return media

def mapeiaCategoriasCheck1(tupla):
    
    categoriaPerto = [-75,-50]
    categoriaDistante = [-100,-76]
    
    if tupla[1] in range(categoriaPerto[0],categoriaPerto[1]+1):
        
        return ("categoriaPertoPrimeiro", [tupla[0]])
    
    elif tupla[1] in range(categoriaDistante[0],categoriaDistante[1]+1):
    
        return ("categoriaDistante", [tupla[0]])
    
    return

def mapeiaCategoriasCheck2(tupla):
    
    categoriaPerto = [-75,-50]
    categoriaDistante = [-100,-76]
    
    if tupla[1] in range(categoriaPerto[0],categoriaPerto[1]+1):
        
        return ("categoriaPertoSegundo", [tupla[0]])
    
    elif tupla[1] in range(categoriaDistante[0],categoriaDistante[1]+1):
    
        return ("categoriaDistante", [tupla[0]])
    
    return

def marcaTuplaDistanteCheck1(tupla):
    
    if tupla[0] == "categoriaDistante":
        return (tupla[0],(1,tupla[1]))
    else:
        return tupla
    
def marcaTuplaDistanteCheck2(tupla):
    
    if tupla[0] == "categoriaDistante":
        return (tupla[0],(2,tupla[1]))
    else:
        return tupla

def mapeiaIntersecao(tupla):
    
    categoria = tupla[0]
    
    if categoria == "categoriaDistante":
        
        tuplasInternas = tupla[1]
        
        if tuplasInternas[0][0] == 1:
            
            distantesCheck1 = tuplasInternas[0][1]
            
            if len(tuplasInternas) == 2:
                distantesCheck2 = tuplasInternas[1][1]
            else:
                distantesCheck2 = []
        
        else:
            
            distantesCheck2 = tuplasInternas[0][1]
            
            if len(tuplasInternas) == 2:
                distantesCheck1 = tuplasInternas[1][1]
            else:
                distantesCheck1 = []
            
        intersecao = []
        
        for mac in distantesCheck1:
            
            if mac in distantesCheck2:
                intersecao.append(mac) 
                distantesCheck1.remove(mac)
                distantesCheck2.remove(mac)
        
        
        return ("AntesPrimeiro", distantesCheck1), ("Intersecao",intersecao), ("DepoisSegundo", distantesCheck2)  
        
    else:
        
        macs = tupla[1][0] # retirar lista externa
        tuplaRetorno = (categoria, macs),
        return tuplaRetorno

def post_resultado(categoriasDivididas):
    
    limite_inf_antes1 = 5
    limite_inf_perto1 = 2
    limite_inf_intersecao = 2
    limite_inf_perto2 = 2
    limite_inf_depois2 = 22
    
    categorias = categoriasDivididas.keys()
    
    checkpointAtingido = 0
    
    if "AntesPrimeiro" in categorias and categoriasDivididas["AntesPrimeiro"] >= limite_inf_antes1:
        if "categoriaPertoPrimeiro" in categorias and categoriasDivididas["categoriaPertoPrimeiro"] >= limite_inf_perto1:
            checkpointAtingido = 1
            if "Intersecao" in categorias and categoriasDivididas["Intersecao"] >= limite_inf_intersecao:
                if "categoriaPertoSegundo" in categorias and categoriasDivididas["categoriaPertoSegundo"] >= limite_inf_perto2:
                    checkpointAtingido = 2
       
    timestamp = int(time.time())

    body_dicionario = {}
    body_dicionario["checkpointAtingido"] = checkpointAtingido
    body_dicionario["timestamp"] = timestamp

    body_json = json.dumps(body_dicionario)
    cabecalho = {"Content-type": "application/json"}

    conexao = httplib.HTTPConnection("172.16.204.174",5000)
    conexao.request("POST", "/api/tamanhos", body_json, cabecalho)
    conexao.close()
    
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print >> sys.stderr, "Usage: nucleo.py <broker url> <topic>"
        exit(-1)

    sc = SparkContext(appName="CoreLenFila")
    ssc = StreamingContext(sc, 30)

    brokerUrl = sys.argv[1]
    topic = sys.argv[2]
     
    lote = MQTTUtils.createStream(ssc, brokerUrl, topic)
    
    lote = lote.map(lambda coleta: coleta.split(","))
    
    loteCheck1 = lote.filter(lambda coleta: int(coleta[0]) == 1)
    loteCheck2 = lote.filter(lambda coleta: int(coleta[0]) == 2)
    
    alocacaoCategoriasCheck1 = loteCheck1.map(lambda coleta: (coleta[2],int(coleta[1]))) \
            .groupByKey().mapValues(list) \
            .mapValues(mediaSinais) \
            .map(mapeiaCategoriasCheck1) \
            .reduceByKey(lambda a, b: a + b) \
            .map(marcaTuplaDistanteCheck1)          
 
    #alocacaoCategoriasCheck1.pprint()  
        
    alocacaoCategoriasCheck2 = loteCheck2.map(lambda coleta: (coleta[2],int(coleta[1]))) \
            .groupByKey().mapValues(list) \
            .mapValues(mediaSinais) \
            .map(mapeiaCategoriasCheck2) \
            .reduceByKey(lambda a, b: a + b) \
            .map(marcaTuplaDistanteCheck2)                        
 
    #alocacaoCategoriasCheck2.pprint()
    
    ## Calculo da intersecao
    
    intersecao = alocacaoCategoriasCheck1.union(alocacaoCategoriasCheck2) \
            .groupByKey().mapValues(list) \
            .flatMap(mapeiaIntersecao)
    
    intersecao.pprint()
    
    quantidadePessoasCategorias = intersecao.map(lambda categoria: [(categoria[0], len(categoria[1]))])
    
    quantidadePessoasCategorias.pprint()
    
    categoriasDivididasDict = quantidadePessoasCategorias.reduce(lambda a, b: a + b) \
                            .map(dict)
    
    categoriasDivididasDict.pprint()
    
    categoriasDivididasDict.foreachRDD(lambda rdd: rdd.foreach(post_resultado))        
            
    ssc.start()
    ssc.awaitTermination()