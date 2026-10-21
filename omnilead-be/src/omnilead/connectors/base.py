"""Kontrak connector tunggal.

Setiap kanal mengimplementasikan antarmuka yang sama. Executor dan agen hanya
bergantung pada ChannelConnector, bukan pada detail tiap platform. Menambah
kanal baru cukup dengan menulis satu kelas baru.

Hanya dua jalur yang diizinkan: API resmi atau handoff manual. Connector yang
tidak punya API untuk sebuah aksi WAJIB menandai aksi itu `available=False` dan
tidak boleh berpura-pura mengaksesnya.
"""

from abc import ABC, abstractmethod

from omnilead.models import Capability, Channel, ChannelStatus, Comment, Post


class ConnectorError(Exception):
    """Kegagalan dari sisi kanal (jaringan, ditolak platform, data tidak ada)."""


class NotConnected(ConnectorError):
    """Token/izin belum ada atau sudah kedaluwarsa."""


class ActionNotSupported(ConnectorError):
    """Aksi tidak diekspos oleh integrasi aktif. Harus lewat handoff."""


class ChannelConnector(ABC):
    channel: Channel

    @abstractmethod
    def capabilities(self) -> list[Capability]:
        """Aksi yang benar-benar didukung koneksi saat ini."""

    @abstractmethod
    def status(self) -> ChannelStatus:
        """Status koneksi untuk halaman Integrasi."""

    @abstractmethod
    def list_posts(self, limit: int = 10) -> list[Post]:
        ...

    @abstractmethod
    def read_comments(self, post_ref: str, limit: int = 50) -> list[Comment]:
        ...

    @abstractmethod
    def post_comment(self, post_ref: str, text: str) -> str:
        """Kirim komentar baru. Mengembalikan ID komentar yang dibuat."""

    @abstractmethod
    def reply_comment(self, comment_ref: str, text: str) -> str:
        """Balas sebuah komentar. Mengembalikan ID komentar balasan."""

    def send_message(
        self,
        recipient: str,
        text: str,
        comment_ref: str | None = None,
        context: dict | None = None,
    ) -> str:
        """Kirim DM/pesan/email. Default: tidak didukung (jatuh ke handoff)."""
        raise ActionNotSupported(f"{self.channel.value}: send_message tidak tersedia")

    def supports(self, action: str) -> bool:
        return any(c.action == action and c.available for c in self.capabilities())
