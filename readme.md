# Primer Punto

# Segundo punto (Juego de Mario)

Implementar un videojuego de plataformas clásico similar a Mario Bros aplicando los conceptos de programación concurrente como hilos, mutex, semáforos, secciones críticas y desplegarlo en un entorno contenedorizado con Docker.

## Detalles

El proyecto se desarrolló en Python utilizando la librería Pygame, que permite gestionar gráficos, eventos y animaciones.

#### Mecánicas del juego:

- Movimiento lateral del jugador (izquierda, derecha y salto).

- Colisiones con plataformas, enemigos y monedas.

- Enemigos que patrullan automáticamente las plataformas.

- Recolección de monedas y aumento de puntuación.

- Sistema de vidas, puntaje e invulnerabilidad temporal.

Se implementaron varios hilos que trabajan simultáneamente para manejar diferentes aspectos del juego sin bloquear el flujo principal.

- PlatformGen: Este es el encargado de generar nuevas plataformas y limpia las antiguas
- CoinCollector : Detecta cuando hay colisiones con monedas
- EnemyManager : Controla movimiento, generación y colisiones de enemigos
- EventProcessor : Gestiona eventos como golpes, monedas o muertes

Tambien se utilizaron diferentes mecanismos como Mutex que protegen variables compartidas como la posición, vidas, plataformas y enemigos. Al igual que semáforos que limitaban la cantidad máxima de enemigos simultáneos. Por ultimo se implemento cola de eventos comunica de forma segura entre hilos los sucesos del juego.

## Contenedor Dockerfile

Para garantizar la portabilidad y compatibilidad del juego, se creó un contenedor Docker con todas las dependencias necesarias.

Con nuestro archivo dockerfile ya creado lo que se hace es crear la imagen de la siguiente manera:

```

docker build -t mario-threading .

```

Ya creada la imagen lo siguiente que se hace es ejecutar el juego con interfaz grafica.

```

xhost +local:docker
docker run -it --rm \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  mario-threading

```
# Tercer punto (Gesto manos)

Este punto se implemento un detector de gestos de mano en tiempo real utilizando MediaPipe, OpenCV y Python, con una arquitectura concurrente basada en hilos (threads), mutex, semáforos y secciones críticas.
Además, se ejecuta dentro de un contenedor Docker, lo que garantiza portabilidad y aislamiento del entorno.

## Objetivo 
EL objetivo de este punto es crear un sistema capaz de capturar video desde la cámara en tiempo real y procesar los frames para detectar gestos de mano mediante MediaPipe Gesture Recognizer. Luego mostrar en pantalla los gestos reconocidos y los puntos de referencia (landmarks) de cada mano.

## Desarrollo del sistema 

El sistema está dividido en dos hilos principales y un conjunto de recursos compartidos protegidos por mecanismos de sincronización.

- Hilo 1: (capture_thread)

Este se encarga de leer los frames de la cámara continuamente.Cada frame capturado se guarda en una variable compartida. Despues utiliza un semáforo para controlar cuántos frames pueden estar en espera de procesamiento. Si el hilo de procesamiento está ocupado, descarta el frame para mantener la fluidez del video y por ultimo actualiza el contador de FPS de capturas

Este hilo trabaja de forma independiente, evitando que el procesamiento bloquee la cámara.

- Hilo 2: (processing_thread)

Este hilo se encarga de leer los frames capturados desde los recursos compartidos.Luego convierte las imágenes a formato RGB y las envía al modelo de MediaPipe Gesture Recognizer.Dibuja los puntos de referencia (landmarks) de cada mano detectada. Despues guarda los resultados procesados para que el hilo principal los muestre, por ultimo calcula los FPS del procesamiento.

Este hilo se ejecuta en paralelo al de captura, asegurando que el modelo procese datos constantemente sin detener la cámara.

## Mecanismos de sincronización:
En el sistema tambien se tubieron encuenta mecanismos de sincronizacion que cumplen una funcion especifica, el Mutex (threading.Lock)  evita que dos hilos modifiquen los mismos datos simultáneamente. Tambien se implento (threading.Semaphore(1)) que asegura que solo un frame se procese a la vez. Por ultimo se utilizo Sección Crítica en cualquier bloque with self.frame_lock donde se accede o modifica información compartida. Estos mecanismos previenen errores como condiciones de carrera y lecturas inconsistentes entre los hilos.

## Gestos reconocidos

El sistema reconoce automáticamente los siguientes gestos predeterminados del modelo de MediaPipe:

- Pulgar arriba 👍
- Pulgar abajo 👎
- Victoria ✌️
- Puño cerrado ✊
- Palma abierta ✋
- Apuntando arriba ☝️
- Te amo 🤟
- Ninguno (sin gesto detectado)

## Ejecución en Docker
Con nuestro archivo dockerfile ya creado lo que se hace es crear la imagen de la siguiente manera:

```
docker build -t gesto_manos .
```
Ejecutar el contenedor con acceso a cámara y entorno gráfico:

```
xhost +local:docker

docker run -it --rm \
  --device=/dev/video0:/dev/video0 \
  --env="DISPLAY=$DISPLAY" \
  --env="QT_X11_NO_MITSHM=1" \
  --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" \
  --privileged \
  gesto_manos
```


