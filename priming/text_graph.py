from dataclasses import dataclass
# from itertools import cycle
from typing import Dict, ClassVar, List
from uuid import UUID, uuid4

# from rich import print as rprint

from document import Document
from text_node import TextNode
from helpers import get_indent_level


@dataclass
class TextGraph:
    root_node: TextNode
    nodes: Dict[UUID, TextNode]

    CYCLE_COLORS: ClassVar[List[str]] = [
        "red",
        "green",
        "blue",
        "yellow",
        "white",
    ]

    def add_edge(self, parent_node, child_node):
        parent_node.children.add(child_node)
        child_node.parent = parent_node

    def add_node(self, node):
        self.nodes[node.node_id] = node

    def search(self, starting_node=None, method="dfs"):
        starting_node = starting_node if starting_node else self.root_node
        return starting_node.search(method)

    def display(self):
        nodes = [(n.line_number or -1, n) for n in self.nodes.values()]
        nodes.sort()
        # color_cycle = cycle(self.CYCLE_COLORS)
        for line_number, node in nodes:
            node_text = node.text or ""
            # color = next(color_cycle)
            # rprint(f"[{color}]{node_text}[/{color}]\n")
            print(f"{node_text}\n")

    @classmethod
    def from_document(cls, document: Document):

        # Build a blank text graph
        root_node = TextNode(
            node_id=uuid4(),
            document=document,
            text=None,
            line_number=0,
            parent=None,
            children=set(),
        )
        nodes = {root_node.node_id: root_node}
        graph = TextGraph(
            root_node=root_node,
            nodes=nodes,
        )

        # Keeps track of "current parent"
        active_node_by_level = {
            0: graph.root_node,
        }
        last_non_blank_level = 0

        chunk_starting_line = None
        chunk_text = ""
        chunk_level = None

        text = document.text
        indent_spaces = document.indent_spaces
        seen_text = False
        for line_number, line in enumerate(text.split("\n")):
            # Scroll through any initial blank lines
            if not seen_text and len(line.strip()) == 0:
                continue

            is_blank = False
            if len(line.strip()) == 0:
                # Blank lines inherit last non-blank line level
                level = last_non_blank_level + 1
                is_blank = True
            else:
                seen_text = True
                level = get_indent_level(line, indent_spaces) + 1

            level_mismatch = (chunk_level is not None) and (chunk_level != level)
            if (is_blank is True) or level_mismatch:

                # Only create a node that has content in it.
                if chunk_text.strip():
                    # Finish previous chunk
                    node = TextNode(
                        node_id=uuid4(),
                        document=document,
                        text=chunk_text,
                        line_number=chunk_starting_line,
                        parent=None,
                        children=set(),
                    )
                    graph.add_node(node)

                    active_node_by_level[chunk_level] = node
                    if not is_blank:
                        last_non_blank_level = chunk_level

                    # Make connections
                    active_parent = active_node_by_level[chunk_level - 1]
                    graph.add_edge(active_parent, node)
                    # print("lvl:", chunk_level, line, "parent:", active_parent.text)

                # Clear chunk
                chunk_starting_line = None
                chunk_text = ""
                chunk_level = None

            # append to chunk
            if chunk_starting_line is None:
                chunk_starting_line = line_number
            if chunk_text:
                chunk_text += "\n" + line
            else:
                chunk_text += line
            chunk_level = level
        return graph
