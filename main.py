import pygame, random, os
from PIL import Image, ImageOps

# ================= CONFIG =================
W, H, FPS = 1000, 600, 120
GROUND, PLAYER_X = 500, 150
GRAVITY, JUMP_FORCE, MAX_JUMPS = 2700, -780, 2
INITIAL_SPEED, TOTAL_DISTANCE = 300, 15000
BAR_W, BAR_H, BAR_Y = 400, 12, 35

pygame.init()
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Cat Run")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 18)
title_font = pygame.font.SysFont("Arial", 50, bold=True)


IMAGES_DIR = "images"

def asset(path):
    return os.path.join(IMAGES_DIR, path)

def image(path, size):
    return pygame.transform.smoothscale(
        pygame.image.load(asset(path)).convert_alpha(), size
    )


def gif(path, size, mirror=False):
    im, frames = Image.open(asset(path)), []
    try:
        while True:
            frame = im.convert("RGBA")
            if mirror: frame = ImageOps.mirror(frame)
            frame.thumbnail(size, Image.Resampling.LANCZOS)
            raw = frame.tobytes()
            surf = pygame.image.fromstring(raw, frame.size, "RGBA").convert_alpha()
            frames.append(surf)
            im.seek(im.tell() + 1)
    except EOFError:
        pass
    return frames


