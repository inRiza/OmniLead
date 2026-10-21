import { api, type ConnectionStart } from "./api";

type FacebookSDK = {
  init: (options: { appId: string; version: string; xfbml: boolean; cookie: boolean }) => void;
  login: (callback: (response: { authResponse?: { code?: string } }) => void, options: Record<string, unknown>) => void;
};
declare global { interface Window { FB?: FacebookSDK } }
let sdk: Promise<FacebookSDK> | undefined;

function loadSDK(): Promise<FacebookSDK> {
  if (window.FB) return Promise.resolve(window.FB);
  if (sdk) return sdk;
  sdk = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://connect.facebook.net/en_US/sdk.js";
    script.async = true;
    const timer = setTimeout(() => { script.remove(); sdk = undefined; reject(new Error("Jendela Meta belum dapat dimuat. Coba kembali.")); }, 15_000);
    script.onload = () => {
      clearTimeout(timer);
      if (window.FB) resolve(window.FB);
      else { sdk = undefined; reject(new Error("Jendela Meta gagal dimuat.")); }
    };
    script.onerror = () => { clearTimeout(timer); script.remove(); sdk = undefined; reject(new Error("Izinkan koneksi ke Meta lalu coba kembali.")); };
    document.head.appendChild(script);
  });
  return sdk;
}

export async function whatsappSignup(start: Extract<ConnectionStart, { mode: "embedded" }>) {
  const fb = await loadSDK();
  fb.init({ appId: start.app_id, version: start.version, xfbml: false, cookie: false });
  const code = await new Promise<string>((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("Waktu penghubungan habis. Coba kembali.")), 180_000);
    fb.login((response) => {
      clearTimeout(timer);
      const value = response.authResponse?.code;
      if (value) resolve(value);
      else reject(new Error("Penghubungan dibatalkan atau izin WhatsApp belum diberikan."));
    }, {
      config_id: start.config_id, response_type: "code", override_default_response_type: true,
      auth_type: "rerequest", extras: { setup: {} },
    });
  });
  // Discover the permitted accounts server-side, never from untrusted postMessage IDs.
  return api.whatsappExchange(start.state, code);
}
