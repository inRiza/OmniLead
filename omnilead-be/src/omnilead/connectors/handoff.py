"""Handoff manual untuk kanal/aksi tanpa API.

Masuk : pengguna menempel teks pesan/komentar; dinormalisasi jadi Comment
        sehingga agen tetap bisa menyusun draf.
Keluar: executor TIDAK mengirim. Ia membuat deep link "Salin & buka", dan
        pengguna mengirim sendiri lalu menandai "Sudah dikirim".

Dipakai untuk aksi yang tidak diekspos API kanal aktif.
"""

from datetime import datetime, timezone
from urllib.parse import quote

from omnilead.models import Channel, Comment

# Pola deep link per kanal. {text} diisi draf yang sudah di-URL-encode.
DEEPLINK = {
    Channel.INSTAGRAM: "https://www.instagram.com/",
}


def ingest_pasted_text(
    channel: Channel,
    post_ref: str,
    author_handle: str,
    text: str,
    pasted_at: datetime | None = None,
) -> Comment:
    """Ubah teks yang ditempel menjadi Comment biasa."""
    ts = pasted_at or datetime.now(timezone.utc)
    return Comment(
        id=f"handoff-{channel}-{int(ts.timestamp() * 1000)}",
        channel=channel,
        post_ref=post_ref,
        author_handle=author_handle or "tidak diketahui",
        text=text.strip(),
        created_at=ts,
    )


def build_handoff(channel: Channel, text: str) -> dict:
    """Siapkan paket untuk tombol Salin & buka."""
    base = DEEPLINK.get(channel, "")
    return {
        "copy_text": text,
        "open_url": base,
        "hint": f"Salin teks, buka {channel.value}, tempel, kirim, lalu tandai Sudah dikirim.",
        "encoded_preview": quote(text[:120]),
    }
