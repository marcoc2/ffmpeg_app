' Create Shortcut with Custom Icon
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = oWS.CurrentDirectory & "\FFmpeg Tools.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)

' Find pythonw
Dim fso, pythonw
Set fso = CreateObject("Scripting.FileSystemObject")
pythonw = "pythonw.exe"

' Target is pythonw + script path
oLink.TargetPath = pythonw
oLink.Arguments = """" & oWS.CurrentDirectory & "\main_gui.py"""
oLink.WorkingDirectory = oWS.CurrentDirectory
oLink.IconLocation = oWS.CurrentDirectory & "\ffmpeg_tools.ico, 0"
oLink.Description = "FFmpeg Tools"
oLink.Save

WScript.Echo "Atalho criado com sucesso! Agora basta arrastar o arquivo 'FFmpeg Tools' (com o ícone verde) para sua barra de tarefas."
