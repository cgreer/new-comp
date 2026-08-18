from pathlib import Path
from collections import defaultdict, deque
from typing import (
    # Any,
    ClassVar,
    cast,
    Dict,
    Set,
    List,
    Tuple,
    Union,
    Protocol,
    Type,
    Optional,
    DefaultDict,
    Iterator,
    Deque,
)
from dataclasses import dataclass, field

from document import Document
from text_graph import TextGraph
from text_node import TextNode

enu = enumerate


@dataclass(frozen=True)
class NoteTag:
    name: str


TAGS = {
    "DEF": NoteTag("DEF"),
    "EX": NoteTag("EX"),
    "PROC": NoteTag("PROC"),
    "NOTE": NoteTag("NOTE"),
    "ALIAS": NoteTag("ALIAS"),
}


def find_tags(text_node: TextNode):
    '''
    Starting from the last token in :text_node's text, check each
    token for a valid note tag until you run into a non-tag token.
    '''
    text = text_node.text.strip().split()
    if not text:
        return []

    tags = []
    token_index = len(text) - 1
    while True:
        if token_index <= 0:
            break
        token = text[token_index]
        if token in TAGS:
            tags.append(token)
        else:
            break
        token_index -= 1
    return tags


def extract_text(text_node):
    raw_text = (text_node.text or "").strip()
    final_text = raw_text.replace("\n", " ")
    return final_text


def normalize_text(text):
    return text.strip().lower()


def concept_key(text):
    return normalize_text(text)


def source_line_num(note):
    return note.source_node.line_number


def truncated_text(text):
    return " ".join(x.strip() for x in text.split("\n"))[0:80]


@dataclass
class Concept:
    primary_name: str
    alternative_names: Set[str]

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        return self.primary_name == other.primary_name

    def __hash__(self):
        return hash(self.primary_name)

    def iter_names(self):
        yield self.primary_name

        for a_name in self.alternative_names:
            yield a_name


Token = str


@dataclass
class Concepts:
    concepts: List[Concept]
    by_name: Optional[Dict[str, Concept]] = field(init=False)
    inverted_index: Optional[DefaultDict[Token, Set[Concept]]] = field(init=False)

    def __post_init__(self):
        # XXX: Can have non-unique concept names?
        self.by_name = self.build_by_name()
        self.inverted_index = self.build_inverted_index()

    def build_by_name(self) -> Dict[str, Concept]:
        by_name = {}
        for concept in self.concepts:
            pcn = concept_key(concept.primary_name)
            assert pcn not in by_name
            by_name[pcn] = concept
            for a_name in concept.alternative_names:
                acn = concept_key(a_name)
                assert acn not in by_name
                by_name[acn] = concept
        return by_name

    def build_inverted_index(self) -> DefaultDict[Token, Set[Concept]]:
        # Make inverted index
        index = defaultdict(set)
        for concept in self.concepts:
            for name in concept.iter_names():
                for token in tokenize(name):
                    index[token].add(concept)
        return index

    def find(self, text) -> Set[Concept]:
        # self.inverted_index = cast(DefaultDict[Token, Set[Concept]], self.inverted_index)

        tokens = tokenize(text)
        tok_i = 0
        matches = set()
        while tok_i < len(tokens):
            token = tokens[tok_i]
            partial_matches = self.inverted_index[token]

            # Check if it's a full match
            # - Starting from the token that matches, check every
            # concept that matches the first token against the text
            # at/following the token.
            full_matches = [] # [(concept, length)]
            for concept in partial_matches:
                for cname in concept.iter_names():
                    name_tokens = tokenize(cname)
                    num_name_tokens = len(name_tokens)
                    matched_tokens = tokens[tok_i: tok_i + num_name_tokens]
                    if name_tokens == matched_tokens:
                        full_matches.append((concept, num_name_tokens))
                        # XXX: Need to cycle through all names for
                        # longest match?
                        break
            if not full_matches:
                tok_i += 1
                continue

            # Take only the longest match
            # - e.g. "matrix multiplication" v. "matrix"
            # - Note that if there is more than one concent name with
            #   the largest num of tokens, then only one will be chosen.
            full_matches.sort(key=lambda x: x[1])
            longest_concept, longest_token_count = full_matches[-1]
            matches.add(longest_concept)

            # Skip past matching tokens
            tok_i += longest_token_count
        return matches


