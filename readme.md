# Primer Punto

La idea es  implementar un análisis de emociones, el cual procese los comentarios de articulos y los separe para identificar si la emocion es negativa o buena. Para esta implementación se realizo los sigueites ajustes.

## Estructura del Proyecto

Primero creamos la carpeta de nuestro proyecto el cual se llamara ``sentiment_project``, el cual dentro de esta se gestionaran todos los archivos que precesaran el Docker y el streamlit.

### Codigo Principal ``sentiment_parallel.py``

```
LEXICON = {
    "bueno": 1,
    "genial": 1,
    "excelente": 2,
    "feliz": 1,
    "contento": 1,

    "malo": -1,
    "terrible": -2,
    "horrible": -2,
    "triste": -1,
    "enojado": -1,
    "molesto": -1,
}

def score_text_lexicon(text: str):
    """
    Analiza un texto usando un léxico básico.
    Devuelve: (label, info)
       label = 'positivo', 'negativo', 'neutro'
       info = diccionario con el puntaje
    """

    t = text.lower()
    score = 0

    for word, value in LEXICON.items():
        if word in t:
            score += value

    if score > 0:
        return "positivo", {"score": score}
    elif score < 0:
        return "negativo", {"score": score}
    else:
        return "neutro", {"score": 0}

def process_text_list(text_list):
    """
    Recibe una lista de strings y regresa una lista de labels.
    (No se usa en Streamlit pero está disponible por si haces pruebas)
    """
    results = []
    for text in text_list:
        label, _ = score_text_lexicon(text)
        results.append(label)
    return results
 ```

### StreamLit ``app.py``

``` 
import streamlit as st
import pandas as pd
import concurrent.futures

from sentiment_parallel import score_text_lexicon  # solo importamos lo necesario

st.set_page_config(page_title="Sentiment Parallel", layout="wide")

st.title("Procesar comentarios en paralelo - Sentiment Analysis")

uploaded = st.file_uploader("Sube un CSV (columna 'comentario')", type=["csv"])
max_workers = st.sidebar.slider("Número de threads", 1, 16, 4)
chunk_size = st.sidebar.number_input(
    "Tamaño de chunk (filas por tarea)", min_value=10, max_value=500, value=50
)

if uploaded:
    try:
        df = pd.read_csv(uploaded)
    except Exception as e:
        st.error(f"Error leyendo CSV: {e}")
        st.stop()

    if "comentario" not in df.columns:
        st.error("El CSV debe tener una columna llamada 'comentario'.")
        st.stop()

    if st.button("Procesar comentarios"):
        st.warning("Procesando comentarios en paralelo...")

        items = list(df["comentario"].fillna("").astype(str).items())
        total = len(items)

        chunks = [items[i:i+chunk_size] for i in range(0, total, chunk_size)]

        progress = st.progress(0)
        results_dict = {}

        def process_chunk(chunk):
            out = []
            for idx, text in chunk:
                label, info = score_text_lexicon(text)
                out.append((idx, label))
            return out

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_chunk, chunk): chunk for chunk in chunks}

            done = 0
            for fut in concurrent.futures.as_completed(futures):
                try:
                    res_list = fut.result()
                except Exception as e:
                    st.error(f"Error en hilo: {e}")
                    continue

                for idx, label in res_list:
                    results_dict[idx] = label

                done += 1
                progress.progress(done / len(chunks))

        df["sentimiento"] = [results_dict[i] for i, _ in items]

        st.success("Procesamiento completado! 🎉")
        st.dataframe(df.head())

        st.download_button(
            "Descargar resultados",
            df.to_csv(index=False).encode("utf-8"),
            "sentimientos.csv",
            "text/csv",
        )
 ```

### Despliegue de Docker ``DockerFile``

```
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
 ```

## Activación del Analisis de Emociones

1. Primero para no generar algun error al iniciar el analisis, se crea y despliega todo mediante un entorno virtual.

<img width="767" height="48" alt="image" src="https://github.com/user-attachments/assets/1a5d5f02-afc3-498f-a015-20c7a7f70a4f" />

2. Luego creamos todos los archivos que anteriormente se explicaron.

<img width="953" height="48" alt="image" src="https://github.com/user-attachments/assets/141d0746-ae7a-465a-8eef-12b78a0f8d96" />

3. Desplegamos mediante docker.

<img width="1835" height="555" alt="image" src="https://github.com/user-attachments/assets/09f6cdc4-57fb-42a4-9104-2699e659df71" />

<img width="1014" height="233" alt="image" src="https://github.com/user-attachments/assets/6fd00310-8239-4cf1-ad7d-1402665629bf" />

<img width="1326" height="385" alt="image" src="https://github.com/user-attachments/assets/679c22fa-b98d-4c55-84b7-259630ba255b" />




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


