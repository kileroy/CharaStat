import subprocess
import os
import signal
import time

# Fonction pour démarrer le bot
def start_bot():
    venv_python = os.path.join(".", "env", "Scripts", "python.exe")
    process = subprocess.Popen([venv_python, "bot.py"])
    return process

# Fonction pour arrêter le bot
def stop_bot(process):
    if process:
        print("Arrêt du bot...")
        process.terminate()  # Terminer le processus
        process.wait()  # Attendre que le processus soit effectivement terminé

if __name__ == "__main__":
    bot_process = None

    while True:
        cmd = input("Commande (reset / quit) > ").strip().lower()

        if cmd == "reset":
            if bot_process:
                stop_bot(bot_process)  # Stopper le bot précédent
            bot_process = start_bot()  # Démarrer le bot
            print("Bot redémarré.")

        elif cmd == "quit":
            if bot_process:
                stop_bot(bot_process)  # Stopper le bot avant de quitter
            print("Fermeture du launcher.")
            break