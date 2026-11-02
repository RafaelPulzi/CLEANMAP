#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

const char* ssid = "SEU_WIFI";
const char* password = "SUA_SENHA";

// IP do servidor Node.js (substitua pelo IPv4 do seu PC)
const char* serverUrl = "http://192.168.0.105:3004/api/gerar-imagem-rota";

// UART para receber do Arduino
#define RXD2 16
#define TXD2 17
HardwareSerial serialFromArduino(2);

String buffer = "";

void setup() {
  Serial.begin(115200);
  serialFromArduino.begin(9600, SERIAL_8N1, RXD2, TXD2);

  // Conecta ao Wi-Fi
  WiFi.begin(ssid, password);
  Serial.print("Conectando ao Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ Wi-Fi conectado!");
  Serial.print("IP local: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  // Lê dados da serial do Arduino
  while (serialFromArduino.available()) {
    char c = serialFromArduino.read();
    if (c == '\n') {
      processLine(buffer);
      buffer = "";
    } else {
      buffer += c;
    }
  }
}

void processLine(String line) {
  line.trim();
  if (line.length() == 0 || !line.startsWith("{")) return;

  Serial.println("📥 Recebido do Arduino:");
  Serial.println(line);

  // Faz parsing do JSON
  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, line);
  if (err) {
    Serial.print("Erro no JSON: ");
    Serial.println(err.c_str());
    return;
  }

  double lat = doc["latitude"];
  double lon = doc["longitude"];

  enviarCoordenadas(lat, lon);
}

void enviarCoordenadas(double lat, double lon) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi desconectado, tentando reconectar...");
    WiFi.reconnect();
    return;
  }

  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");

  // Corpo do POST compatível com o servidor Node
  String payload = "{";
  payload += "\"origem_latitude\":" + String(lat, 6) + ",";
  payload += "\"origem_longitude\":" + String(lon, 6) + ",";
  payload += "\"destino_latitude\": -23.55962,";
  payload += "\"destino_longitude\": -46.65823";
  payload += "}";

  int responseCode = http.POST(payload);

  if (responseCode > 0) {
    Serial.printf("🌍 POST enviado (%d): %s\n", responseCode, http.getString().c_str());
  } else {
    Serial.printf("❌ Erro HTTP: %s\n", http.errorToString(responseCode).c_str());
  }

  http.end();
}
