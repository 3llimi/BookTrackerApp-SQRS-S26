import subprocess
import sys

result = subprocess.run(
    ["radon", "cc", "src/", "-a", "-s"],
    capture_output=True,
    text=True
)

print(result.stdout)

# fail if any grade C, D, or F found in output
if " C " in result.stdout or " D " in result.stdout or " F " in result.stdout:
    print("❌ Complexity gate failed: grade C or worse found")
    sys.exit(1)

print("✅ Complexity gate passed")
sys.exit(0)