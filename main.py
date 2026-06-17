import os
import sys
import pygame
import cv2
import numpy as np

# --- CONFIGURACIÓN ---
# Pantalla 1 (Tótem - Vertical) -> AHORA A LA IZQUIERDA
PANTALLA_ANCHO = 766   
PANTALLA_ALTO = 1366
TIEMPO_CARRUSEL_MS = 5000  

# Pantalla 0 (Operador - Horizontal) -> AHORA A LA DERECHA
INFO_ANCHO = 1920
INFO_ALTO = 1080

ESTADO_IDLE = "IDLE"
ESTADO_REPRODUCION = "REPRODUCIENDO"

# --- PALETA DE COLORES MÍSTICA ---
COLOR_FONDO = (15, 12, 28)        # Negro/Morado profundo
COLOR_TARJETA = (32, 24, 54)      # Lila oscuro para los contenedores
COLOR_TEXTO = (240, 235, 255)     # Blanco místico / Lavanda claro
COLOR_BOTON = (74, 36, 122)       # Púrpura mágico
COLOR_BOTON_HOVER = (109, 44, 184)# Púrpura brillante
COLOR_BOTON_ACTIVO = (235, 94, 40)# Naranja místico (al reproducir)
COLOR_BORDE = (235, 94, 40)       # Naranja para contrastes y bordes

