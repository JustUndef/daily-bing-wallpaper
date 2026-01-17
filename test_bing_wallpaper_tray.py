# -*- coding: utf-8 -*-
"""
Unit tests for Bing Wallpaper Tray Manager
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# Mock pystray and PIL before importing bing_wallpaper_tray
sys.modules['pystray'] = mock.MagicMock()
sys.modules['PIL'] = mock.MagicMock()
sys.modules['PIL.Image'] = mock.MagicMock()
sys.modules['PIL.ImageDraw'] = mock.MagicMock()


class TestWallpaperManagerConfig:
    """Test WallpaperManager configuration handling"""
    
    def test_load_config_no_file(self, monkeypatch):
        """Test config loading when no file exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_config = Path(tmpdir) / "nonexistent" / "config.json"
            
            # Mock the CONFIG_FILE
            with mock.patch('bing_wallpaper_tray.CONFIG_FILE', fake_config):
                from bing_wallpaper_tray import WallpaperManager
                
                # Mock other dependencies
                with mock.patch('bing_wallpaper_tray.WallpaperManager.is_task_enabled', return_value=False):
                    with mock.patch('bing_wallpaper_tray.WallpaperManager.refresh_wallpaper_list'):
                        manager = WallpaperManager()
                        assert manager.config == {}
    
    def test_load_config_valid_file(self, monkeypatch):
        """Test loading valid config file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_file = config_dir / "config.json"
            
            test_config = {
                "download_folder": "C:\\Test\\Wallpapers",
                "market": "en-US",
                "user_paused": True
            }
            config_file.write_text(json.dumps(test_config), encoding='utf-8')
            
            with mock.patch('bing_wallpaper_tray.CONFIG_FILE', config_file):
                from bing_wallpaper_tray import WallpaperManager
                
                with mock.patch('bing_wallpaper_tray.WallpaperManager.is_task_enabled', return_value=False):
                    with mock.patch('bing_wallpaper_tray.WallpaperManager.refresh_wallpaper_list'):
                        manager = WallpaperManager()
                        assert manager.config["download_folder"] == "C:\\Test\\Wallpapers"
                        assert manager.config["market"] == "en-US"
                        assert manager.user_paused == True
    
    def test_save_config_preserves_existing(self):
        """Test that save_config preserves existing config values"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_file = config_dir / "config.json"
            
            # Create initial config
            initial_config = {
                "download_folder": "C:\\Test",
                "market": "en-US"
            }
            config_file.write_text(json.dumps(initial_config), encoding='utf-8')
            
            with mock.patch('bing_wallpaper_tray.CONFIG_FILE', config_file):
                from bing_wallpaper_tray import WallpaperManager
                
                with mock.patch('bing_wallpaper_tray.WallpaperManager.is_task_enabled', return_value=False):
                    with mock.patch('bing_wallpaper_tray.WallpaperManager.refresh_wallpaper_list'):
                        manager = WallpaperManager()
                        manager.user_paused = True
                        manager.save_config()
                
                # Read back the config
                saved_config = json.loads(config_file.read_text(encoding='utf-8'))
                assert saved_config["download_folder"] == "C:\\Test"
                assert saved_config["market"] == "en-US"
                assert saved_config["user_paused"] == True


class TestWallpaperManagerWallpaperList:
    """Test wallpaper list management"""
    
    def test_refresh_wallpaper_list_no_directory(self):
        """Test refresh when directory doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent_dir = Path(tmpdir) / "nonexistent"
            
            with mock.patch('bing_wallpaper_tray.CONFIG_FILE', Path(tmpdir) / "config.json"):
                from bing_wallpaper_tray import WallpaperManager
                
                with mock.patch('bing_wallpaper_tray.WallpaperManager.is_task_enabled', return_value=False):
                    manager = WallpaperManager()
                    manager.wallpaper_dir = nonexistent_dir
                    manager.refresh_wallpaper_list()
                    
                    assert manager.wallpapers == []
    
    def test_refresh_wallpaper_list_finds_images(self):
        """Test that refresh finds image files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            wallpaper_dir = Path(tmpdir) / "wallpapers"
            wallpaper_dir.mkdir()
            
            # Create test image files
            (wallpaper_dir / "test1.jpg").touch()
            (wallpaper_dir / "test2.png").touch()
            (wallpaper_dir / "test3.webp").touch()
            (wallpaper_dir / "not_image.txt").touch()
            
            with mock.patch('bing_wallpaper_tray.CONFIG_FILE', Path(tmpdir) / "config.json"):
                from bing_wallpaper_tray import WallpaperManager
                
                with mock.patch('bing_wallpaper_tray.WallpaperManager.is_task_enabled', return_value=False):
                    with mock.patch('bing_wallpaper_tray.WallpaperManager.get_current_wallpaper', return_value=None):
                        manager = WallpaperManager()
                        manager.wallpaper_dir = wallpaper_dir
                        manager.refresh_wallpaper_list()
                        
                        # Should find 3 image files, not the txt file
                        assert len(manager.wallpapers) == 3
                        assert all(w.suffix in ['.jpg', '.png', '.webp'] for w in manager.wallpapers)


