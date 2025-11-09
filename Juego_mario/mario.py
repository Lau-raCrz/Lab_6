import pygame
import threading
import time
import random
import queue
from dataclasses import dataclass
from typing import List, Tuple, Optional

# === INICIALIZAR PYGAME ===
pygame.init()

# === CONSTANTES ===
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Constantes de cámara y generación
CAMERA_THRESHOLD = 300
PLATFORM_GENERATION_DISTANCE = 1000
PLATFORM_CLEANUP_DISTANCE = 500

# === COLORES ===
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 215, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)

# === CONFIGURACIÓN DE PANTALLA ===
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Mario Bros - Versión Optimizada con Threading")
clock = pygame.time.Clock()

# === IMÁGENES (CARGA Y ESCALADO) ===
player_img_idle = pygame.image.load("Mario_quieto.png").convert_alpha()
player_img_right = pygame.image.load("MArio_derecha.png").convert_alpha()
player_img_left = pygame.image.load("Mario_izq.png").convert_alpha()
player_img_jump = pygame.image.load("Mario_saltando.png").convert_alpha()

enemy_img = pygame.image.load("Enemigo.png").convert_alpha()
platform_img = pygame.image.load("Plataforma.png").convert_alpha()
floor_img = pygame.image.load("Piso.png").convert_alpha()
background_img = pygame.image.load("Fondo.jpeg").convert()
coin_img = pygame.image.load("Moneda.png").convert_alpha()

# Tamaños base
PLAYER_W, PLAYER_H = 40, 60
ENEMY_W, ENEMY_H = 40, 40
PLATFORM_H = 20
COIN_SIZE = 30