class TotemMisticoMac:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        pygame.font.init()
        
        # Fuentes místicas
        self.fuente_titulo = pygame.font.SysFont("Georgia", 48, bold=True)
        self.fuente_subtitulo = pygame.font.SysFont("Georgia", 24, italic=True)
        self.fuente_botones = pygame.font.SysFont("Arial", 22, bold=True)
        self.fuente_estado = pygame.font.SysFont("Courier New", 26, bold=True)
        
        # -----------------------------------------------------------------
        # ENTORNO GRÁFICO EXTENDIDO (Optimizando multi-monitor para Mac)
        # -----------------------------------------------------------------
        print("🔮 Desplegando Consola Alquímica en macOS (Tótem Izquierda)...")
        os.environ['SDL_VIDEO_WINDOW_POS'] = "0,0"
        
        self.ancho_total = INFO_ANCHO + PANTALLA_ANCHO
        self.alto_total = max(INFO_ALTO, PANTALLA_ALTO)
        
        self.pantalla_global = pygame.display.set_mode((self.ancho_total, self.alto_total), pygame.NOFRAME)
        pygame.display.set_caption("Consola de Control Alquímico")
        
        self.pantalla_info = pygame.Surface((INFO_ANCHO, INFO_ALTO))
        self.pantalla_totem = pygame.Surface((PANTALLA_ANCHO, PANTALLA_ALTO))
        
        self.reloj = pygame.time.Clock()
        self.estado = ESTADO_IDLE
        self.preparacion_activa = None
        
        # --- LISTA DE PREPARACIONES (Mapeo directo de tus audios) ---
        self.preparaciones = [
            "CalderitosMisticos", "CrujienteTentacio", "Eclipse", "Embrujo", "GomiBoing",
            "LunaLlena", "Manzana", "PerlasMagicas", "Polaris", "VaquitaEncantada"
        ]
        
        # Estructura para almacenar las áreas de click de los botones
        self.rects_botones = {}
        self.generar_layout_botones()
        
        # --- CARGA DE RECURSOS ---
        self.lista_imagenes = []
        self.indice_carrusel = 0
        self.ultimo_cambio_carrusel = pygame.time.get_ticks()
        self.cargar_carrusel()
        
        self.ruta_video_unico = os.path.join(".", "mirror_face.mp4")
        self.video_cap = None
        self.audio_canal = None
        self.verificar_video_principal()

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
            superficie_vacia.fill((20, 15, 30))
            self.lista_imagenes.append(superficie_vacia)

    def generar_layout_botones(self):
        """Calcula una cuadrícula equilibrada de 2 filas x 5 columnas para la pantalla de control"""
        columnas = 5
        filas = 2
        
        btn_ancho = 300
        btn_alto = 140
        espacio_x = 40
        espacio_y = 50
        
        # Centrar cuadrícula en la zona inferior de la pantalla de info de manera local
        inicio_x = (INFO_ANCHO - (columnas * btn_ancho + (columnas - 1) * espacio_x)) // 2
        inicio_y = 350 
        
        for i, prep in enumerate(self.preparaciones):
            col = i % columnas
            fila = i // columnas
            
            x = inicio_x + col * (btn_ancho + espacio_x)
            y = inicio_y + fila * (btn_alto + espacio_y)
            
            self.rects_botones[prep] = pygame.Rect(x, y, btn_ancho, btn_alto)

    def disparar_preparacion(self, nombre_prep):
        """Detiene lo anterior e inicia la reproducción sincronizada de audio + video"""
        ruta_audio = os.path.join(".", "audios", f"{nombre_prep}.wav")
        if not os.path.exists(ruta_audio):
            print(f"⚠️ No se encontró el archivo de audio en: {ruta_audio}")
            return
        
        pygame.mixer.stop()
        try:
            sound = pygame.mixer.Sound(ruta_audio)
            self.audio_canal = sound.play()
            self.preparacion_activa = nombre_prep
        except Exception as e:
            print(f"⚠️ Error al reproducir audio: {e}")
            return

        if self.video_cap:
            self.video_cap.release()
        self.video_cap = cv2.VideoCapture(self.ruta_video_unico)
        self.estado = ESTADO_REPRODUCION

    def actualizar(self):
        tiempo_actual = pygame.time.get_ticks()
        
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
                self.preparacion_activa = None
                self.ultimo_cambio_carrusel = pygame.time.get_ticks()

    def dibujar_info(self):
        """Dibuja el panel táctil místico para el operador"""
        self.pantalla_info.fill(COLOR_FONDO)
        
        # --- ENCABEZADO ---
        pygame.draw.line(self.pantalla_info, COLOR_BORDE, (50, 40), (INFO_ANCHO - 50, 40), 2)
        
        titulo = self.fuente_titulo.render("CONSOLA DE CONTROL ALQUÍMICO", True, COLOR_TEXTO)
        self.pantalla_info.blit(titulo, ((INFO_ANCHO - titulo.get_width()) // 2, 80))
        
        subtitulo = self.fuente_subtitulo.render("Selecciona un elixir para despertar el espejo mágico", True, COLOR_BORDE)
        self.pantalla_info.blit(subtitulo, ((INFO_ANCHO - subtitulo.get_width()) // 2, 160))
        
        # --- ÁREA DE BOTONES ---
        # Calcular posición del mouse relativa a la superficie local de info
        mouse_x, mouse_y = pygame.mouse.get_pos()
        mouse_pos_relativa = (mouse_x - PANTALLA_ANCHO, mouse_y)
        
        for prep, rect in self.rects_botones.items():
            # Determinar color según estado usando la posición corregida del mouse
            if self.preparacion_activa == prep:
                color_actual = COLOR_BOTON_ACTIVO
                borde_espesor = 4
            elif rect.collidepoint(mouse_pos_relativa):
                color_actual = COLOR_BOTON_HOVER
                borde_espesor = 2
            else:
                color_actual = COLOR_BOTON
                borde_espesor = 1
                
            pygame.draw.rect(self.pantalla_info, COLOR_TARJETA, rect.move(4, 4), border_radius=12)
            pygame.draw.rect(self.pantalla_info, color_actual, rect, border_radius=12)
            pygame.draw.rect(self.pantalla_info, COLOR_BORDE if color_actual != COLOR_BOTON else COLOR_TEXTO, rect, width=borde_espesor, border_radius=12)
            
            texto_formateado = "".join([" " + c if c.isupper() and i > 0 else c for i, c in enumerate(prep)])
            txt_surf = self.fuente_botones.render(texto_formateado, True, COLOR_TEXTO)
            
            txt_x = rect.x + (rect.width - txt_surf.get_width()) // 2
            txt_y = rect.y + (rect.height - txt_surf.get_height()) // 2
            self.pantalla_info.blit(txt_surf, (txt_x, txt_y))
            
        # --- BARRA DE ESTADO INFERIOR ---
        panel_estado_rect = pygame.Rect(100, 850, INFO_ANCHO - 200, 120)
        pygame.draw.rect(self.pantalla_info, COLOR_TARJETA, panel_estado_rect, border_radius=15)
        pygame.draw.rect(self.pantalla_info, COLOR_BORDE, panel_estado_rect, width=2, border_radius=15)
        
        msg_estado = f"ESTADO DEL ESPEJO: [{self.estado}]"
        if self.estado == ESTADO_REPRODUCION:
            msg_estado += f"  |  MANIFIESTO ACTIVO: {self.preparacion_activa.upper()}"
            
        color_msg = COLOR_BOTON_ACTIVO if self.estado == ESTADO_REPRODUCION else (0, 230, 150)
        txt_estado = self.fuente_estado.render(msg_estado, True, color_msg)
        self.pantalla_info.blit(txt_estado, (panel_estado_rect.x + 40, panel_estado_rect.y + (panel_estado_rect.height - txt_estado.get_height()) // 2))

    def dibujar_totem(self):
        """Renderiza los gráficos dedicados a la pantalla del Tótem Vertical"""
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
                self.pantalla_totem.fill((10, 8, 20))

    def despachar_ventanas(self):
        """Une ambas pantallas: Tótem a la izquierda (0,0), Operador a la derecha (PANTALLA_ANCHO,0)"""
        self.pantalla_global.blit(self.pantalla_totem, (0, 0))
        self.pantalla_global.blit(self.pantalla_info, (PANTALLA_ANCHO, 0))
        pygame.display.flip()

    def ejecutar(self):
        ejecutando = True
        while ejecutando:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    ejecutando = False
                elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                    ejecutando = False
                
                # Procesar clicks del mouse mapeados al panel del operador
                elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    pos_mouse = pygame.mouse.get_pos()
                    # Corregir X restando el ancho del Tótem para saber dónde hizo click en la superficie de info
                    pos_mouse_relativa = (pos_mouse[0] - PANTALLA_ANCHO, pos_mouse[1])
                    
                    for prep, rect in self.rects_botones.items():
                        if rect.collidepoint(pos_mouse_relativa):
                            print(f"🔮 Alquimia activada de forma manual: {prep}")
                            self.disparar_preparacion(prep)
                            break
            
            self.actualizar()
            self.dibujar_totem()
            self.dibujar_info()
            self.despachar_ventanas()
            
            self.reloj.tick(30) 
            
        if self.video_cap:
            self.video_cap.release()
        pygame.quit()

if __name__ == "__main__":
    totem = TotemMisticoMac()
    totem.ejecutar()