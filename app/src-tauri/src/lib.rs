use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::Manager;

pub struct SidecarProcess(pub Mutex<Option<Child>>);

fn start_sidecar() -> Option<Child> {
    let exe_dir = std::env::current_exe().ok()?.parent()?.to_path_buf();
    #[cfg(target_os = "windows")]
    let sidecar = exe_dir.join("anonymizer-sidecar.exe");
    #[cfg(not(target_os = "windows"))]
    let sidecar = exe_dir.join("anonymizer-sidecar");

    if !sidecar.exists() {
        eprintln!("[anonymizer] sidecar not found at {}", sidecar.display());
        eprintln!("[anonymizer] run sidecar/build_sidecar.sh (or .bat) first");
        return None;
    }

    match Command::new(&sidecar)
        .args(["--port", "8765"])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
    {
        Ok(child) => Some(child),
        Err(e) => {
            eprintln!("[anonymizer] failed to spawn sidecar: {e}");
            None
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(SidecarProcess(Mutex::new(None)))
        .setup(|app| {
            if let Some(child) = start_sidecar() {
                *app.state::<SidecarProcess>().0.lock().unwrap() = Some(child);
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                let state = window.app_handle().state::<SidecarProcess>();
                let child_opt = state.0.lock().unwrap().take();
                if let Some(mut child) = child_opt {
                    let _ = child.kill();
                    let _ = child.wait();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
