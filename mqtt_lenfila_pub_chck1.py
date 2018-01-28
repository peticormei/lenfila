import time
import pandas as pd
import numpy as np
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta

fieldnames = None

client = mqtt.Client("lenPub")
client.connect("172.16.207.12", 1883)

def string_to_datetime(string):
    timestamp = datetime.strptime(string, "%I:%M:%S %p")
    timestamp = timedelta(hours=timestamp.hour, minutes=timestamp.minute, seconds=timestamp.second)
    return timestamp.total_seconds()

def df_filter_timestamp(bottom, top):
    return df_lenfila[(df_lenfila["Timestamp"] >= bottom) & (df_lenfila["Timestamp"] < top)]

def send_mqtt(base):
    data = base[["Checkpoint", "MAC"]].values
    str_data = [",".join([str(value) for value in row]) for row in data]
    for row in str_data:
        result = client.publish("hello", row)
        print("Dado enviado:", row)

df_lenfila = pd.read_csv("dataset_checkpoint1.csv")
df_lenfila["Timestamp"] = df_lenfila["Timestamp"].apply(string_to_datetime)


window_size = timedelta(0, 15).total_seconds()
bottom_base = df_lenfila.iloc[0]["Timestamp"]
top_base = bottom_base + window_size

print("Inicializando simulacao...")
df_filtered = df_filter_timestamp(bottom_base, top_base)

signal = df_filtered.copy(deep=True)
signal.sort_values("Checkpoint")
print(signal.values[0], signal.values[-1])
while not df_filtered.empty:
    print("\nEnviando dados")
    send_mqtt(df_filtered)
    print("Dados enviados")
    print("\nHorario de envio:", datetime.now().__str__())
    print("Dados enviados:", df_filtered.shape[0])
    print("Bottom base:", bottom_base,"Top base:", top_base)
    bottom_base = top_base
    top_base = bottom_base + window_size
    df_filtered = df_filter_timestamp(bottom_base, top_base)
    time.sleep(15)

print("\nSimulacao finalizado!")
