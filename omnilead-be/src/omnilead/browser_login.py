"""Owner-authorized sign-in helpers. Credentials never enter the visual planner."""

import re
from urllib.parse import urlsplit

AUTH_WORDS = re.compile(r"\b(?:log\s*in|sign\s*in|masuk\s+(?:ke\s+)?(?:akun|instagram|facebook|gmail|email|whatsapp)|hubungkan\s+akun|password\w*|passwd|kata\s*sandi\w*|sandi\w*|otp|kode\s*verifikasi|secret|access\s*token)\b", re.I)
SECRET_WORDS = re.compile(r"\b(?:password\w*|passwd|kata\s*sandi\w*|sandi\w*|otp|kode\s*verifikasi|secret|access\s*token)\b", re.I)


def auth_status(browser, channel):
    parts = urlsplit(browser.url)
    path = parts.path.lower()
    items = [item for item in browser.refs.values() if isinstance(item, dict)]
    fields = [item for item in items if item.get("role") in {"textbox", "spinbutton"}]
    labels = " ".join(str(item.get("name") or "") for item in items)
    field_labels = " ".join(str(item.get("name") or "") for item in fields)
    auth_page = (parts.hostname == "accounts.google.com" or bool(re.search(r"/(?:accounts/login|login|challenge|checkpoint|two_factor|two_step_verification)(?:/|\.|$)", path)))
    if auth_page and re.search(r"captcha|recaptcha|prove.you.are.human|buktikan.*manusia", labels, re.I):
        return {"stage": "manual", "message": "Ada pemeriksaan keamanan. Selesaikan pada browser atau kontrol manual, lalu tulis lanjutkan."}
    if auth_page and re.search(r"\bcode\b|\bkode\b", field_labels, re.I):
        return {"stage": "verification", "message": "Instagram/platform meminta kode verifikasi. Masukkan kode melalui kartu aman di chat."}
    if channel in {"instagram", "facebook"} and auth_page and "login" in path:
        return {"stage": "credentials", "message": "Isi akun dan password pada kartu aman. Saya akan mengisi formulir dan menekan login untuk Anda."}
    if channel == "email" and urlsplit(browser.url).hostname == "accounts.google.com":
        stage = "password" if re.search(r"password|kata sandi", field_labels, re.I) or "pwd" in path else "username"
        return {"stage": stage, "message": "Google meminta " + ("password" if stage == "password" else "alamat email") + ". Masukkan lewat kartu aman."}
    if browser.login_required() or re.search(r"challenge|checkpoint|two_factor", path):
        return {"stage": "manual", "message": "Selesaikan QR atau pemeriksaan akun pada layar browser, lalu tulis lanjutkan."}
    return {"stage": "none", "message": ""}


def submit_login(browser, channel, stage, username, password, code, cancelled):
    """Only fixed login fields and exact sign-in buttons; never caller-provided selectors."""
    expected_url = browser.url

    def fill(selector, text, label):
        if cancelled():
            raise RuntimeError("Sign-in cancelled")
        browser.inspect()
        if browser.url != expected_url or cancelled():
            raise ValueError("Sign-in page changed")
        candidates = [ref for ref, item in browser.refs.items() if isinstance(item, dict)
            and item.get("role") == "textbox" and re.search(label, str(item.get("name") or ""), re.I)]
        target = {"ref": candidates[0]} if len(candidates) == 1 else {"selector": selector}
        browser.act("type", **target, text=text, submit=False)

    if stage == "credentials":
        fields = {"instagram": ('input[name="username"]', 'input[name="password"]'),
                  "facebook": ('input[name="email"]', 'input[name="pass"]')}
        user_field, pass_field = fields[channel]
        fill(user_field, username, r"username|email|e-mail|mobile|phone|nama pengguna|telepon")
        fill(pass_field, password, r"password|kata sandi")
    elif stage == "username":
        fill('input[type="email"]', username, r"email|e-mail|phone")
    elif stage == "password":
        fill('input[type="password"]', password, r"password|kata sandi")
    elif stage == "verification":
        candidates = [(ref, item) for ref, item in browser.refs.items() if isinstance(item, dict) and item.get("role") in {"textbox", "spinbutton"}
            and re.search(r"code|kode", str(item.get("name") or ""), re.I)]
        if len(candidates) != 1:
            raise ValueError("Verification field is ambiguous")
        if cancelled():
            raise RuntimeError("Sign-in cancelled")
        browser.act("type", ref=candidates[0][0], text=code, submit=False)
    else:
        raise ValueError("Sign-in page requires manual control")
    browser.inspect()
    if browser.url != expected_url:
        raise ValueError("Sign-in page changed")
    names = r"(?:log\s*in|sign\s*in|masuk|next|berikutnya|continue|lanjutkan|confirm|konfirmasi|verify|verifikasi|submit)"
    buttons = [ref for ref, item in browser.refs.items() if isinstance(item, dict) and item.get("role") == "button"
        and re.fullmatch(names, str(item.get("name") or "").strip(), re.I)]
    if len(buttons) != 1:
        raise ValueError("Sign-in button is ambiguous")
    if cancelled():
        raise RuntimeError("Sign-in cancelled")
    browser.act("click", ref=buttons[0])