class NoteLike(Protocol):
    name: str
    source_node: TextNode

    @classmethod
    def from_text_node(cls, text_node):
        pass


@dataclass(frozen=True)
class DefinitionNote:
    name: str
    meaning: str
    source_node: TextNode = field(repr=False)

    TAG = "DEF"

    @classmethod
    def from_text_node(cls, text_node):
        name = text_node.parent.text_content()
        meaning = text_node.text_content()
        meaning = meaning.replace(cls.TAG, "").strip()
        source_node = text_node
        return cls(name, meaning, source_node)

    def line_num(self):
        return self.source_node.parent.line_number

    def root_path(self) -> List[TextNode]:
        name_node = self.source_node.parent
        return name_node.root_path()

    def primary_concept(self, concepts: Concepts) -> Concept:
        # Get the name of the primary concept
        concepts.by_name = cast(Dict[str, Concept], concepts.by_name)

        primary_concept_name = concept_key(self.name)
        return concepts.by_name[primary_concept_name]

    def involved_concepts(self, concepts: Concepts) -> Set[Concept]:
        # primary concept + any concepts referred to in meaning text
        involved = set([self.primary_concept(concepts)])
        for con in concepts.find(self.meaning):
            involved.add(con)
        return involved

    def dependent_concepts(self, concepts: Concepts) -> Set[Concept]:
        meaning_concepts = concepts.find(self.meaning)
        return meaning_concepts - set([self.primary_concept(concepts)])

    def associations(self):
        return [concept_key(self.name)]

    def display_text(self):
        # XXX: Should use sub_text("raw")?
        return f"{self.name}\n\n{self.meaning}"

    def display(self):
        print(self.display_text())


@dataclass(frozen=True)
class AliasNote:
    name: str
    alias_of: str
    source_node: TextNode = field(repr=False)

    TAG = "ALIAS"

    @classmethod
    def from_text_node(cls, text_node):
        name = text_node.text_content()
        name = name.replace(cls.TAG, "").strip()
        alias_of = text_node.parent.text_content()
        source_node = text_node
        return cls(name, alias_of, source_node)

    def line_num(self):
        return self.source_node.line_number

    def root_path(self) -> List[TextNode]:
        name_node = self.source_node.parent
        return name_node.root_path()

    def primary_concept(self, concepts: Concepts) -> Concept:
        primary_concept_name = concept_key(self.alias_of)
        return concepts.by_name[primary_concept_name]

    def involved_concepts(self, concepts: Concepts) -> Set[Concept]:
        return set([self.primary_concept(concepts)])

    def associations(self):
        return [concept_key(self.alias_of)]

    def display_text(self):
        return f"{self.name} is an alias for {self.alias_of}"

    def display(self):
        print(self.display_text())


@dataclass(frozen=True)
class ExampleNote:
    name: str
    content: str
    source_node: TextNode = field(repr=False)

    TAG = "EX"

    @classmethod
    def from_text_node(cls, text_node):
        name = text_node.text_content()
        name = name.replace(cls.TAG, "").strip()
        content = text_node.sub_text()
        source_node = text_node
        return cls(name, content, source_node)

    def line_num(self):
        return self.source_node.line_number

    def primary_concept(self, concepts: Concepts) -> Concept:
        return None

    def root_path(self) -> List[TextNode]:
        return self.source_node.root_path()

    def involved_concepts(self, concepts: Concepts) -> Set[Concept]:
        return concepts.find(self.name)

    def associations(self):
        # Get the parent node's text
        parent_text_node = self.source_node.parent
        if not parent_text_node:
            return []
        parent_text = extract_text(parent_text_node)

        return [concept_key(parent_text)]

    def display_text(self):
        raw_content = self.source_node.sub_text("raw")
        return f"{self.name}\n\n{raw_content}"

    def display(self):
        print(self.display_text())


