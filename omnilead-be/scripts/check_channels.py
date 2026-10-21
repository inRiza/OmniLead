"""Cek kredensial kanal di omnilead-be/.env tanpa menampilkan token.

Jalankan dari folder omnilead-be:
    uv run python scripts/check_channels.py

Default hanya membaca (aman). Untuk mencoba mengirim pesan uji, tambahkan:
    --whatsapp-to 62812xxxx   nomor harus terdaftar sebagai penerima uji di Meta,
                              dan pesan teks bebas butuh jendela 24 jam terbuka
                              (kirim pesan dulu dari nomor itu ke nomor bisnis)
    --gmail-to nama@domain    mengirim email uji dari akun Gmail yang terhubung
"""

import argparse
import sys

from omnilead.config import Settings
from omnilead.connectors.base import ConnectorError, NotConnected
from omnilead.connectors.gmail import GmailConnector
from omnilead.connectors.instagram import InstagramConnector
from omnilead.connectors.whatsapp import WhatsAppConnector

TEST_TEXT = "Tes koneksi OmniLead dari check_channels.py"


def report(name: str, ok: bool | None, detail: str) -> None:
    mark = {True: "OK   ", False: "GAGAL", None: "KOSONG"}[ok]
    print(f"[{mark}] {name:<10} {detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--whatsapp-to", help="kirim pesan uji WhatsApp ke nomor ini")
    parser.add_argument("--gmail-to", help="kirim email uji ke alamat ini")
    args = parser.parse_args()

    s = Settings()
    failed = False

    ig = InstagramConnector(s)
    if not ig.status().connected:
        report("Instagram", None, "OMNILEAD_INSTAGRAM_USER_ID / _ACCESS_TOKEN belum diisi")
    else:
        try:
            posts = ig.list_posts(limit=1)
            report("Instagram", True, f"terbaca, post terbaru: {posts[0].url if posts else '(belum ada post)'}")
        except (NotConnected, ConnectorError) as exc:
            failed = True
            report("Instagram", False, str(exc))

    wa = WhatsAppConnector(s)
    if not wa.configured:
        report("WhatsApp", None, "OMNILEAD_WHATSAPP_PHONE_NUMBER_ID / _ACCESS_TOKEN belum diisi")
    else:
        try:
            info = wa.phone_info()
            report("WhatsApp", True, f"{info.get('display_phone_number', '?')} ({info.get('verified_name', '?')})")
            if args.whatsapp_to:
                ref = wa.send_message(args.whatsapp_to, TEST_TEXT)
                report("WhatsApp", True, f"pesan uji terkirim ke {args.whatsapp_to} (id {ref})")
        except (NotConnected, ConnectorError) as exc:
            failed = True
            report("WhatsApp", False, str(exc))

    gm = GmailConnector(s)
    if not gm.configured:
        report("Gmail", None, "OMNILEAD_GMAIL_CLIENT_ID / _CLIENT_SECRET / _REFRESH_TOKEN belum diisi")
    else:
        try:
            profile = gm.profile()
            report("Gmail", True, f"{profile.get('emailAddress', '?')} ({profile.get('messagesTotal', '?')} pesan)")
            if args.gmail_to:
                ref = gm.send_message(args.gmail_to, TEST_TEXT, context={"subject": "Tes koneksi OmniLead"})
                report("Gmail", True, f"email uji terkirim ke {args.gmail_to} (id {ref})")
        except (NotConnected, ConnectorError) as exc:
            failed = True
            report("Gmail", False, str(exc))

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
