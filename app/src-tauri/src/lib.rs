use serde::{Deserialize, Serialize};
use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    AppHandle, Emitter, Manager,
};

#[derive(Debug, Serialize, Deserialize)]
pub struct EngineTelemetry {
    pub active_pilot: String,
    pub target_window: String,
    pub latency_ms: f64,
    pub memory_mb: f64,
    pub tokens_saved: u64,
    pub cost_saved_usd: f64,
    pub is_paused: bool,
}

#[tauri::command]
fn panic_abort(app: AppHandle) -> Result<bool, String> {
    log::warn!("EMERGENCY HARDWARE PANIC KILL SWITCH TRIGGERED");
    // Broadcast event to frontend
    let _ = app.emit("extra://panic-state-change", true);
    Ok(true)
}

#[tauri::command]
fn resume_pilot(app: AppHandle) -> Result<bool, String> {
    log::info!("Resuming AI Pilot automation");
    let _ = app.emit("extra://panic-state-change", false);
    Ok(false)
}

#[tauri::command]
fn get_engine_telemetry() -> EngineTelemetry {
    EngineTelemetry {
        active_pilot: "Cursor IDE".to_string(),
        target_window: "Google Chrome".to_string(),
        latency_ms: 2.34,
        memory_mb: 28.4,
        tokens_saved: 1482000,
        cost_saved_usd: 19.24,
        is_paused: false,
    }
}

#[tauri::command]
fn set_speed_mode(mode: String) -> Result<String, String> {
    log::info!("Updating execution speed mode to: {}", mode);
    Ok(mode)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            // Register global hardware panic kill switch (Ctrl + Alt + Escape)
            #[cfg(desktop)]
            {
                use tauri_plugin_global_shortcut::{Code, Modifiers, Shortcut, ShortcutState};
                let panic_shortcut = Shortcut::new(Some(Modifiers::CONTROL | Modifiers::ALT), Code::Escape);
                let app_handle = app.handle().clone();
                if let Ok(plugin) = tauri_plugin_global_shortcut::Builder::new()
                    .with_handler(move |_app, shortcut, event| {
                        if shortcut == &panic_shortcut && event.state() == ShortcutState::Pressed {
                            let _ = panic_abort(app_handle.clone());
                        }
                    })
                    .build()
                {
                    let _ = app.handle().plugin(plugin);
                }
            }

            // Configure System Tray
            let show_i = MenuItem::with_id(app, "show", "Show Extra Station", true, None::<&str>)?;
            let panic_i = MenuItem::with_id(app, "panic", "Emergency Panic Stop (Ctrl+Alt+Esc)", true, None::<&str>)?;
            let quit_i = MenuItem::with_id(app, "quit", "Quit Extra Station", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show_i, &panic_i, &quit_i])?;

            let _tray = TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .menu(&menu)
                .tooltip("Extra Station — Sovereign AI Cockpit")
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "panic" => {
                        let _ = panic_abort(app.clone());
                    }
                    "quit" => {
                        app.exit(0);
                    }
                    _ => {}
                })
                .build(app)?;

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            panic_abort,
            resume_pilot,
            get_engine_telemetry,
            set_speed_mode
        ])
        .run(tauri::generate_context!())
        .expect("error while building tauri application");
}
