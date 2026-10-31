//! Casca desktop do Freddy. Hoje só abre o painel (React) numa janela.
//! Quando o backend Python existir, é aqui que o app pode subir o processo
//! dele junto (sidecar) e encerrar ao fechar.

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("erro ao abrir o Freddy");
}
