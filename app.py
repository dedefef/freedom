import pygame
import math
import random
import sys

# --- 초기화 및 화면 설정 ---
pygame.init()
WIDTH, HEIGHT = 1280, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Mini LoL - Python Edition")
clock = pygame.time.Clock()

# --- 색상 팔레트 ---
BG_COLOR = (28, 38, 32)
LANE_COLOR = (58, 54, 48)
RIVER_COLOR = (32, 74, 96)
BLUE_TEAM = (50, 150, 255)
RED_TEAM = (240, 70, 70)
GOLD_COLOR = (255, 215, 0)
HP_GREEN = (60, 220, 90)
HP_BG = (40, 40, 40)
MANA_BLUE = (60, 170, 255)
WHITE = (245, 245, 245)
DARK_UI = (20, 24, 30)

# --- 폰트 설정 ---
font_sm = pygame.font.SysFont("malgungothic", 14, bold=True)
font_md = pygame.font.SysFont("malgungothic", 18, bold=True)
font_lg = pygame.font.SysFont("malgungothic", 48, bold=True)

# --- 유틸리티 함수 ---
def get_dist(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

class FloatingText:
    def __init__(self, x, y, text, color):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.timer = 45

    def update(self):
        self.y -= 0.8
        self.timer -= 1

    def draw(self, surf):
        alpha = max(0, min(255, int((self.timer / 45) * 255)))
        txt_surf = font_sm.render(self.text, True, self.color)
        txt_surf.set_alpha(alpha)
        surf.blit(txt_surf, (self.x - txt_surf.get_width() // 2, self.y))

class Particle:
    def __init__(self, x, y, color, speed, size, life):
        self.x = x
        self.y = y
        angle = random.uniform(0, math.pi * 2)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color = color
        self.size = size
        self.life = life
        self.max_life = life

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, surf):
        r = max(1, int(self.size * (self.life / self.max_life)))
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), r)

class Projectile:
    def __init__(self, x, y, tx, ty, speed, damage, radius, color, team, is_skill=False, pierce=False, target_entity=None):
        self.x = x
        self.y = y
        self.speed = speed
        self.damage = damage
        self.radius = radius
        self.color = color
        self.team = team
        self.is_skill = is_skill
        self.pierce = pierce
        self.target_entity = target_entity
        self.hit_list = []
        self.life = 90

        angle = math.atan2(ty - y, tx - x)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed

    def update(self):
        if self.target_entity and self.target_entity.alive:
            angle = math.atan2(self.target_entity.y - self.y, self.target_entity.x - self.x)
            self.vx = math.cos(angle) * self.speed
            self.vy = math.sin(angle) * self.speed
        elif self.target_entity and not self.target_entity.alive:
            self.life = 0

        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, surf):
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surf, WHITE, (int(self.x), int(self.y)), max(2, self.radius // 2))

# --- 엔티티 클래스 ---
class Entity:
    def __init__(self, x, y, hp, radius, team, color):
        self.x = x
        self.y = y
        self.max_hp = hp
        self.hp = hp
        self.radius = radius
        self.team = team
        self.color = color
        self.alive = True

    def take_damage(self, amount, floating_texts, particles, color=WHITE):
        if not self.alive:
            return False
        self.hp -= amount
        floating_texts.append(FloatingText(self.x, self.y - self.radius - 10, f"-{int(amount)}", color))
        for _ in range(5):
            particles.append(Particle(self.x, self.y, self.color, random.uniform(1, 3), 4, 15))
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            for _ in range(18):
                particles.append(Particle(self.x, self.y, self.color, random.uniform(2, 6), 6, 25))
            return True
        return False

    def draw_hp_bar(self, surf, width=50, height=6, offset_y=12):
        bx = self.x - width // 2
        by = self.y - self.radius - offset_y
        pygame.draw.rect(surf, HP_BG, (bx, by, width, height))
        ratio = max(0, self.hp / self.max_hp)
        bar_col = HP_GREEN if self.team == "blue" else RED_TEAM
        pygame.draw.rect(surf, bar_col, (bx, by, int(width * ratio), height))
        pygame.draw.rect(surf, (15, 15, 15), (bx, by, width, height), 1)

class Structure(Entity):
    def __init__(self, x, y, hp, radius, team, is_nexus=False):
        color = BLUE_TEAM if team == "blue" else RED_TEAM
        super().__init__(x, y, hp, radius, team, color)
        self.is_nexus = is_nexus
        self.attack_range = 240 if not is_nexus else 0
        self.attack_cd = 0
        self.damage = 95

    def update(self, enemies, projectiles):
        if not self.alive or self.is_nexus:
            return
        if self.attack_cd > 0:
            self.attack_cd -= 1
            return

        # 사거리 내 적 탐색 (미니언 우선)
        target = None
        min_dist = self.attack_range
        for e in enemies:
            if e.alive and e.team != self.team:
                d = get_dist((self.x, self.y), (e.x, e.y))
                if d <= min_dist:
                    if isinstance(e, Minion):
                        target = e
                        break
                    elif target is None:
                        target = e
        if target:
            self.attack_cd = 75
            projectiles.append(Projectile(self.x, self.y, target.x, target.y, 9, self.damage, 8, self.color, self.team, target_entity=target))

    def draw(self, surf):
        if not self.alive:
            pygame.draw.circle(surf, (45, 45, 45), (int(self.x), int(self.y)), self.radius)
            return
        # 사거리 표시 (포탑)
        if not self.is_nexus:
            pygame.draw.circle(surf, (*self.color, 40), (int(self.x), int(self.y)), self.attack_range, 1)
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surf, GOLD_COLOR if self.is_nexus else WHITE, (int(self.x), int(self.y)), self.radius - 8, 3)
        self.draw_hp_bar(surf, width=80 if self.is_nexus else 65, height=8, offset_y=16)

