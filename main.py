import os
import sys
import serial
import threading
import pygame
import cv2
import numpy as np

# Importación explícita del módulo de video experimental de SDL2 en Pygame
import pygame._sdl2.video as sdl2_video

# --- CONFIGURACIÓN ---
PUERTO_SERIAL = '/dev/ttyACM0'  # Ajusta según tu puerto real
BAUD_RATE = 115200

# Pantalla 1 (Tótem - Vertical)
PANTALLA_ANCHO = 1080   
PANTALLA_ALTO = 1920
TIEMPO_CARRUSEL_MS = 5000  

# Pantalla 0 (Operador - Horizontal)
INFO_ANCHO = 1920
INFO_ALTO = 1080

ESTADO_IDLE = "IDLE"
ESTADO_REPRODUCION = "REPRODUCIENDO"

class TotemInteractivoUnicoVideo:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        pygame.font.init()
        
        # Lock de seguridad para la sincronización de hilos (Serial -> Gráficos)
        self.lock = threading.Lock()
        
        # Variables de monitoreo que se mostrarán en el panel de control
        self.texto_zodiaco = "Ninguno"
        self.texto_modo = "Ninguno"
        self.texto_nfc = "Ninguna"
        
        self.fuente_grande = pygame.font.SysFont("Arial", 55, bold=True)
        self.fuente_media = pygame.font.SysFont("Arial", 40)
        
        # -----------------------------------------------------------------
        # CREACIÓN DE VENTANAS INDEPENDIENTES (Multimonitor nativo por hardware)
        # -----------------------------------------------------------------
        print("📺 Levantando entorno de ventanas independientes...")
        
        # VENTANA 1: El Tótem Vertical
        self.ventana_totem = sdl2_video.Window(
            "Tótem Vertical - Animación", 
            size=(PANTALLA_ANCHO, PANTALLA_ALTO),
            fullscreen=True
        )
        # Forzamos la posición física en el segundo monitor (Pixel 1920 en X)
        # NOTA: Si el tótem se queda en la de operador, cambia este valor a (-1080, 0)
        self.ventana_totem.position = (1920, 0) 
        
        self.renderer_totem = sdl2_video.Renderer(self.ventana_totem)
        self.pantalla_totem = pygame.Surface((PANTALLA_ANCHO, PANTALLA_ALTO))
        
        # VENTANA 2: Panel de Control Horizontal (Monitor principal del operador)
        self.ventana_info = sdl2_video.Window(
            "PANEL DE MONITOREO - BOTONES", 
            size=(INFO_ANCHO, INFO_ALTO)
        )
        # Forzamos la posición física en el monitor de inicio (Pixel 0 en X)
        self.ventana_info.position = (0, 0)
        
        self.renderer_info = sdl2_video.Renderer(self.ventana_info)
        self.pantalla_info = pygame.Surface((INFO_ANCHO, INFO_ALTO))
        
        self.reloj = pygame.time.Clock()
        self.estado = ESTADO_IDLE
        self.moneda_detectada = None
        
        # --- CARGA DE RECURSOS ---
        self.lista_imagenes = []
        self.indice_carrusel = 0
        self.ultimo_cambio_carrusel = pygame.time.get_ticks()
        self.cargar_carrusel()
        
        self.ruta_video_unico = os.path.join(".", "mirror_face.mp4")
        self.video_cap = None
        self.audio_canal = None
        self.verificar_video_principal()
        
        # Iniciar Hilo de escucha Serial asíncrono
        self.hilo_serial = threading.Thread(target=self.escuchar_arduino, daemon=True)
        self.hilo_serial.start()

    def verificar_video_principal(self):
        if not os.path.exists(self.ruta_video_unico):
            print(f"❌ Error Crítico: No se encontró el video base en '{self.ruta_video_unico}'")
            pygame.quit()
            sys.exit(1)

    def cargar_carrusel(self):
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
        ruta_audio = os.path.join(".", "audios", f"{id_moneda}.wav")
        if not os.path.exists(ruta_audio):
            print(f"⚠️ Moneda detectada ({id_moneda}), pero no tiene audio asignado. Ignorando...")
            return 
        
        pygame.mixer.stop()
        sound = pygame.mixer.Sound(ruta_audio)
        self.audio_canal = sound.play()

        if self.video_cap:
            self.video_cap.release()
        self.video_cap = cv2.VideoCapture(self.ruta_video_unico)
        self.estado = ESTADO_REPRODUCION

    def escuchar_arduino(self):
        try:
            arduino = serial.Serial(PUERTO_SERIAL, BAUD_RATE, timeout=1)
            print("🔌 Puerto Serial abierto de forma asíncrona. Escuchando eventos...")
        except Exception as e:
            print(f"❌ Error al abrir puerto serial {PUERTO_SERIAL}: {e}")
            return

        while True:
            try:
                if arduino.in_waiting > 0:
                    linea = arduino.readline().decode('utf-8', errors='ignore').strip()
                    
                    with self.lock:
                        if linea.startswith("ZODIACO:"):
                            self.texto_zodiaco = linea.replace("ZODIACO:", "")
                        elif linea.startswith("MODO:"):
                            self.texto_modo = linea.replace("MODO:", "")
                        elif linea.startswith("NFC:"):
                            self.texto_nfc = linea.replace("NFC:", "")
                            self.moneda_detectada = self.texto_nfc
            except Exception as e:
                print(f"Error en lectura serial: {e}")

    def actualizar(self):
        tiempo_actual = pygame.time.get_ticks()
        
        if self.moneda_detectada:
            id_trabajo = self.moneda_detectada
            self.moneda_detectada = None
            self.iniciar_orden(id_trabajo)

        if self.estado == ESTADO_IDLE:
            if tiempo_actual - self.ultimo_cambio_carrusel > TIEMPO_CARRUSEL_MS:
                self.indice_carrusel = (self.indice_carrusel + 1) % len(self.lista_imagenes)
                self.ultimo_cambio_carrusel = tiempo_actual

        elif self.estado == ESTADO_REPRODUCION:
            if self.audio_canal and not self.audio_canal.get_busy():
                if self.video_cap:
                    self.video_cap.release()
                    self.video_cap = None
                self.estado = ESTADO_IDLE
                self.ultimo_cambio_carrusel = pygame.time.get_ticks()

    def dibujar_totem(self):
        """Renderiza los gráficos dedicados a la pantalla del Tótem"""
        if self.estado == ESTADO_IDLE:
            imagen = self.lista_imagenes[self.indice_carrusel]
            self.pantalla_totem.blit(imagen, (0, 0))
            
        elif self.estado == ESTADO_REPRODUCION:
            if self.video_cap and self.video_cap.isOpened():
                ret, frame = self.video_cap.read()
                if ret:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame = cv2.resize(frame, (PANTALLA_ANCHO, PANTALLA_ALTO))
                    frame = np.rot90(frame)
                    frame = cv2.flip(frame, 0)
                    
                    superficie_video = pygame.surfarray.make_surface(frame)
                    self.pantalla_totem.blit(superficie_video, (0, 0))
                else:
                    self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            else:
                self.pantalla_totem.fill((0, 0, 0))

    def dibujar_info(self):
        """Renderiza los gráficos dedicados al panel del operador"""
        self.pantalla_info.fill((20, 24, 35))
        
        titulo = self.fuente_grande.render("SISTEMA DE MONITOREO EN VIVO - REPORTE DE BOTONES", True, (0, 255, 200))
        self.pantalla_info.blit(titulo, (80, 80))
        
        with self.lock:
            txt_zod = self.fuente_media.render(f"🔮 Signo Zodiacal Pulsado:  {self.texto_zodiaco}", True, (255, 255, 255))
            txt_mod = self.fuente_media.render(f"🎮 Modo Secundario Activo: {self.texto_modo}", True, (255, 215, 0))
            txt_nfc = self.fuente_media.render(f"🪙 ID Moneda NFC Detectada:  {self.texto_nfc}", True, (0, 191, 255))
            
        self.pantalla_info.blit(txt_zod, (80, 280))
        self.pantalla_info.blit(txt_mod, (80, 420))
        self.pantalla_info.blit(txt_nfc, (80, 560))
        
        txt_status = self.fuente_media.render(f"Estado del Renderizador: [{self.estado}]", True, (0, 255, 0) if self.estado == "IDLE" else (255, 69, 0))
        self.pantalla_info.blit(txt_status, (80, 800))

    def despachar_ventanas(self):
        """Vuelca de forma segura los búferes de Pygame hacia los Renderers de hardware de SDL2"""
        # Actualizar la textura y dibujar en la pantalla del Tótem
        textura_totem = sdl2_video.Texture.from_surface(self.renderer_totem, self.pantalla_totem)
        self.renderer_totem.clear()
        textura_totem.draw()
        self.renderer_totem.present()
        
        # Actualizar la textura y dibujar en el Panel de Información
        textura_info = sdl2_video.Texture.from_surface(self.renderer_info, self.pantalla_info)
        self.renderer_info.clear()
        textura_info.draw()
        self.renderer_info.present()

    def ejecutar(self):
        ejecutando = True
        while ejecutando:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    ejecutando = False
                elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                    ejecutando = False
            
            self.actualizar()
            
            # Dibujado independiente en los búferes lógicos
            self.dibujar_totem()
            self.dibujar_info()
            
            # Despacho síncrono a la GPU
            self.despachar_ventanas()
            
            self.reloj.tick(30) 
            
        if self.video_cap:
            self.video_cap.release()
        pygame.quit()

if __name__ == "__main__":
    totem = TotemInteractivoUnicoVideo()
    totem.ejecutar()