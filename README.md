# AppSanti Launcher

Panel de control (Tkinter) para abrir las herramientas de Editorial y CPS desde un solo lugar, con registro de tiempo de uso y auto-actualización.

Este repositorio contiene únicamente el código del launcher (`Launcher.py`). Las herramientas que lanza (Calculadora de Lomo, Contador de Caracteres, etc.) viven como carpetas hermanas en la misma ubicación que `AppSanti.exe` y no forman parte de este repo.

## Uso

Se distribuye como `AppSanti.exe` (ver [Releases](../../releases)). Al abrirse, chequea automáticamente si hay una versión nueva publicada y se actualiza sola.

## Build local

```
pip install pyinstaller
pyinstaller --name "AppSanti" --onefile --windowed Launcher.py
```
