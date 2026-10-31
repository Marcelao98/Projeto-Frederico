// Sem janela de console no Windows quando for o app instalado.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    freddy_lib::run()
}
