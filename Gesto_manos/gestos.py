import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import time
import urllib.request
import os
import threading
from queue import Queue
from collections import deque

# ==================== CONFIGURACIÓN GLOBAL ====================
class SharedResources:
    """Clase para manejar recursos compartidos entre threads"""
    def __init__(self):
        # Mutex para proteger el frame actual
        self.frame_lock = threading.Lock()
        
        # Semáforo para controlar el flujo de procesamiento
        # Permite hasta 1 frame en espera de procesamiento
        self.processing_semaphore = threading.Semaphore(1)
        
        # Datos compartidos (sección crítica)
        self.current_frame = None
        self.processed_frame = None
        self.gesture_results = None
        
        # Flags de control
        self.running = True
        self.new_frame_available = False
        
        # Estadísticas
        self.stats_lock = threading.Lock()
        self.frames_captured = 0
        self.frames_processed = 0
        self.capture_fps = 0.0
        self.processing_fps = 0.0
        
    def set_frame(self, frame):
        """Guarda un nuevo frame capturado (sección crítica)"""
        with self.frame_lock:  # MUTEX: Entrada a sección crítica
            self.current_frame = frame.copy()
            self.new_frame_available = True
            self.frames_captured += 1
            
    def get_frame(self):
        """Obtiene el frame actual para procesamiento (sección crítica)"""
        with self.frame_lock:  # MUTEX: Entrada a sección crítica
            if self.current_frame is not None:
                frame = self.current_frame.copy()
                self.new_frame_available = False
                return frame
        return None
    
    def set_results(self, frame, results):
        """Guarda los resultados del procesamiento (sección crítica)"""
        with self.frame_lock:  # MUTEX: Entrada a sección crítica
            self.processed_frame = frame
            self.gesture_results = results
            self.frames_processed += 1
    
    def get_results(self):
        """Obtiene los resultados para visualización (sección crítica)"""
        with self.frame_lock:  # MUTEX: Entrada a sección crítica
            return self.processed_frame, self.gesture_results
    
    def update_stats(self, capture_fps=None, processing_fps=None):
        """Actualiza estadísticas (sección crítica)"""
        with self.stats_lock:  
            if capture_fps is not None:
                self.capture_fps = capture_fps
            if processing_fps is not None:
                self.processing_fps = processing_fps
    
    def get_stats(self):
        """Obtiene estadísticas (sección crítica)"""
        with self.stats_lock:  
            return {
                'frames_captured': self.frames_captured,
                'frames_processed': self.frames_processed,
                'capture_fps': self.capture_fps,
                'processing_fps': self.processing_fps
            }

def download_model():
    """Descarga el modelo de reconocimiento de gestos si no existe"""
    model_path = "gesture_recognizer.task"
    
    if not os.path.exists(model_path):
        print("Descargando modelo de reconocimiento de gestos...")
        model_url = "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/latest/gesture_recognizer.task"
        urllib.request.urlretrieve(model_url, model_path)
        print("Modelo descargado exitosamente!")
    
    return model_path

def draw_landmarks_on_image(rgb_image, detection_result):
    """Dibuja los landmarks de las manos en la imagen"""
    hand_landmarks_list = detection_result.hand_landmarks
    annotated_image = rgb_image.copy()
    h, w, _ = annotated_image.shape
    
    FINGER_COLORS = [
        (255, 0, 0),    # Pulgar - Rojo
        (0, 255, 0),    # Índice - Verde
        (0, 0, 255),    # Medio - Azul
        (255, 255, 0),  # Anular - Amarillo
        (255, 0, 255)   # Meñique - Magenta
    ]
    
    # Conexiones de la mano
    HAND_CONNECTIONS = [
        (0, 1), (1, 2), (2, 3), (3, 4),  # Pulgar
        (0, 5), (5, 6), (6, 7), (7, 8),  # Índice
        (0, 9), (9, 10), (10, 11), (11, 12),  # Medio
        (0, 13), (13, 14), (14, 15), (15, 16),  # Anular
        (0, 17), (17, 18), (18, 19), (19, 20),  # Meñique
        (5, 9), (9, 13), (13, 17)  # Palma
    ]
    
    for hand_landmarks in hand_landmarks_list:
        # Dibujar las conexiones
        for connection in HAND_CONNECTIONS:
            start_idx = connection[0]
            end_idx = connection[1]
            
            start_point = hand_landmarks[start_idx]
            end_point = hand_landmarks[end_idx]
            
            start_x = int(start_point.x * w)
            start_y = int(start_point.y * h)
            end_x = int(end_point.x * w)
            end_y = int(end_point.y * h)
            
            # Color basado en el dedo
            if end_idx <= 4:
                color = FINGER_COLORS[0]
            elif end_idx <= 8:
                color = FINGER_COLORS[1]
            elif end_idx <= 12:
                color = FINGER_COLORS[2]
            elif end_idx <= 16:
                color = FINGER_COLORS[3]
            else:
                color = FINGER_COLORS[4]
            
            cv2.line(annotated_image, (start_x, start_y), (end_x, end_y), color, 2)
        
        # Dibujar los puntos
        for idx, landmark in enumerate(hand_landmarks):
            x = int(landmark.x * w)
            y = int(landmark.y * h)
            
            if idx <= 4:
                color = FINGER_COLORS[0]
            elif idx <= 8:
                color = FINGER_COLORS[1]
            elif idx <= 12:
                color = FINGER_COLORS[2]
            elif idx <= 16:
                color = FINGER_COLORS[3]
            else:
                color = FINGER_COLORS[4]
            
            cv2.circle(annotated_image, (x, y), 5, color, -1)
            cv2.circle(annotated_image, (x, y), 5, (255, 255, 255), 1)
    
    return annotated_image

