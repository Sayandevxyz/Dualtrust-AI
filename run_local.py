"""
DualTrust AI — One-Command Local Runner
Starts both the FastAPI Backend (port 8000) and the Vite Frontend (port 5173),
seeds the database, and launches the browser.
"""
import os
import sys
import subprocess
import time
import webbrowser
import signal

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")


def main():
    print("=" * 60)
    print("  DUALTRUST AI — FRAUD-RESILIENT LOAN UNDERWRITING")
    print("  Team: Destroyers X")
    print("=" * 60)

    # 1. Ensure seed data is generated
    print("\n[1/3] Ensuring database is seeded with 3 demo scenarios...")
    try:
        subprocess.run([sys.executable, "-m", "app.utils.seed_data"], cwd=BACKEND_DIR, check=True)
    except Exception as e:
        print(f"[WARN] Seed script encountered: {e}. Continuing...")

    # 2. Start Backend
    print("\n[2/3] Starting FastAPI Backend on http://localhost:8000...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=BACKEND_DIR
    )

    # Give backend a moment to boot
    time.sleep(2)

    # 3. Start Frontend
    print("\n[3/3] Starting Vite Frontend on http://localhost:5173...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=FRONTEND_DIR
    )

    time.sleep(2)
    frontend_url = "http://localhost:5173"
    print("\n" + "=" * 60)
    print(f"  DualTrust AI is running!")
    print(f"  Frontend Dashboard: {frontend_url}")
    print(f"  Backend API Docs:   http://localhost:8000/docs")
    print(f"  Demo Credentials:   demo@dualtrust.ai / demo1234")
    print("=" * 60)
    print("  Press Ctrl+C to terminate both servers.")
    print("=" * 60 + "\n")

    try:
        webbrowser.open(frontend_url)
    except Exception:
        pass

    try:
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None:
                print("[ERROR] Backend process exited unexpectedly.")
                break
            if frontend_proc.poll() is not None:
                print("[ERROR] Frontend process exited unexpectedly.")
                break
    except KeyboardInterrupt:
        print("\nStopping DualTrust AI services...")
    finally:
        for proc in (backend_proc, frontend_proc):
            try:
                if sys.platform == "win32":
                    subprocess.call(["taskkill", "/F", "/T", "/PID", str(proc.pid)])
                else:
                    proc.terminate()
            except Exception:
                pass
        print("DualTrust AI services stopped cleanly.")


if __name__ == "__main__":
    main()
