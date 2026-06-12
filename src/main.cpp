#include <Arduino.h>
#include <Wire.h> 
#include <Adafruit_PN532.h>
#include <Adafruit_NeoPixel.h>

// --- CONFIGURACIÓN DE LOS LEDS ---
#define PIN_LEDS      2  
#define NUM_LEDS     30 

uint8_t rojoActual = 0, verdeActual = 0, azulActual = 0;

Adafruit_NeoPixel tiras(NUM_LEDS, PIN_LEDS, NEO_GRB + NEO_KHZ800);

// --- PALETA DE 16 COLORES EN MATRIZ (R, G, B) ---
const uint8_t PALETA_COLORES[16][3] = {
  {255, 0, 0},     // 0. Rojo Puro
  {255, 60, 0},    // 1. Naranja Intenso
  {255, 120, 0},   // 2. Ámbar / Dorado
  {255, 200, 0},   // 3. Amarillo Neón
  {120, 255, 0},   // 4. Verde Lima
  {0, 255, 0},     // 5. Verde Esmeralda
  {0, 255, 130},   // 6. Turquesa / Menta
  {0, 255, 255},   // 7. Cian / Celeste
  {0, 100, 255},   // 8. Azul Eléctrico
  {0, 0, 255},     // 9. Azul Marino Fuerte
  {70, 0, 255},    // 10. Índigo / Violeta
  {160, 0, 255},   // 11. Púrpura Vibrante
  {255, 0, 255},   // 12. Magenta / Fucsia
  {255, 0, 100},   // 13. Rosa Frambuesa
  {139, 69, 19},    // 14. Marrón Chocolate
  {230, 230, 250}  // 15. Blanco Lavanda
};

// --- CONFIGURACIÓN DEL NFC ---
Adafruit_PN532 nfc(-1, -1);

// --- CONFIGURACIÓN DE BOTONES ---
const int botonesPrincipales[12] = {3, 4, 5, 6, 7, 8, 9, 10, 11, A0, A1, A2};
const int botonesSecundarios[4]  = {12, 13, A3, 1}; 

// --- VARIABLES DE ESTADO ---
int seleccionPrincipal = -1;
int seleccionSecundaria = -1;
enum Estado { SELECCION_1, SELECCION_2, ESPERANDO_NFC };
Estado estadoActual = SELECCION_1;

// Prototipos obligatorios
void cambiarColorGradual(uint8_t rDestino, uint8_t gDestino, uint8_t bDestino, int pasos, int esperaMs);
int obtenerIndiceColor(String codigo);

void setup() {
  Serial.begin(115200);
  
  // Inicializar Tiras LED
  tiras.begin();
  cambiarColorGradual(50, 50, 50, 40, 10); // Luz de espera blanca tenue

  // Inicializar Botones
  for(int i=0; i<12; i++) pinMode(botonesPrincipales[i], INPUT_PULLUP);
  for(int i=0; i<4; i++)  pinMode(botonesSecundarios[i], INPUT_PULLUP);

  // Inicializar NFC
  nfc.begin();
  uint32_t versiondata = nfc.getFirmwareVersion();
  if (!versiondata) {
    Serial.println(F("Error: No se encontro el modulo PN532"));
    while (1); 
  } else {
    Serial.println(F("NFC iniciado"));
  }
  nfc.SAMConfig(); 
}

void loop() {
  switch (estadoActual) {
    
    case SELECCION_1:
      for (int i = 0; i < 12; i++) {
        if (digitalRead(botonesPrincipales[i]) == LOW) { 
          Serial.println(F("Boton presionado"));
          seleccionPrincipal = i + 1;
          cambiarColorGradual(0, 0, 255, 50, 10); // Azul de transición
          delay(300); 
          estadoActual = SELECCION_2;
          break;
        }
      }
      break;

    case SELECCION_2:
      for (int i = 0; i < 4; i++) {
        if (digitalRead(botonesSecundarios[i]) == LOW) {
          Serial.println(F("Boton presionado"));
          seleccionSecundaria = i + 1;
          cambiarColorGradual(0, 255, 0, 50, 10); // Verde de transición
          delay(300);
          estadoActual = ESPERANDO_NFC;
          break;
        }
      }
      break;

    case ESPERANDO_NFC:
      uint8_t success;
      uint8_t uid[] = { 0, 0, 0, 0, 0, 0, 0 };  
      uint8_t uidLength;                        
      
      success = nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLength, 300);
      
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
        } else {
          for (uint8_t i = 0; i < uidLength; i++) {
            codigoMoneda += String(uid[i], HEX);
          }
        }

        // --- REPORTE SERIAL ---
        Serial.print(F("DATA:"));
        Serial.print(seleccionPrincipal);
        Serial.print(F(","));
        Serial.print(seleccionSecundaria);
        Serial.print(F(","));
        Serial.println(codigoMoneda);
        
        // --- ASIGNACIÓN DE COLOR SEGÚN LA MONEDA ---
        int indiceColor = obtenerIndiceColor(codigoMoneda);
        uint8_t rDestino = PALETA_COLORES[indiceColor][0];
        uint8_t gDestino = PALETA_COLORES[indiceColor][1];
        uint8_t bDestino = PALETA_COLORES[indiceColor][2];
        
        // 1. Destello rápido en el color único asignado a esa moneda para celebrar el éxito
        cambiarColorGradual(rDestino, gDestino, bDestino, 20, 8); 
        delay(1500); // Mantenemos el color encendido mientras el video/audio arranca en Python
        
        // 2. Reiniciamos variables y regresamos la tira led al color base de espera (IDLE)
        seleccionPrincipal = -1;
        seleccionSecundaria = -1;
        cambiarColorGradual(50, 50, 50, 40, 10); 
        estadoActual = SELECCION_1;
      }
      break;
  }
}

// --- FUNCIÓN DE TRANSICIÓN SUAVE (FADE) ---
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

// --- ALGORITMO DE HASHING PARA INDEXAR EL COLOR ---
int obtenerIndiceColor(String codigo) {
  unsigned int sumaAsccii = 0;
  for (unsigned int i = 0; i < codigo.length(); i++) {
    sumaAsccii += (int)codigo[i]; // Sumamos el valor numérico de cada caracter del String
  }
  return sumaAsccii % 16; // El residuo nos asegura un índice válido estricto entre 0 y 15
}