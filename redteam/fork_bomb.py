# Hostile: fork until something stops us. Children exec a tiny `sleep`, so memory is
# not what runs out first. Expected: the pids limit (128).
import os

n = 0
while True:
    if os.fork() == 0:
        os.execv("/bin/sleep", ["sleep", "120"])
    n += 1
    print("forked", n, flush=True)
