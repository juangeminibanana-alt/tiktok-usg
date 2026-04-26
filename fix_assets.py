import os
from pathlib import Path

pack_dir = Path("character_pack")

renames = {
    "42984832-c143-4727-af6a-b583cbee5369.jpg": "juan_anchor.jpg",
    "hombre_202604250538.jpeg": "juan_mirror.jpg",
    "Gemini_Generated_Image_5tlb7x5tlb7x5tlb.png": "product_jacket.png"
}

for old, new in renames.items():
    old_path = pack_dir / old
    new_path = pack_dir / new
    if old_path.exists():
        os.rename(old_path, new_path)
        print(f"✅ Renombrado: {old} -> {new}")
    else:
        print(f"⚠️ No se encontró: {old}")

print("\n¡Todo listo! Ya puedes correr: python langgraph_orchestrator.py")
