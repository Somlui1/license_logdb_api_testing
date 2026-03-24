import os
import sys
import requests
import subprocess
import tempfile
import questionary
from questionary import Choice

# ===========================================================================
#  CONFIGURATION
# ===========================================================================
BASE_API_URL = "http://10.10.3.215:8181/tools/cli-tools/choice"
BASE_SCRIPT_URL = "http://10.10.3.215:8181/tools/cli-tools/choice/download"

# Folder structure per your design
INSTALLER_DIR = os.path.join(tempfile.gettempdir(), "itsupport_tools")
CHOICE_DIR = os.path.join(INSTALLER_DIR, "choice")
COMPONENT_DIR = os.path.join(INSTALLER_DIR, "component")

# Enable ANSI colors for Windows Terminal
if os.name == 'nt':
    os.system('color')

def show_banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    banner = """
      ___    _____            ___            _ __    _ __                    _     
     |_ _|  |_   _|    o O O / __|   _  _   | '_ \  | '_ \   ___      _ _   | |_   
      | |     | |     o      \__ \  | +| |  | .__/  | .__/  / _ \    | '_|  |  _|  
     |___|   _|_|_   TS__[O] |___/   \_,_|  |_|__   |_|__   \___/   _|_|_   _\__|  
    _|""\"""|_|""\"""| {======|_|""\"""|_|""\"""|_|""\"""|_|""\"""|_|""\"""|_|""\"""|_|""\"""|___ 
    "`-0-0-'"`-0-0-'./o--000'"`-0-0-'"`-0-0-'"`-0-0-'"`-0-0-'"`-0-0-'"`-0-0-'"`-0-0-' 
    """
    print(f"\033[96m{banner}\033[0m")
    print("  \033[36mBootstrapper Installer v2.0 (Python TUI Edition)\033[0m")
    print("  \033[90mDynamic Setup via API\033[0m\n")
    print("  \033[90m" + ("-" * 64) + "\033[0m\n")

def setup_workspace():
    print("\033[93m [*] Cleaning workspace...\033[0m")
    os.makedirs(CHOICE_DIR, exist_ok=True)
    os.makedirs(COMPONENT_DIR, exist_ok=True)
    print(f"\033[92m [OK] Workspace ready -> {INSTALLER_DIR}\033[0m\n")

def fetch_choices():
    print(f"\033[93m [*] Contacting API: {BASE_API_URL} ...\033[0m")
    try:
        response = requests.get(BASE_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "success":
            choices = data.get("data", [])
            print(f"\033[92m [OK] API returned {len(choices)} available choice(s).\033[0m\n")
            return choices
        else:
            print(f"\033[91m [!] API Error: {data.get('message')}\033[0m")
            return []
    except Exception as e:
        print(f"\033[91m [!] Failed to fetch choices: {e}\033[0m")
        return []

def download_script(file_name):
    local_path = os.path.join(CHOICE_DIR, file_name)
    
    # Check Cache
    if os.path.exists(local_path):
        print(f"\033[90m     Cached: {file_name} (using local copy)\033[0m")
        return local_path

    remote_url = f"{BASE_SCRIPT_URL}/{file_name}"
    print(f"\033[93m [*] Downloading: {file_name} ...\033[0m")
    
    try:
        response = requests.get(remote_url, timeout=15)
        response.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(response.content)
        print(f"\033[92m [OK] Downloaded: {file_name}\033[0m")
        return local_path
    except Exception as e:
        print(f"\033[91m [!] Download failed for {file_name}: {e}\033[0m")
        return None

def execute_script(file_name):
    local_path = download_script(file_name)
    if not local_path:
        return False, "Download failed"

    print(f"\033[93m [*] Executing: {file_name} ...\033[0m")
    try:
        # Assuming the downloaded files are PowerShell (.ps1) scripts
        # If they are .exe or .bat, you can change the command here.
        cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", local_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return True, "Installed successfully"
        else:
            return False, f"Execution failed: {result.stderr.strip()}"
    except Exception as e:
        return False, str(e)

def main():
    show_banner()
    setup_workspace()

    # Step 1: Fetch API
    choices_data = fetch_choices()
    if not choices_data:
        print("\033[91m [!] No choices available from API. Exiting.\033[0m")
        sys.exit(1)

    # Step 2: Interactive Menu using Questionary
    q_choices = [
        Choice(title=f"{c['name']} (priority: {c['priority']})", value=c)
        for c in choices_data
    ]

    selected = questionary.checkbox(
        "Select choice(s) to install:",
        choices=q_choices,
        instruction="(Use Space to toggle, Up/Down to navigate, Enter to submit)"
    ).ask()

    if not selected:
        print("\n\033[91m [!] No choices selected. Exiting installer.\033[0m")
        sys.exit(0)

    # Step 3: Sort by Priority
    selected.sort(key=lambda x: int(x['priority']))

    show_banner()
    print("\033[97m  Execution Queue (sorted by priority):\033[0m\n")
    for i, task in enumerate(selected, 1):
        print(f"    {i}. \033[33m[Priority: {task['priority']}]\033[0m \033[96m{task['name']}\033[0m -> \033[90m{task['script']}\033[0m")
    print("\n\033[90m" + ("-" * 64) + "\033[0m\n")

    # Step 4: Execute
    results = []
    total = len(selected)

    for i, task in enumerate(selected, 1):
        print(f"\n\033[90m" + ("-" * 64) + "\033[0m")
        print(f"\033[97m  [{i}/{total}] {task['name']} (Priority: {task['priority']})\033[0m")
        print(f"\033[90m" + ("-" * 64) + "\033[0m")

        success, details = execute_script(task['script'])
        results.append({
            "name": task['name'],
            "priority": task['priority'],
            "status": "OK" if success else "FAILED",
            "details": details
        })

    # Step 5: Summary Report
    print("\n\n\033[90m" + ("=" * 64) + "\033[0m")
    print("\033[97m  INSTALLATION SUMMARY\033[0m")
    print("\033[90m" + ("=" * 64) + "\033[0m\n")

    success_count = 0
    for r in results:
        if r['status'] == 'OK':
            success_count += 1
            print(f"  \033[92m[OK]\033[0m \033[97m{r['name']}\033[0m \033[90m(priority: {r['priority']})\033[0m -- \033[92mInstalled\033[0m")
        else:
            print(f"  \033[91m[!!]\033[0m \033[97m{r['name']}\033[0m \033[90m(priority: {r['priority']})\033[0m -- \033[91mFailed\033[0m")
            print(f"       \033[90m{r['details']}\033[0m")

    print(f"\n\033[90m" + ("-" * 64) + "\033[0m")
    if success_count == total:
        print(f"  \033[92mAll {success_count} choice(s) installed successfully!\033[0m")
    else:
        print(f"  \033[33m{success_count} succeeded, {total - success_count} failed.\033[0m")
    print(f"\033[90m" + ("-" * 64) + "\033[0m\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\033[91m [!] Installation aborted by user.\033[0m")
        sys.exit(0)