@dataclass(frozen=True)
class ProcedureNote(ExampleNote):
    TAG = "PROC"


@dataclass(frozen=True)
class NoteNote:
    name: str
    source_node: TextNode = field(repr=False)

    TAG = "NOTE"

    @classmethod
    def from_text_node(cls, text_node):
        name = text_node.text_content()
        name = name.replace(cls.TAG, "").strip()
        source_node = text_node
        return cls(name, source_node)

    def line_num(self):
        return self.source_node.line_number

    def root_path(self) -> List[TextNode]:
        return self.source_node.root_path()

    def primary_concept(self, concepts: Concepts) -> Concept:
        return None

    def involved_concepts(self, concepts: Concepts) -> Set[Concept]:
        return concepts.find(self.name)

    def associations(self):
        # Get the parent node's text
        parent_text_node = self.source_node.parent
        if not parent_text_node:
            return []
        parent_text = extract_text(parent_text_node)

        return [concept_key(parent_text)]

    def display_text(self):
        raw_content = self.source_node.sub_text("raw")
        # return f"{self.name}"
        return f"{self.name}\n\n{raw_content}"

    def display(self):
        print(self.display_text())


Note = Union[
    DefinitionNote,
    AliasNote,
    ExampleNote,
    ProcedureNote,
    NoteNote,
]

NoteClass = Type[Note]

NoteClasses = (
    DefinitionNote,
    AliasNote,
    ExampleNote,
    ProcedureNote,
    NoteNote,
)


def tokenize(text):
    cleaned_text = (
        normalize_text(text)
        .replace(",", "")
        .replace("'s", "")
        .replace(".", "")
        .replace(";", "")

        .replace("\t", " ")
        .replace("—", " ")
    )
    return cleaned_text.split(" ")


@dataclass
class Section:
    name: str
    parent: Optional['Section'] = field(repr=False)
    children: Set['Section'] = field(repr=False)
    notes: Set[Note] = field(repr=False)
    source_node: TextNode = field(repr=False)

    def line_num(self):
        return self.source_node.line_number

    def doc_name(self):
        return self.source_node.document.name

    def location(self):
        return (self.doc_name(), self.line_num())

    def hashable_key(self):
        return self.location()

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        return self.hashable_key() == other.hashable_key()

    def __hash__(self):
        return hash(self.hashable_key())

    def children_ordered(self, reverse=False) -> List['Section']:
        secs = [x for x in self.children] # type: ignore
        secs.sort(key=lambda x: x.line_num(), reverse=reverse)
        return secs

    def descendant_notes(self) -> Set[Note]:
        '''
        This section's note + this section's children's notes + ...

        Because this is an true section (has a location in a
        document), there are no cycles to worry about, it's a DAG:
            a
                b
                    d
                c
                    d
                    e
        '''
        notes = set()
        notes.update(self.notes)
        stack = []
        stack.extend(self.children)
        while stack:
            sec = stack.pop()
            notes.update(sec.notes)
            stack.extend(sec.children)
        return notes

    def descendant_sections(self) -> List['Section']:
        '''
        Sections are returned in order of appearence in document.
        Cycles are not possible.
        '''
        stack = deque()
        for sec in self.children_ordered(reverse=True):
            stack.appendleft((sec, 0))
        dsections = []
        while stack:
            sec, depth = stack.popleft()
            dsections.append((sec, depth))
            for sec in sec.children_ordered(reverse=True):
                stack.appendleft((sec, depth + 1))
        return dsections

    def ascendant_sections(self):
        '''
        All the parent sections + their parent sections + ... until
        you get to root section
        '''
        raise NotImplementedError

        stack = deque()
        for sec in self.parents:
            stack.appendleft((sec, 0))

        seen = set()
        dsections = []
        while stack:
            sec, depth = stack.popleft()
            dsections.append((sec, depth))
            for sec in sec.parents:
                if sec in seen:
                    continue
                stack.appendleft((sec, depth + 1))
        return dsections


SecKey = Tuple[str, int] # DocName, LineNum


