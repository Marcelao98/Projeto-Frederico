//! Casca desktop do Freddy: abre o painel (React) numa janela e liga o
//! backend sozinho, sem terminal.
//!
//! No app instalado, o painel é servido em http://localhost:PORTA em vez do
//! endereço interno do Tauri (tauri://localhost). O player embutido do
//! YouTube recusa tocar em página sem uma origem web normal; em localhost ele
//! toca igual no navegador e no modo de desenvolvimento.
//!
//! O backend (Python, empacotado com PyInstaller pelo workflow app.yml) vem
//! junto como "sidecar" (`freddy-backend`). Se já tem um Freddy respondendo
//! na porta (freddy.sh, `python -m freddy`), o app só usa ele. O backend
//! recebe o pid do app em FREDDY_PAI e desliga sozinho se o app fechar ou
//! cair; ao sair, o app ainda manda desligar.

use std::net::{SocketAddr, TcpStream};
use std::sync::Mutex;
use std::time::Duration;

use tauri::{AppHandle, Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

/// Porta local do painel no app instalado. Fixa: o localStorage (temas,
/// playlists salvas) é guardado por endereço, então mudar a porta "esquece" tudo.
const PORTA: u16 = 47_823;
/// Porta do backend (backend/freddy/config.py, PORTA_PADRAO).
const PORTA_DO_FREDDY: u16 = 47_824;

/// O backend que o app ligou (None se já estava ligado por outro jeito).
struct Backend(Mutex<Option<CommandChild>>);

fn freddy_ja_ligado() -> bool {
    let endereco = SocketAddr::from(([127, 0, 0, 1], PORTA_DO_FREDDY));
    TcpStream::connect_timeout(&endereco, Duration::from_millis(400)).is_ok()
}

fn ligar_backend(app: &AppHandle) {
    let mut comando = match app.shell().sidecar("freddy-backend") {
        Ok(c) => c,
        Err(e) => {
            eprintln!("Freddy: backend não encontrado no app ({e})");
            return;
        }
    };
    // O FFmpeg que vem junto (Windows) mora do lado do executável do app.
    if let Some(pasta) = std::env::current_exe().ok().and_then(|exe| exe.parent().map(|p| p.to_path_buf())) {
        let mut caminhos = vec![pasta];
        if let Some(path) = std::env::var_os("PATH") {
            caminhos.extend(std::env::split_paths(&path));
        }
        if let Ok(path) = std::env::join_paths(caminhos) {
            comando = comando.env("PATH", path);
        }
    }
    comando = comando.env("FREDDY_PAI", std::process::id().to_string());
    match comando.spawn() {
        Ok((mut saida, filho)) => {
            app.manage(Backend(Mutex::new(Some(filho))));
            // Empacotado, o backend escreve no freddy.log; aqui só esvazia o cano.
            tauri::async_runtime::spawn(async move {
                while let Some(evento) = saida.recv().await {
                    if let CommandEvent::Terminated(fim) = evento {
                        eprintln!("Freddy: o backend saiu ({:?})", fim.code);
                    }
                }
            });
        }
        Err(e) => eprintln!("Freddy: não consegui ligar o backend ({e})"),
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let mut app = tauri::Builder::default().plugin(tauri_plugin_shell::init());
    // Em desenvolvimento o Vite já serve em http://localhost:5173 (devUrl).
    if !cfg!(debug_assertions) {
        app = app.plugin(tauri_plugin_localhost::Builder::new(PORTA).build());
    }
    app.setup(|app| {
        // Em desenvolvimento, quem liga o backend é você (freddy.sh / python -m freddy).
        if !cfg!(debug_assertions) && !freddy_ja_ligado() {
            ligar_backend(app.handle());
        }
        let url = if cfg!(debug_assertions) {
            WebviewUrl::App("index.html".into())
        } else {
            WebviewUrl::External(format!("http://localhost:{PORTA}").parse().expect("url local"))
        };
        WebviewWindowBuilder::new(app, "main", url)
            .title("Freddy")
            .inner_size(1280.0, 820.0)
            .min_inner_size(380.0, 600.0)
            .center()
            .build()?;
        Ok(())
    })
    .build(tauri::generate_context!())
    .expect("erro ao abrir o Freddy")
    .run(|app, evento| {
        if let RunEvent::Exit = evento {
            if let Some(backend) = app.try_state::<Backend>() {
                if let Some(filho) = backend.0.lock().ok().and_then(|mut f| f.take()) {
                    let _ = filho.kill();
                }
            }
        }
    });
}
