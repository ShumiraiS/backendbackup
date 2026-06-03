#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h> // Render HTTPS support
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ================= WIFI CONFIGURATION =================
const char* ssid = "TECH";
const char* password = "Jefter1234";

// ================= API & DB ENDPOINTS =================
const char* serverName = "https://backendbackup-slv6.onrender.com/api/ingest/industry/";
const char* site_id = "IND_E11719";

// ================= FIREBASE RTDB PUMP URL =============
// The base database URL (MUST end in a slash '/')
const char* firebaseDatabaseURL = "https://efflu-aibackend-default-rtdb.firebaseio.com/";

// If your Firebase Security Rules are locked (returning 401 error):
// Paste your Database Secret key here. If your rules are open (e.g. read: true), leave this empty "".
const char* databaseSecret = "a5cE2Cd583tNahUcbXv7npfliBDQW4Ue0QciQmZT"; 

// ============== SENSOR PINS ============
#define PH_PIN       34
#define TURBID_PIN   35
#define ONE_WIRE_BUS 4
#define FLOAT_PIN    23  // Float switch water level sensor (GND & GPIO 23, labeled D23)

// ============== PUMP & RELAY PINS =====
#define PUMP_PIN     19  // Relay Channel: Water Flow Pump 1

// ============== RELAY ACTIVE STATE =====
// Note: Most standard Arduino relay modules are Active-LOW.
// Swap these if your relay module is Active-HIGH.
#define RELAY_ON     LOW  
#define RELAY_OFF    HIGH 

// ============== DS18B20 ================
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// ============== GLOBAL SECURE CLIENT =================
// Declaring the secure client globally allocates its SSL handshake buffer 
// in heap/global memory rather than the task stack. This prevents ESP32 stack overflow crashes.
WiFiClientSecure secureClient;

// ============== TIMERS & CONTROL VARIABLES =
unsigned long lastTime = 0;
unsigned long timerDelay = 60000;          // 60 sec server ingest interval
unsigned long lastCommandCheck = 0;
unsigned long commandCheckDelay = 2000;    // Check Firebase for pump commands every 2 seconds
bool firstRun = true;                      // Run sensor readings & server transmission immediately at boot

// =======================================
// FUNCTION TO AVERAGE ADC READINGS
// =======================================
int readAverage(int pin) {
  long total = 0;
  for (int i = 0; i < 10; i++) {
    total += analogRead(pin);
    delay(10);
  }
  return total / 10;
}

// =======================================
// SETUP
// =======================================
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n--- ESP32 Startup ---");

  analogReadResolution(12);
  sensors.begin();

  // Sensors Setup
  pinMode(PH_PIN, INPUT);
  pinMode(TURBID_PIN, INPUT);
  pinMode(FLOAT_PIN, INPUT_PULLUP); // LOW = Float switch activated (water present/high)
  
  // Relay Pins Setup
  pinMode(PUMP_PIN, OUTPUT);
  
  // Start with pump off
  digitalWrite(PUMP_PIN, RELAY_OFF);

  // WiFi Connection
  WiFi.begin(ssid, password);
  Serial.println("Connecting to WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi Connected");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());

  // Configure secure client connection parameter
  secureClient.setInsecure();

  // ===================================================
  // RESET PUMP STATE IN DATABASE TO OFF ON STARTUP
  // ===================================================
  // This satisfies your rule: The pump must start OFF. 
  // We write {"pump": false} directly to Firebase so that the web UI gets updated to reflect it is off.
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    String requestURL = String(firebaseDatabaseURL) + "pump_control.json";
    if (strlen(databaseSecret) > 0) {
      requestURL += "?auth=" + String(databaseSecret);
    }
    
    Serial.println("[SYSTEM] Resetting pump command in Firebase to OFF...");
    http.begin(secureClient, requestURL);
    http.addHeader("Content-Type", "application/json");
    
    int httpResponseCode = http.PUT("{\"pump\":false}");
    if (httpResponseCode == 200) {
      Serial.println("[SYSTEM] Reset pump command to OFF in Firebase successfully on boot.");
    } else {
      Serial.print("[SYSTEM] Failed to reset pump on boot, HTTP Code: ");
      Serial.println(httpResponseCode);
    }
    http.end();
  }
}