class Minion(Entity):
    def __init__(self, x, y, team):
        color = (100, 180, 255) if team == "blue" else (255, 110, 110)
        super().__init__(x, y, 220, 13, team, color)
        self.speed = 1.6
        self.attack_range = 55
        self.damage = 18
        self.attack_cd = 0

    def update(self, all_units):
        if not self.alive:
            return
        if self.attack_cd > 0:
            self.attack_cd -= 1

        target = None
        min_dist = 220
        for u in all_units:
            if u.alive and u.team != self.team:
                d = get_dist((self.x, self.y), (u.x, u.y))
                if d < min_dist:
                    min_dist = d
                    target = u

        if target:
            if min_dist <= self.attack_range:
                if self.attack_cd == 0:
                    self.attack_cd = 60
                    return ("melee", target, self.damage)
            else:
                angle = math.atan2(target.y - self.y, target.x - self.x)
                self.x += math.cos(angle) * self.speed
                self.y += math.sin(angle) * self.speed
        else:
            dir_x = 1 if self.team == "blue" else -1
            self.x += dir_x * self.speed
            # 중앙 라인으로 정렬
            if abs(self.y - HEIGHT // 2) > 5:
                self.y += 1 if self.y < HEIGHT // 2 else -1
        return None

    def draw(self, surf):
        if not self.alive:
            return
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surf, WHITE, (int(self.x), int(self.y)), self.radius, 1)
        self.draw_hp_bar(surf, width=30, height=4, offset_y=8)

