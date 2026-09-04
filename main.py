import pygame, random, os
from PIL import Image, ImageOps

# ================= CONFIG =================
# Define as dimensões da janela e a taxa de atualização do jogo.
W, H, FPS = 1000, 600, 120

# Parâmetros físicos e de posicionamento do personagem.
GROUND, PLAYER_X = 500, 150
GRAVITY, JUMP_FORCE, MAX_JUMPS = 2700, -780, 2

# Velocidade inicial e distância total utilizada para controlar o progresso.
INITIAL_SPEED, TOTAL_DISTANCE = 300, 15000

# Dimensões e posição vertical da barra de progresso.
BAR_W, BAR_H, BAR_Y = 400, 12, 35


pygame.init()
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Cat Run")
clock = pygame.time.Clock()

# Fontes utilizadas na interface.
font = pygame.font.SysFont("Arial", 18)
title_font = pygame.font.SysFont("Arial", 50, bold=True)


IMAGES_DIR = "images"


# Centraliza a construção dos caminhos dos arquivos de imagem,
# evitando repetir a pasta de recursos em diferentes partes do código.
def asset(path):
    return os.path.join(IMAGES_DIR, path)


# Carrega e redimensiona imagens estáticas utilizando interpolação suave.
# convert_alpha() preserva transparência, permitindo imagens com fundo transparente.
def image(path, size):
    return pygame.transform.smoothscale(
        pygame.image.load(asset(path)).convert_alpha(), size
    )


# Carrega os quadros de uma animação GIF e os converte para superfícies do Pygame.
# O processamento antecipado dos frames facilita a reprodução da animação durante o jogo.
def gif(path, size, mirror=False):
    im, frames = Image.open(asset(path)), []

    try:
        while True:
            frame = im.convert("RGBA")

            # Permite inverter horizontalmente determinadas animações.
            if mirror:
                frame = ImageOps.mirror(frame)

            # Redimensionamento com filtro de alta qualidade.
            frame.thumbnail(size, Image.Resampling.LANCZOS)

            # Conversão do frame do PIL para uma superfície compatível com o Pygame.
            raw = frame.tobytes()
            surf = pygame.image.fromstring(
                raw, frame.size, "RGBA"
            ).convert_alpha()

            frames.append(surf)

            # Avança para o próximo frame do GIF.
            im.seek(im.tell() + 1)

    except EOFError:
        # EOFError indica que todos os frames foram processados.
        pass

    return frames


