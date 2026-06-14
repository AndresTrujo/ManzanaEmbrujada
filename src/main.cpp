#include <Arduino.h>
#include <Wire.h> 
#include <Adafruit_PN532.h>
#include <Adafruit_NeoPixel.h>

// --- CONFIGURACIÓN DE LOS LEDS ---
#define PIN_LEDS      2   
#define NUM_LEDS     300  

uint8_t rojoActual = 0, verdeActual = 0, azulActual = 0;
unsigned long ultimoEventoMs = 0; 
const unsigned long TIEMPO_IDLE_MS = 3000; // 3 segundos antes de volver al blanco de espera

Adafruit_NeoPixel tiras(NUM_LEDS, PIN_LEDS, NEO_GRB + NEO_KHZ800);

// --- COLORES BASE PARA REFERENCIA ---
// Blanco: {255, 255, 255} | Rojo: {255, 0, 0} | Verde: {0, 255, 0} | Amarillo: {255, 200, 0} | Azul: {0, 0, 255}

// --- MAPA DE COLORES FIJOS: BOTONES PRINCIPALES (1 al 12) ---
const uint8_t PALETA_PRINCIPALES[12][3] = {
  {255, 255, 255}, // Btn 1: Blanco
  {255, 0, 0},     // Btn 2: Rojo
  {0, 255, 0},     // Btn 3: Verde
  {255, 255, 255}, // Btn 4: Blanco
  {255, 200, 0},   // Btn 5: Amarillo
  {0, 0, 255},     // Btn 6: Azul
  {0, 0, 255},     // Btn 7: Azul
  {255, 255, 255}, // Btn 8: Blanco
  {255, 0, 0},     // Btn 9: Rojo
  {0, 0, 255},     // Btn 10: Azul
  {255, 200, 0},   // Btn 11: Amarillo
  {0, 255, 0}      // Btn 12: Verde
};

// --- MAPA DE COLORES FIJOS: BOTONES SECUNDARIOS (1 al 4) ---
const uint8_t PALETA_SECUNDARIOS[4][3] = {
  {255, 0, 0},     // Btn 1: Rojo
  {255, 200, 0},   // Btn 2: Amarillo
  {0, 0, 255},     // Btn 3: Azul
  {255, 255, 255}  // Btn 4: Blanco
};

// --- PALETA DE 16 COLORES HASH PARA MONEDAS NFC ---
const uint8_t PALETA_NFC[16][3] = {
  {255, 0, 0}, {255, 60, 0}, {255, 120, 0}, {255, 200, 0},
  {120, 255, 0}, {0, 255, 0}, {0, 255, 130}, {0, 255, 255},
  {0, 100, 255}, {0, 0, 255}, {70, 0, 255}, {160, 0, 255},
  {255, 0, 255}, {255, 0, 100}, {139, 69, 19}, {230, 230, 250}
};

// --- CONFIGURACIÓN DEL NFC ---
Adafruit_PN532 nfc(-1, -1);

// --- CONFIGURACIÓN DE BOTONES ---
const int botonesPrincipales[12] = {13, 12, 14, 27, 26, 25, 33, 32, 15, 4, 16, 17};
const int botonesSecundarios[4]  = {5, 18, 19, 23};

unsigned long ultimoDebounceBotones[16] = {0};
const unsigned long TIEMPO_DEBOUNCE = 250; 

// Prototipos
void cambiarColorGradual(uint8_t rDestino, uint8_t gDestino, uint8_t bDestino, int pasos, int esperaMs);
int obtenerIndiceColor(String codigo);
void revisarBotones();
void revisarNFC();

void setup() {
  Serial.begin(115200);
  delay(500);
  
  tiras.begin();
  tiras.setBrightness(255); 
  cambiarColorGradual(50, 50, 50, 40, 6); // Inicializar en IDLE (Blanco tenue de espera)
  ultimoEventoMs = millis();

  for(int i=0; i<12; i++) pinMode(botonesPrincipales[i], INPUT_PULLUP);
  for(int i=0; i<4; i++)  pinMode(botonesSecundarios[i], INPUT_PULLUP);

  Wire.begin(21, 22);

  nfc.begin();
  uint32_t versiondata = nfc.getFirmwareVersion();
  if (!versiondata) {
    Serial.println(F("❌ Error: PN532 no detectado"));
    while (1) delay(10); 
  }
  nfc.SAMConfig(); 
  Serial.println(F("--- ESP32 MAPA DE COLORES LISTO ---"));
}

