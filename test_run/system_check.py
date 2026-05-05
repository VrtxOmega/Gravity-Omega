import platform
import os
import datetime

def get_system_info():
    """Gather and print system information"""
    print("=== SYSTEM INFORMATION ===")
    print(f"Operating System: {platform.system()} {platform.release()}")
    print(f"OS Version: {platform.version()}")
    print(f"CPU Count: {os.cpu_count()}")
    print(f"Python Version: {platform.python_version()}")
    print(f"Current Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Machine Architecture: {platform.machine()}")
    print(f"Processor: {platform.processor()}")
    print("==========================")

if __name__ == "__main__":
    get_system_info()