@dataclass
class Sections:
    by_key: Dict[SecKey, Section] = field(init=False, default_factory=dict)
    seen_doc_names: Set[str] = field(init=False, default_factory=set)

    def add(self, sec_key, section):
        self.by_key[sec_key] = section
        self.seen_doc_names.add(sec_key[0])

    def root_sections(self):
        rs = []
        for doc_name in sorted(self.seen_doc_names):
            rs.append(self.by_key[(doc_name, "")])
        return rs

    def iter_sections(self, includes: Set[Section] = None) -> Iterator[Tuple[Section, int]]:
        '''
        :includes - Only include included sections. Assumes that root
        section is always included. If None, then every section is
        allowed.
        '''
        for root_section in self.root_sections():
            stack: Deque[Tuple[Section, int]] = deque()
            for sec in root_section.children_ordered(reverse=True):
                if (includes is not None) and (sec not in includes):
                    continue
                stack.appendleft((sec, 0))
            while stack:
                sec, depth = stack.popleft()
                yield sec, depth
                for sec in sec.children_ordered(reverse=True):
                    if (includes is not None) and (sec not in includes):
                        continue
                    stack.appendleft((sec, depth + 1))


@dataclass
class TreeNode:
    name: str
    parents: Dict[str, 'TreeNode']
    children: Dict[str, 'TreeNode']
    sections: Set[Section]

    def _comparable_key(self):
        return self.name

    def __eq__(self, other) -> bool:
        if self.__class__ != other.__class__:
            return False
        return self._comparable_key() == other._comparable_key()

    def __hash__(self) -> int:
        return hash(self._comparable_key())

    @classmethod
    def make_name(cls, section):
        return section.name.strip().lower()

    def display_name(self):
        # Just return the first found name
        for sec in self.sections:
            return sec.name

    def children_ordered(self, reverse=False):
        secs = list(self.children.values()) # type: ignore
        secs.sort(key=lambda x: x.smallest_line_num(), reverse=reverse)
        return secs

    def smallest_line_num(self):
        return min(sec.line_num() for sec in self.sections)

    def notes(self) -> List[Note]:
        all_notes = []
        for sec in self.sections:
            all_notes.extend(sec.notes)
        all_notes.sort(key=lambda x: x.source_node.location())
        return all_notes

    def descendant_notes(self) -> Set[Note]:
        all_notes = set()
        for sec in self.sections:
            all_notes.update(sec.descendant_notes())
        return all_notes

    def descendant_sections(self) -> List[Section]:
        all_sections = set()
        for sec in self.sections:
            all_sections.update(sec.descendant_sections())
        all_sections = list(all_sections)
        all_sections.sort(key=lambda x: x.location())
        return all_sections


@dataclass
class VirtualTree:
    root_node: TreeNode = field(init=False)
    _nodes_by_name: Dict[str, TreeNode] = field(init=False)

    def __post_init__(self):
        self.root_node = TreeNode(
            name="",
            parents={},
            children={},
            sections=set(),
        )
        self._nodes_by_name = {self.root_node.name: self.root_node}

    def add_path(self, path: List[Section]):
        # Start a the root and work your way down
        # XXX: Need to add root section to root node?
        assert path[0].name == ""
        self.root_node.sections.add(path[0])

        cur_node = self.root_node
        for section in path[1:]:
            node_name = TreeNode.make_name(section)
            if node_name not in cur_node.children:
                new_node = TreeNode(
                    name=node_name,
                    parents={},
                    children={},
                    sections=set(),
                )
                self.connect(cur_node, new_node)
                self._nodes_by_name[node_name] = new_node
            next_node = cur_node.children[node_name]
            next_node.sections.add(section)
            cur_node = next_node

    def get_vsection(self, vsec_name: str):
        return self._nodes_by_name.get(vsec_name)

    def iter_vsections(self, includes: Set[TreeNode] = None) -> Iterator[Tuple[TreeNode, int]]:
        '''
        :includes - Only include included sections. Assumes that root
        section is always included. If None, then every section is
        allowed.

        XXX: Have to watch out for cycles?
        '''
        stack: Deque[Tuple[TreeNode, int]] = deque()
        for vsec in self.root_node.children_ordered(reverse=True):
            if (includes is not None) and (vsec not in includes):
                continue
            stack.appendleft((vsec, 0))
        while stack:
            vsec, depth = stack.popleft()
            yield vsec, depth
            for vsec in vsec.children_ordered(reverse=True):
                if (includes is not None) and (vsec not in includes):
                    continue
                stack.appendleft((vsec, depth + 1))

    def connect(self, parent_node, child_node):
        parent_node.children[child_node.name] = child_node
        child_node.parents[parent_node.name] = parent_node


