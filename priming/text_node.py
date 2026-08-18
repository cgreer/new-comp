from __future__ import annotations

from typing import (
    Set,
    Optional,
)
from uuid import UUID
from dataclasses import dataclass
from typing import List
from helpers import unindent
from document import Document


@dataclass
class TextNode:
    node_id: UUID # uuid4
    document: Document
    text: Optional[str] # XXX Why optional? Make root "" instead?
    line_number: int # 1-based (root text node is 0)
    parent: Optional['TextNode']
    children: Set['TextNode']

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        return self.node_id == other.node_id

    def __hash__(self):
        return hash(self.node_id)

    def location(self):
        return (self.document.name, self.line_number)

    def text_content(self):
        if self.text is None:
            return ""
        content = self.text.split("\n")
        content = [x.strip() for x in content]
        return " ".join(content)

    def root_path(self) -> List[TextNode]:
        rp = []
        current = self
        while True:
            if current.parent is None:
                break
            rp.append(current.parent)
            current = current.parent
        rp.reverse()
        return rp

    def sub_text(self, algo="processed", include_root=False) -> str:
        # XXX: Reconstitue newlines between paragraphs in raw algo
        initial_idx = 0 if include_root else 1
        if algo == "processed":
            # This makes one big paragraph of the sub text
            sub_nodes = self.search()[initial_idx:]
            text = "\n".join([x.text_content() for x in sub_nodes])
            return text
        elif algo == "raw":
            # This shows (mostly) exactly what it looks like in the
            # file, except unindented and any blank newlines removed
            # (not desirable, it's a bug).
            sub_nodes = self.search()[initial_idx:]
            txt = []
            for sn in sub_nodes:
                txt.append(sn.text)
            return unindent("\n".join(txt))
        else:
            raise KeyError()

    def root_path_string(self, sep: str = "/") -> str:
        return "/".join([(x.text or "").strip().replace("/", "") for x in self.root_path()])

    def level(self):
        return len(self.root_path()) - 1

    def search(self, method: str = "dfs"):
        assert method in ("dfs",), "Invalid search method"

        # DFS
        visited, stack = set(), [self]
        while stack:
            node = stack.pop()
            if node not in visited:
                visited.add(node)
                stack.extend(node.children - visited)

        # Return them in the order that they were in for the original text
        visited = list(visited)
        visited.sort(key=lambda x: x.line_number or -1)
        return visited
