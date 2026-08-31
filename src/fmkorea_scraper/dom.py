"""Small Scrapling DOM helpers shared by parsers."""

from __future__ import annotations

from scrapling.parser import Selector

Node = Selector


def parse_html(html: str | bytes, *, url: str = "") -> Node:
    return Selector(html, url=url)


def first(root: Node, selector: str) -> Node | None:
    return root.css(selector).first


def text(node: Node | None) -> str:
    if node is None:
        return ""
    return " ".join(str(node.get_all_text(" ", strip=True)).split())


def attr(node: Node | None, name: str) -> str | None:
    if node is None:
        return None
    value = node.attrib.get(name)
    return str(value) if value is not None else None


def classes(node: Node | None) -> set[str]:
    return set((attr(node, "class") or "").split())


def has_ancestor_tag(node: Node, tags: set[str]) -> bool:
    parent = node.parent
    while parent is not None:
        if parent.tag in tags:
            return True
        parent = parent.parent
    return False


def has_ancestor_class(node: Node, class_name: str) -> bool:
    parent = node.parent
    while parent is not None:
        if class_name in classes(parent):
            return True
        parent = parent.parent
    return False


def find_ancestor(node: Node, *, tag: str, class_name: str | None = None) -> Node | None:
    parent = node.parent
    while parent is not None:
        if parent.tag == tag and (class_name is None or class_name in classes(parent)):
            return parent
        parent = parent.parent
    return None