@dataclass
class StructuredNotes:
    definitions: List[DefinitionNote]
    aliases: List[AliasNote]
    examples: List[ExampleNote]
    procedures: List[ProcedureNote]
    notes: List[NoteNote]

    sections: Dict[str, Section] = field(init=False)
    sections_by_note: Dict[Note, Set[Section]] = field(init=False)
    vsection_tree: VirtualTree = field(init=False)
    vsections_by_note: Dict[Note, List[TreeNode]] = field(init=False)
    concepts: Concepts = field(init=False)
    notes_by_concept: Dict[Concept, Set[Note]] = field(init=False)
    initial_token_index: Dict[str, Set[Note]] = field(init=False)

    TAGS_BY_TYPE: ClassVar = dict(
        definition={"DEF"},
        alias={"ALIAS"},
        example={"EX"},
        procedure={"PROC"},
        note={"NOTE"},
    )

    NOTE_CLASS_BY_TYPE: ClassVar = dict(
        definition=DefinitionNote,
        alias=AliasNote,
        example=ExampleNote,
        procedure=ProcedureNote,
        note=NoteNote,
    )

    INDENT: ClassVar[str] = "  "

    def __post_init__(self):
        (
            self.sections,
            self.sections_by_note,
            self.vsection_tree,
            self.vsections_by_note,
        ) = self.extract_sections()
        # root_section, sections, sections_by_note = cls.build_sections(all_notes)

        self.concepts = self.extract_concepts()
        self.notes_by_concept = self.build_notes_by_concept(self.concepts)
        self.initial_token_index = self.build_inverted_index(only_initial=True)

    def extract_sections(self):
        sections = Sections()
        sections_by_note: Dict[Note, Set[Section]] = {}

        vsection_tree = VirtualTree()
        vsections_by_note: Dict[Note, List[TreeNode]] = {}
        for note in self.iter_all():
            # Build section path up to root section
            # - Assert root section exists as a concept
            root_path = note.root_path()
            if not root_path:
                continue

            # Construct Section Path
            # - root_path includes the blank root text node
            # - Check for invalid intermediate root sections
            # - Add sections to index if not exists
            section_path: List[Section] = []
            for node_idx, node in enu(root_path):
                sec_name = node.text_content()
                if (node_idx != 0) and (not sec_name):
                    raise RuntimeError("Invalid intermediate root section")
                sec_key = (node.document.name, node.line_number)
                if sec_key not in sections.by_key:
                    new_sec = Section(
                        name=sec_name,
                        parent=None,
                        children=set(),
                        notes=set(),
                        source_node=node,
                    )
                    sections.add(sec_key, new_sec)
                sec = sections.by_key[sec_key]
                section_path.append(sec)

            # Set the sec_path for this note
            sections_by_note[note] = set(section_path)

            # Add this note to its direct parent section.
            section_path[-1].notes.add(note)

            # Make connections between sections
            section_edges = zip(section_path[:-1], section_path[1:])
            for sec, child_sec in section_edges:
                sec.children.add(child_sec)
                child_sec.parent = sec

            # Add to virtual section tree
            vsection_tree.add_path(section_path)
            vsections_by_note[note] = set()
            for sec in section_path:
                vsec_name = TreeNode.make_name(sec)
                vsec = vsection_tree.get_vsection(vsec_name)
                vsections_by_note[note].add(vsec)

        return (
            sections,
            sections_by_note,
            vsection_tree,
            vsections_by_note,
        )

    def extract_concepts(self):
        concepts_by_name = {}
        for note in self.definitions:
            concept_name = concept_key(note.name)
            con = Concept(concept_name, set())
            concepts_by_name[con.primary_name] = con

        # Update alternative_names
        for note in self.aliases:
            aliased_concept_name = concept_key(note.alias_of)
            alias_name = concept_key(note.name)
            if not (aliased_concept_name in concepts_by_name):
                print(f"Undefined concept w/ alias: {aliased_concept_name}")
                continue
            aliased_concept = concepts_by_name[aliased_concept_name]
            aliased_concept.alternative_names.add(alias_name)
        all_concepts = list(concepts_by_name.values())
        return Concepts(all_concepts)

    def build_notes_by_concept(self, concepts: Concepts) -> Dict[Concept, Set[Note]]:
        # XXX: Move attr list out or enumerate some other way.
        # Maybe make it per note (concept fields?)
        notes_by_concept: Dict[Concept, Set[Note]] = {}
        attrs = ("name", "meaning", "content")
        for note in self.iter_all():
            for attr in attrs:
                attr_value = getattr(note, attr, None)
                if not attr_value:
                    continue
                for con in self.concepts.find(attr_value):
                    if con not in notes_by_concept:
                        notes_by_concept[con] = set()
                    notes_by_concept[con].add(note)
        return notes_by_concept

    def build_inverted_index(self, only_initial=False):
        '''
        :only_initial - only index first token of every concept.
        '''
        # Make inverted index
        index = defaultdict(set)
        for note in self.iter_all():
            for token in tokenize(note.name):
                index[token].add(note)
                if only_initial:
                    break
        return index

    def find_referenced_notes(self, text, longest_match=True) -> Set[Note]:
        '''
        Extract referenced notes in a piece of text
        '''
        # Extract any notes in a piece of text
        # - Iterate through every token in text. When you find a token
        #   that matches the initial token of a note in collection of
        #   notes, check if the full name of that note is in the text. If
        #   the full name matches then add it to matched notes.
        # - XXX: Upgrade to prefix tree solution if you need it to be more
        #   efficient.
        initial_token_index = self.initial_token_index

        matched_notes = defaultdict(set)
        tokenized_text = tokenize(text)
        normalized_text = normalize_text(text)
        for i, token in enumerate(tokenized_text):
            potential_matches = initial_token_index[token]
            for note in potential_matches:
                normalized_name = normalize_text(note.name)
                position = normalized_text.find(normalized_name)
                if position < 0:
                    continue # -1 when not found
                matched_notes[position].add(note)

        # Take note with longest match + drop position info
        # - If you have note like "good burger" and another note
        #   like "good", you typically only want "good burger" since it's the
        #   longest match.
        final_matches = set()
        for pos, notes in matched_notes.items():
            if longest_match:
                longest_match = max(notes, key=lambda x: len(x.name))
                final_matches.add(longest_match)
            else:
                for note in notes:
                    final_matches.add(note)
        return final_matches

    def iter_all(self):
        for notes in (
            self.definitions,
            self.aliases,
            self.examples,
            self.procedures,
            self.notes,
        ):
            for note in notes:
                yield note

    @classmethod
    def from_notes_file(cls, file_path):
        doc_name = Path(file_path).stem
        doc = Document.from_file(doc_name, file_path)
        graph = TextGraph.from_document(doc)
        return cls.from_text_graph(graph)

    @classmethod
    def from_text_graph(cls, text_graph):
        # Extract all notes
        notes_by_type = dict(
            definition=[],
            alias=[],
            example=[],
            procedure=[],
            note=[],
        )
        for text_node in text_graph.search():
            if not text_node.text:
                continue
            if text_node.text == "STOP_PARSING":
                break
            tags = find_tags(text_node)
            if not tags:
                continue

            for note_type, type_tags in cls.TAGS_BY_TYPE.items():
                note_class = cls.NOTE_CLASS_BY_TYPE[note_type]
                for tag in tags:
                    if tag in type_tags:
                        note = note_class.from_text_node(text_node)
                        notes_by_type[note_type].append(note)

        return cls(
            definitions=notes_by_type["definition"],
            aliases=notes_by_type["alias"],
            examples=notes_by_type["example"],
            procedures=notes_by_type["procedure"],
            notes=notes_by_type["note"],
        )

    def virtual_outline(self, notes: Set[Note] = None, mask: Note = None):
        # Get subset of vsections that are relevant for the notes of
        # interest to include.
        includes = None
        if notes:
            includes = set()
            for note in notes:
                includes.update(self.vsections_by_note[note])

        # Display outline
        # - Show relevant vsections and--for each vsection--any notes
        #   of interest that belong to that vsection.
        # - XXX It's possible to get the same vsection twice, so might
        #   want to collapse notes on subsequent when that happens.
        output = []
        info: List[Union[TreeNode, Note]] = []
        for vsection, depth in self.vsection_tree.iter_vsections(includes=includes):
            ind = depth * self.INDENT
            child_ind = (depth + 1) * self.INDENT
            output.append(ind + vsection.display_name())
            info.append(vsection)
            for note in vsection.notes():
                if (notes is not None) and (note not in notes):
                    continue
                if note == mask:
                    note_str = "???"
                else:
                    note_str = f"{note.TAG}: {note.name}"
                output.append(child_ind + note_str)
                info.append(note)
        output_str = "\n".join(output)
        return output_str, info


