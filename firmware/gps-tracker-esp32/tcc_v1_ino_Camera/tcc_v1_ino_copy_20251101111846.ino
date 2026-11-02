#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <base64.h>
#include <ArduinoJson.h>

// ====== DEFINIÇÃO DO MODELO DA CÂMERA ======
#define CAMERA_MODEL_AI_THINKER
#include "camera_pins.h"

// ====== CONFIGURAÇÕES DE REDE ======
const char* ssid = "nome da rede";
const char* password = "senha da rede";

//const char* ssid = "UNIP-MARQUES";
//const char* password = "1011121314";


// ====== CREDENCIAIS BACKBLAZE ======
String keyID = "005ceee880b4d780000000001";
String applicationKey = "K005n6QlaGyfwzt5PUF0Ax5JPE/yXC0";
String bucketId = "bc8e5ecec868a08b948d0718";   // ID do bucket
String bucketName = "tcc-pipeline-imagens-gustavo"; // opcional

// ====== VARIÁVEIS DE AUTENTICAÇÃO ======
String apiUrl;
String authToken;
String uploadUrl;
String uploadAuthToken;

// ====== FUNÇÃO PARA EXIBIR ERROS JSON ======
void mostrarErroJson(const String& payload) {
  StaticJsonDocument<512> doc;
  DeserializationError error = deserializeJson(doc, payload);
  if (!error) {
    if (doc.containsKey("status") && doc.containsKey("code") && doc.containsKey("message")) {
      Serial.printf("Erro JSON: status=%d, code=%s, message=%s\n",
        doc["status"].as<int>(),
        doc["code"].as<const char*>(),
        doc["message"].as<const char*>());
      return;
    }
  }
  Serial.println("Erro inesperado (não foi possível parsear JSON de erro):");
  Serial.println(payload);
}

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(false);

  // ====== CONFIGURAÇÃO DA CÂMERA ======
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;

  if (psramFound()) {
    config.fb_count = 2;
  }

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Falha ao inicializar a câmera");
    return;
  }

  // ====== CONEXÃO WI-FI ======
  WiFi.begin(ssid, password);
  Serial.print("Conectando ao Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi conectado!");
}

// ====== FUNÇÃO PARA AUTENTICAR NO B2 ======
bool autenticarB2() {
  HTTPClient http;
  String url = "https://api.backblazeb2.com/b2api/v2/b2_authorize_account";
  String credentials = keyID + ":" + applicationKey;
  String encodedAuth = base64::encode(credentials);

  http.begin(url);
  http.addHeader("Authorization", "Basic " + encodedAuth);

  int httpCode = http.GET();
  String payload = http.getString();

  if (httpCode == 200) {
    Serial.println("Autenticado com sucesso!");
    Serial.println(payload);

    StaticJsonDocument<1024> doc;
    if (deserializeJson(doc, payload)) {
      Serial.println("Falha ao parsear JSON de autenticação");
      http.end();
      return false;
    }

    apiUrl = doc["apiUrl"].as<String>();
    authToken = doc["authorizationToken"].as<String>();
    http.end();
    return true;
  } else {
    Serial.printf("Erro ao autenticar: %d\n", httpCode);
    mostrarErroJson(payload);
    http.end();
    return false;
  }
}

// ====== FUNÇÃO PARA OBTER URL DE UPLOAD ======
bool obterUploadUrl() {
  HTTPClient http;
  String url = apiUrl + "/b2api/v2/b2_get_upload_url";

  http.begin(url);
  http.addHeader("Authorization", authToken);

  String body = "{\"bucketId\":\"" + bucketId + "\"}";
  int httpCode = http.POST(body);
  String payload = http.getString();

  if (httpCode == 200) {
    Serial.println("Upload URL obtida!");
    Serial.println(payload);

    StaticJsonDocument<1024> doc;
    if (deserializeJson(doc, payload)) {
      Serial.println("Falha ao parsear JSON do uploadUrl");
      http.end();
      return false;
    }

    uploadUrl = doc["uploadUrl"].as<String>();
    uploadAuthToken = doc["authorizationToken"].as<String>();
    http.end();
    return true;
  } else {
    Serial.printf("Erro ao obter upload URL: %d\n", httpCode);
    mostrarErroJson(payload);
    http.end();
    return false;
  }
}

// ====== FUNÇÃO PARA ENVIAR FOTO ======
bool enviarFotoB2(camera_fb_t* fb) {
  HTTPClient http;
  http.begin(uploadUrl);

  http.addHeader("Authorization", uploadAuthToken);
  http.addHeader("X-Bz-File-Name", "foto_" + String(millis()) + ".jpg");
  http.addHeader("Content-Type", "b2/x-auto");
  http.addHeader("X-Bz-Content-Sha1", "do_not_verify");

  int httpCode = http.POST(fb->buf, fb->len);
  String payload = http.getString();

  if (httpCode == 200) {
    Serial.println("Foto enviada com sucesso!");
    http.end();
    return true;
  } else {
    Serial.printf("Erro ao enviar foto: %d\n", httpCode);
    mostrarErroJson(payload);
    http.end();
    return false;
  }
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    if (!autenticarB2()) return;
    if (!obterUploadUrl()) return;

    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Falha na captura da foto");
      return;
    }

    enviarFotoB2(fb);
    esp_camera_fb_return(fb);
  } else {
    Serial.println("Wi-Fi desconectado");
  }

  delay(60000); // espera 60 segundos antes da próxima foto
}