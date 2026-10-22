import re
from dataclasses import dataclass, field

LINE = re.compile(r'^(\s*)-\s+([A-Za-z]+)(?:\s+"((?:[^"\\]|\\.)*)")?(.*)$')
URL = re.compile(r"\[url=([^\]]+)\]")
REF = re.compile(r"\[ref=([^\]]+)\]")
COMMENT_URL = re.compile(r"instagram\.com/([^/]+)/([^/]+)/c/(\d+)/?")
PROFILE_URL = re.compile(r"instagram\.com/([A-Za-z0-9._]+)/?$")
COMMENT_LABEL = re.compile(r"^(commented|replied to your comment|mentioned you in a comment)\s*:\s*", re.I)
OWN_PREVIEW = re.compile(r"^(you|anda|kamu)\s*:\s*", re.I)
STATUS_TEXT = re.compile(r"^(unread|belum dibaca|active( now|\s+\d+\s*\w+(\s+ago)?)?|aktif( sekarang|\s+\d+\s*\w+(\s+(yang )?lalu)?)?|seen|dilihat)$", re.I)
NOTICE_LABEL = re.compile(r"\s(commented|replied to your comment|mentioned you in a comment)\s*:", re.I)
AVATAR = "user-profile-picture"
UNSUPPORTED = re.compile(r"^(unsupported message|pesan tidak didukung)\b", re.I)
MEDIA = "[media]"
TAB_COUNT = re.compile(r"\s*\(\d+\+?\)\s*$")
FOLDER_TABS = {
    "Primary": {"primary", "utama"},
    "General": {"general", "umum"},
    "Requests": {"request", "requests", "message requests", "permintaan", "permintaan pesan"},
}
SYSTEM_PREVIEW = re.compile(r"^(liked a message|menyukai pesan|\d+\+? new messages?|\d+\+? pesan baru|.* sent an? (attachment|photo|video|voice message|reel|post|sticker|gif)\.?|.* mengirim (lampiran|foto|video|pesan suara|reel|postingan|stiker)\.?|reacted .* to your message|.* reacted to your message|bereaksi .*|sent a message\.?|you sent .*|anda mengirim .*)$", re.I)


@dataclass
class Node:
    role: str
    name: str
    attrs: str
    depth: int
    children: list["Node"] = field(default_factory=list)
    parent: "Node | None" = None

    @property
    def url(self) -> str:
        m = URL.search(self.attrs)
        return m.group(1) if m else ""

    @property
    def ref(self) -> str:
        m = REF.search(self.attrs)
        return m.group(1) if m else ""


@dataclass
class Thread:
    name: str
    preview: str
    unread: bool
    incoming: bool
    time: str


@dataclass
class Message:
    direction: str
    author: str
    text: str


@dataclass
class CommentNotice:
    username: str
    text: str
    comment_id: str
    post_code: str
    time: str


def parse_tree(snapshot: str) -> Node:
    root = Node("root", "", "", -1)
    stack = [root]
    for raw in snapshot.splitlines():
        m = LINE.match(raw)
        if not m:
            continue
        depth = len(m.group(1))
        node = Node(m.group(2), (m.group(3) or "").replace('\\"', '"'), m.group(4) or "", depth)
        while stack[-1].depth >= depth:
            stack.pop()
        node.parent = stack[-1]
        stack[-1].children.append(node)
        stack.append(node)
    return root


def walk(node: Node):
    for child in node.children:
        yield child
        yield from walk(child)


def _texts(node: Node, skip_abbr: bool = True) -> list[str]:
    out: list[str] = []
    for child in node.children:
        if child.role == "Abbr" and skip_abbr:
            continue
        if child.role == "StaticText":
            if child.name.strip():
                out.append(child.name.strip())
            continue
        out.extend(_texts(child, skip_abbr))
    return out


def _abbr_text(node: Node) -> str:
    for child in walk(node):
        if child.role == "Abbr":
            texts = _texts(child, skip_abbr=False)
            return texts[0] if texts else child.name
    return ""


def threads(snapshot: str) -> list[Thread]:
    out: list[Thread] = []
    for node in walk(parse_tree(snapshot)):
        if node.role != "button" or not node.name.startswith(AVATAR):
            continue
        texts = [t for t in _texts(node) if not STATUS_TEXT.match(t)]
        if len(texts) < 2:
            continue
        name, preview = texts[0], " ".join(texts[1:]).strip()
        if SYSTEM_PREVIEW.match(preview):
            continue
        incoming = not OWN_PREVIEW.match(preview)
        out.append(Thread(name=name[:200], preview=OWN_PREVIEW.sub("", preview)[:2000],
                          unread=bool(re.search(r"\bUnread\b|Belum dibaca", node.name)), incoming=incoming,
                          time=_abbr_text(node)))
    return out


