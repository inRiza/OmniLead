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


def find_ref(snapshot_refs: dict, *names: str) -> str:
    wanted = {n.lower() for n in names}
    for ref, item in snapshot_refs.items():
        if isinstance(item, dict) and str(item.get("name", "")).strip().lower() in wanted:
            return ref
    return ""
