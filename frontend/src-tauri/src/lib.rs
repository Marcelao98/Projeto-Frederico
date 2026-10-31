//! Casca desktop do Freddy: abre o painel (React) numa janela.
//!
//! No app instalado, o painel é servido em http://localhost:PORTA em vez do
//! endereço interno do Tauri (tauri://localhost). O player embutido do
//! YouTube recusa tocar em página sem uma origem web normal; em localhost ele
//! toca igual no navegador e no modo de desenvolvimento.
//!
//! Quando o backend Python existir, é aqui que o app pode subir o processo
//! dele junto (sidecar) e encerrar ao fechar.

use tauri::{WebviewUrl, WebviewWindowBuilder};

/// Porta local do painel no app instalado. Fixa: o localStorage (temas,
/// playlists salvas) é guardado por endereço, então mudar a porta "esquece" tudo.
const PORTA: u16 = 47_823;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let mut app = tauri::Builder::default();
    // Em desenvolvimento o Vite já serve em http://localhost:5173 (devUrl).
    if !cfg!(debug_assertions) {
        app = app.plugin(tauri_plugin_localhost::Builder::new(PORTA).build());
    }
    app.setup(|app| {
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
    .run(tauri::generate_context!())
    .expect("erro ao abrir o Freddy");
}
