extern "C" {
  #include <user_interface.h>
}
#include <ESP8266WiFi.h>
#include "FS.h"
#include <PubSubClient.h>

#define DATA_LENGTH           112

#define TYPE_MANAGEMENT       0x00
#define TYPE_CONTROL          0x01
#define TYPE_DATA             0x02
#define SUBTYPE_PROBE_REQUEST 0x04

#define CHANNEL_HOP_INTERVAL_MS   1000
static os_timer_t channelHop_timer;
static int tempo_passado = 0;
static int num_pacotes_coletados = 0;
char buffer_pacotes[200][25];

const char* mqtt_broker = "192.168.0.105";
WiFiClient espClient;
PubSubClient client(espClient);

#define DISABLE 0
#define ENABLE  1

struct RxControl {
 signed rssi:8; // signal intensity of packet
 unsigned rate:4;
 unsigned is_group:1;
 unsigned:1;
 unsigned sig_mode:2; // 0:is 11n packet; 1:is not 11n packet;
 unsigned legacy_length:12; // if not 11n packet, shows length of packet.
 unsigned damatch0:1;
 unsigned damatch1:1;
 unsigned bssidmatch0:1;
 unsigned bssidmatch1:1;
 unsigned MCS:7; // if is 11n packet, shows the modulation and code used (range from 0 to 76)
 unsigned CWB:1; // if is 11n packet, shows if is HT40 packet or not
 unsigned HT_length:16;// if is 11n packet, shows length of packet.
 unsigned Smoothing:1;
 unsigned Not_Sounding:1;
 unsigned:1;
 unsigned Aggregation:1;
 unsigned STBC:2;
 unsigned FEC_CODING:1; // if is 11n packet, shows if is LDPC packet or not.
 unsigned SGI:1;
 unsigned rxend_state:8;
 unsigned ampdu_cnt:8;
 unsigned channel:4; //which channel this packet in.
 unsigned:12;
};

struct SnifferPacket{
    struct RxControl rx_ctrl;
    uint8_t data[DATA_LENGTH];
    uint16_t cnt;
    uint16_t len;
};

static void showMetadata(SnifferPacket *snifferPacket) {

  unsigned int frameControl = ((unsigned int)snifferPacket->data[1] << 8) + snifferPacket->data[0];

  uint8_t version      = (frameControl & 0b0000000000000011) >> 0;
  uint8_t frameType    = (frameControl & 0b0000000000001100) >> 2;
  uint8_t frameSubType = (frameControl & 0b0000000011110000) >> 4;
  uint8_t toDS         = (frameControl & 0b0000000100000000) >> 8;
  uint8_t fromDS       = (frameControl & 0b0000001000000000) >> 9;

  // Only look for probe request packets
  if (frameType != TYPE_MANAGEMENT ||
      frameSubType != SUBTYPE_PROBE_REQUEST)
        return;

  String rssi = String(snifferPacket->rx_ctrl.rssi);
  Serial.print("RSSI: ");
  Serial.print(rssi);

  Serial.print(" Ch: ");
  Serial.print(wifi_get_channel());

  char addr[] = "00:00:00:00:00:00";
  getMAC(addr, snifferPacket->data, 10);
  Serial.print(" Peer MAC: ");
  Serial.print(addr);

  uint8_t SSID_length = snifferPacket->data[25];
  Serial.print(" SSID: ");
  printDataSpan(26, SSID_length, snifferPacket->data);

  Serial.println();

  int qtdDigitos = rssi.length() - 1;
  int repeticoes = 3 - qtdDigitos;
  
  String rssi_final = rssi.substring(1);
    
  for(int i=0; i < repeticoes; i++){
    rssi_final = "0" + rssi_final;
    }
  rssi_final = "-" + rssi_final;

  String pacote_str = "1," + rssi_final + "," + addr;
  char pacote_array[25];
  pacote_str.toCharArray(pacote_array,25);
  
  snprintf(buffer_pacotes[num_pacotes_coletados], 25, "%s", pacote_array);
  num_pacotes_coletados ++;
}

/*
 * Callback for promiscuous mode
 */
static void ICACHE_FLASH_ATTR sniffer_callback(uint8_t *buffer, uint16_t length) {
  struct SnifferPacket *snifferPacket = (struct SnifferPacket*) buffer;
  showMetadata(snifferPacket);
}

static void printDataSpan(uint16_t start, uint16_t size, uint8_t* data) {
  for(uint16_t i = start; i < DATA_LENGTH && i < start+size; i++) {
    Serial.write(data[i]);
  }
}

