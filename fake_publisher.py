import time
import pandas as pd
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta

fieldnames = None
topics = "outTopic"

client = mqtt.Client("lenPub")
client.connect("localhost", 1883)


def string_to_datetime(string):
    timestamp = datetime.strptime(string, "%I:%M:%S %p")
    timestamp = timedelta(hours=timestamp.hour, minutes=timestamp.minute, seconds=timestamp.second)
    return timestamp.total_seconds()


def df_filter_timestamp(bottom, top):
    return df_lenfila[(df_lenfila["Timestamp"] >= bottom) & (df_lenfila["Timestamp"] < top)]


df_lenfila = pd.read_csv("dataset.csv")
df_lenfila["Timestamp"] = df_lenfila["Timestamp"].apply(string_to_datetime)

total_dados = 0
window_size = timedelta(0, 15).total_seconds()
bottom_base = df_lenfila.iloc[0]["Timestamp"]
top_base = bottom_base + window_size

print("Inicializando simulacao...")
df_filtered = df_filter_timestamp(bottom_base, top_base)
while not df_filtered.empty:
    print("\nHorario de envio:", datetime.now().__str__())
    total_dados += df_filtered.shape[0]
    print("Dados enviados:", df_filtered.shape[0])
    print("Bottom base:", bottom_base, "Top base:", top_base)
    bottom_base = top_base
    top_base = bottom_base + window_size
    df_filtered = df_filter_timestamp(bottom_base, top_base)

    e = df_filtered[["Checkpoint 1", "MAC"]].values.tolist()
    str_list = []
    for x in e:
        x[0] = str(x[0])
        str_list.append(",".join(x))

    str_list = ";".join(str_list)

    client.publish("hello", str_list)
    time.sleep(15)

print("\nSimulacao finalizado!")
print("Total de dados enviados:", total_dados)
