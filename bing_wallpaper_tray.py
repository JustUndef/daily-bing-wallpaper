# -*- coding: utf-8 -*-
"""
Bing Wallpaper Downloader - System Tray Manager
Manages wallpaper auto-download, enables/disables scheduled task, and allows navigation through downloaded wallpapers.
"""

import ctypes
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw
except ImportError:
    print("Error: Required packages not installed.")
    print("Please install: pip install pystray pillow")
    sys.exit(1)

# Configuration storage
CONFIG_FILE = Path(os.getenv('APPDATA', '')) / 'BingWallpaperDownloader' / 'config.json'
TASK_NAME = "BingWallpaperDownloader"


class WallpaperManager:
    def __init__(self):
        self.config = self.load_config()
        self.wallpaper_dir = Path(self.config.get('download_folder', str(Path.home() / "Pictures" / "BingWallpapers")))
        self.current_wallpaper_index = 0
        self.wallpapers: List[Path] = []
        self.auto_enabled = self.is_task_enabled()
        self.user_paused = self.config.get('user_paused', False)
        self.refresh_wallpaper_list()
        
    def load_config(self) -> dict:
        """Load configuration from JSON file"""
        if not CONFIG_FILE.exists():
            return {}
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def save_config(self):
        """Save configuration to file"""
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing config
        config = self.load_config()
        
        # Update with tray-specific settings
        config['user_paused'] = self.user_paused
        config['last_manual_selection'] = datetime.now().isoformat()
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
    
    def refresh_wallpaper_list(self):
        """Scan wallpaper directory and build sorted list"""
        if not self.wallpaper_dir.exists():
            self.wallpapers = []
            return
        
        # Find all image files
        images = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp', '*.bmp']:
            images.extend(self.wallpaper_dir.glob(ext))
        
        # Sort by modification time (newest first)
        self.wallpapers = sorted(images, key=lambda p: p.stat().st_mtime, reverse=True)
        
        # Find current wallpaper
        current = self.get_current_wallpaper()
        if current and current in self.wallpapers:
            self.current_wallpaper_index = self.wallpapers.index(current)
    
    def get_current_wallpaper(self) -> Optional[Path]:
        """Get the currently set Windows wallpaper"""
        SPI_GETDESKWALLPAPER = 0x0073
        buf = ctypes.create_unicode_buffer(512)
        ctypes.windll.user32.SystemParametersInfoW(SPI_GETDESKWALLPAPER, len(buf), buf, 0)
        path_str = buf.value
        if path_str:
            return Path(path_str)
        return None
    
    def set_wallpaper(self, path: Path) -> bool:
        """Set Windows desktop wallpaper"""
        SPI_SETDESKWALLPAPER = 20
        SPIF_UPDATEINIFILE = 0x01
        SPIF_SENDWININICHANGE = 0x02
        try:
            result = ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER, 0, str(path.resolve()), 
                SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE
            )
            return result != 0
        except Exception as e:
            print(f"Error setting wallpaper: {e}")
            return False
    
    def next_wallpaper(self):
        """Switch to next (newer) wallpaper"""
        if not self.wallpapers:
            return False
        
        # Can't go forward if already at newest (index 0)
        if self.current_wallpaper_index == 0:
            return False
        
        self.current_wallpaper_index = self.current_wallpaper_index - 1
        wallpaper = self.wallpapers[self.current_wallpaper_index]
        
        # If user goes back to the latest, they might want auto-update
        if self.current_wallpaper_index == 0 and self.user_paused:
            # User is back at the latest - they can manually resume if they want
            pass
        
        return self.set_wallpaper(wallpaper)
    
    def previous_wallpaper(self):
        """Switch to previous (older) wallpaper"""
        if not self.wallpapers:
            return False
        
        # Can't go back if already at oldest
        if self.current_wallpaper_index >= len(self.wallpapers) - 1:
            return False
        
        self.current_wallpaper_index = self.current_wallpaper_index + 1
        wallpaper = self.wallpapers[self.current_wallpaper_index]
        
        # If user selects an older wallpaper, pause auto-update
        if self.current_wallpaper_index > 0:
            self.user_paused = True
            self.save_config()
        
        return self.set_wallpaper(wallpaper)
    
    def get_current_wallpaper_info(self) -> str:
        """Get info about current wallpaper"""
        if not self.wallpapers:
            return "No wallpapers found"
        
        if self.current_wallpaper_index >= len(self.wallpapers):
            return "Unknown wallpaper"
        
        wallpaper = self.wallpapers[self.current_wallpaper_index]
        index_display = self.current_wallpaper_index + 1
        total = len(self.wallpapers)
        
        return f"{wallpaper.name}\n({index_display} of {total})"
    
    def is_task_enabled(self) -> bool:
        """Check if scheduled task is enabled"""
        try:
            result = subprocess.run(
                ['schtasks', '/Query', '/TN', TASK_NAME, '/FO', 'LIST'],
                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                # Check if task is enabled
                for line in result.stdout.split('\n'):
                    if 'Status:' in line or 'Scheduled Task State:' in line:
                        return 'Ready' in line or 'Running' in line or 'Enabled' in line
            return False
        except Exception as e:
            print(f"Error checking task status: {e}")
            return False
    
    def enable_auto_download(self):
        """Enable the scheduled task"""
        try:
            subprocess.run(
                ['schtasks', '/Change', '/TN', TASK_NAME, '/ENABLE'],
                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.auto_enabled = True
            self.user_paused = False
            self.save_config()
            return True
        except Exception as e:
            print(f"Error enabling task: {e}")
            return False
    
    def disable_auto_download(self):
        """Disable the scheduled task"""
        try:
            subprocess.run(
                ['schtasks', '/Change', '/TN', TASK_NAME, '/DISABLE'],
                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.auto_enabled = False
            return True
        except Exception as e:
            print(f"Error disabling task: {e}")
            return False
    
    def run_download_now(self):
        """Trigger immediate download"""
        try:
            subprocess.run(
                ['schtasks', '/Run', '/TN', TASK_NAME],
                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            return True
        except Exception as e:
            print(f"Error running task: {e}")
            return False
    
    def open_wallpaper_folder(self):
        """Open wallpaper folder in Explorer"""
        if self.wallpaper_dir.exists():
            os.startfile(self.wallpaper_dir)


class TrayApp:
    def __init__(self):
        self.manager = WallpaperManager()
        self.icon = None
        
    def create_icon_image(self) -> Image.Image:
        """Create a simple icon for the system tray"""
        # Create a 64x64 image with a simple wallpaper icon design
        img = Image.new('RGB', (64, 64), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw a simple picture frame
        draw.rectangle([8, 8, 56, 56], outline='blue', width=3)
        draw.rectangle([12, 12, 52, 52], outline='lightblue', width=2)
        
        # Draw a simple mountain/landscape
        draw.polygon([(20, 42), (32, 25), (44, 42)], fill='green')
        draw.ellipse([38, 18, 48, 28], fill='yellow')
        
        return img
    
    def get_menu(self):
        """Build the system tray menu"""
        status_text = "🟢 Auto-Download: Enabled" if self.manager.auto_enabled else "🔴 Auto-Download: Disabled"
        if self.manager.user_paused:
            status_text += " (Paused - user selection)"
        
        # Determine if Previous/Next buttons should be enabled
        can_go_previous = self.manager.current_wallpaper_index < len(self.manager.wallpapers) - 1
        can_go_next = self.manager.current_wallpaper_index > 0
        
        return pystray.Menu(
            item(status_text, lambda: None, enabled=False),
            item(self.manager.get_current_wallpaper_info(), lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            
            item('⬅️ Previous Wallpaper', self.on_previous, enabled=can_go_previous),
            item('➡️ Next Wallpaper', self.on_next, enabled=can_go_next),
            pystray.Menu.SEPARATOR,
            
            item(
                '✓ Enable Auto-Download' if not self.manager.auto_enabled else '✗ Disable Auto-Download',
                self.on_toggle_auto
            ),
            item(
                '▶️ Resume Auto-Update' if self.manager.user_paused else None,
                self.on_resume,
                visible=self.manager.user_paused
            ),
            item('🔄 Download Now', self.on_download_now),
            pystray.Menu.SEPARATOR,
            
            item('📁 Open Wallpaper Folder', self.on_open_folder),
            item('🔄 Refresh List', self.on_refresh),
            pystray.Menu.SEPARATOR,
            
            item('❌ Exit', self.on_exit)
        )
    
    def on_previous(self):
        """Handle previous wallpaper"""
        self.manager.previous_wallpaper()
        self.update_menu()
    
    def on_next(self):
        """Handle next wallpaper"""
        self.manager.next_wallpaper()
        self.update_menu()
    
    def on_toggle_auto(self):
        """Toggle auto-download"""
        if self.manager.auto_enabled:
            self.manager.disable_auto_download()
        else:
            self.manager.enable_auto_download()
        self.update_menu()
    
    def on_resume(self):
        """Resume auto-update after manual selection"""
        self.manager.user_paused = False
        self.manager.save_config()
        if not self.manager.auto_enabled:
            self.manager.enable_auto_download()
        # Go back to latest wallpaper
        self.manager.current_wallpaper_index = 0
        if self.manager.wallpapers:
            self.manager.set_wallpaper(self.manager.wallpapers[0])
        self.update_menu()
    
    def on_download_now(self):
        """Trigger immediate download"""
        self.manager.run_download_now()
        # Wait a bit and refresh
        import threading
        def delayed_refresh():
            import time
            time.sleep(3)
            self.manager.refresh_wallpaper_list()
            self.update_menu()
        threading.Thread(target=delayed_refresh, daemon=True).start()
    
    def on_open_folder(self):
        """Open wallpaper folder"""
        self.manager.open_wallpaper_folder()
    
    def on_refresh(self):
        """Refresh wallpaper list"""
        self.manager.refresh_wallpaper_list()
        self.update_menu()
    
    def on_exit(self):
        """Exit application"""
        if self.icon:
            self.icon.stop()
    
    def update_menu(self):
        """Update the tray menu"""
        if self.icon:
            self.icon.menu = self.get_menu()
    
    def run(self):
        """Start the system tray application"""
        icon_image = self.create_icon_image()
        self.icon = pystray.Icon(
            "BingWallpaperDownloader",
            icon_image,
            "Bing Wallpaper Downloader",
            menu=self.get_menu()
        )
        
        self.icon.run()


def main():
    try:
        app = TrayApp()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