class TestTaskManagement:
    """Test scheduled task management"""
    
    def test_is_task_enabled_task_not_found(self):
        """Test checking task status when task doesn't exist"""
        with mock.patch('bing_wallpaper_tray.CONFIG_FILE', Path("test_config.json")):
            from bing_wallpaper_tray import WallpaperManager
            
            with mock.patch('bing_wallpaper_tray.WallpaperManager.refresh_wallpaper_list'):
                with mock.patch('subprocess.run') as mock_run:
                    # Simulate task not found
                    mock_run.return_value.returncode = 1
                    mock_run.return_value.stdout = ""
                    
                    manager = WallpaperManager()
                    result = manager.is_task_enabled()
                    
                    assert result == False
    
    def test_is_task_enabled_task_ready(self):
        """Test checking task status when task is ready"""
        with mock.patch('bing_wallpaper_tray.CONFIG_FILE', Path("test_config.json")):
            from bing_wallpaper_tray import WallpaperManager
            
            with mock.patch('bing_wallpaper_tray.WallpaperManager.refresh_wallpaper_list'):
                with mock.patch('subprocess.run') as mock_run:
                    # Simulate task is ready
                    mock_run.return_value.returncode = 0
                    mock_run.return_value.stdout = "Status: Ready\nOther info"
                    
                    manager = WallpaperManager()
                    result = manager.is_task_enabled()
                    
                    assert result == True


