import os
import sys
import serial
import threading
import pygame
import cv2
import numpy as np

#TenS09 Manzana Envenenada
#TenS01 Boing
#TenS04 Polaris
#TenS05 Calderitos
#04539d59380289 Crujiente tentacion
#TenS10 Embrujos
#TenT19 Vaquita
#TenT13 Luna Llena
#TenT12 Perlas Magicas
#TenT08 Eclipse 


# --- CONFIGURACIÓN ---
PUERTO_SERIAL = '/dev/ttyACM0'
BAUD_RATE = 115200

# Pantalla 1080p en Vertical
PANTALLA_ANCHO = 1080   
PANTALLA_ALTO = 1920
TIEMPO_CARRUSEL_MS = 5000  # 5 segundos por imagen en IDLE

# --- ESTADOS ---a nose n
ESTADO_IDLE = "IDLE"
ESTADO_REPRODUCION = "REPRODUCIENDO"

class TotemInteractivoUnicoVideo:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        
        # Modo pantalla completa para el tótem
        INDICE_MONITOR = 1 
        
        # Pasamos el parámetro display=INDICE_MONITOR
        self.pantalla = pygame.display.set_mode(
            (PANTALLA_ANCHO, PANTALLA_ALTO), 
            pygame.FULLSCREEN, 
            display=INDICE_MONITOR
        )
        self.reloj = pygame.time.Clock()
        
        self.estado = ESTADO_IDLE
        self.moneda_detectada = None
        
        # 1. Cargar Carrusel de Imágenes
        self.lista_imagenes = []
        self.indice_carrusel = 0
        self.ultimo_cambio_carrusel = pygame.time.get_ticks()
        self.cargar_carrusel()
        
        # 2. Cargar Video Único Global
        self.ruta_video_unico = os.path.join(".", "mirror_face.mp4")
        self.video_cap = None
        self.audio_canal = None
        self.verificar_video_principal()
        
        # 3. Hilo Serial para Arduino Uno
        self.hilo_serial = threading.Thread(target=self.escuchar_arduino, daemon=True)
        self.hilo_serial.start()

    def verificar_video_principal(self):
        """Asegura que el video base exista antes de iniciar"""
        if not os.path.exists(self.ruta_video_unico):
            print(f"❌ Error Crítico: No se encontró el video base en '{self.ruta_video_unico}'")
            pygame.quit()
            sys.exit(1)

    def cargar_carrusel(self):
        """Carga y escala las imágenes de espera a vertical"""
        ruta_carrusel = os.path.join(".", "carrusel")
        if os.path.exists(ruta_carrusel):
            for archivo in sorted(os.listdir(ruta_carrusel)):
                if archivo.lower().endswith(('.png', '.jpg', '.jpeg')):
                    img = pygame.image.load(os.path.join(ruta_carrusel, archivo))
                    img = pygame.transform.scale(img, (PANTALLA_ANCHO, PANTALLA_ALTO))
                    self.lista_imagenes.append(img)
        
        if not self.lista_imagenes:
            superficie_vacia = pygame.Surface((PANTALLA_ANCHO, PANTALLA_ALTO))
            superficie_vacia.fill((20, 20, 20))
            self.lista_imagenes.append(superficie_vacia)

    def iniciar_orden(self, id_moneda):
        """Intenta disparar el audio específico. Si no existe, ignora la moneda y sigue en IDLE"""
        ruta_audio = os.path.join(".", "audios", f"{id_moneda}.wav")
        
        # --- FILTRO DE AUDIO EXISTENTE ---
        if not os.path.exists(ruta_audio):
            print(f"⚠️ Moneda detectada ({id_moneda}), pero no tiene audio asignado. Ignorando...")
            # Al no cambiar self.estado a ESTADO_REPRODUCION, el carrusel sigue corriendo sin notar el cambio
            return 
        
        # Si el audio sí existe, procedemos con la interrupción normal:
        pygame.mixer.stop()
        
        # Reproducir el sonido correspondiente
        sound = pygame.mixer.Sound(ruta_audio)
        self.audio_canal = sound.play()

        # Inicializar o reiniciar el puntero del video único al fotograma 0
        if self.video_cap:
            self.video_cap.release()
        self.video_cap = cv2.VideoCapture(self.ruta_video_unico)
        
        # Cambiamos el estado para que el bucle empiece a dibujar el video
        self.estado = ESTADO_REPRODUCION

    def escuchar_arduino(self):
        """Monitorea el puerto serial de fondo"""
        try:
            arduino = serial.Serial(PUERTO_SERIAL, BAUD_RATE, timeout=1)
            print(" Conectado al Arduino Uno. Esperando lecturas NFC...")
        except Exception as e:
            print(f"❌ Error al abrir puerto serial {PUERTO_SERIAL}: {e}")
            return

        while True:
            try:
                if arduino.in_waiting > 0:
                    linea = arduino.readline().decode('utf-8', errors='ignore').strip()
                    if linea.startswith("DATA:"):
                        partes = linea.split(",")
                        if len(partes) >= 3:
                            # Capturamos el ID de la moneda
                            self.moneda_detectada = partes[2]
            except Exception as e:
                print(f"Error en lectura serial: {e}")

    def actualizar(self):
        """Manejo de tiempos y transiciones de estado"""
        tiempo_actual = pygame.time.get_ticks()
        
        # Si el hilo serial detectó una moneda, interrumpimos de inmediato
        if self.moneda_detectada:
            id_trabajo = self.moneda_detectada
            self.moneda_detectada = None
            self.iniciar_orden(id_trabajo)

        if self.estado == ESTADO_IDLE:
            if tiempo_actual - self.ultimo_cambio_carrusel > TIEMPO_CARRUSEL_MS:
                self.indice_carrusel = (self.indice_carrusel + 1) % len(self.lista_imagenes)
                self.ultimo_cambio_carrusel = tiempo_actual

        elif self.estado == ESTADO_REPRODUCION:
            # En cuanto el canal de audio se libere (termine de hablar), volvemos a IDLE
            if self.audio_canal and not self.audio_canal.get_busy():
                if self.video_cap:
                    self.video_cap.release()
                    self.video_cap = None
                self.estado = ESTADO_IDLE
                self.ultimo_cambio_carrusel = pygame.time.get_ticks()

    def dibujar(self):
        """Dibuja los elementos en la pantalla vertical"""
        if self.estado == ESTADO_IDLE:
            imagen = self.lista_imagenes[self.indice_carrusel]
            self.pantalla.blit(imagen, (0, 0))
            
        elif self.estado == ESTADO_REPRODUCION:
            if self.video_cap and self.video_cap.isOpened():
                ret, frame = self.video_cap.read()
                if ret:
                    # Formatear frame de OpenCV a Pygame
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Rotar 90° para visualización vertical física (ajustar según montaje)
                    frame = cv2.resize(frame, (PANTALLA_ANCHO, PANTALLA_ALTO))
                    
                    frame = np.rot90(frame)
                    frame = cv2.flip(frame, 0)
                    
                    superficie_video = pygame.surfarray.make_surface(frame)
                    self.pantalla.blit(superficie_video, (0, 0))
                else:
                    # Loop: Si el video termina pero el audio sigue hablandon, rebobinamos a cero
                    self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            else:
                self.pantalla.fill((0, 0, 0))

        pygame.display.flip()

    def ejecutar(self):
        """Bucle de ejecución principal de Pygame"""
        ejecutando = True
        while ejecutando:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    ejecutando = False
                elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                    ejecutando = False
            
            self.actualizar()
            self.dibujar()
            self.reloj.tick(30) # Sincronizado a 30 fotogramas por segundo
            
        if self.video_cap:
            self.video_cap.release()
        pygame.quit()

if __name__ == "__main__":
    totem = TotemInteractivoUnicoVideo()
    totem.ejecutar()