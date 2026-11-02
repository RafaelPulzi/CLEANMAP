#include <TinyGPSPlus.h>
#include <SoftwareSerial.h>

static const int RXPin = 4, TXPin = 3;
static const uint32_t GPSBaud = 9600;

SoftwareSerial gpsSerial(RXPin, TXPin);
TinyGPSPlus gps;

unsigned long lastSend = 0;
const unsigned long sendInterval = 2000;

void setup() {
  Serial.begin(9600);
  gpsSerial.begin(GPSBaud);
  delay(2000);
  Serial.println("INICIANDO_GPS_JSON");
}

void loop() {
  while (gpsSerial.available() > 0) {
    gps.encode(gpsSerial.read());
  }

  if (gps.location.isValid() && (millis() - lastSend >= sendInterval)) {
    lastSend = millis();

    double lat = gps.location.lat();
    double lng = gps.location.lng();
    unsigned long fixAge = gps.location.age();

    Serial.print("{");
    Serial.print("\"latitude\":");
    Serial.print(lat, 6);
    Serial.print(",\"longitude\":");
    Serial.print(lng, 6);
    Serial.print(",\"fixAgeMs\":");
    Serial.print(fixAge);
    Serial.print(",\"ts\":");
    Serial.print(millis());
    Serial.println("}");
  }
}
