import shutil

src = "/home/no-khushu/.gemini/antigravity-ide/brain/2292fd89-ff53-4038-b65a-a56e2c530ac2/dashboard_mockup_1780842636057.png"
dst = "/home/no-khushu/Documents/Project/Hacathon/IncidentOS-AI/frontend/public/dashboard-mockup.png"

try:
    shutil.copyfile(src, dst)
    print("Copied successfully.")
except Exception as e:
    print(f"Error copying: {e}")