class Game:
    def __init__(self):

        # Carregamento dos recursos gráficos utilizados pelo jogo.
        self.bg = image("fundo.png", (W, H))
        self.cat = gif("cat.gif", (100, 100))
        self.fish = gif("fish.gif", (75, 75))
        self.victory = image("victory.png", (430, 300))
        self.cat_icon = image("cat-icon.png", (40, 40))
        self.fish_icon = image("peixe.png", (85, 85))

        # Estrutura de dados que define os obstáculos disponíveis.
        # Cada tupla contém: arquivo, tamanho e indicação de espelhamento.
        self.obstacle_data = [
            ("pedra.png", (90, 90), False),
            ("tronco.png", (190, 105), False),
            ("galho.png", (150, 80), False),
            ("cobra.gif", (100, 70), True),
        ]

        # Dicionário utilizado para armazenar os frames de cada obstáculo.
        # Dessa forma, os recursos são carregados uma única vez.
        self.obstacle_images = {}

        for path, size, mirror in self.obstacle_data:
            self.obstacle_images[path] = (
                gif(path, size, mirror)
                if path.endswith(".gif")
                else [image(path, size)]
            )

        # Máquina de estados simples para controlar as diferentes telas do jogo.
        self.state = "home"

        self.reset()

    def reset(self):
        # Reinicializa todas as variáveis de uma partida.
        self.speed = INITIAL_SPEED
        self.distance = 0.0
        self.bg_x = 0.0

        # Define a posição inicial do personagem sobre o solo.
        self.player_y = GROUND - self.cat[0].get_height()
        self.vy = 0.0
        self.jumps = 0

        # Lista dinâmica de obstáculos presentes na fase.
        self.obstacles = []

        # Controle temporal do surgimento de obstáculos.
        self.spawn_timer = 0.0
        self.next_spawn = random.uniform(1.55, 2.5)

        # Controle das animações.
        self.cat_frame = self.fish_frame = 0
        self.cat_anim = self.fish_anim = 0.0

        # Estado e posição inicial do peixe.
        self.fish_x = W + 500
        self.fish_active = False

    @property
    def player_rect(self):
        # Cria uma área de colisão menor que a imagem visual do personagem.
        # Isso evita colisões excessivamente rígidas baseadas no tamanho da sprite.
        s = self.cat[self.cat_frame]

        return pygame.Rect(
            PLAYER_X + int(s.get_width() * .25),
            int(self.player_y + s.get_height() * .25),
            int(s.get_width() * .5),
            int(s.get_height() * .65),
        )

    def start(self):
        # Reinicia os dados e altera o estado para iniciar a partida.
        self.reset()
        self.state = "playing"

    def jump(self):
        # Permite salto somente durante a partida e limita a dois saltos.
        # Essa técnica implementa o chamado "double jump".
        if self.state == "playing" and self.jumps < MAX_JUMPS:
            self.vy = JUMP_FORCE
            self.jumps += 1

    def spawn(self):
        # Seleciona aleatoriamente um tipo de obstáculo.
        path, _, _ = random.choice(self.obstacle_data)

        frames = self.obstacle_images[path]
        surf = frames[0]

        # Posiciona o obstáculo fora da área visível da tela.
        x = W + random.randint(30, 150)

        # Mantém uma distância mínima entre obstáculos consecutivos.
        if self.obstacles and x - (
            self.obstacles[-1]["x"] + self.obstacles[-1]["w"]
        ) < 260:
            x += 260

        # Armazena os dados do obstáculo em um dicionário.
        # Essa estrutura permite controlar posição, tamanho e animação.
        self.obstacles.append({
            "x": float(x),
            "y": GROUND - surf.get_height(),
            "w": surf.get_width(),
            "h": surf.get_height(),
            "frames": frames,
            "frame": 0,
            "anim": 0.0
        })

    def game_over(self):
        # Altera o estado do jogo para a tela de derrota.
        self.state = "gameover"

    def win(self):
        # Altera o estado do jogo para a tela de vitória.
        self.state = "victory"

    def update(self, dt):

        # Atualiza o deslocamento visual do cenário.
        # O operador % W cria um efeito de repetição contínua do fundo.
        if self.state in ("home", "playing"):
            visual_speed = (
                self.speed
                if self.state == "playing"
                else INITIAL_SPEED
            )

            self.bg_x = (
                self.bg_x - visual_speed * dt
            ) % W

        # A lógica de jogo só é executada durante o estado "playing".
        if self.state != "playing":
            return

        # Calcula o percentual de progresso da fase.
        progress = min(self.distance / TOTAL_DISTANCE, 1.0)

        # Aumenta gradualmente a velocidade conforme o jogador avança.
        self.speed = INITIAL_SPEED + progress * 180

        # ================= FÍSICA =================
        # Implementação de movimento vertical baseada em velocidade e gravidade.
        self.vy += GRAVITY * dt
        self.player_y += self.vy * dt

        floor_y = GROUND - self.cat[0].get_height()

        # Impede que o personagem atravesse o chão e reinicia sua velocidade vertical.
        if self.player_y >= floor_y:
            self.player_y, self.vy, self.jumps = floor_y, 0, 0

        # ================= ANIMAÇÃO =================
        # O tempo acumulado determina quando trocar o frame da animação.
        self.cat_anim += dt

        if self.cat_anim >= .08:
            self.cat_anim = 0
            self.cat_frame = (
                self.cat_frame + 1
            ) % len(self.cat)

        # ================= SPAWN =================
        # O surgimento dos obstáculos é baseado em tempo,
        # utilizando intervalos aleatórios para variar a dificuldade.
        self.spawn_timer += dt

        if (
            self.spawn_timer >= self.next_spawn
            and TOTAL_DISTANCE - self.distance > 700
        ):
            self.spawn()

            self.spawn_timer = 0
            self.next_spawn = random.uniform(1.35, 2.3)

        # ================= OBSTÁCULOS =================
        alive = []

        for o in self.obstacles:

            # Movimento dos obstáculos da direita para a esquerda.
            # O uso de dt torna o movimento independente da taxa de FPS.
            o["x"] -= self.speed * dt

            # Controle da animação individual do obstáculo.
            o["anim"] += dt

            if len(o["frames"]) > 1 and o["anim"] >= .10:
                o["anim"] = 0
                o["frame"] = (
                    o["frame"] + 1
                ) % len(o["frames"])

            # Área de colisão reduzida em relação à imagem do obstáculo.
            rect = pygame.Rect(
                int(o["x"] + o["w"] * .15),
                int(o["y"] + o["h"] * .15),
                int(o["w"] * .70),
                int(o["h"] * .75)
            )

            # Verificação de colisão entre jogador e obstáculo.
            if self.player_rect.colliderect(rect):
                self.game_over()
                return

            # Remove obstáculos que já saíram completamente da tela.
            if o["x"] + o["w"] > 0:
                alive.append(o)

        self.obstacles = alive

        # ================= PROGRESSO =================
        # A distância percorrida é calculada a partir da velocidade e do tempo.
        self.distance += self.speed * dt
        remaining = TOTAL_DISTANCE - self.distance

        # O peixe é ativado quando o jogador entra na parte final da fase.
        if remaining <= 800:
            self.fish_active = True

            # Movimento do objetivo em direção à área do jogador.
            target_x = W + 500 - (800 - remaining)
            self.fish_x = target_x

            # Controle da animação do peixe.
            self.fish_anim += dt

            if self.fish_anim >= .12:
                self.fish_anim = 0
                self.fish_frame = (
                    self.fish_frame + 1
                ) % len(self.fish)

            fs = self.fish[self.fish_frame]

            # Define a área de colisão do peixe.
            fish_rect = pygame.Rect(
                int(self.fish_x + fs.get_width() * .15),
                int(
                    GROUND
                    - fs.get_height()
                    + fs.get_height() * .15
                ),
                int(fs.get_width() * .70),
                int(fs.get_height() * .70)
            )

            # Colisão com o peixe representa a conclusão da fase.
            if self.player_rect.colliderect(fish_rect):
                self.win()
                return

            # Caso o peixe ultrapasse o jogador, a fase termina.
            if fish_rect.right < self.player_rect.left:
                self.game_over()
                return

    def text(self, txt, y, big=False):
        # Centraliza a renderização dos textos da interface.
        f = title_font if big else font
        s = f.render(txt, True, "white")
        screen.blit(
            s,
            s.get_rect(center=(W // 2, y))
        )

    def draw(self):

        # ================= FUNDO INFINITO =================
        # Duas cópias do cenário são desenhadas lado a lado.
        # Quando uma sai da tela, a outra mantém a continuidade visual.
        screen.blit(
            self.bg,
            (int(self.bg_x) - W, 0)
        )

        screen.blit(
            self.bg,
            (int(self.bg_x), 0)
        )

        # ================= JOGADOR =================
        if self.state != "home":
            screen.blit(
                self.cat[self.cat_frame],
                (PLAYER_X, int(self.player_y))
            )

        # ================= OBSTÁCULOS =================
        for o in self.obstacles:
            screen.blit(
                o["frames"][o["frame"]],
                (int(o["x"]), int(o["y"]))
            )

        # ================= PEIXE =================
        if self.fish_active and self.state == "playing":
            fs = self.fish[self.fish_frame]

            screen.blit(
                fs,
                (
                    int(self.fish_x),
                    GROUND - fs.get_height()
                )
            )

        # ================= BARRA DE PROGRESSO =================
        if self.state == "playing":
            x = W // 2 - BAR_W // 2

            # Fundo da barra.
            pygame.draw.rect(
                screen,
                (65, 65, 65),
                (x, BAR_Y, BAR_W, BAR_H),
                border_radius=6
            )

            # Preenchimento proporcional à distância percorrida.
            progress = min(
                self.distance / TOTAL_DISTANCE,
                1
            )

            pygame.draw.rect(
                screen,
                (240, 210, 40),
                (
                    x,
                    BAR_Y,
                    int(BAR_W * progress),
                    BAR_H
                ),
                border_radius=6
            )

            # Ícones representam visualmente o início e o objetivo da fase.
            screen.blit(
                self.cat_icon,
                self.cat_icon.get_rect(
                    center=(x - 30, BAR_Y + BAR_H // 2)
                )
            )

            screen.blit(
                self.fish_icon,
                self.fish_icon.get_rect(
                    center=(x + BAR_W + 30, BAR_Y + BAR_H // 2)
                )
            )

        # ================= INTERFACE DE ESTADOS =================
        # Overlay semitransparente é utilizado para destacar as informações
        # das telas de menu, derrota e vitória.
        if self.state in ("home", "gameover", "victory"):
            overlay = pygame.Surface(
                (W, H),
                pygame.SRCALPHA
            )

            overlay.fill((0, 0, 0, 145))
            screen.blit(overlay, (0, 0))

            if self.state == "home":
                self.text("CAT RUN", 180, True)
                self.text(
                    "SPACE = PULAR  |  SPACE 2x = DOUBLE JUMP",
                    250
                )
                self.text("ENTER = START", 340)

            elif self.state == "gameover":
                self.text("GAME OVER", 190, True)
                self.text(
                    "O gato não conseguiu alcançar o peixe.",
                    255
                )
                self.text("ENTER = RECOMEÇAR", 340)

            else:
                screen.blit(
                    self.victory,
                    self.victory.get_rect(
                        center=(W // 2, 225)
                    )
                )

                self.text(
                    "ENTER = RECOMEÇAR",
                    470
                )

    def run(self):
        running = True

        # Game Loop principal: processa entrada, atualiza a lógica
        # e renderiza o resultado continuamente.
        while running:

            # Calcula o delta time e limita valores muito altos,
            # evitando grandes saltos na física após travamentos ou pausas.
            dt = min(
                clock.tick(FPS) / 1000.0,
                1 / 30
            )

            # ================= EVENTOS =================
            for event in pygame.event.get():

                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:

                    if event.key == pygame.K_SPACE:
                        self.jump()

                    elif event.key in (
                        pygame.K_RETURN,
                        pygame.K_KP_ENTER
                    ):
                        if self.state != "playing":
                            self.start()

            # Atualiza a lógica e posteriormente renderiza a cena.
            self.update(dt)
            self.draw()

            # Atualiza a tela após o processo de renderização.
            pygame.display.flip()

        pygame.quit()


# Permite executar o jogo diretamente por este arquivo.
if __name__ == "__main__":
    Game().run()