# ==================== THREAD 1: CAPTURA DE FRAMES ====================
def capture_thread(shared_resources, camera_id=0):
    """Thread para captura continua de frames desde la cámara"""
    print(f"[THREAD-CAPTURE] Iniciando captura desde cámara {camera_id}...")
    
    cap = cv2.VideoCapture(camera_id)
    
    if not cap.isOpened():
        print("[THREAD-CAPTURE] ERROR: No se pudo abrir la cámara")
        shared_resources.running = False
        return
    
    print("[THREAD-CAPTURE] Cámara abierta exitosamente")
    
    prev_time = time.time()
    fps_counter = 0
    
    while shared_resources.running:
        ret, frame = cap.read()
        
        if not ret:
            print("[THREAD-CAPTURE] ERROR: No se pudo leer el frame")
            break
        
        frame = cv2.flip(frame, 1)
        
        if shared_resources.processing_semaphore.acquire(blocking=False):
            try:
                shared_resources.set_frame(frame)
            finally:
                pass
        
        # Calcular FPS de captura
        fps_counter += 1
        curr_time = time.time()
        if curr_time - prev_time >= 1.0:
            capture_fps = fps_counter / (curr_time - prev_time)
            shared_resources.update_stats(capture_fps=capture_fps)
            fps_counter = 0
            prev_time = curr_time
        
        time.sleep(0.001)
    
    cap.release()
    print("[THREAD-CAPTURE] Thread de captura finalizado")

def processing_thread(shared_resources, recognizer):
    """Thread para procesar gestos en los frames capturados"""
    print("[THREAD-PROCESS] Iniciando procesamiento de gestos...")
    
    prev_time = time.time()
    fps_counter = 0
    
    gesture_display = {
        "Thumb_Up": "Pulgar Arriba",
        "Thumb_Down": "Pulgar Abajo",
        "Victory": "Victoria",
        "Closed_Fist": "Mano Cerrado",
        "Open_Palm": "Palma Abierta",
        "Pointing_Up": "Apuntando Arriba",
        "ILoveYou": "Te Amo",
        "None": "Ninguno"
    }
    
    while shared_resources.running:
        # Esperar a que haya un nuevo frame disponible
        if not shared_resources.new_frame_available:
            time.sleep(0.005)
            continue
        
        # SECCIÓN CRÍTICA: Obtener frame para procesar
        frame = shared_resources.get_frame()
        
        if frame is None:
            # SEMÁFORO: Liberar si no hay frame
            shared_resources.processing_semaphore.release()
            continue
        
        try:
            # Convertir BGR a RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Crear el objeto de imagen de MediaPipe
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            # Calcular timestamp en milisegundos
            timestamp_ms = int(time.time() * 1000)
            
            # Reconocer gestos
            recognition_result = recognizer.recognize_for_video(mp_image, timestamp_ms)
            
            # Dibujar landmarks en el frame
            if recognition_result.hand_landmarks:
                annotated_image = draw_landmarks_on_image(rgb_frame, recognition_result)
                frame = cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR)
            
            # Preparar información de gestos
            gesture_info = []
            if recognition_result.hand_landmarks:
                for hand_idx in range(len(recognition_result.hand_landmarks)):
                    hand_landmarks = recognition_result.hand_landmarks[hand_idx]
                    
                    if recognition_result.gestures and hand_idx < len(recognition_result.gestures):
                        gesture = recognition_result.gestures[hand_idx][0]
                        gesture_name = gesture.category_name
                        gesture_score = gesture.score
                        
                        handedness = "Desconocida"
                        if recognition_result.handedness and hand_idx < len(recognition_result.handedness):
                            hand_label = recognition_result.handedness[hand_idx][0].category_name
                            handedness = "Derecha" if hand_label == "Left" else "Izquierda"
                        
                        gesture_text = gesture_display.get(gesture_name, gesture_name)
                        
                        gesture_info.append({
                            'text': gesture_text,
                            'hand': handedness,
                            'score': gesture_score,
                            'landmark': hand_landmarks[0]
                        })
            
            # SECCIÓN CRÍTICA: Guardar resultados procesados
            shared_resources.set_results(frame, gesture_info)
            
            # Calcular FPS de procesamiento
            fps_counter += 1
            curr_time = time.time()
            if curr_time - prev_time >= 1.0:
                processing_fps = fps_counter / (curr_time - prev_time)
                shared_resources.update_stats(processing_fps=processing_fps)
                fps_counter = 0
                prev_time = curr_time
                
        except Exception as e:
            print(f"[THREAD-PROCESS] ERROR en procesamiento: {e}")
        finally:
            # SEMÁFORO: Liberar para permitir nueva captura
            shared_resources.processing_semaphore.release()
    
    print("[THREAD-PROCESS] Thread de procesamiento finalizado")

