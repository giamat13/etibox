"""Join Blender render frames into animated GIFs: models/sim/renders/<tag>_NNNN.png -> models/sim/<tag>.gif"""
import glob, os, re
from PIL import Image, ImageDraw

files = sorted(glob.glob("models/sim/renders/*_[0-9][0-9][0-9][0-9].png"))
groups = {}
for f in files:
    groups.setdefault(re.sub(r"_\d{4}\.png$", "", os.path.basename(f)), []).append(f)
for tag, fs in groups.items():
    frames = []
    for f in fs:
        im = Image.open(f).convert("RGB")
        ImageDraw.Draw(im).text((10, 10), tag.replace("_", "  "), fill=(0, 0, 0))
        frames.append(im)
    frames[0].save(f"models/sim/{tag}.gif", save_all=True, append_images=frames[1:], duration=80, loop=0)
    print(tag, len(frames), "frames")
