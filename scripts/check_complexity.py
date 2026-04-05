import subprocess
import sys

result = subprocess.run(
    ["radon", "cc", "src/", "-a", "-s"], capture_output=True, text=True
)

print(result.stdout)

# the grade is the letter AFTER the dash at the end of each line
bad_grades = []
for line in result.stdout.splitlines():
    if " - " in line:
        # extract the grade letter after the last " - "
        grade = line.split(" - ")[-1].strip()[0]  # first char after " - "
        if grade in ("C", "D", "F"):
            bad_grades.append(line.strip())

if bad_grades:
    print("\n❌ Complexity gate failed — grade C or worse found:")
    for line in bad_grades:
        print(f"  {line}")
    sys.exit(1)

print("✅ Complexity gate passed")
sys.exit(0)
