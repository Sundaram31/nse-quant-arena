"""Cross-Platform GUI App Launcher (Windows, Mac, Linux) - Safe & Antivirus-Friendly."""
import sys
import os
import time
import subprocess
import webbrowser
import threading

def run_streamlit():
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nse_system', 'dashboard', 'app.py')
    cmd = [
        sys.executable,
        '-m',
        'streamlit',
        'run',
        app_path,
        '--server.port', '8501',
        '--server.address', '0.0.0.0',
        '--server.headless', 'false',
        '--browser.gatherUsageStats', 'false'
    ]
    subprocess.run(cmd)

def open_browser():
    time.sleep(1.5)
    webbrowser.open('http://localhost:8501')

def main():
    print('Starting NSE Quantitative Trading Platform...')
    print('Opening your web browser at http://localhost:8501')
    
    # Open browser in separate thread
    t = threading.Thread(target=open_browser, daemon=True)
    t.start()

    # Start Streamlit server
    run_streamlit()

if __name__ == '__main__':
    main()