static void getMAC(char *addr, uint8_t* data, uint16_t offset) {
  sprintf(addr, "%02x:%02x:%02x:%02x:%02x:%02x", data[offset+0], data[offset+1], data[offset+2], data[offset+3], data[offset+4], data[offset+5]);
}

/**
 * Callback for channel hoping
 */
void channelHop()
{
  tempo_passado ++;
  // hoping channels 1-14
  uint8 new_channel = wifi_get_channel() + 1;
  if (new_channel > 14)
    new_channel = 1;
  wifi_set_channel(new_channel);
}

void criaArquivoCredenciais(String ssid, String username, String password){

  File arquivo = SPIFFS.open("/credenciais.txt", "w");
  if(arquivo){
    arquivo.println(ssid);
    arquivo.println(username);
    arquivo.println(password);
    }
  arquivo.close();
  }

IPAddress conectarRede(){
  
  File credenciais = SPIFFS.open("/credenciais.txt", "r");
  
  String ssid = credenciais.readStringUntil('\n');  
  String username = credenciais.readStringUntil('\n');  
  String password = credenciais.readStringUntil('\n');  
  
  credenciais.close();

  int ssid_tamanho = ssid.length();
  char ssid_array[ssid_tamanho];
  ssid.toCharArray(ssid_array, ssid_tamanho);
  
  int password_tamanho = password.length();
  char password_array[password_tamanho];
  password.toCharArray(password_array, password_tamanho);
  
  WiFi.begin(ssid_array, password_array);
  while (WiFi.status() != WL_CONNECTED) { 
      Serial.println("Tentando conectar na rede");
      delay(500);
  }
    
  IPAddress ipRecebido = WiFi.localIP();
  return ipRecebido;
}

void coletar_pacotes(bool modo){
  
  if(modo==1){
    wifi_promiscuous_enable(ENABLE);
    os_timer_arm(&channelHop_timer, CHANNEL_HOP_INTERVAL_MS, 1);
  }else{
    wifi_promiscuous_enable(DISABLE);
    os_timer_disarm(&channelHop_timer);
    }
}

void publica_pacotes_coletados(){
  
  Serial.print("Conectando com o broker MQTT... ");
  client.connect("ESP8266Client");
  if (client.connected()) {
    Serial.println("Conectado");
  }

  for(int indice = 0; indice < num_pacotes_coletados; indice++){
    
    Serial.print("Publish message: ");
    Serial.println(buffer_pacotes[indice]);
  
    client.publish("coletor", buffer_pacotes[indice]);
    
  } 
  
  Serial.print("Disconectando do broker...");
  client.disconnect();
  if (!client.connected()) {
    Serial.println("Disconectado");
  }
}

void setup() {
  // set the WiFi chip to "promiscuous" mode aka monitor mode
  Serial.begin(115200);
  delay(10);
  wifi_set_opmode(STATION_MODE);
  wifi_set_channel(1);
  wifi_promiscuous_enable(DISABLE);
  delay(10);
  wifi_set_promiscuous_rx_cb(sniffer_callback);
  delay(10);
  wifi_promiscuous_enable(ENABLE);

  // setup the channel hoping callback timer
  os_timer_disarm(&channelHop_timer);
  os_timer_setfn(&channelHop_timer, (os_timer_func_t *) channelHop, NULL);
  os_timer_arm(&channelHop_timer, CHANNEL_HOP_INTERVAL_MS, 1);

  SPIFFS.begin();
  //criaArquivoCredenciais("ssid", "username", "password");  // execute esta função uma única vez substituindo os parâmetros por credenciais válidas para acessar a rede

  client.setServer(mqtt_broker, 1883);
}

void loop() {
  
  Serial.print(tempo_passado);
  Serial.print(" segundos de coleta, ");
  Serial.print(num_pacotes_coletados);
  Serial.println(" pacotes coletados.");
  
  if(tempo_passado > 29 || num_pacotes_coletados > 199){
    coletar_pacotes(DISABLE);
    Serial.println("Coleta pausada.");
    
    Serial.println("Conectando na rede...");
    IPAddress ip = conectarRede();
    Serial.print("Conectado! Ip recebido: ");
    Serial.println(ip);

    publica_pacotes_coletados();
    
    coletar_pacotes(ENABLE);
    Serial.println("Coleta retomada");
    
    tempo_passado = 0;
    num_pacotes_coletados = 0;
    }
   delay(1000);
}

/*
 * conexão em rede com usuário e senha, vide: https://www.hallgeirholien.no/post/esp8266-eap/
 */