def comments(snapshot: str) -> list[CommentNotice]:
    out: list[CommentNotice] = []
    seen: set[str] = set()
    for node in walk(parse_tree(snapshot)):
        if node.role != "generic" or not NOTICE_LABEL.search(node.name):
            continue
        texts = _texts(node)
        label = next((t for t in texts if COMMENT_LABEL.match(t)), None)
        if label is None:
            continue
        username = ""
        for child in walk(node):
            m = PROFILE_URL.search(child.url)
            if child.role == "link" and m:
                username = m.group(1)
                break
        siblings = node.parent.children if node.parent else []
        after = siblings[siblings.index(node) + 1:] if node in siblings else []
        target = next((COMMENT_URL.search(s.url) for s in [node, *walk(node), *after]
                       if COMMENT_URL.search(s.url)), None)
        if target is None or not username or target.group(3) in seen:
            continue
        seen.add(target.group(3))
        out.append(CommentNotice(username=username, text=COMMENT_LABEL.sub("", label)[:2000],
                                 comment_id=target.group(3), post_code=target.group(2), time=_abbr_text(node)))
    return out


def _author(group: Node) -> str:
    names = [c.name.split() for c in walk(group) if c.role == "button" and c.name.strip()]
    tails = {n[-1] for n in names if n}
    return tails.pop() if len(tails) == 1 else ""


def conversation_username(snapshot: str) -> str:
    """Only profile controls in the conversation pane establish a peer identity.

    Ignore arbitrary URLs in message bodies and the sidebar's own Profile link.
    Return empty if a group/multiple peers makes identity ambiguous.
    """
    peers = set()
    for node in walk(parse_tree(snapshot)):
        if node.role != "link" or any(p.role == "article" for p in _ancestors(node)):
            continue
        match = PROFILE_URL.search(node.url)
        if match and re.match(r"^(open the profile page of|buka (halaman )?profil)\s+", node.name, re.I):
            peers.add(match.group(1).lower())
    return next(iter(peers)) if len(peers) == 1 else ""


def _ancestors(node: Node) -> list[Node]:
    out = []
    while node.parent:
        node = node.parent
        out.append(node)
    return out


def conversation(snapshot: str, limit: int = 10) -> list[Message]:
    articles = [n for n in walk(parse_tree(snapshot)) if n.role == "article"]
    if not articles:
        return []
    shared = set(map(id, _ancestors(articles[0])))
    for article in articles[1:]:
        shared &= set(map(id, _ancestors(article)))
    pane = next(a for a in _ancestors(articles[0]) if id(a) in shared)
    peers = {m.group(1).lower() for n in walk(pane) if n.role == "link" and (m := PROFILE_URL.search(n.url))}
    out: list[Message] = []
    for article in articles:
        text = article.name.strip() or " ".join(_texts(article)).strip()
        if not text:
            continue
        if UNSUPPORTED.match(text):
            text = MEDIA
        group = next((c for c in article.children if c.role == "group"), None)
        if group is None and article.parent:
            siblings = article.parent.children
            group = next((c for c in siblings[siblings.index(article) + 1:] if c.role == "group"), None)
        author = _author(group) if group else ""
        if author:
            incoming = author.lower() in peers
        else:
            siblings = article.parent.children if article.parent else []
            before = siblings[siblings.index(article) - 1] if siblings.index(article) > 0 else None
            incoming = bool(before and before.role == "link" and PROFILE_URL.search(before.url))
        out.append(Message(direction="in" if incoming else "out", author=author, text=text[:2000]))
    return out[-limit:] if limit > 0 else []


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def thread_ref(refs: dict, name: str) -> str:
    wanted, prefix = _norm(name), AVATAR + " "
    for ref, item in refs.items():
        if not isinstance(item, dict) or item.get("role") != "button":
            continue
        label = _norm(str(item.get("name", "")))
        if label.startswith(prefix) and (label[len(prefix):] + " ").startswith(wanted + " "):
            return ref
    return ""


def folder_ref(refs: dict, folder: str) -> str:
    wanted = FOLDER_TABS.get(folder, {folder.lower()})
    for ref, item in refs.items():
        if isinstance(item, dict) and item.get("role") == "tab" \
                and _norm(TAB_COUNT.sub("", str(item.get("name", "")))) in wanted:
            return ref
    return ""


def button_ref(refs: dict, *names: str) -> str:
    wanted = {_norm(n) for n in names}
    for ref, item in refs.items():
        if isinstance(item, dict) and item.get("role") == "button" and _norm(str(item.get("name", ""))) in wanted:
            return ref
    return ""


def find_ref(snapshot_refs: dict, *names: str) -> str:
    wanted = {n.lower() for n in names}
    for ref, item in snapshot_refs.items():
        if isinstance(item, dict) and str(item.get("name", "")).strip().lower() in wanted:
            return ref
    return ""
