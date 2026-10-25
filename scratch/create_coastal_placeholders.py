"""
Generate rich coastal editorial texture images for Waqt
"""
import os
from PIL import Image, ImageDraw

static_img_dir = r"s:\Project\Kadu Capstone\static\images"
os.makedirs(static_img_dir, exist_ok=True)

# 1. coastal-hero.jpg (1600x600 deep marine coastal gradient with subtle water ripple waves)
hero_img = Image.new("RGB", (1600, 600), (15, 44, 45)) # deep-tide
draw_hero = ImageDraw.Draw(hero_img)

# Deep ocean gradient
for y in range(600):
    factor = y / 600.0
    r = int(15 * (1 - factor) + 24 * factor)
    g = int(44 * (1 - factor) + 68 * factor)
    b = int(45 * (1 - factor) + 70 * factor)
    draw_hero.line([(0, y), (1600, y)], fill=(r, g, b))

# Coastal contour lines in subtle turmeric & sand
for i in range(12):
    y_base = 250 + i * 28
    draw_hero.arc([(-200 + i * 40, y_base - 100), (1800, y_base + 300)], start=0, end=180, fill=(35, 80, 82), width=2)

hero_img.save(os.path.join(static_img_dir, "coastal-hero.jpg"), quality=90)
print("Created coastal-hero.jpg")

# 2. coastal-card.jpg (600x400 warm twilight harbor texture)
card_img = Image.new("RGB", (600, 400), (22, 54, 56))
draw_card = ImageDraw.Draw(card_img)

for y in range(400):
    factor = y / 400.0
    r = int(22 * (1 - factor) + 40 * factor)
    g = int(54 * (1 - factor) + 75 * factor)
    b = int(56 * (1 - factor) + 78 * factor)
    draw_card.line([(0, y), (600, y)], fill=(r, g, b))

for j in range(8):
    y_wave = 150 + j * 30
    draw_card.arc([(-100, y_wave), (700, y_wave + 150)], start=0, end=180, fill=(45, 95, 98), width=2)

card_img.save(os.path.join(static_img_dir, "coastal-card.jpg"), quality=90)
print("Created coastal-card.jpg")