// =======================================
// LOOP
// =======================================
void loop() {
  unsigned long currentMillis = millis();

  // =======================================
  // 1. CHECK FIREBASE PUMP COMMANDS (Every 2s)
  // =======================================
  if (currentMillis - lastCommandCheck > commandCheckDelay) {
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;

      // Construct the Firebase request URL
      // Realtime Database REST API requires the resource to end in '.json'
      String requestURL = String(firebaseDatabaseURL) + "pump_control.json";
      
      // If a database secret is provided, append it for authentication
      if (strlen(databaseSecret) > 0) {
        requestURL += "?auth=" + String(databaseSecret);
      }

      // GET commands directly from Firebase
      http.begin(secureClient, requestURL);
      int httpResponseCode = http.GET();

      if (httpResponseCode == 200) {
        String payload = http.getString();
        StaticJsonDocument<256> doc;
        DeserializationError error = deserializeJson(doc, payload);

        if (!error) {
          // Read state from JSON. Supports: {"pump": true}, {"pump1": true}, or raw boolean values.
          bool pumpState = false;
          if (doc.is<JsonObject>()) {
            pumpState = doc["pump"] | doc["pump1"] | false;
          } else {
            pumpState = doc.as<bool>();
          }

          digitalWrite(PUMP_PIN, pumpState ? RELAY_ON : RELAY_OFF);
          
          Serial.print("[PUMP COMMANDS]: Pump = ");
          Serial.println(pumpState ? "ON" : "OFF");
        } else {
          Serial.print("[PUMP COMMANDS] JSON parsing failed: ");
          Serial.println(error.c_str());
        }
      } else {
        Serial.print("[PUMP COMMANDS] HTTP error fetching commands: ");
        Serial.println(httpResponseCode);
        if (httpResponseCode == 401) {
          Serial.println("-> Check database secret or set database rules to public for pump_control.");
        }
      }
      http.end();
    }
    lastCommandCheck = currentMillis;
  }

  // =======================================
  // 2. TIMED CLOUD DATA INGESTION (Every 60s or immediately on boot)
  // =======================================
  if (firstRun || (currentMillis - lastTime > timerDelay)) {

    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("WiFi Lost. Reconnecting...");
      WiFi.begin(ssid, password);
      while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
      }
      Serial.println("\nReconnected.");
    }

    // --- READ SENSORS ---
    sensors.requestTemperatures();
    float temperatureC = sensors.getTempCByIndex(0);
    if (temperatureC == -127.00) {
      Serial.println("DS18B20 Error! Check wire connection and 4.7k ohm pull-up resistor. Using fallback 25.0 °C.");
      temperatureC = 25.0; // Use fallback temperature to prevent ingest failure and allow other sensors to report
    }

    int phRaw = readAverage(PH_PIN);
    float phVoltage = phRaw * (3.3 / 4095.0);
    float phValue = 7 + ((2.5 - phVoltage) / 0.18);

    int turbRaw = readAverage(TURBID_PIN);
    float turbVoltage = turbRaw * (3.3 / 4095.0);
    float turbidityNTU = -1120.4 * turbVoltage * turbVoltage + 5742.3 * turbVoltage - 4352.9;
    if (turbidityNTU < 0) turbidityNTU = 0;

    // Check float switch (0 = Closed/Water Present, 1 = Open/Water Empty)
    int floatState = digitalRead(FLOAT_PIN);
    String waterLevel = (floatState == LOW) ? "Water Present (High)" : "Low/No Water";

    float codValue = random(180, 260);
    float chloridesValue = random(200, 300);

    // ==========================================
    // SHOW SENSOR DATA IN THE SERIAL MONITOR
    // ==========================================
    Serial.println("\n================= SENSOR READINGS =================");
    Serial.print("pH Value:         "); Serial.println(phValue);
    Serial.print("Temperature:      "); Serial.print(temperatureC); Serial.println(" °C");
    Serial.print("Turbidity:        "); Serial.print(turbidityNTU); Serial.println(" NTU");
    Serial.print("Water Level:      "); Serial.println(waterLevel);
    Serial.print("COD (Simulated):  "); Serial.print(codValue); Serial.println(" mg/L");
    Serial.print("Chlorides (Sim):  "); Serial.print(chloridesValue); Serial.println(" mg/L");
    Serial.println("===================================================");

    // --- SEND DATA TO SERVER ---
    HTTPClient http;
    http.begin(secureClient, serverName); 
    http.addHeader("Content-Type", "application/json");

    StaticJsonDocument<512> doc;
    doc["site_id"] = site_id;
    doc["ph"] = phValue;
    doc["temperature"] = temperatureC;
    doc["cod"] = codValue;
    doc["chlorides"] = chloridesValue;
    doc["suspended_solids"] = turbidityNTU;
    doc["water_level"] = waterLevel;

    String requestBody;
    serializeJson(doc, requestBody);

    Serial.println("Sending JSON to Render...");
    Serial.println(requestBody);

    int httpResponseCode = http.POST(requestBody);

    if (httpResponseCode > 0) {
      Serial.print("HTTP Response Code: ");
      Serial.println(httpResponseCode);
      String response = http.getString();
      Serial.println("Server Response:");
      Serial.println(response);
    } else {
      Serial.print("HTTP Error: ");
      Serial.println(httpResponseCode);
    }

    http.end();
    
    firstRun = false; // Reset boot flag
    lastTime = currentMillis;
  }
}
