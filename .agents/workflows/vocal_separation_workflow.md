---
description: Vocal Separation Workflow
---
# Vocal Separation Workflow

This workflow represents the first major step of A Cappella processing.

1. Use **htdemucs** (https://github.com/facebookresearch/demucs) to isolate the vocal percussion as a "drums" channel.
2. Use **SepACap** (https://github.com/ETH-DISCO/SepACap), **BS-RoFormer**, or **Mel-Band RoFormer** (https://github.com/ZFTurbo/Music-Source-Separation-Training) to process the "VP-less" mix and split it into SATB (Soprano, Alto, Tenor, Bass) components.
