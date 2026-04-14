import pygame
import random
import math
import sys

# 初期化
pygame.init()

# 定数
WIDTH = 800
HEIGHT = 600
FPS = 60
GRAVITY = 0.1

# 色の定義
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
COLORS = [
    (255, 100, 100),  # 赤
    (100, 255, 100),  # 緑
    (100, 100, 255),  # 青
    (255, 255, 100),  # 黄
    (255, 100, 255),  # マゼンタ
    (100, 255, 255),  # シアン
    (255, 165, 0),    # オレンジ
    (255, 192, 203),  # ピンク
]

class Particle:
    def __init__(self, x, y, vx, vy, color, life=60):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.life = life
        self.max_life = life
        self.size = random.randint(2, 4)
    
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += GRAVITY
        self.life -= 1
        
        # 速度を少し減衰
        self.vx *= 0.99
        self.vy *= 0.99
    
    def draw(self, screen):
        if self.life > 0:
            # 円を描画
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.size)
    
    def is_alive(self):
        return self.life > 0

class Firework:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.target_y = random.randint(100, 300)
        self.speed = random.randint(8, 12)
        self.color = random.choice(COLORS)
        self.exploded = False
        self.particles = []
        
    def update(self):
        if not self.exploded:
            # 上昇中
            self.y -= self.speed
            if self.y <= self.target_y:
                self.explode()
        else:
            # 爆発後のパーティクル更新
            for particle in self.particles[:]:
                particle.update()
                if not particle.is_alive():
                    self.particles.remove(particle)
    
    def explode(self):
        self.exploded = True
        num_particles = random.randint(20, 40)
        
        for _ in range(num_particles):
            # 円形に拡散するパーティクルを生成
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 8)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            
            particle = Particle(
                self.x, self.y, vx, vy, 
                self.color, 
                life=random.randint(40, 80)
            )
            self.particles.append(particle)
    
    def draw(self, screen):
        if not self.exploded:
            # 上昇中の花火
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), 3)
            # 軌跡を描画
            for i in range(5):
                trail_y = self.y + i * 5
                if trail_y < HEIGHT:
                     alpha = 255 - i * 50  # ← ここを追加！
                     trail_color = (*self.color, alpha)
                     trail_surface = pygame.Surface((4, 4), pygame.SRCALPHA)
                     pygame.draw.circle(trail_surface, trail_color, (2, 2), 2)
                     screen.blit(trail_surface, (int(self.x) - 2, int(trail_y) - 2))
        else:
            # 爆発後のパーティクル描画
            for particle in self.particles:
                particle.draw(screen)
    
    def is_finished(self):
        return self.exploded and len(self.particles) == 0

class FireworksApp:
    def __init__(self):
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.screen_w, self.screen_h = self.screen.get_size()
        pygame.display.set_caption("花火アプリ - クリックまたはスペースキーで花火を打ち上げ")
        self.clock = pygame.time.Clock()
        self.fireworks = []
        self.auto_timer = 0
        self.font = pygame.font.SysFont("meiryo", 24)
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # マウスクリックで花火を打ち上げ
                x, y = event.pos
                self.launch_firework(x)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    # スペースキーでランダムな位置に花火を打ち上げ
                    x = random.randint(100, self.screen_w - 100)
                    self.launch_firework(x)
                elif event.key == pygame.K_ESCAPE:
                    return False
        return True
    
    def launch_firework(self, x):
        firework = Firework(x, self.screen_h)
        self.fireworks.append(firework)
    
    def update(self):
        # 花火の更新
        for firework in self.fireworks[:]:
            firework.update()
            if firework.is_finished():
                self.fireworks.remove(firework)
        
        # 自動で花火を打ち上げ（時々）
        self.auto_timer += 1
        if self.auto_timer > random.randint(120, 240):  # 2-4秒間隔
            x = random.randint(100, self.screen_w - 100)
            self.launch_firework(x)
            self.auto_timer = 0
    
    def draw(self):
        # 軌跡効果のための半透明の黒いサーフェス
        s = pygame.Surface((self.screen_w, self.screen_h))
        s.set_alpha(30)
        s.fill(BLACK)
        self.screen.blit(s, (0, 0))
        
        # 花火を描画
        for firework in self.fireworks:
            firework.draw(self.screen)
        
        # 操作説明を描画
        text = self.font.render("click or space to launch HANABI", True, WHITE)
        self.screen.blit(text, (10, 10))
        
        text2 = self.font.render("ESC for Exit", True, WHITE)
        self.screen.blit(text2, (10, 50))
        
        pygame.display.flip()
    
    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    app = FireworksApp()
    app.run()