def get_highlightables(file_path):
    structured_notes = StructuredNotes.from_notes_file(file_path)

    # Select subset of notes that should be highlighted.
    snotes = structured_notes.definitions + structured_notes.aliases
    highlightables = []
    for thing in snotes:
        highlightables.append(thing.name.lower())
        # highlightables.append(thing.name.title())
    return highlightables


class NoteTypes:
    DEFINITION = 0
    ALIAS = 1
    EXAMPLE = 2
    PROCEDURE = 3
    EXAMPLE = 4
    NOTE = 5


def coverage_view(file_path, indent_spaces=4):
    structured_notes = StructuredNotes.from_notes_file(file_path)

    # Aggregate notes by concept (definition key)
    to_iter = [
        (NoteTypes.DEFINITION, structured_notes.definitions),
        (NoteTypes.ALIAS, structured_notes.aliases),
        (NoteTypes.EXAMPLE, structured_notes.examples),
        (NoteTypes.PROCEDURE, structured_notes.procedures),
        (NoteTypes.NOTE, structured_notes.notes),
    ]
    notes_by_definition = defaultdict(list)
    for note_type, notes in to_iter:
        for note in notes:
            for assoc_concept in note.associations():
                notes_by_definition[assoc_concept].append((
                    note_type,
                    note,
                ))

    # Grab definitions in page order
    defs_to_iter = [(source_line_num(x), x) for x in structured_notes.definitions]
    defs_to_iter.sort(key=lambda x: x[0])

    # Compose view
    display_string = ""
    for _, def_note in defs_to_iter:
        def_name = concept_key(def_note.name)
        display_string += f"\n{def_name}"

        notes = notes_by_definition[def_name]
        notes.sort(key=lambda x: x[0])
        for note_type, note in notes:
            indent = " " * indent_spaces
            label = note.name
            tag = None
            if note_type == NoteTypes.DEFINITION:
                tag = "DEF"
                label = truncated_text(note.meaning)
            elif note_type == NoteTypes.ALIAS:
                tag = "ALIAS"
            elif note_type == NoteTypes.EXAMPLE:
                tag = "EX"
            elif note_type == NoteTypes.PROCEDURE:
                tag = "PROC"
            elif note_type == NoteTypes.NOTE:
                tag = "NOTE"
                label = truncated_text(note.name)
            display_string += f"\n{indent}{label} [{tag.lower()}]"
    return display_string


def update_coverage_file(notes_file_path, coverage_file_path, indent_spaces=4):
    view = coverage_view(notes_file_path, indent_spaces)
    with open(coverage_file_path, 'w') as f:
        f.write(view)


if __name__ == "__main__":
    pass