class TestWallpaperInfo:
    """Test wallpaper info display"""
    
    def test_get_current_wallpaper_info_no_wallpapers(self):
        """Test info display when no wallpapers exist"""
        with mock.patch('bing_wallpaper_tray.CONFIG_FILE', Path("test_config.json")):
            from bing_wallpaper_tray import WallpaperManager
            
            with mock.patch('bing_wallpaper_tray.WallpaperManager.is_task_enabled', return_value=False):
                with mock.patch('bing_wallpaper_tray.WallpaperManager.refresh_wallpaper_list'):
                    manager = WallpaperManager()
                    manager.wallpapers = []
                    
                    info = manager.get_current_wallpaper_info()
                    assert "No wallpapers found" in info
    
    def test_get_current_wallpaper_info_with_wallpapers(self):
        """Test info display with wallpapers"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_wallpaper.jpg"
            test_file.touch()
            
            with mock.patch('bing_wallpaper_tray.CONFIG_FILE', Path("test_config.json")):
                from bing_wallpaper_tray import WallpaperManager
                
                with mock.patch('bing_wallpaper_tray.WallpaperManager.is_task_enabled', return_value=False):
                    with mock.patch('bing_wallpaper_tray.WallpaperManager.refresh_wallpaper_list'):
                        manager = WallpaperManager()
                        manager.wallpapers = [test_file]
                        manager.current_wallpaper_index = 0
                        
                        info = manager.get_current_wallpaper_info()
                        assert "test_wallpaper.jpg" in info
                        assert "(1 of 1)" in info


class TestWallpaperNavigation:
    """Test wallpaper navigation with boundary checks"""
    
    def test_next_wallpaper_at_newest(self):
        """Test that next_wallpaper returns False when at newest (index 0)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_files = [Path(tmpdir) / f"wallpaper{i}.jpg" for i in range(3)]
            for f in test_files:
                f.touch()
            
            with mock.patch('bing_wallpaper_tray.CONFIG_FILE', Path("test_config.json")):
                from bing_wallpaper_tray import WallpaperManager
                
                with mock.patch('bing_wallpaper_tray.WallpaperManager.is_task_enabled', return_value=False):
                    with mock.patch('bing_wallpaper_tray.WallpaperManager.refresh_wallpaper_list'):
                        manager = WallpaperManager()
                        manager.wallpapers = test_files
                        manager.current_wallpaper_index = 0
                        
                        # Should return False at newest
                        result = manager.next_wallpaper()
                        assert result == False
                        assert manager.current_wallpaper_index == 0
    
    def test_previous_wallpaper_at_oldest(self):
        """Test that previous_wallpaper returns False when at oldest (last index)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_files = [Path(tmpdir) / f"wallpaper{i}.jpg" for i in range(3)]
            for f in test_files:
                f.touch()
            
            with mock.patch('bing_wallpaper_tray.CONFIG_FILE', Path("test_config.json")):
                from bing_wallpaper_tray import WallpaperManager
                
                with mock.patch('bing_wallpaper_tray.WallpaperManager.is_task_enabled', return_value=False):
                    with mock.patch('bing_wallpaper_tray.WallpaperManager.refresh_wallpaper_list'):
                        manager = WallpaperManager()
                        manager.wallpapers = test_files
                        manager.current_wallpaper_index = 2  # Last index
                        
                        # Should return False at oldest
                        result = manager.previous_wallpaper()
                        assert result == False
                        assert manager.current_wallpaper_index == 2
    
    def test_next_wallpaper_middle(self):
        """Test that next_wallpaper moves to newer wallpaper in middle"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_files = [Path(tmpdir) / f"wallpaper{i}.jpg" for i in range(3)]
            for f in test_files:
                f.touch()
            
            with mock.patch('bing_wallpaper_tray.CONFIG_FILE', Path("test_config.json")):
                from bing_wallpaper_tray import WallpaperManager
                
                with mock.patch('bing_wallpaper_tray.WallpaperManager.is_task_enabled', return_value=False):
                    with mock.patch('bing_wallpaper_tray.WallpaperManager.refresh_wallpaper_list'):
                        with mock.patch('bing_wallpaper_tray.WallpaperManager.set_wallpaper', return_value=True):
                            manager = WallpaperManager()
                            manager.wallpapers = test_files
                            manager.current_wallpaper_index = 1  # Middle
                            
                            # Should move to newer (index 0)
                            result = manager.next_wallpaper()
                            assert result == True
                            assert manager.current_wallpaper_index == 0
    
    def test_previous_wallpaper_middle(self):
        """Test that previous_wallpaper moves to older wallpaper in middle"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_files = [Path(tmpdir) / f"wallpaper{i}.jpg" for i in range(3)]
            for f in test_files:
                f.touch()
            
            with mock.patch('bing_wallpaper_tray.CONFIG_FILE', Path("test_config.json")):
                from bing_wallpaper_tray import WallpaperManager
                
                with mock.patch('bing_wallpaper_tray.WallpaperManager.is_task_enabled', return_value=False):
                    with mock.patch('bing_wallpaper_tray.WallpaperManager.refresh_wallpaper_list'):
                        with mock.patch('bing_wallpaper_tray.WallpaperManager.set_wallpaper', return_value=True):
                            manager = WallpaperManager()
                            manager.wallpapers = test_files
                            manager.current_wallpaper_index = 1  # Middle
                            
                            # Should move to older (index 2)
                            result = manager.previous_wallpaper()
                            assert result == True
                            assert manager.current_wallpaper_index == 2


class TestJumpToLatest:
    """Test jump to latest wallpaper functionality"""
    
    def test_jump_to_latest_from_middle(self):
        """Test jumping to latest wallpaper from middle of list"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_files = [Path(tmpdir) / f"wallpaper{i}.jpg" for i in range(5)]
            for f in test_files:
                f.touch()
            
            with mock.patch('bing_wallpaper_tray.CONFIG_FILE', Path("test_config.json")):
                from bing_wallpaper_tray import WallpaperManager
                
                with mock.patch('bing_wallpaper_tray.WallpaperManager.is_task_enabled', return_value=False):
                    with mock.patch('bing_wallpaper_tray.WallpaperManager.refresh_wallpaper_list'):
                        with mock.patch('bing_wallpaper_tray.WallpaperManager.set_wallpaper', return_value=True):
                            manager = WallpaperManager()
                            manager.wallpapers = test_files
                            manager.current_wallpaper_index = 3  # Not at latest
                            
                            # Should jump to index 0
                            result = manager.jump_to_latest()
                            assert result == True
                            assert manager.current_wallpaper_index == 0
    
    def test_jump_to_latest_already_at_latest(self):
        """Test that jump_to_latest returns False when already at latest"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_files = [Path(tmpdir) / f"wallpaper{i}.jpg" for i in range(3)]
            for f in test_files:
                f.touch()
            
            with mock.patch('bing_wallpaper_tray.CONFIG_FILE', Path("test_config.json")):
                from bing_wallpaper_tray import WallpaperManager
                
                with mock.patch('bing_wallpaper_tray.WallpaperManager.is_task_enabled', return_value=False):
                    with mock.patch('bing_wallpaper_tray.WallpaperManager.refresh_wallpaper_list'):
                        manager = WallpaperManager()
                        manager.wallpapers = test_files
                        manager.current_wallpaper_index = 0  # Already at latest
                        
                        # Should return False
                        result = manager.jump_to_latest()
                        assert result == False
                        assert manager.current_wallpaper_index == 0
    
    def test_jump_to_latest_no_wallpapers(self):
        """Test that jump_to_latest handles no wallpapers"""
        with mock.patch('bing_wallpaper_tray.CONFIG_FILE', Path("test_config.json")):
            from bing_wallpaper_tray import WallpaperManager
            
            with mock.patch('bing_wallpaper_tray.WallpaperManager.is_task_enabled', return_value=False):
                with mock.patch('bing_wallpaper_tray.WallpaperManager.refresh_wallpaper_list'):
                    manager = WallpaperManager()
                    manager.wallpapers = []
                    
                    # Should return False when no wallpapers
                    result = manager.jump_to_latest()
                    assert result == False


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
