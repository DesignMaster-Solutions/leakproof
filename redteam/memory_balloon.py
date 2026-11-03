# Hostile: grab 1.5 GB of RAM, 64 MB at a time, touching every page. Expected: the memory limit (512 MB).
blocks = []
for i in range(24):
    blocks.append(bytearray(b"x") * (64 * 1024 * 1024))
    print("allocated_mb", (i + 1) * 64, flush=True)
print("BALLOON_DONE")
