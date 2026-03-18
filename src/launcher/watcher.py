import os
import time
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigChangeHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_run = 0
        self.root = Path("/app")

    def on_modified(self, event):
        # Debounce: prevent multiple triggers for a single save
        if time.time() - self.last_run < 2:
            return
        
        if event.is_directory or not event.src_path.endswith(('.yaml', '.yml')):
            return

        print(f"Detected change in {event.src_path}. Triggering update...")
        self.last_run = time.time()

        try:
            # 1. Regenerate all configs using the process manager
            print("Regenerating configs...")
            subprocess.run(["python3", "-m", "src.launcher.process_manager", "--root", str(self.root), "generate-configs"], check=True)

            # 2. Reload Nginx (Internal only)
            if os.getenv("NGINX_INTERNAL", "true").lower() == "true":
                print("Reloading internal Nginx...")
                subprocess.run(["docker", "exec", "audia-nginx", "nginx", "-s", "reload"], check=False)

            # 3. Restart Llama-swap (Required as it lacks native SIGHUP support)
            if os.getenv("LLAMA_SWAP_INTERNAL", "true").lower() == "true":
                print("Restarting Llama-swap container...")
                subprocess.run(["docker", "restart", "audia-llama-cpp"], check=False)

            print("Update complete. LiteLLM Gateway reloads its own config automatically.")
        except Exception as e:
            print(f"Error during hot-reload: {e}")

if __name__ == "__main__":
    config_root = os.getenv("CONFIG_ROOT", "/app/config")
    print(f"Watcher started. Monitoring {config_root}/project and {config_root}/local")
    
    observer = Observer()
    handler = ConfigChangeHandler()
    
    # Monitor both project defaults and local overrides
    project_path = os.path.join(config_root, "project")
    local_path = os.path.join(config_root, "local")
    
    if os.path.exists(project_path):
        observer.schedule(handler, project_path, recursive=False)
    if os.path.exists(local_path):
        observer.schedule(handler, local_path, recursive=False)
        
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
