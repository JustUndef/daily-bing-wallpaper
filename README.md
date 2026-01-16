# Bing Wallpaper Downloader

Automatically downloads daily Bing wallpapers and sets them as your Windows desktop background.

## Features

- Downloads high-resolution Bing wallpapers (up to 4K UHD)
- Automatically sets the latest wallpaper as desktop background
- Supports multiple markets (regions) with fallback options
- Can download multiple days of wallpapers (up to 8 days back)
- Smart file management with skip/unique/overwrite modes
- Optional autostart on Windows boot or user login

## For End Users - Using the Installer

### Download and Install

1. Download `BingWallpaperDownloader_Setup.exe` from the releases
2. Double-click the installer
3. Follow the setup wizard:
   - **Choose Install Location**: Select where to install the program
   - **Download Folder**: Choose where wallpapers will be saved (default: Pictures\BingWallpapers)
   - **Market Selection**: Pick your region (affects available images)
   - **Resolution**: Choose your preferred quality (4K recommended)
   - **Download Settings**: 
     - Number of wallpapers to download (1-8)
     - Whether to automatically set as desktop background
   - **Autostart Options**:
     - Run daily at system startup (recommended)
     - Run when you log in

### What Gets Installed

- The main executable in Program Files
- Windows Task Scheduler entry (if autostart enabled)
- Configuration stored in Windows Registry
- Download folder automatically created

### Uninstalling

1. Go to Windows Settings > Apps > Apps & features
2. Find "Bing Wallpaper Downloader"
3. Click Uninstall
4. You'll be asked if you want to delete downloaded wallpapers

## For Developers - Building from Source

### Prerequisites

1. **Python 3.10+** - [Download](https://www.python.org/downloads/)
2. **Inno Setup 6.0+** - [Download](https://jrsoftware.org/isdl.php)
3. **Visual Studio Build Tools** (for Nuitka) - [Download](https://visualstudio.microsoft.com/downloads/)
   - Install "Desktop development with C++"

### Build Steps

#### Option 1: Build Everything (EXE + Installer)

```powershell
.\bing_wallpaper.build.ps1
```

This will:
- Create a virtual environment
- Install dependencies (nuitka, requests)
- Compile Python to standalone EXE
- Build the installer with Inno Setup

Output files:
- `dist/BingWallpaperDownloader.exe` - Standalone executable
- `installer_output/BingWallpaperDownloader_Setup.exe` - Full installer

#### Option 2: Build Only the EXE

```powershell
.\bing_wallpaper.build.ps1 -BuildInstaller:$false
```

#### Option 3: Build with Code Signing

```powershell
# Using certificate from Windows certificate store
.\bing_wallpaper.build.ps1 -Sign:$true -CertSource store

# Using PFX file
.\bing_wallpaper.build.ps1 -Sign:$true -CertSource pfx -PfxPath "path\to\cert.pfx" -PfxPassword "password"
```

### Build Script Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `-Console` | `$false` | Show console window |
| `-Sign` | `$false` | Enable code signing |
| `-BuildInstaller` | `$true` | Build Inno Setup installer |
| `-InnoSetupPath` | `C:\Program Files (x86)\Inno Setup 6\ISCC.exe` | Path to Inno Setup compiler |
| `-IconIco` | `""` | Custom icon for EXE |
| `-LTO` | `$true` | Link-time optimization |

### Manual Usage (Without Installer)

Run the standalone EXE with command-line arguments:

```powershell
# Download today's wallpaper and set as background
.\BingWallpaperDownloader.exe --set-latest

# Download 8 days of wallpapers from German Bing
.\BingWallpaperDownloader.exe --mkt de-DE --count 8

# Custom download location
.\BingWallpaperDownloader.exe --out "D:\Wallpapers" --set-latest

# Specify resolution preferences
.\BingWallpaperDownloader.exe --res "3840x2160,2560x1440,1920x1080"
```

### Command-Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--mkt` | `de-DE` | Primary market (de-DE, en-US, en-GB, fr-FR, etc.) |
| `--fallback-mkts` | `en-US` | Fallback markets (comma-separated) |
| `--count` | `8` | Number of wallpapers to download (1-8) |
| `--out` | `%USERPROFILE%\Pictures\BingWallpapers` | Download directory |
| `--res` | `UHD,3840x2160,2560x1440,1920x1200,1920x1080` | Resolution preferences |
| `--mode` | `skip` | File handling: `skip`, `unique`, or `overwrite` |
| `--name-mode` | `slug` | Filename format: `slug` or `title` |
| `--set-latest` | (off) | Set latest wallpaper as desktop background |

### File Handling Modes

- **skip**: Don't re-download existing files (efficient)
- **unique**: Append _1, _2, etc. if file exists
- **overwrite**: Replace existing files

### Filename Modes

- **slug**: Use Bing's OHR identifier (e.g., `2025-01-16_Waterfall.jpg`) - More reliable
- **title**: Use image title from metadata - More descriptive but may have duplicates

## Project Structure

```
daily-bing-wallpaper/
├── bing_wallpaper.py           # Main Python script
├── bing_wallpaper.build.ps1    # Build script (creates EXE and installer)
├── installer.iss                # Inno Setup script (GUI installer)
├── dist/                        # Compiled EXE output
├── installer_output/            # Installer output
└── build/                       # Build artifacts and venv
```

## How It Works

1. Queries Bing's `HPImageArchive.aspx` API for wallpaper metadata
2. Builds candidate URLs with different resolutions and formats
3. Downloads the highest available resolution (tries UHD → 4K → 2K → Full HD)
4. Saves with date + identifier filename (e.g., `2025-01-16_Waterfall.jpg`)
5. Optionally sets as Windows desktop wallpaper via Win32 API

## Autostart Configuration

The installer can configure two types of autostart:

### Daily at System Startup (Recommended)
- Uses Windows Task Scheduler
- Runs daily at 9 AM + 2 minutes after boot
- Runs even if user isn't logged in
- Won't start if already running

### At User Login
- Creates shortcut in Startup folder
- Only runs when you log in
- Simpler but less flexible

## Troubleshooting

### Installer Issues

**"Inno Setup not found"**
- Download and install Inno Setup 6: https://jrsoftware.org/isdl.php

**"MSVC not found"**
- Install Visual Studio Build Tools with C++ workload

### Runtime Issues

**"Download failed"**
- Check internet connection
- Try different market with `--mkt en-US`
- Some regions may have temporary API issues

**"Wallpaper not setting"**
- Requires Windows (uses Windows API)
- May need to run as administrator on some systems
- Check that `--set-latest` flag is used

**Scheduled task not running**
- Open Task Scheduler (`taskschd.msc`)
- Look for "BingWallpaperDownloader"
- Check "Last Run Result" for errors
- Ensure "Run whether user is logged on or not" is NOT set (requires password)

## License

MIT License - Feel free to use, modify, and distribute.

## Credits

- Bing for providing beautiful daily wallpapers
- Nuitka for Python-to-binary compilation
- Inno Setup for professional installers
