# PlatformIO pre-build script:
# set per-env source directory (src/entry | src/exit) berdasarkan nama env,
# karena `src_dir` hanya bisa di blok [platformio] global (tidak per-env).
#
# Referensi:
#   PROJECT_SRC_DIR  = variabel modern (Project Configuration)
#   PROJECTSRC_DIR   = legacy (dipakai platform espressif32 untuk sdkconfig dll)
Import("env")
import os

env_name = env.subst("$PIOENV")
unit = "exit" if "exit" in env_name else "entry"
src = os.path.join(env.subst("$PROJECT_DIR"), "src", unit)

env["PROJECT_SRC_DIR"] = src
env["PROJECTSRC_DIR"] = src  # legacy, tetap di-set agar platform espressif32 konsisten

print(">> [%s] PROJECT_SRC_DIR = %s" % (env_name, src))