class Champion(Entity):
    def __init__(self, x, y, team, name):
        color = BLUE_TEAM if team == "blue" else RED_TEAM
        super().__init__(x, y, 650, 20, team, color)
        self.name = name
        self.max_mana = 350
        self.mana = 350
        self.speed = 3.4
        self.ad = 55
        self.ap = 60
        self.attack_range = 175
        self.attack_cd = 0
        self.max_attack_cd = 45

        self.target_pos = None
        self.target_unit = None
        self.gold = 500
        self.level = 1
        self.xp = 0
        self.respawn_timer = 0

        # 스킬 쿨타임 (Q, W, E, R)
        self.cds = {"Q": 0, "W": 0, "E": 0, "R": 0}
        self.max_cds = {"Q": 150, "W": 270, "E": 300, "R": 600}
        self.mana_costs = {"Q": 45, "W": 60, "E": 50, "R": 100}

    def gain_xp(self, amount, floating_texts):
        self.xp += amount
        if self.xp >= self.level * 100:
            self.xp -= self.level * 100
            self.level += 1
            self.max_hp += 85
            self.hp = min(self.max_hp, self.hp + 150)
            self.max_mana += 40
            self.mana = min(self.max_mana, self.mana + 100)
            self.ad += 8
            self.ap += 10
            floating_texts.append(FloatingText(self.x, self.y - 35, f"LEVEL UP! ({self.level})", GOLD_COLOR))

    def cast_skill(self, key, mx, my, projectiles, floating_texts, particles):
        if not self.alive or self.cds[key] > 0:
            return
        cost = self.mana_costs[key]
        if self.mana < cost:
            if self.team == "blue":
                floating_texts.append(FloatingText(self.x, self.y - 25, "마나 부족!", MANA_BLUE))
            return

        self.mana -= cost
        self.cds[key] = self.max_cds[key]

        if key == "Q":  # 신비한 화살 (관통 투사체)
            dmg = 75 + self.ad * 0.8 + self.ap * 0.5
            projectiles.append(Projectile(self.x, self.y, mx, my, 13, dmg, 9, (100, 240, 255), self.team, is_skill=True, pierce=False))
        elif key == "W":  # 정수 보호막 & 회복
            heal = 90 + self.ap * 0.7
            self.hp = min(self.max_hp, self.hp + heal)
            floating_texts.append(FloatingText(self.x, self.y - 25, f"+{int(heal)}", HP_GREEN))
            for _ in range(15):
                particles.append(Particle(self.x, self.y, HP_GREEN, random.uniform(1, 4), 5, 20))
        elif key == "E":  # 비전 이동 (점멸 대시)
            angle = math.atan2(my - self.y, mx - self.x)
            dash_dist = min(160, get_dist((self.x, self.y), (mx, my)))
            for _ in range(12):
                particles.append(Particle(self.x, self.y, (200, 120, 255), random.uniform(1, 3), 5, 18))
            self.x = max(30, min(WIDTH - 30, self.x + math.cos(angle) * dash_dist))
            self.y = max(30, min(HEIGHT - 130, self.y + math.sin(angle) * dash_dist))
            self.target_pos = None
        elif key == "R":  # 정조준 일격 (초대형 관통 궁극기)
            dmg = 190 + self.ad * 1.1 + self.ap * 0.9
            projectiles.append(Projectile(self.x, self.y, mx, my, 15, dmg, 22, GOLD_COLOR, self.team, is_skill=True, pierce=True))

    def update(self, projectiles, floating_texts):
        if not self.alive:
            self.respawn_timer -= 1
            if self.respawn_timer <= 0:
                self.alive = True
                self.hp = self.max_hp
                self.mana = self.max_mana
                self.x = 110 if self.team == "blue" else WIDTH - 110
                self.y = HEIGHT // 2
                self.target_pos = None
                self.target_unit = None
            return

        # 자연 재생 및 쿨타임 감소
        self.hp = min(self.max_hp, self.hp + 0.08)
        self.mana = min(self.max_mana, self.mana + 0.25)
        if self.attack_cd > 0:
            self.attack_cd -= 1
        for k in self.cds:
            if self.cds[k] > 0:
                self.cds[k] -= 1

        # 타겟 공격 로직
        if self.target_unit and self.target_unit.alive:
            dist = get_dist((self.x, self.y), (self.target_unit.x, self.target_unit.y))
            if dist <= self.attack_range:
                self.target_pos = None
                if self.attack_cd == 0:
                    self.attack_cd = self.max_attack_cd
                    projectiles.append(Projectile(
                        self.x, self.y, self.target_unit.x, self.target_unit.y,
                        11, self.ad, 6, WHITE, self.team, target_entity=self.target_unit
                    ))
            else:
                angle = math.atan2(self.target_unit.y - self.y, self.target_unit.x - self.x)
                self.x += math.cos(angle) * self.speed
                self.y += math.sin(angle) * self.speed
        elif self.target_pos:
            dist = get_dist((self.x, self.y), self.target_pos)
            if dist > 4:
                angle = math.atan2(self.target_pos[1] - self.y, self.target_pos[0] - self.x)
                self.x += math.cos(angle) * self.speed
                self.y += math.sin(angle) * self.speed
            else:
                self.target_pos = None

    def draw(self, surf):
        if not self.alive:
            return
        # 사거리 가이드 (플레이어만 은은하게 표시)
        if self.team == "blue":
            pygame.draw.circle(surf, (70, 110, 150), (int(self.x), int(self.y)), self.attack_range, 1)

        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surf, GOLD_COLOR, (int(self.x), int(self.y)), self.radius, 2)

        # 체력바 + 마나바 + 레벨
        self.draw_hp_bar(surf, width=56, height=7, offset_y=16)
        bx = self.x - 28
        by = self.y - self.radius - 8
        pygame.draw.rect(surf, HP_BG, (bx, by, 56, 4))
        pygame.draw.rect(surf, MANA_BLUE, (bx, by, int(56 * (self.mana / self.max_mana)), 4))

        lvl_txt = font_sm.render(f"Lv.{self.level} {self.name}", True, WHITE)
        surf.blit(lvl_txt, (self.x - lvl_txt.get_width() // 2, self.y - self.radius - 34))

# --- AI 컨트롤러 (적 챔피언) ---
def update_ai(ai, player, all_units, projectiles, floating_texts, particles):
    if not ai.alive:
        return

    # 1. 적 미니언/플레이어 탐색
    nearest_enemy = None
    min_d = 380
    for u in all_units:
        if u.alive and u.team == "blue":
            d = get_dist((ai.x, ai.y), (u.x, u.y))
            if d < min_d:
                min_d = d
                nearest_enemy = u

    # 2. 체력이 낮으면 후퇴 및 W 회복
    if ai.hp < ai.max_hp * 0.35:
        ai.cast_skill("W", ai.x, ai.y, projectiles, floating_texts, particles)
        ai.target_unit = None
        ai.target_pos = (WIDTH - 120, HEIGHT // 2)
        return

    # 3. 교전 및 스킬 사용
    if nearest_enemy:
        ai.target_unit = nearest_enemy
        if min_d < 320 and ai.cds["Q"] == 0:
            ai.cast_skill("Q", nearest_enemy.x, nearest_enemy.y, projectiles, floating_texts, particles)
        if player.alive and get_dist((ai.x, ai.y), (player.x, player.y)) < 450 and ai.cds["R"] == 0:
            ai.cast_skill("R", player.x, player.y, projectiles, floating_texts, particles)
    else:
        ai.target_unit = None
        ai.target_pos = (WIDTH // 2 + 120, HEIGHT // 2)

# --- 메인 게임 루프 ---
def main():
    player = Champion(130, HEIGHT // 2, "blue", "이즈리얼(나)")
    enemy_champ = Champion(WIDTH - 130, HEIGHT // 2, "red", "라이즈(AI)")

    structures = [
        Structure(90, HEIGHT // 2, 2200, 34, "blue", is_nexus=True),
        Structure(340, HEIGHT // 2, 1200, 24, "blue", is_nexus=False),
        Structure(WIDTH - 90, HEIGHT // 2, 2200, 34, "red", is_nexus=True),
        Structure(WIDTH - 340, HEIGHT // 2, 1200, 24, "red", is_nexus=False),
    ]

    minions = []
    projectiles = []
    particles = []
    floating_texts = []
    click_markers = []

    wave_timer = 120
    game_over = None

    while True:
        mx, my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if game_over:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    main()
                continue

            # 마우스 우클릭: 이동 또는 타겟 공격
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3 and player.alive:
                if my < HEIGHT - 100:
                    clicked_enemy = None
                    for u in [enemy_champ] + minions + structures:
                        if u.alive and u.team == "red" and get_dist((mx, my), (u.x, u.y)) <= u.radius + 12:
                            clicked_enemy = u
                            break
                    if clicked_enemy:
                        player.target_unit = clicked_enemy
                        click_markers.append([clicked_enemy.x, clicked_enemy.y, 20, RED_TEAM])
                    else:
                        player.target_unit = None
                        player.target_pos = (mx, my)
                        click_markers.append([mx, my, 20, HP_GREEN])

            # 키보드 입력: 스킬(QWER), 스톱(S), 상점 구매(1, 2, 3)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    player.cast_skill("Q", mx, my, projectiles, floating_texts, particles)
                elif event.key == pygame.K_w:
                    player.cast_skill("W", mx, my, projectiles, floating_texts, particles)
                elif event.key == pygame.K_e:
                    player.cast_skill("E", mx, my, projectiles, floating_texts, particles)
                elif event.key == pygame.K_r:
                    player.cast_skill("R", mx, my, projectiles, floating_texts, particles)
                elif event.key == pygame.K_s:
                    player.target_pos = None
                    player.target_unit = None
                # 아이템 상점 단축키 (1: 롱소드, 2: 증폭의 고서, 3: 루비 수정)
                elif event.key == pygame.K_1 and player.gold >= 300:
                    player.gold -= 300
                    player.ad += 15
                    floating_texts.append(FloatingText(player.x, player.y - 30, "공격력 +15 구매!", GOLD_COLOR))
                elif event.key == pygame.K_2 and player.gold >= 300:
                    player.gold -= 300
                    player.ap += 22
                    floating_texts.append(FloatingText(player.x, player.y - 30, "주문력 +22 구매!", MANA_BLUE))
                elif event.key == pygame.K_3 and player.gold >= 300:
                    player.gold -= 300
                    player.max_hp += 160
                    player.hp += 160
                    floating_texts.append(FloatingText(player.x, player.y - 30, "최대체력 +160 구매!", HP_GREEN))

        if not game_over:
            # 미니언 웨이브 생성 (13초마다 3마리씩)
            wave_timer += 1
            if wave_timer >= 780:
                wave_timer = 0
                for i in range(3):
                    minions.append(Minion(160 - i * 35, HEIGHT // 2 + random.randint(-25, 25), "blue"))
                    minions.append(Minion(WIDTH - 160 + i * 35, HEIGHT // 2 + random.randint(-25, 25), "red"))

            all_units = [player, enemy_champ] + minions + structures

            # 업데이트
            player.update(projectiles, floating_texts)
            update_ai(enemy_champ, player, all_units, projectiles, floating_texts, particles)
            enemy_champ.update(projectiles, floating_texts)

            for s in structures:
                s.update(all_units, projectiles)

            for m in minions:
                res = m.update(all_units)
                if res and res[0] == "melee":
                    _, tgt, dmg = res
                    killed = tgt.take_damage(dmg, floating_texts, particles)
                    if killed and isinstance(tgt, Minion) and tgt.team == "red":
                        if get_dist((player.x, player.y), (tgt.x, tgt.y)) < 450:
                            player.gain_xp(25, floating_texts)

            # 투사체 충돌 처리
            for p in projectiles[:]:
                p.update()
                if p.life <= 0:
                    projectiles.remove(p)
                    continue

                for u in all_units:
                    if not u.alive or u.team == p.team or u in p.hit_list:
                        continue
                    if p.target_entity and p.target_entity != u:
                        continue

                    if get_dist((p.x, p.y), (u.x, u.y)) <= p.radius + u.radius:
                        col = GOLD_COLOR if p.is_skill else WHITE
                        killed = u.take_damage(p.damage, floating_texts, particles, col)
                        p.hit_list.append(u)

                        if killed and p.team == "blue":
                            if isinstance(u, Minion):
                                player.gold += 35
                                player.gain_xp(35, floating_texts)
                                floating_texts.append(FloatingText(u.x, u.y, "+35G", GOLD_COLOR))
                            elif isinstance(u, Champion):
                                player.gold += 300
                                player.gain_xp(150, floating_texts)
                                u.respawn_timer = 300
                                floating_texts.append(FloatingText(u.x, u.y, "적 처치! +300G", GOLD_COLOR))
                            elif isinstance(u, Structure):
                                player.gold += 250
                        elif killed and p.team == "red" and isinstance(u, Champion):
                            u.respawn_timer = 300

                        if not p.pierce:
                            if p in projectiles:
                                projectiles.remove(p)
                            break

            minions = [m for m in minions if m.alive]
            for pt in particles[:]:
                pt.update()
                if pt.life <= 0:
                    particles.remove(pt)
            for ft in floating_texts[:]:
                ft.update()
                if ft.timer <= 0:
                    floating_texts.remove(ft)

            # 승패 판정 (넥서스 파괴 여부)
            if not structures[0].alive:
                game_over = "패배 (DEFEAT)"
            elif not structures[2].alive:
                game_over = "승리 (VICTORY)"

        # --- 렌더링 ---
        screen.fill(BG_COLOR)

        # 맵 디자인 (강 & 미드 라인)
        pygame.draw.rect(screen, RIVER_COLOR, (WIDTH // 2 - 45, 0, 90, HEIGHT))
        pygame.draw.rect(screen, LANE_COLOR, (0, HEIGHT // 2 - 75, WIDTH, 150))
        pygame.draw.line(screen, (80, 75, 68), (0, HEIGHT // 2 - 75), (WIDTH, HEIGHT // 2 - 75), 3)
        pygame.draw.line(screen, (80, 75, 68), (0, HEIGHT // 2 + 75), (WIDTH, HEIGHT // 2 + 75), 3)

        # 클릭 이펙트
        for cm in click_markers[:]:
            pygame.draw.circle(screen, cm[3], (int(cm[0]), int(cm[1])), cm[2], 2)
            cm[2] -= 1
            if cm[2] <= 0:
                click_markers.remove(cm)

        for s in structures:
            s.draw(screen)
        for m in minions:
            m.draw(screen)
        player.draw(screen)
        enemy_champ.draw(screen)

        for p in projectiles:
            p.draw(screen)
        for pt in particles:
            pt.draw(screen)
        for ft in floating_texts:
            ft.draw(screen)

        # --- 하단 HUD 인터페이스 ---
        pygame.draw.rect(screen, DARK_UI, (0, HEIGHT - 100, WIDTH, 100))
        pygame.draw.line(screen, GOLD_COLOR, (0, HEIGHT - 100), (WIDTH, HEIGHT - 100), 2)

        # 챔피언 스탯 정보
        stats = [
            f"레벨: {player.level}   골드: {player.gold}G",
            f"공격력(AD): {player.ad}   주문력(AP): {player.ap}",
            f"체력: {int(player.hp)}/{player.max_hp}   마나: {int(player.mana)}/{player.max_mana}"
        ]
        for idx, text in enumerate(stats):
            col = GOLD_COLOR if idx == 0 else WHITE
            screen.blit(font_sm.render(text, True, col), (25, HEIGHT - 88 + idx * 26))

        # 스킬 아이콘 (Q, W, E, R)
        skill_names = {"Q": "Q: 화살", "W": "W: 회복", "E": "E: 점멸", "R": "R: 궁극기"}
        for i, key in enumerate(["Q", "W", "E", "R"]):
            bx = 380 + i * 95
            by = HEIGHT - 82
            cd = player.cds[key]
            box_col = (50, 90, 140) if cd == 0 else (45, 45, 50)
            pygame.draw.rect(screen, box_col, (bx, by, 80, 65), border_radius=6)
            pygame.draw.rect(screen, GOLD_COLOR if cd == 0 else (100, 100, 100), (bx, by, 80, 65), 2, border_radius=6)

            lbl = font_sm.render(skill_names[key], True, WHITE)
            screen.blit(lbl, (bx + 40 - lbl.get_width() // 2, by + 10))
            if cd > 0:
                cd_txt = font_md.render(f"{cd / 60:.1f}s", True, RED_TEAM)
                screen.blit(cd_txt, (bx + 40 - cd_txt.get_width() // 2, by + 34))
            else:
                cost_txt = font_sm.render(f"MP {player.mana_costs[key]}", True, MANA_BLUE)
                screen.blit(cost_txt, (bx + 40 - cost_txt.get_width() // 2, by + 36))

        # 상점 단축키 안내
        shop_info = [
            "[상점 - 300G 소모]",
            "[1] 롱소드 (AD +15)",
            "[2] 증폭의 고서 (AP +22)",
            "[3] 루비 수정 (HP +160)"
        ]
        for idx, line in enumerate(shop_info):
            col = GOLD_COLOR if idx == 0 else (200, 200, 200)
            screen.blit(font_sm.render(line, True, col), (800, HEIGHT - 92 + idx * 21))

        # 조작법 안내
        ctrl_info = [
            "[조작법]",
            "우클릭: 이동 / 기본공격",
            "Q, W, E, R: 마우스 방향 스킬",
            "S: 정지"
        ]
        for idx, line in enumerate(ctrl_info):
            col = GOLD_COLOR if idx == 0 else (180, 180, 180)
            screen.blit(font_sm.render(line, True, col), (1040, HEIGHT - 92 + idx * 21))

        # 부활 대기 알림
        if not player.alive:
            respawn_msg = font_lg.render(f"부활 대기 중... {player.respawn_timer / 60:.1f}초", True, RED_TEAM)
            screen.blit(respawn_msg, (WIDTH // 2 - respawn_msg.get_width() // 2, HEIGHT // 2 - 40))

        # 게임 종료 오버레이
        if game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            screen.blit(overlay, (0, 0))
            end_txt = font_lg.render(game_over, True, GOLD_COLOR if "승리" in game_over else RED_TEAM)
            restart_txt = font_md.render("R 키를 눌러 다시 시작하세요", True, WHITE)
            screen.blit(end_txt, (WIDTH // 2 - end_txt.get_width() // 2, HEIGHT // 2 - 50))
            screen.blit(restart_txt, (WIDTH // 2 - restart_txt.get_width() // 2, HEIGHT // 2 + 20))

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