void loop() {
  revisarBotones();
  revisarNFC();

  // Temporizador para regresar a IDLE (Blanco tenue)
  if (millis() - ultimoEventoMs > TIEMPO_IDLE_MS) {
    if (rojoActual != 50 || verdeActual != 50 || azulActual != 50) {
      cambiarColorGradual(50, 50, 50, 25, 8); 
    }
  }
}

void revisarBotones() {
  unsigned long tiempoActual = millis();

  // Revisar bloque principal
  for (int i = 0; i < 12; i++) {
    if (digitalRead(botonesPrincipales[i]) == LOW) {
      if (tiempoActual - ultimoDebounceBotones[i] > TIEMPO_DEBOUNCE) {
        Serial.print(F("BOTON_P:"));
        Serial.println(i + 1);
        
        // Obtener el color asignado a este botón principal
        uint8_t r = PALETA_PRINCIPALES[i][0];
        uint8_t g = PALETA_PRINCIPALES[i][1];
        uint8_t b = PALETA_PRINCIPALES[i][2];
        
        cambiarColorGradual(r, g, b, 12, 4); // Reacción de color instantánea
        ultimoEventoMs = millis();
        ultimoDebounceBotones[i] = tiempoActual;
        break;
      }
    }
  }

  // Revisar bloque secundario
  for (int i = 0; i < 4; i++) {
    if (digitalRead(botonesSecundarios[i]) == LOW) {
      if (tiempoActual - ultimoDebounceBotones[i + 12] > TIEMPO_DEBOUNCE) {
        Serial.print(F("BOTON_S:"));
        Serial.println(i + 1);
        
        // Obtener el color asignado a este botón secundario
        uint8_t r = PALETA_SECUNDARIOS[i][0];
        uint8_t g = PALETA_SECUNDARIOS[i][1];
        uint8_t b = PALETA_SECUNDARIOS[i][2];
        
        cambiarColorGradual(r, g, b, 12, 4); // Reacción de color instantánea
        ultimoEventoMs = millis();
        ultimoDebounceBotones[i + 12] = tiempoActual;
        break;
      }
    }
  }
}

void revisarNFC() {
  uint8_t success;
  uint8_t uid[] = { 0, 0, 0, 0, 0, 0, 0 };  
  uint8_t uidLength;                        
  
  success = nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLength, 50);
  
  if (success) {
    uint8_t data[16];
    String codigoMoneda = "";
    
    if (nfc.mifareclassic_ReadDataBlock(4, data)) {
      for (int i = 0; i < 16; i++) {
        if (data[i] >= 32 && data[i] <= 126) { 
          codigoMoneda += (char)data[i];
        }
      }
      codigoMoneda.trim(); 
    } 
    
    if (codigoMoneda.length() == 0) {
      for (uint8_t i = 0; i < uidLength; i++) {
        if (uid[i] < 0x10) codigoMoneda += "0";
        codigoMoneda += String(uid[i], HEX);
      }
    }

    Serial.print(F("NFC:"));
    Serial.println(codigoMoneda);
    
    // Las monedas mantienen su lógica Hash usando su propia paleta (PALETA_NFC)
    int indiceColor = obtenerIndiceColor(codigoMoneda);
    uint8_t rDestino = PALETA_NFC[indiceColor][0];
    uint8_t gDestino = PALETA_NFC[indiceColor][1];
    uint8_t bDestino = PALETA_NFC[indiceColor][2];
    
    cambiarColorGradual(rDestino, gDestino, bDestino, 15, 5); 
    
    delay(2000); // Sostener el color de la moneda 2 segundos
    ultimoEventoMs = millis(); 
  }
}

void cambiarColorGradual(uint8_t rDestino, uint8_t gDestino, uint8_t bDestino, int pasos, int esperaMs) {
  for (int i = 0; i <= pasos; i++) {
    uint8_t rIntermedio = rojoActual + ((rDestino - rojoActual) * i / pasos);
    uint8_t gIntermedio = verdeActual + ((gDestino - verdeActual) * i / pasos);
    uint8_t bIntermedio = azulActual + ((bDestino - azulActual) * i / pasos);
    
    uint32_t colorPaso = tiras.Color(rIntermedio, gIntermedio, bIntermedio);
    
    for (int j = 0; j < NUM_LEDS; j++) {
      tiras.setPixelColor(j, colorPaso);
    }
    tiras.show();
    delay(esperaMs);
  }
  rojoActual = rDestino;
  verdeActual = gDestino;
  azulActual = bDestino;
}

int obtenerIndiceColor(String codigo) {
  unsigned int sumaAscii = 0;
  for (unsigned int i = 0; i < codigo.length(); i++) {
    sumaAscii += (int)codigo[i];
  }
  return sumaAscii % 16;
}