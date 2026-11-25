# -*- coding: utf-8 -*-
"""生成应用图标 icon.ico（绿色圆角方块 + 白色“音”）"""
from PIL import Image, ImageDraw, ImageFont

SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# 绿色圆角方块
d.rounded_rectangle([0, 0, SIZE, SIZE], radius=48, fill=(76, 175, 80, 255))

# 白色“音”
text = "音"
font = None
for fp in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc",
           r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\simsun.ttc"):
    try:
        font = ImageFont.truetype(fp, 150)
        break
    except Exception:
        continue
if font is None:
    font = ImageFont.load_default()

bbox = d.textbbox((0, 0), text, font=font)
w = bbox[2] - bbox[0]
h = bbox[3] - bbox[1]
x = (SIZE - w) / 2 - bbox[0]
y = (SIZE - h) / 2 - bbox[1]
d.text((x, y), text, font=font, fill=(255, 255, 255, 255))

out = r"C:\Users\chen\Desktop\VoiceInput\icon.ico"
img.save(out, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("saved", out)
