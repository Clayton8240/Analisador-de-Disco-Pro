; Script para o Inno Setup do Analisador de Disco Pro
; Versão Final Corrigida

; Define uma variável para o caminho dos ficheiros de origem
#define SourcePath "dist"

[Setup]
; Informações básicas da aplicação
AppName=Analisador de Disco Pro
AppVersion=1.0
AppPublisher=Clayton8240
AppPublisherURL=https://sites.google.com/view/clayton-almeida/página-inicial
DefaultDirName={autopf}\AnalisadorDeDiscoPro
DefaultGroupName=Analisador de Disco Pro
OutputBaseFilename=setup-analisador-disco-pro
PrivilegesRequired=admin
LicenseFile=politica_privacidade.txt

; Configuração do instalador
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\AnalisadorDeDisco.exe

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}";

[Files]
; *** CORREÇÃO AQUI ***
; O caminho agora aponta para a subpasta "AnalisadorDeDisco" dentro da pasta "dist".
Source: "{#SourcePath}\AnalisadorDeDisco\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Adiciona o ícone e a política de privacidade para referência, se necessário.
Source: "app_icon.ico"; DestDir: "{app}"
Source: "politica_privacidade.txt"; DestDir: "{app}";

[Icons]
; Atalho no Menu Iniciar
Name: "{group}\Analisador de Disco Pro"; Filename: "{app}\AnalisadorDeDisco.exe"
Name: "{group}\{cm:UninstallProgram,Analisador de Disco Pro}"; Filename: "{uninstallexe}"

; Atalho no Ambiente de Trabalho (se o utilizador selecionar a tarefa)
Name: "{autodesktop}\Analisador de Disco Pro"; Filename: "{app}\AnalisadorDeDisco.exe"; Tasks: desktopicon

[Run]
; Executa a aplicação no final da instalação, se o utilizador desejar.
Filename: "{app}\AnalisadorDeDisco.exe"; Description: "{cm:LaunchProgram,Analisador de Disco Pro}"; Flags: nowait postinstall skipifsilent