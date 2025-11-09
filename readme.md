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

