import torch
import os
import sys
from huggingface_hub import hf_hub_download

# Setup
sys.path.append(os.path.abspath('ext/SepACap'))
from src.model import Model
from src.utils import util_system

config_path = 'ext/SepACap/configs/modelMusicSep.yaml'
config = util_system.parse_yaml(config_path)["config"]

model = Model(**config["model"])

params = sum(p.numel() for p in model.parameters())
params_mb = params * 4 / (1024 ** 2) # fp32
print(f"Model parameters: {params/1e6:.2f}M")
print(f"Model size in memory: {params_mb:.2f} MB")

# To estimate VRAM for a 45-second chunk (batch=1, channel=1, length=45*24000=1080000)
# We can't actually allocate the activations on CPU easily without running it, but we can do a dry run with float16 or just CPU if we have enough RAM
