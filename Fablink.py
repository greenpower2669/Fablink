import sys
import os
import json
import subprocess
import time
from PyQt5.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QAction, 
                             QWidget, QDialog, QLineEdit, QFormLayout, 
                             QDialogButtonBox, QMessageBox, QVBoxLayout, QLabel, QPushButton)
from PyQt5.QtGui import QIcon, QCursor
from PyQt5.QtCore import Qt, QSize, QCoreApplication
from PyQt5.QtNetwork import QLocalServer, QLocalSocket

class SingleApplication(QApplication):
    def __init__(self, id, *args, **kwargs):
        super(SingleApplication, self).__init__(*args, **kwargs)
        self._id = id
        self._activationWindow = None
        self._activateOnMessage = None

        self._outSocket = QLocalSocket()
        self._outSocket.connectToServer(self._id)
        self._isRunning = self._outSocket.waitForConnected()

        if self._isRunning:
            self._outSocket.disconnectFromServer()
        else:
            self._outSocket = None
            self._inSocket = None
            self._server = QLocalServer()
            self._server.listen(self._id)
            self._server.newConnection.connect(self._onNewConnection)

    def isRunning(self):
        return self._isRunning

    def _onNewConnection(self):
        if self._inSocket:
            self._inSocket.readyRead.disconnect(self._onReadyRead)
        self._inSocket = self._server.nextPendingConnection()
        if not self._inSocket:
            return
        self._inSocket.readyRead.connect(self._onReadyRead)

    def _onReadyRead(self):
        if self._activationWindow and self._activateOnMessage:
            self._activationWindow.setWindowState(self._activationWindow.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
            self._activationWindow.raise_()
            self._activationWindow.activateWindow()

    def setActivationWindow(self, activationWindow, activateOnMessage = True):
        self._activationWindow = activationWindow
        self._activateOnMessage = activateOnMessage

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Paramètres")
        layout = QFormLayout(self)
        
        self.shortcut_dir = QLineEdit(self)
        self.button_height = QLineEdit(self)
        
        layout.addRow("Répertoire des raccourcis:", self.shortcut_dir)
        layout.addRow("Hauteur des boutons:", self.button_height)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

class InfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Information sur FabLinks")
        layout = QVBoxLayout(self)
        
        info_text = """
        FabLinks - Gestionnaire de raccourcis
        
        Fonctionnement :
        1. L'icône FabLinks apparaît dans la barre des tâches.
        2. Cliquez sur l'icône pour ouvrir le menu des raccourcis.
        3. Sélectionnez un raccourci pour l'ouvrir.
        4. Clic droit sur l'icône pour accéder aux options.
        
        Options :
        - Paramètres : Modifier le répertoire des raccourcis et la hauteur des boutons.
        - Quitter : Fermer l'application.
        
        Note : Les raccourcis (.lnk) doivent être placés dans le répertoire spécifié.
        """
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        close_button = QPushButton("Fermer")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

class FabLinks(QWidget):
    def __init__(self):
        super().__init__()
        self.load_config()
        self.init_ui()
        
    def load_config(self):
        default_config = {
            'shortcut_dir': 'rac',
            'window_size': [300, 400],
            'button_height': 40
        }
        try:
            with open('config.json', 'r') as f:
                self.config = json.load(f)
            for key, value in default_config.items():
                if key not in self.config:
                    self.config[key] = value
        except FileNotFoundError:
            self.config = default_config
            self.save_config()
        print("Configuration chargée")
        
    def save_config(self):
        with open('config.json', 'w') as f:
            json.dump(self.config, f)
        print("Configuration sauvegardée")
        
    def init_ui(self):
        window_size = self.config.get('window_size', [300, 400])
        self.setGeometry(300, 300, *window_size)
        self.setWindowTitle('FabLinks')
        
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(os.path.join('rac', 'icon.png')))
        self.tray_icon.setToolTip("FabLinks")
        
        self.menu = QMenu()
        self.update_menu()
        
        self.tray_icon.setContextMenu(self.create_context_menu())
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()
        
    def update_menu(self):
        self.menu.clear()
        
        close_action = QAction("X", self)
        close_action.triggered.connect(self.close)
        self.menu.addAction(close_action)
        
        self.menu.addSeparator()
        
        shortcut_dir = self.config['shortcut_dir']
        for filename in os.listdir(shortcut_dir):
            if filename.endswith('.lnk'):
                name = os.path.splitext(filename)[0]
                icon_path = os.path.join(shortcut_dir, f"{name}.png")
                if os.path.exists(icon_path):
                    icon = QIcon(icon_path)
                else:
                    icon = QIcon()
                
                action = QAction(icon, name, self)
                action.triggered.connect(lambda checked, f=filename: self.open_shortcut(f))
                self.menu.addAction(action)
        
        print("Menu mis à jour")
        
    def create_context_menu(self):
        menu = QMenu()
        
        info_action = QAction("Info", self)
        info_action.triggered.connect(self.show_info)
        menu.addAction(info_action)
        
        settings_action = QAction("Paramètres", self)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)
        
        quit_action = QAction("Quitter", self)
        quit_action.triggered.connect(self.quit)
        menu.addAction(quit_action)
        
        return menu
        
    def open_shortcut(self, filename):
        full_path = os.path.join(self.config['shortcut_dir'], filename)
        subprocess.Popen(f'start "" "{full_path}"', shell=True)
        print(f"Raccourci ouvert: {filename}")
        
    def show_info(self):
        dialog = InfoDialog(self)
        dialog.exec_()
        print("Information affichée")
        
    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.shortcut_dir.setText(self.config['shortcut_dir'])
        dialog.button_height.setText(str(self.config['button_height']))
        
        if dialog.exec_():
            self.config['shortcut_dir'] = dialog.shortcut_dir.text()
            self.config['button_height'] = int(dialog.button_height.text())
            self.save_config()
            self.update_menu()
        print("Paramètres ouverts")
        
    def quit(self):
        print("Quitting application...")
        self.save_config()
        self.cleanup()
        QCoreApplication.instance().quit()
        time.sleep(0.5)  # Attendre 500 ms avant de terminer
        sys.exit(0)
        
    def cleanup(self):
        print("Performing cleanup...")
        if self.tray_icon:
            self.tray_icon.hide()
            self.tray_icon.deleteLater()
        # Ajoutez ici d'autres opérations de nettoyage si nécessaire
        
    def closeEvent(self, event):
        print("Close event received")
        self.quit()
        event.accept()

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.menu.popup(QCursor.pos())

if __name__ == '__main__':
    app = SingleApplication('FabLinks_unique_id', sys.argv)
    if app.isRunning():
        print("Une autre instance est déjà en cours d'exécution.")
        sys.exit(0)
    ex = FabLinks()
    app.setActivationWindow(ex)
    exit_code = app.exec_()
    sys.exit(exit_code)