class Game:
    def __init__(self):
        self.bg = image("fundo.png", (W, H))
        self.cat = gif("cat.gif", (100, 100))
        self.fish = gif("fish.gif", (75, 75))
        self.victory = image("victory.png", (430, 300))
        self.cat_icon = image("cat-icon.png", (40, 40))
        self.fish_icon = image("peixe.png", (85, 85))

        self.obstacle_data = [
            ("pedra.png", (90, 90), False),
            ("tronco.png", (190, 105), False),
            ("galho.png", (150, 80), False),
            ("cobra.gif", (100, 70), True),
        ]
        self.obstacle_images = {}
        for path, size, mirror in self.obstacle_data:
            self.obstacle_images[path] = gif(path, size, mirror) if path.endswith(".gif") else [image(path, size)]

        self.state = "home"
        self.reset()

    def reset(self):
        self.speed = INITIAL_SPEED
        self.distance = 0.0
        self.bg_x = 0.0
        self.player_y = GROUND - self.cat[0].get_height()
        self.vy = 0.0
        self.jumps = 0
        self.obstacles = []
        self.spawn_timer = 0.0
        self.next_spawn = random.uniform(1.55, 2.5)
        self.cat_frame = self.fish_frame = 0
        self.cat_anim = self.fish_anim = 0.0
        self.fish_x = W + 500
        self.fish_active = False

    @property
    def player_rect(self):
        s = self.cat[self.cat_frame]
        return pygame.Rect(
            PLAYER_X + int(s.get_width() * .25),
            int(self.player_y + s.get_height() * .25),
            int(s.get_width() * .5),
            int(s.get_height() * .65),
        )

    def start(self):
        self.reset()
        self.state = "playing"

    def jump(self):
        if self.state == "playing" and self.jumps < MAX_JUMPS:
            self.vy = JUMP_FORCE
            self.jumps += 1

    def spawn(self):
        path, _, _ = random.choice(self.obstacle_data)
        frames = self.obstacle_images[path]
        surf = frames[0]
        x = W + random.randint(30, 150)

        # Mantém distância mínima entre obstáculos.
        if self.obstacles and x - (self.obstacles[-1]["x"] + self.obstacles[-1]["w"]) < 260:
            x += 260

        self.obstacles.append({
            "x": float(x), "y": GROUND - surf.get_height(),
            "w": surf.get_width(), "h": surf.get_height(),
            "frames": frames, "frame": 0, "anim": 0.0
        })

    def game_over(self):
        self.state = "gameover"

    def win(self):
        self.state = "victory"

    def update(self, dt):
        # Fundo também se move na home.
        if self.state in ("home", "playing"):
            visual_speed = self.speed if self.state == "playing" else INITIAL_SPEED
            self.bg_x = (self.bg_x - visual_speed * dt) % W

        if self.state != "playing":
            return

        progress = min(self.distance / TOTAL_DISTANCE, 1.0)
        self.speed = INITIAL_SPEED + progress * 180

        # Física do gato.
        self.vy += GRAVITY * dt
        self.player_y += self.vy * dt
        floor_y = GROUND - self.cat[0].get_height()
        if self.player_y >= floor_y:
            self.player_y, self.vy, self.jumps = floor_y, 0, 0

        # Animação do gato.
        self.cat_anim += dt
        if self.cat_anim >= .08:
            self.cat_anim = 0
            self.cat_frame = (self.cat_frame + 1) % len(self.cat)

        # Spawn baseado em tempo, ajustado pela velocidade.
        self.spawn_timer += dt
        if self.spawn_timer >= self.next_spawn and TOTAL_DISTANCE - self.distance > 700:
            self.spawn()
            self.spawn_timer = 0
            self.next_spawn = random.uniform(1.35, 2.3)

        # Obstáculos.
        alive = []
        for o in self.obstacles:
            o["x"] -= self.speed * dt
            o["anim"] += dt
            if len(o["frames"]) > 1 and o["anim"] >= .10:
                o["anim"] = 0
                o["frame"] = (o["frame"] + 1) % len(o["frames"])

            rect = pygame.Rect(
                int(o["x"] + o["w"] * .15), int(o["y"] + o["h"] * .15),
                int(o["w"] * .70), int(o["h"] * .75)
            )
            if self.player_rect.colliderect(rect):
                self.game_over()
                return
            if o["x"] + o["w"] > 0:
                alive.append(o)
        self.obstacles = alive

        # Progresso da fase.
        self.distance += self.speed * dt
        remaining = TOTAL_DISTANCE - self.distance

        # Peixe aparece nos últimos 800 pontos e vem até o jogador.
        if remaining <= 800:
            self.fish_active = True
            target_x = W + 500 - (800 - remaining)
            self.fish_x = target_x

            self.fish_anim += dt
            if self.fish_anim >= .12:
                self.fish_anim = 0
                self.fish_frame = (self.fish_frame + 1) % len(self.fish)

            fs = self.fish[self.fish_frame]
            fish_rect = pygame.Rect(
                int(self.fish_x + fs.get_width() * .15),
                int(GROUND - fs.get_height() + fs.get_height() * .15),
                int(fs.get_width() * .70), int(fs.get_height() * .70)
            )

            if self.player_rect.colliderect(fish_rect):
                self.win()
                return
            if fish_rect.right < self.player_rect.left:
                self.game_over()
                return

    def text(self, txt, y, big=False):
        f = title_font if big else font
        s = f.render(txt, True, "white")
        screen.blit(s, s.get_rect(center=(W // 2, y)))

    def draw(self):
        # Fundo infinito.
        screen.blit(self.bg, (int(self.bg_x) - W, 0))
        screen.blit(self.bg, (int(self.bg_x), 0))

        # Jogador.
        if self.state != "home":
            screen.blit(self.cat[self.cat_frame], (PLAYER_X, int(self.player_y)))

        # Obstáculos.
        for o in self.obstacles:
            screen.blit(o["frames"][o["frame"]], (int(o["x"]), int(o["y"])))

        # Peixe.
        if self.fish_active and self.state == "playing":
            fs = self.fish[self.fish_frame]
            screen.blit(fs, (int(self.fish_x), GROUND - fs.get_height()))

        # Barra de progresso.
        if self.state == "playing":
            x = W // 2 - BAR_W // 2
            pygame.draw.rect(screen, (65, 65, 65), (x, BAR_Y, BAR_W, BAR_H), border_radius=6)
            progress = min(self.distance / TOTAL_DISTANCE, 1)
            pygame.draw.rect(screen, (240, 210, 40), (x, BAR_Y, int(BAR_W * progress), BAR_H), border_radius=6)
            screen.blit(self.cat_icon, self.cat_icon.get_rect(center=(x - 30, BAR_Y + BAR_H // 2)))
            screen.blit(self.fish_icon, self.fish_icon.get_rect(center=(x + BAR_W + 30, BAR_Y + BAR_H // 2)))

        # Overlays.
        if self.state in ("home", "gameover", "victory"):
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 145))
            screen.blit(overlay, (0, 0))

            if self.state == "home":
                self.text("CAT RUN", 180, True)
                self.text("SPACE = PULAR  |  SPACE 2x = DOUBLE JUMP", 250)
                self.text("ENTER = START", 340)

            elif self.state == "gameover":
                self.text("GAME OVER", 190, True)
                self.text("O gato não conseguiu alcançar o peixe.", 255)
                self.text("ENTER = RECOMEÇAR", 340)

            else:
                screen.blit(self.victory, self.victory.get_rect(center=(W // 2, 225)))
                self.text("ENTER = RECOMEÇAR", 470)

    def run(self):
        running = True
        while running:
            dt = min(clock.tick(FPS) / 1000.0, 1 / 30)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.jump()
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if self.state != "playing":
                            self.start()

            self.update(dt)
            self.draw()
            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    Game().run()