import tkinter as tk
from tkinter import scrolledtext
from threading import Thread
import requests
import xml.etree.ElementTree as ET
from requests.exceptions import RequestException
import concurrent.futures
import urllib.parse

# ------------- LOGIKA DRUKAREK ---------------

def detect_printer(ip):
    try:
        url_hp = f"http://{ip}/cdm/print/v1/mediaConfiguration"
        resp_hp = requests.get(url_hp, timeout=1, verify=False)
        if resp_hp.status_code == 200:
            return 'HP', ip

        url_lex = f"http://{ip}/webglue/content?depth=0&c=TrayConfiguration&lang=en"
        resp_lex = requests.get(url_lex, timeout=1)
        if resp_lex.status_code == 200 and 'TrayConfiguration' in resp_lex.text:
            return 'Lexmark', ip

    except RequestException:
        pass
    return None, ip

def change_hp_paper_size(ip, log):
    url = f"https://{ip}/cdm/print/v1/mediaConfiguration"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*"
    }

    payload = {
        "version": "1.1.0",
        "mediaSettings": {
            "tray2": {
                "mediaSize": "iso_a4_210x297mm",
                "mediaType": "plain"
            }
        }
    }

    try:
        resp = requests.put(url, json=payload, headers=headers, timeout=3, verify=False)
        if resp.status_code == 200:
            log("HP: Settings changed successfully using JSON API!")
            return True
        else:
            log(f"HP: Failed to change settings. Status code: {resp.status_code}")
    except Exception as e:
        log(f"HP: Error: {e}")
    return False


def change_lexmark_paper_size(ip, log):
    url = f"http://{ip}/webglue/content"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"http://{ip}/",
        "Origin": f"http://{ip}",
        "User-Agent": "Mozilla/5.0"
    }
    data = {
        "data": '{"Tray1Size":"22"}',
        "c": "TrayConfiguration",
        "lang": "en"
    }
    try:
        resp = requests.post(url, data=data, headers=headers, timeout=1)
        if resp.status_code == 200:
            log("Lexmark: Settings changed successfuly!")
            return True
        else:
            log(f"Lexmark: Sending error: {resp.status_code}")
            return False
    except Exception as e:
        log(f"Lexmark: Error: {e}")
        return False

# ------------- FUNKCJA GŁÓWNA Z WĄTKAMI ---------------

import threading

def find_and_configure_printer(log, enable_close_button):
    base_ip = "192.168.1."
    ip_range = range(130, 181)
    log(f"Scanning subnet {base_ip}{ip_range.start}-{ip_range.stop - 1}...")

    found_event = threading.Event()

    def check_ip(i):
        if found_event.is_set():
            return False

        ip = base_ip + str(i)
        log(f"Checking {ip}...")

        printer_type, ip_found = detect_printer(ip)
        if printer_type:
            found_event.set()
            log(f"Found {printer_type} printer at {ip_found}")
            if printer_type == 'HP':
                success = change_hp_paper_size(ip_found, log)
            elif printer_type == 'Lexmark':
                success = change_lexmark_paper_size(ip_found, log)
            else:
                log("Unsupported printer type.")
                success = False

            if success:
                log("Done! :)")
            else:
                log("Failed to change settings.")
            return True
        return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_ip, i): i for i in ip_range}
        for future in concurrent.futures.as_completed(futures):
            if found_event.is_set():
                break

    if not found_event.is_set():
        log("No printer found in the subnet.")
    enable_close_button()


# ------------- GUI TKINTER ---------------

def run_gui():
    window = tk.Tk()
    window.title("Printer Page Fixer")
    window.geometry("800x600")

    log_area = scrolledtext.ScrolledText(window, wrap=tk.WORD, state='disabled', font=("Consolas", 10))
    log_area.pack(expand=True, fill='both', padx=10, pady=10)

    def log(message):
        log_area.configure(state='normal')
        log_area.insert(tk.END, message + "\n")
        log_area.configure(state='disabled')
        log_area.see(tk.END)

    def enable_close():
        close_button.config(state=tk.NORMAL)

    def start_scan():
        start_button.config(state=tk.DISABLED)
        log("Starting scan...")
        Thread(target=lambda: find_and_configure_printer(log, enable_close)).start()

    start_button = tk.Button(window, text="Start", command=start_scan, font=("Arial", 12))
    start_button.pack(pady=5)

    close_button = tk.Button(window, text="Close", command=window.destroy, state=tk.DISABLED, font=("Arial", 12))
    close_button.pack(pady=5)

    window.mainloop()

if __name__ == "__main__":
    run_gui()
