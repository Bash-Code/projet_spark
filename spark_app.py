import os

import pyspark
import requests
from pyspark.sql import SparkSession
from pyspark.sql.functions import explode
from pyspark.sql.functions import split

os.environ["PYSPARK_PYTHON"] = "python3"
os.environ["SPARK_LOCAL_HOSTNAME"] = "localhost"


def send_data(tags: dict) -> None:
    url = 'http://localhost:5001/updateData'
    response = requests.post(url, json=tags)


def process_row(row: pyspark.sql.types.Row) -> None:
    
    tags = row.asDict()
    print(tags)  
    send_data(tags)


def new():
    # on crée une session de Spark (“SparkSession”) locale, 
    # le point de départ de toutes les fonctionnalités liées à Spark.
    spark = SparkSession.builder.appName("SparkTwitterAnalysis").getOrCreate()

    sc = spark.sparkContext
    sc.setLogLevel("ERROR")

    # Ce DataFrame 'lines' représente une table illimitée contenant les données de texte en continu. 
    # Cette table contient une colonne de chaînes nommée « valeur » 
    # et chaque ligne des données de texte en continu devient une ligne dans la table.

    # créons un flux de données DataFrame qui représente les données textuelles reçues d'un serveur écoutant sur localhost : 9009
    lines = spark.readStream.format("socket").option("host", "127.0.0.1").option("port", 9009).load()
    
    # Puis, nous avons utilisé deux fonctions SQL intégrées - split et explode, 
    # pour diviser chaque ligne de texte en plusieurs lignes de la table avec un mot chacune. 
    # De plus, nous utilisons la fonction ‘alias’ pour nommer la nouvelle colonne "hashtag".

    words = lines.select(explode(split(lines.value, " ")).alias("hashtag"))

    # Enfin, nous avons défini le wordCounts DataFrame en regroupant les valeurs uniques dans le Dataset 
    # et en les comptant. 

    wordCounts = words.groupBy("hashtag").count()
    # print(type(wordCounts))             # <class 'pyspark.sql.dataframe.DataFrame'>

    # Nous avons maintenant mis en place la requête sur les données de streaming. 
    # Il ne reste plus qu'à commencer à recevoir des données et à calculer les counts. 
    # Pour ce faire, nous l'avons configuré pour imprimer (print) l'ensemble complet des counts sur la console 
    # à chaque mise à jour. Et puis démarrez le calcul du streaming en utilisant start().

    
    query = wordCounts.writeStream.foreach(process_row).outputMode('Update').start()

    query.awaitTermination()


if __name__ == '__main__':
    try:
        new()
    except BrokenPipeError:
        exit("Pipe Broken, Exiting...")
    except KeyboardInterrupt:
        exit("Keyboard Interrupt, Exiting..")
    except Exception as e:
        exit("Error in Spark App")