# ==================== MAIN: VISUALIZACIÓN ====================
def main():
    print("=" * 60)
    print("Detector de Gestos ")
    print("=" * 60)
    print("Arquitectura:")
    print("  🧵 Hilo 1: Captura de frames")
    print("  🧵 Hilo 2: Procesamiento de gestos")
    print("  🔒 Mutex: Protección de recursos compartidos")
    print("  🚦 Semáforo: Sincronización entre hilos")
    print("  🔐 Sección Crítica: Acceso exclusivo a datos")
    print("=" * 60)
    print("Gestos reconocidos:")
    print("  - Pulgar Arriba, Pulgar Abajo, Victoria")
    print("  - Puño Cerrado, Palma Abierta, Apuntando Arriba")
    print("  - Te Amo")
    print("=" * 60)
    print("Presiona 'q' para salir")
    print()
    
    # Descargar el modelo
    model_path = download_model()
    
    # Configurar el reconocedor de gestos
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.GestureRecognizerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5
    )
    recognizer = vision.GestureRecognizer.create_from_options(options)
    
    # Crear recursos compartidos
    shared_resources = SharedResources()
    
    # Crear y arrancar threads
    thread_capture = threading.Thread(
        target=capture_thread, 
        args=(shared_resources, 0),
        name="CaptureThread"
    )
    
    thread_process = threading.Thread(
        target=processing_thread, 
        args=(shared_resources, recognizer),
        name="ProcessingThread"
    )
    
    print("\n[MAIN] Iniciando threads...")
    thread_capture.start()
    thread_process.start()
    print("[MAIN] Threads iniciados\n")
    
    # Loop principal de visualización
    while shared_resources.running:
        # SECCIÓN CRÍTICA: Obtener frame procesado y resultados
        processed_frame, gesture_info = shared_resources.get_results()
        
        if processed_frame is not None:
            frame = processed_frame.copy()
            h, w, _ = frame.shape
            
            # Obtener estadísticas
            stats = shared_resources.get_stats()
            
            # Mostrar información de threads
            y_pos = 30
            cv2.putText(frame, f"FPS Captura: {stats['capture_fps']:.1f}", 
                       (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            y_pos += 30
            cv2.putText(frame, f"FPS Proceso: {stats['processing_fps']:.1f}", 
                       (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            y_pos += 30
            cv2.putText(frame, f"Capturados: {stats['frames_captured']}", 
                       (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            y_pos += 30
            cv2.putText(frame, f"Procesados: {stats['frames_processed']}", 
                       (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            # Mostrar información de gestos detectados
            if gesture_info:
                num_hands = len(gesture_info)
                cv2.putText(frame, f"Manos: {num_hands}", (10, 150), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                
                for info in gesture_info:
                    hand_x = int(info['landmark'].x * w)
                    hand_y = int(info['landmark'].y * h)
                    
                    text = info['text']
                    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
                    
                    # Dibujar rectángulo de fondo
                    cv2.rectangle(frame, 
                                 (hand_x - 10, hand_y - text_size[1] - 35),
                                 (hand_x + text_size[0] + 10, hand_y - 15),
                                 (0, 0, 0), -1)
                    
                    # Mostrar el gesto
                    cv2.putText(frame, text, 
                               (hand_x, hand_y - 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    
                    # Mostrar info adicional
                    info_text = f"{info['hand']} ({info['score']:.2f})"
                    cv2.putText(frame, info_text, 
                               (hand_x, hand_y + 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Mostrar el frame
            cv2.imshow('Detector de Gestos ', frame)
        
        # Verificar si se presiona 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\n[MAIN] Señal de salida recibida")
            shared_resources.running = False
            break
    
    # Esperar a que los threads terminen
    print("[MAIN] Esperando finalización de threads...")
    thread_capture.join(timeout=2)
    thread_process.join(timeout=2)
    
    # Limpiar
    cv2.destroyAllWindows()
    recognizer.close()
    
    # Mostrar estadísticas finales
    final_stats = shared_resources.get_stats()
    print("\n" + "=" * 60)
    print("ESTADÍSTICAS FINALES:")
    print(f"  Frames capturados: {final_stats['frames_captured']}")
    print(f"  Frames procesados: {final_stats['frames_processed']}")
    print(f"  FPS de captura: {final_stats['capture_fps']:.2f}")
    print(f"  FPS de procesamiento: {final_stats['processing_fps']:.2f}")
    print("=" * 60)
    print("[MAIN] Programa finalizado")

if __name__ == "__main__":
    main()