# Escalado
player_img_idle = pygame.transform.scale(player_img_idle, (PLAYER_W, PLAYER_H))
player_img_right = pygame.transform.scale(player_img_right, (PLAYER_W, PLAYER_H))
player_img_left = pygame.transform.scale(player_img_left, (PLAYER_W, PLAYER_H))
player_img_jump = pygame.transform.scale(player_img_jump, (PLAYER_W, PLAYER_H))
enemy_img = pygame.transform.scale(enemy_img, (ENEMY_W, ENEMY_H))
background_img = pygame.transform.scale(background_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
coin_img = pygame.transform.scale(coin_img, (COIN_SIZE, COIN_SIZE))

# === SINCRONIZACIÓN MEJORADA ===
player_mutex = threading.Lock()
enemy_mutex = threading.Lock()
coin_mutex = threading.Lock()
platform_mutex = threading.Lock()
game_state_mutex = threading.Lock()

enemy_semaphore = threading.Semaphore(5)
event_queue = queue.Queue()

# === VARIABLES COMPARTIDAS ===
@dataclass
class GameState:
    player_x: float = 50
    player_y: float = 500
    player_velocity_x: float = 0
    player_velocity_y: float = 0
    player_coins: int = 0
    player_score: int = 0
    player_lives: int = 3
    camera_x: float = 0
    world_furthest_x: float = 800
    game_running: bool = True
    invulnerable_until: float = 0

game_state = GameState()
shared_enemies: List['Enemy'] = []
shared_platforms: List['Platform'] = []
shared_coins: List['Coin'] = []

# === CLASES DEL JUEGO ===
class Player:
    def __init__(self):
        self.width = PLAYER_W
        self.height = PLAYER_H
        self.gravity = 0.5
        self.max_fall_speed = 15
        self.on_ground = False
        self.direction = "right"
        self.jumping = False
        self.jump_strength = -12

    def draw(self):
        with game_state_mutex:
            is_invulnerable = time.time() < game_state.invulnerable_until
            
            if is_invulnerable and int(time.time() * 10) % 2 == 0:
                return
            
            if self.jumping:
                image = player_img_jump
            elif self.direction == "left":
                image = player_img_left
            elif self.direction == "right":
                image = player_img_right
            else:
                image = player_img_idle

            screen_x = game_state.player_x - game_state.camera_x
            screen.blit(image, (screen_x, game_state.player_y))

    def update(self):
        with game_state_mutex:
            game_state.player_velocity_y += self.gravity
            
            if game_state.player_velocity_y > self.max_fall_speed:
                game_state.player_velocity_y = self.max_fall_speed
            
            steps = max(1, int(abs(game_state.player_velocity_y) / 5))
            step_velocity = game_state.player_velocity_y / steps
            
            collision_occurred = False
            for _ in range(steps):
                game_state.player_y += step_velocity
                
                with platform_mutex:
                    for platform in shared_platforms:
                        if game_state.player_velocity_y > 0:
                            if (game_state.player_y + self.height >= platform.y and
                                game_state.player_y + self.height <= platform.y + PLATFORM_H and
                                game_state.player_x + self.width > platform.x + 5 and
                                game_state.player_x < platform.x + platform.width - 5):
                                
                                game_state.player_y = platform.y - self.height
                                game_state.player_velocity_y = 0
                                self.on_ground = True
                                self.jumping = False
                                collision_occurred = True
                                break
                
                if collision_occurred:
                    break
            
            if not collision_occurred:
                self.on_ground = False
                
            if game_state.player_y >= SCREEN_HEIGHT - self.height:
                game_state.player_y = SCREEN_HEIGHT - self.height
                game_state.player_velocity_y = 0
                self.on_ground = True
                self.jumping = False

            if game_state.player_x < game_state.camera_x:
                game_state.player_x = game_state.camera_x

    def jump(self):
        if self.on_ground:
            with game_state_mutex:
                game_state.player_velocity_y = self.jump_strength
            self.jumping = True
            self.on_ground = False


class Enemy:
    def __init__(self, x: float, y: float, platform_bounds: Tuple[float, float, float]):
        self.x = x
        self.y = y
        self.width = ENEMY_W
        self.height = ENEMY_H
        self.speed = 2
        self.direction = random.choice([-1, 1])
        self.active = True
        self.velocity_y = 0
        self.gravity = 0.5
        self.on_ground = False
        self.platform_left = platform_bounds[0]
        self.platform_right = platform_bounds[1]
        self.platform_y = platform_bounds[2]
        self.being_stomped = False

    def draw(self):
        if not self.active:
            return
        screen_x = self.x - game_state.camera_x
        if -self.width < screen_x < SCREEN_WIDTH:
            screen.blit(enemy_img, (screen_x, self.y))

    def update(self):
        if not self.active or self.being_stomped:
            return

        self.velocity_y += self.gravity
        self.y += self.velocity_y

        self.on_ground = False
        with platform_mutex:
            for platform in shared_platforms:
                if (self.y + self.height >= platform.y and
                    self.y + self.height <= platform.y + 10 and
                    self.x + self.width > platform.x and
                    self.x < platform.x + platform.width):
                    self.y = platform.y - self.height
                    self.velocity_y = 0
                    self.on_ground = True
                    self.platform_left = platform.x
                    self.platform_right = platform.x + platform.width
                    self.platform_y = platform.y
                    break

        if self.y > SCREEN_HEIGHT - self.height:
            self.y = SCREEN_HEIGHT - self.height
            self.velocity_y = 0
            self.on_ground = True

        self.x += self.speed * self.direction

        if self.on_ground:
            enemy_center = self.x + self.width / 2
            margin = 15

            if enemy_center <= self.platform_left + margin:
                self.direction = 1
                self.x = self.platform_left + margin - self.width / 2
            elif enemy_center >= self.platform_right - margin:
                self.direction = -1
                self.x = self.platform_right - margin - self.width / 2

    def check_collision_with_player(self) -> Optional[str]:
        if not self.active or self.being_stomped:
            return None
        
        with game_state_mutex:
            if time.time() < game_state.invulnerable_until:
                return None
            
            player_rect = pygame.Rect(game_state.player_x, game_state.player_y,
                                     PLAYER_W, PLAYER_H)
            player_velocity_y = game_state.player_velocity_y
            player_bottom = game_state.player_y + PLAYER_H

        enemy_rect = pygame.Rect(self.x, self.y, self.width, self.height)

        if player_rect.colliderect(enemy_rect):
            enemy_top = self.y
            
            stomp_margin_top = 25
            stomp_margin_bottom = 5
            
            if (player_velocity_y > 0 and
                player_bottom >= enemy_top - stomp_margin_bottom and
                player_bottom <= enemy_top + stomp_margin_top):
                return 'stomp'
            else:
                return 'damage'
        
        return None

    def deactivate(self):
        self.active = False
        self.being_stomped = True


class Platform:
    def __init__(self, x: float, y: float, width: int, use_floor: bool = False):
        self.x = x
        self.y = y
        self.width = width
        self.height = PLATFORM_H
        self.use_floor = use_floor

    def draw(self):
        screen_x = self.x - game_state.camera_x
        if screen_x + self.width > 0 and screen_x < SCREEN_WIDTH:
            if self.use_floor:
                tex = pygame.transform.scale(floor_img, (self.width, self.height))
            else:
                tex = pygame.transform.scale(platform_img, (self.width, self.height))
            screen.blit(tex, (screen_x, self.y))

    def overlaps_with(self, other: 'Platform', margin: int = 30) -> bool:
        return not (self.x + self.width + margin < other.x or
                   self.x > other.x + other.width + margin or
                   self.y + self.height + margin < other.y or
                   self.y > other.y + other.height + margin)


class Coin:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.size = COIN_SIZE
        self.active = True
        self.float_offset = random.uniform(0, 100)
        self.float_speed = 0.1

    def draw(self):
        if not self.active:
            return

        self.float_offset += self.float_speed
        float_y = self.y + int(5 * pygame.math.Vector2(0, 1).rotate(self.float_offset * 10).y)

        screen_x = self.x - game_state.camera_x
        if -self.size < screen_x < SCREEN_WIDTH:
            screen.blit(coin_img, (screen_x, float_y))

    def check_collision(self) -> bool:
        if not self.active:
            return False

        with game_state_mutex:
            player_rect = pygame.Rect(game_state.player_x, game_state.player_y,
                                     PLAYER_W, PLAYER_H)

        coin_rect = pygame.Rect(self.x, self.y, self.size, self.size)

        if player_rect.colliderect(coin_rect):
            self.active = False
            return True
        return False


# === FUNCIONES DE UTILIDAD ===
def update_camera():
    with game_state_mutex:
        if game_state.player_x > game_state.camera_x + CAMERA_THRESHOLD:
            game_state.camera_x = game_state.player_x - CAMERA_THRESHOLD


def generate_platform_segment(start_x: float) -> Tuple[List[Platform], List[Coin]]:
    platforms = []
    coins = []
    
    floor = Platform(start_x, 550, 800, use_floor=True)
    platforms.append(floor)
    
    num_platforms = random.randint(3, 5)
    current_x = start_x + 200
    
    for i in range(num_platforms):
        attempts = 0
        max_attempts = 15
        
        while attempts < max_attempts:
            platform_x = current_x + random.randint(150, 300)
            platform_y = random.randint(320, 480)
            platform_width = random.randint(150, 280)
            
            new_platform = Platform(platform_x, platform_y, platform_width)
            
            has_overlap = False
            for existing_platform in platforms:
                if new_platform.overlaps_with(existing_platform, margin=40):
                    has_overlap = True
                    break
            
            if not has_overlap:
                platforms.append(new_platform)
                
                if random.random() < 0.7:
                    num_coins = random.randint(2, 5)
                    coin_spacing = platform_width / (num_coins + 1)
                    
                    for j in range(num_coins):
                        coin_x = platform_x + coin_spacing * (j + 1) - COIN_SIZE / 2
                        coin_y = platform_y - random.randint(50, 100)
                        coins.append(Coin(coin_x, coin_y))
                
                current_x = platform_x
                break
            
            attempts += 1
    
    num_floating = random.randint(2, 4)
    for _ in range(num_floating):
        coin_x = start_x + random.randint(200, 700)
        coin_y = random.randint(150, 400)
        coins.append(Coin(coin_x, coin_y))
    
    return platforms, coins


# === HILOS DEL JUEGO ===
def platform_generation_thread():
    print("🏗️  [THREAD] Platform Generator iniciado")
    
    while game_state.game_running:
        try:
            with game_state_mutex:
                player_x = game_state.player_x
                world_x = game_state.world_furthest_x
            
            if player_x + PLATFORM_GENERATION_DISTANCE > world_x:
                new_platforms, new_coins = generate_platform_segment(world_x)
                
                with platform_mutex:
                    shared_platforms.extend(new_platforms)
                
                with coin_mutex:
                    shared_coins.extend(new_coins)
                
                with game_state_mutex:
                    game_state.world_furthest_x += 800
                
                print(f"🏗️  Generado hasta X={game_state.world_furthest_x} | "
                      f"Plataformas: +{len(new_platforms)-1} | Monedas: +{len(new_coins)}")
            
            with game_state_mutex:
                camera_pos = game_state.camera_x
            
            with platform_mutex:
                before = len(shared_platforms)
                shared_platforms[:] = [p for p in shared_platforms 
                                      if p.x + p.width > camera_pos - PLATFORM_CLEANUP_DISTANCE]
                removed = before - len(shared_platforms)
                if removed > 0:
                    print(f"🧹 Limpiadas {removed} plataformas")
            
            with coin_mutex:
                shared_coins[:] = [c for c in shared_coins 
                                  if c.x > camera_pos - PLATFORM_CLEANUP_DISTANCE]
            
            time.sleep(0.3)
            
        except Exception as e:
            print(f"❌ Error en platform_generation_thread: {e}")


def coin_collection_thread():
    print("🪙 [THREAD] Coin Collector iniciado")
    
    while game_state.game_running:
        try:
            with coin_mutex:
                for coin in shared_coins:
                    if coin.check_collision():
                        event_queue.put(("COIN_COLLECTED", coin))
            
            time.sleep(0.02)
            
        except Exception as e:
            print(f"❌ Error en coin_collection_thread: {e}")


def enemy_management_thread():
    print("👾 [THREAD] Enemy Manager iniciado")
    
    while game_state.game_running:
        try:
            if enemy_semaphore.acquire(blocking=False):
                with enemy_mutex:
                    active_enemies = len([e for e in shared_enemies if e.active])
                
                if active_enemies < 5:
                    with platform_mutex:
                        with game_state_mutex:
                            camera_x = game_state.camera_x
                        
                        suitable_platforms = [
                            p for p in shared_platforms 
                            if not p.use_floor and 
                            p.width >= 120 and
                            camera_x + 400 < p.x < camera_x + SCREEN_WIDTH + 300
                        ]
                    
                    if suitable_platforms:
                        platform = random.choice(suitable_platforms)
                        spawn_x = platform.x + platform.width / 2 - ENEMY_W / 2
                        spawn_y = platform.y - ENEMY_H - 10
                        platform_bounds = (platform.x, platform.x + platform.width, platform.y)
                        
                        new_enemy = Enemy(spawn_x, spawn_y, platform_bounds)
                        
                        with enemy_mutex:
                            shared_enemies.append(new_enemy)
                        
                        print(f"👾 Enemigo spawneado en X={int(spawn_x)}")
                    else:
                        enemy_semaphore.release()
                else:
                    enemy_semaphore.release()
            
            with enemy_mutex:
                for enemy in shared_enemies[:]:
                    enemy.update()
                    
                    collision_type = enemy.check_collision_with_player()
                    
                    if collision_type == 'stomp':
                        event_queue.put(("ENEMY_STOMPED", enemy))
                    elif collision_type == 'damage':
                        event_queue.put(("ENEMY_COLLISION", enemy))
                    
                    with game_state_mutex:
                        camera_x = game_state.camera_x
                    
                    if enemy.x < camera_x - 300 or enemy.y > SCREEN_HEIGHT + 100:
                        shared_enemies.remove(enemy)
                        if enemy.active:
                            enemy_semaphore.release()
                    elif not enemy.active:
                        shared_enemies.remove(enemy)
                        enemy_semaphore.release()
            
            time.sleep(0.03)
            
        except Exception as e:
            print(f"❌ Error en enemy_management_thread: {e}")


def event_processing_thread():
    print("⚡ [THREAD] Event Processor iniciado")
    
    while game_state.game_running:
        try:
            if not event_queue.empty():
                event_type, data = event_queue.get()
                
                if event_type == "ENEMY_COLLISION":
                    with game_state_mutex:
                        game_state.player_lives -= 1
                        game_state.invulnerable_until = time.time() + 2.0
                        game_state.player_x -= 30
                        game_state.player_velocity_y = -8
                    
                    data.deactivate()
                    print(f"💔 ¡Colisión! Vidas restantes: {game_state.player_lives}")
                
                elif event_type == "ENEMY_STOMPED":
                    with game_state_mutex:
                        game_state.player_score += 100
                        game_state.player_velocity_y = -10
                    
                    data.deactivate()
                    print(f"⭐ ¡Enemigo eliminado! +100 puntos | Total: {game_state.player_score}")
                
                elif event_type == "COIN_COLLECTED":
                    with game_state_mutex:
                        game_state.player_coins += 1
                        game_state.player_score += 10
                    print(f"🪙 Moneda recolectada! Total: {game_state.player_coins} | Puntos: {game_state.player_score}")
            
            time.sleep(0.01)
            
        except Exception as e:
            print(f"❌ Error en event_processing_thread: {e}")


# === INICIALIZACIÓN ===
def initialize_game():
    global shared_platforms, shared_coins
    
    print("\n" + "="*60)
    print("🎮 INICIALIZANDO JUEGO")
    print("="*60)
    
    initial_platforms, initial_coins = generate_platform_segment(0)
    shared_platforms.extend(initial_platforms)
    shared_coins.extend(initial_coins)
    
    print(f"✅ Mundo inicial: {len(initial_platforms)} plataformas, {len(initial_coins)} monedas")
    
    threads = [
        threading.Thread(target=platform_generation_thread, daemon=True, name="PlatformGen"),
        threading.Thread(target=coin_collection_thread, daemon=True, name="CoinCollector"),
        threading.Thread(target=enemy_management_thread, daemon=True, name="EnemyManager"),
        threading.Thread(target=event_processing_thread, daemon=True, name="EventProcessor"),
    ]
    
    for thread in threads:
        thread.start()
        print(f"✅ Hilo '{thread.name}' iniciado")
    
    print("="*60)
    print("🎮 ¡JUEGO LISTO!")
    print("="*60 + "\n")


# === BUCLE PRINCIPAL ===
def main():
    player = Player()
    initialize_game()

    font = pygame.font.SysFont('Arial', 22)
    font_big = pygame.font.SysFont('Arial', 32, bold=True)

    print("\n🎮 Controles:")
    print("   ← → : Mover")
    print("   ESPACIO: Saltar")
    print("   ESC: Salir\n")

    while game_state.game_running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_state.game_running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    player.jump()
                elif event.key == pygame.K_ESCAPE:
                    game_state.game_running = False

        keys = pygame.key.get_pressed()
        move_speed = 5
        
        with game_state_mutex:
            if keys[pygame.K_LEFT]:
                game_state.player_x -= move_speed
                player.direction = "left"
            elif keys[pygame.K_RIGHT]:
                game_state.player_x += move_speed
                player.direction = "right"
            else:
                player.direction = "idle"

        update_camera()
        player.update()

        with game_state_mutex:
            if game_state.player_lives <= 0:
                game_state.game_running = False

        screen.blit(background_img, (0, 0))

        with platform_mutex:
            for platform in shared_platforms:
                platform.draw()

        with coin_mutex:
            for coin in shared_coins:
                if coin.active:
                    coin.draw()

        with enemy_mutex:
            for enemy in shared_enemies:
                if enemy.active:
                    enemy.draw()

        player.draw()

        with game_state_mutex:
            lives_text = font.render(f"❤️ x{game_state.player_lives}", True, RED)
            score_text = font.render(f"Puntos: {game_state.player_score}", True, WHITE)
            coins_text = font_big.render(f"🪙 {game_state.player_coins}", True, YELLOW)
            
            if time.time() < game_state.invulnerable_until:
                invuln_text = font.render("⚡ INVULNERABLE", True, GREEN)
                screen.blit(invuln_text, (SCREEN_WIDTH//2 - 80, 10))

        screen.blit(lives_text, (10, 10))
        screen.blit(score_text, (10, 40))
        screen.blit(coins_text, (SCREEN_WIDTH - 120, 10))

        pygame.display.flip()
        clock.tick(FPS)

    screen.fill(BLACK)
    
    with game_state_mutex:
        final_score = game_state.player_score
        final_coins = game_state.player_coins
    
    game_over_text = font_big.render("GAME OVER", True, RED)
    final_score_text = font.render(f"Puntos Finales: {final_score}", True, YELLOW)
    final_coins_text = font.render(f"Monedas Recolectadas: {final_coins}", True, YELLOW)
    
    screen.blit(game_over_text, (SCREEN_WIDTH//2 - 120, SCREEN_HEIGHT//2 - 80))
    screen.blit(final_score_text, (SCREEN_WIDTH//2 - 140, SCREEN_HEIGHT//2 - 20))
    screen.blit(final_coins_text, (SCREEN_WIDTH//2 - 150, SCREEN_HEIGHT//2 + 20))
    
    pygame.display.flip()
    
    print("\n" + "="*60)
    print("🎮 GAME OVER")
    print("="*60)
    print(f"   Puntuación final: {final_score}")
    print(f"   Monedas recolectadas: {final_coins}")
    print("="*60 + "\n")
    
    time.sleep(4)
    pygame.quit()


if __name__ == "__main__":
    main()
