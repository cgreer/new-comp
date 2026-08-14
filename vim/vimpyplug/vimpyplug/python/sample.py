import vim

from dataclasses import dataclass, field
from typing import (
    Any,
    List,
    Optional,
    Dict,
    Tuple,
)

from pathlib import Path
import json
from collections import defaultdict

from texttable import TextTable

HOME = str(Path.home())

enu = enumerate


class SearchRegions:
    UNDER = 0
    ABOVE = 1
    AROUND = 2


SearchRegionsVal = int
Distance = int
StartLineNum = int
EndLineNum = int


@dataclass
class Section:
    line_num: int
    line: str
    level: int # Root's level is -1
    parent: Optional['Section'] = field(repr=False) # Root's parent is None
    children: List['Section'] = field(repr=False)

    def _hash_key(self) -> Tuple[Any, ...]:
        return (self.line_num,)

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False

        return self._hash_key() == other._hash_key()

    def __hash__(self):
        return hash(self._hash_key())

    def path(self) -> List['Section']:
        p = []
        curr = self
        while True:
            if curr.parent is None:
                break
            p.append(curr)
            curr = curr.parent
        p.reverse()
        return p

    def selected_outline_view(self) -> List['Section']:
        '''
        Give that this section is "selected", return the path of
        sections to this section (from root to this section) and it's
        child sections.
        '''
        view = self.path()
        view.extend(self.children)
        return view

    def under_view(self) -> List['Section']:
        '''
        Give that this section is "selected", return the path of
        sections to this section (from root to this section) and it's
        child sections.
        '''
        view = self.path()[:-1]
        nearest_under = self.nearest(n=35, region=SearchRegions.UNDER)
        view.extend([x[0] for x in nearest_under])
        view.sort(key=lambda x: x.line_num)
        return view

    def above_view(self) -> List['Section']:
        '''
        Give that this section is "selected", return the path of
        sections to this section (from root to this section) and it's
        child sections.
        '''
        nearest = self.nearest(n=35, region=SearchRegions.ABOVE)
        view = [x[0] for x in nearest]
        for node in self.path()[:-1]:
            if node in view:
                continue
            view.append(node)
        view.sort(key=lambda x: x.line_num)
        return view

    def local_tasks_view(self) -> List['Section']:
        '''
        Get all tasks under this root node.
        '''

        def is_task_sec(s):
            if " !!" in s.line:
                return True
            if " ??" in s.line:
                return True
            return False

        view_secs = set()
        for sec, distance in self.search():
            if is_task_sec(sec):
                view_secs.update(sec.path())
        view = sorted(view_secs, key=lambda x: x.line_num)
        return view

    def search(
        self,
        region: SearchRegionsVal = SearchRegions.UNDER,
    ) -> List[Tuple['Section', Distance]]:
        # Set max level
        # - If ABOVE is specified, then don't search under this node's
        #   level.
        max_level = 1_000_000
        if region == SearchRegions.ABOVE:
            max_level = self.level

        # Initialize Queue
        queue = []
        queue.append((self, 0))
        seen = set([self])

        # Search
        nodes = []
        while queue:
            cnode, cdistance = queue.pop()
            if cnode.parent:
                nodes.append((cnode, cdistance))
            if not cnode.parent:
                continue

            # Add children
            for child in cnode.children:
                if child.level > max_level:
                    continue
                if child not in seen:
                    queue.append((child, cdistance + 1))
                    seen.add(child)

            # Add parent
            if region in (SearchRegions.ABOVE, SearchRegions.AROUND):
                if cnode.parent not in seen:
                    queue.append((cnode.parent, cdistance + 1))
                    seen.add(cnode.parent)

        return nodes

    def nearest(
        self,
        n: int,
        region: SearchRegionsVal,
    ) -> List[Tuple['Section', Distance]]:
        all_nodes = self.search(region=region)
        all_nodes.sort(key=lambda x: x[1])
        return all_nodes[:n]

    def range(self) -> Tuple[StartLineNum, EndLineNum]:
        end = -1
        for sec, dist in self.search():
            end = max(sec.line_num, end)
        return self.line_num, end


Level = int


def selected_section_range(kwargs):
    _, highlighted_section = parse_local_sections()
    hrange = highlighted_section.range()
    return list(hrange)


def indent_level(text: str, spaces_per=4):
    indent_spaces = len(text) - len(text.lstrip())
    level = indent_spaces // spaces_per
    return level


RootSection = Section
HighlightedSection = Section


def parse_sections(
    min_line: int,
    max_line: int,
    cursor_location: int,
) -> Tuple[RootSection, HighlightedSection]:
    current_section: Dict[Level, Section] = {}

    root_section = Section(
        line_num=-1,
        line="",
        level=-1,
        parent=None,
        children=[],
    )
    current_section[-1] = root_section

    lines = vim.current.buffer
    highlighted_section = None
    for line_idx, line in enu(lines[min_line: max_line + 1]):
        line_num = min_line + line_idx
        if not line.strip():
            continue
        level = indent_level(line)

        # Make new section
        parent = current_section[level - 1]
        section = Section(
            line_num=line_num,
            line=line,
            level=level,
            parent=parent,
            children=[],
        )
        current_section[level] = section
        if not highlighted_section and (line_num >= cursor_location):
            highlighted_section = section

        # Add to parent's children
        parent.children.append(section)

    return root_section, highlighted_section


def toggle_task(kwargs):
    cbuffer = vim.current.buffer
    cwindow = vim.current.window

    # Get current line info
    clnum = cwindow.cursor[0]
    cline = cbuffer[clnum - 1]

    # Compose new line
    # - Figure out which task it is currently on and cycle to
    #   the next one.
    if " !!" in cline:
        toggled_line = cline.replace("!!", "??")
    elif " ??" in cline:
        toggled_line = cline.replace(" ??", "")
    else:
        toggled_line = cline + " !!"

    # Replace line with toggled line
    cbuffer[clnum - 1] = toggled_line


def toggle_note(kwargs):
    cbuffer = vim.current.buffer
    cwindow = vim.current.window

    # Get current line info
    clnum = cwindow.cursor[0]
    cline = cbuffer[clnum - 1]

    # Compose new line
    # - Figure out which task it is currently on and cycle to
    #   the next one.
    if " NOTE" in cline:
        toggled_line = cline.replace("NOTE", "PROC")
    elif " PROC" in cline:
        toggled_line = cline.replace("PROC", "EX")
    elif " EX" in cline:
        toggled_line = cline.replace("EX", "DEF")
    elif " DEF" in cline:
        toggled_line = cline.replace(" DEF", "")
    else:
        toggled_line = cline + " NOTE"

    # Replace line with toggled line
    cbuffer[clnum - 1] = toggled_line


def print_country():
    print("Country")


def make_test():
    # File path of buffer you're in
    cur_word = vim.eval('expand("<cWORD>")')
    test_string = f"def test_{cur_word}():\n    pass"
    return test_string


def indentation_level(line, spaces_per_level=4):
    num_left_spaces = len(line) - len(line.lstrip())
    if (num_left_spaces % spaces_per_level) != 0:
        raise ValueError("Not an increment of spaces_per_level")
    return int(num_left_spaces / spaces_per_level)


def log_menu_choice(selection):
    path = HOME + "/menu_choices.log"
    with open(path, 'a') as f:
        f.write("\n" + selection)
    return None


INFINIMENU_CHOICES = {
    'PasteFromClipboard()',
    'InsertMRUText()',
    'TogglePaste()',
    'Tableify()',
    'InsertSymbol()',
    'InsertUnicodeSymbol()',
    'TriageSessionStart()',
    'TriageSessionStart(15)',
    'TriageSessionStart(30)',
    'PyMakeTest()',
    'MRUFiles()',
    'MRUDirectories()',
    'MRUClean()',
    'FZFBufferLines()',
    'FZFFiles()',
    'FZFRipGrep()',
    'Attr2Args()',
    'DataclassSnippet()',
    'NewPyFileSnippet()',
    'IfNameMainSnippet()',
}


def menu_choices_lru():
    path = HOME + "/menu_choices.log"
    choices = set()
    last_choices = []
    with open(path, 'r') as f:
        lines = f.readlines()
        for choice in lines[::-1]:
            choice_clean = choice.strip()
            if not choice_clean:
                continue
            if choice_clean not in INFINIMENU_CHOICES:
                continue
            if choice_clean in choices:
                continue
            choices.add(choice_clean)
            last_choices.append(choice_clean)
    for choice in INFINIMENU_CHOICES:
        if choice not in choices:
            last_choices.append(choice)
    return last_choices


def get_current_line():
    current_window = vim.current.window
    cursor_row, cursor_column = current_window.cursor
    current_buffer = vim.current.buffer
    current_line = current_buffer[cursor_row - 1]
    return current_line


def level_topics():
    # Get current line
    cur_line = get_current_line()

    # Collect all headings at this level
    current_buffer = vim.current.buffer # List[str]
    # level = indentation_level(cur_line)
    level = len(cur_line) - len(cur_line.lstrip())
    menu_lines = []
    for i, line in enumerate(current_buffer):
        if not line.strip():
            continue
        line_level = len(line) - len(line.lstrip())
        if line_level != level:
            continue
        menu_line = format_jumpable_line(i, line)
        menu_lines.append(menu_line)
    return menu_lines


def format_jumpable_line(line_num, content):
    jumpable_line = "{:<9}{}".format(line_num, content.rstrip())
    return jumpable_line


def get_table_text(header_line_num):
    '''
    Collect lines until you hit a blank line
    '''
    buf_lines = vim.current.buffer

    table_text = ""
    line_num = header_line_num
    while buf_lines[line_num - 1].strip():
        table_text += buf_lines[line_num - 1].strip() + "\n"
        line_num += 1
    return table_text, line_num - 1


def toggle_table(kwargs):
    curs_line_num, curs_col = vim.current.window.cursor
    cbuffer = vim.current.buffer
    cur_line = cbuffer[curs_line_num - 1]
    is_raw_table = "|" in cur_line

    # Find header line
    # - If raw, scroll up until you get to a line that doesn't have
    #   pipe and use the last piped line.
    # - If formatted, you're either on the header line already (check
    #   the next line for header row) or you need to scan up the document
    #   until you find the header row.
    header_line_num = None
    if is_raw_table:
        scan_lnum = curs_line_num
        while True:
            if scan_lnum <= 1:
                break
            if "|" not in cbuffer[scan_lnum - 1]:
                break
            scan_lnum -= 1
        header_line_num = scan_lnum + 1
    else:
        next_line = cbuffer[curs_line_num]
        if TextTable.HEADER_ROW_CHAR in next_line:
            header_line_num = curs_line_num
        else:
            scan_lnum = curs_line_num
            while True:
                if scan_lnum <= 1:
                    break
                if TextTable.HEADER_ROW_CHAR in cbuffer[scan_lnum - 1]:
                    break
                scan_lnum -= 1
            header_line_num = scan_lnum - 1
    assert header_line_num

    ttext, last_line_num = get_table_text(header_line_num)
    if is_raw_table:
        tt = TextTable.from_raw_text(ttext)
        output_text = tt.to_formatted_table()
    else:
        tt = TextTable.from_formatted_text(ttext)
        output_text = tt.to_raw_table()
    # print(output_text)

    # Format output lines
    # - Indent to original indentation
    indent_len = len(cur_line) - len(cur_line.lstrip())
    output_lines = output_text.strip().split("\n")
    output_lines = [(" " * indent_len) + x for x in output_lines]

    # Replace lines
    # - Delete lines
    # - Append table text at line X
    del vim.current.buffer[header_line_num - 1:last_line_num]
    vim.current.buffer.append(output_lines, header_line_num - 1)

    # Move cursor to end of table at indented column
    final_table_end = header_line_num + len(output_lines) - 1
    vim.current.window.cursor = (final_table_end, indent_len)


def tablify(json_args):
    kwargs = json.loads(json_args)
    assert "text" in kwargs

    sep = "|"

    # First pass
    # - Get longest field per column
    # - Get table data sans indentations
    row_content = []
    longest_per_col = defaultdict(int)
    num_cols = None
    lines = kwargs["text"].split("\n")
    for line in lines:
        if line.strip().startswith('--'):
            continue
        content = [x.strip() for x in line.split(sep)]
        for col_idx, col in enu(content):
            col_width = len(col) + 1 # +1 for comma
            if col_width >= longest_per_col[col_idx]:
                longest_per_col[col_idx] = col_width
        if num_cols is None:
            num_cols = len(content)
        else:
            assert len(content) == num_cols
        row_content.append(content)

    # Compute max_len
    max_len = sum(longest_per_col.values())
    max_len += (num_cols - 1) * 3

    # Compose final table
    table_lines = []
    indent = len(lines[0]) - len(lines[0].lstrip())
    indent_text = " " * indent
    for i, row in enu(row_content):
        table_line = []
        for col_idx in range(num_cols):
            if col_idx == (num_cols - 1):
                # Last column
                just_amnt = 0
            else:
                # Not last column
                just_amnt = longest_per_col[col_idx]
            just_text = (row[col_idx]).ljust(just_amnt)
            table_line.append(just_text)
        table_lines.append(indent_text + f" {sep} ".join(table_line))
        # Header line
        if i == 0:
            table_lines.append(indent_text + "-" * max_len)

    return table_lines


def get_line_num():
    return int(vim.eval("line('.')")) - 1


def is_top_level_line(line):
    if line[0] in (" ", "\t"):
        return False
    return True


class FileTypes:
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    CPP = "cpp"
    WIKI = "wiki"
    UNKNOWN = "unknown"

    @classmethod
    def from_path(cls, file_path):
        suffix = file_path.split(".")[-1]
        if suffix == "py":
            return cls.PYTHON
        elif suffix == "wiki":
            return cls.WIKI
        elif suffix == "js":
            return cls.JAVASCRIPT
        elif suffix in ("cpp", "cc", "h", "hpp"):
            return cls.CPP
        else:
            return cls.UNKNOWN


def extract_lines(
    patterns,
    toplevel=False,
    only_local=None,
):
    '''
    only_local: if int supplied, restrict lines to "local" tags (those
    in that local indent level.
    '''
    lines = vim.current.buffer

    # Restrict to relevant lines
    min_line = 0
    max_line = len(lines) - 1
    if only_local is not None:
        for line_num in range(only_local, -1, -1):
            line = lines[line_num]
            if line.strip() == "":
                continue
            if is_top_level_line(lines[line_num]):
                min_line = line_num
                break

        # If line called from is top level then we want to collect all
        # tags under that top-level tag, so start collecting from next
        # line instead of current one.
        start_line = only_local
        line = lines[only_local]
        if line.strip() != "":
            if is_top_level_line(lines[only_local]):
                start_line += 1

        for line_num in range(start_line, len(lines)):
            line = lines[line_num]
            if line.strip() == "":
                continue
            if is_top_level_line(lines[line_num]):
                max_line = line_num - 1
                break

    # Extract lines from relevant range
    fzf_lines = []
    for line_num in range(min_line, max_line):
        line = lines[line_num]
        if line.strip() == "":
            continue

        # Only allow toplevel lines if requested
        if toplevel is True:
            if not is_top_level_line(line):
                continue

        # Only allow lines that pass pattern
        checks = [pat(line) for pat in patterns]
        if not any(checks):
            continue

        fzf_line = format_jumpable_line(line_num, line)
        fzf_lines.append(fzf_line)
    return fzf_lines


def class_pat(line):
    return line.strip().startswith("class ")


def def_pat(line):
    return line.strip().startswith("def ")


FXN_NAME_LETTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
FXN_NAME_LETTERS = set(list(FXN_NAME_LETTERS))


def lame_cc_pat(line):
    if "(" not in line:
        return False

    lstrp = line.strip()
    for excluded_start in ("//", "for", "while", "if"):
        if lstrp.startswith(excluded_start):
            return False
    if lstrp.endswith(";"):
        return False

    parts = line.split("(")
    if "=" in parts[0]:
        return False

    return True


def js_func_pat(line):
    if line.strip().startswith("if "):
        return False
    if line.strip().startswith("for "):
        return False

    letters, lp, rp, rb = False, False, False, False
    for char in line.strip():
        if char in FXN_NAME_LETTERS:
            letters = True
        if letters:
            if char == "(":
                lp = True
        if letters and lp:
            if char == ")":
                rp = True
        if letters and lp and rp:
            if char == "{":
                rb = True

        if not lp:
            if char not in FXN_NAME_LETTERS:
                return False

    return letters and lp and rp and rb


def js_func_pat2(line):
    return "function" in line


def section_depth_3(line):
    # Check if <= depth 3
    indent_len = len(line) - len(line.strip())
    if indent_len > (2 * 4):
        return False

    # Check if non-blank
    return len(line.strip()) > 0


def section_depth_2(line):
    # Check if <= depth 3
    indent_len = len(line) - len(line.strip())
    if indent_len > (1 * 4):
        return False

    # Check if non-blank
    return len(line.strip()) > 0


def section_depth_1(line):
    # Check if <= depth 3
    indent_len = len(line) - len(line.strip())
    if indent_len > (0 * 4):
        return False

    # Check if non-blank
    return len(line.strip()) > 0


def taglines():
    # File path of buffer you're in
    file_path = vim.eval('expand("%:p")')

    ft = FileTypes.from_path(file_path)
    if ft == FileTypes.PYTHON:
        patterns = [class_pat, def_pat]
    elif ft == FileTypes.JAVASCRIPT:
        patterns = [class_pat, js_func_pat2]
    elif ft == FileTypes.CPP:
        patterns = [class_pat, lame_cc_pat]
    else:
        patterns = [section_depth_1]

    # Collect all the class/def lines
    return extract_lines(patterns)


def classlines():
    patterns = [class_pat]
    return extract_lines(patterns)


def top_tags():
    # Collect all the class/def lines
    patterns = [class_pat, def_pat]
    return extract_lines(patterns, toplevel=True)


def local_tags():
    # File path of buffer you're in
    file_path = vim.eval('expand("%:p")')
    line_num = get_line_num()

    ft = FileTypes.from_path(file_path)
    if ft == FileTypes.PYTHON:
        patterns = [class_pat, def_pat]
    elif ft == FileTypes.JAVASCRIPT:
        patterns = [class_pat, js_func_pat2]
    elif ft == FileTypes.CPP:
        patterns = [class_pat, js_func_pat]
    else:
        return selected_outline()
        # patterns = [section_depth_3]

    # Collect all the class/def lines
    return extract_lines(patterns, only_local=line_num)


def local_tasks():
    return local_tasks_outline()


def section_span(cursor_location: int) -> Tuple[int, int]:
    '''
    Get the starting/ending line numbers of a main section in a block
    of text.
    '''
    # Find start/end of section
    lines = vim.current.buffer
    start_location = cursor_location
    while True:
        if start_location == 0:
            break
        line = lines[start_location]
        if line and is_top_level_line(line):
            break
        start_location -= 1

    end_location = cursor_location + 1
    while True:
        if end_location >= len(lines):
            break
        line = lines[end_location]
        if line and is_top_level_line(line):
            break
        end_location += 1

    return start_location, end_location


def parse_local_sections():
    cursor_location = get_line_num()
    start_loc, end_loc = section_span(cursor_location)
    root_section, highlighted_section = parse_sections(
        min_line=start_loc,
        max_line=end_loc,
        cursor_location=cursor_location,
    )
    return root_section, highlighted_section


def secs_to_fzf(secs, highlighted_section):
    fzf_lines = []
    for section in secs:
        line = section.line
        if section is highlighted_section:
            line += "           <--------- YOU ARE HERE"
        fzf_line = format_jumpable_line(section.line_num, line)
        fzf_lines.append(fzf_line)
    return fzf_lines


def selected_outline():
    root_section, highlighted_section = parse_local_sections()
    return secs_to_fzf(
        highlighted_section.under_view(),
        highlighted_section,
    )


def above_outline():
    root_section, highlighted_section = parse_local_sections()
    return secs_to_fzf(
        highlighted_section.above_view(),
        highlighted_section,
    )


def local_tasks_outline():
    root_section, highlighted_section = parse_local_sections()
    fzf_lines = []
    for section in root_section.local_tasks_view():
        fzf_line = format_jumpable_line(section.line_num, section.line)
        fzf_lines.append(fzf_line)
    return fzf_lines


def local_tags_d2():
    # File path of buffer you're in
    file_path = vim.eval('expand("%:p")')
    line_num = get_line_num()

    ft = FileTypes.from_path(file_path)
    if ft == FileTypes.PYTHON:
        patterns = [class_pat, def_pat]
    elif ft == FileTypes.JAVASCRIPT:
        patterns = [class_pat, js_func_pat]
    elif ft == FileTypes.CPP:
        patterns = [class_pat, js_func_pat]
    else:
        patterns = [section_depth_2]

    # Collect all the class/def lines
    return extract_lines(patterns, only_local=line_num)


def attr_to_args(json_kwargs):
    kwargs = json.loads(json_kwargs)
    start = kwargs["start"]
    end = kwargs["end"]
    cbuffer = vim.current.buffer
    for lnum in range(start - 1, end):
        cline = cbuffer[lnum]
        replacement = cline.split(":")[0]
        replacement += "=" + replacement.strip() + ","
        cbuffer[lnum] = replacement


DATACLASS_SNIPPET = [
    "from dataclasses import dataclass, field",
    "@dataclass",
    "class ReplaceMe:",
    "    relace_me: int",
    "    relace_me: field(init=False)",
    "",
    "    def __post_init__(self):",
    "        pass",
]

TYPING_SNIPPET = [
    "from typing import (",
    "    Any,",
    "    Optional,",
    "    Union,",
    "    ClassVar,",

    "    Dict,",
    "    List,",
    "    Tuple,",
    ")",
]

IF_NAME_MAIN_SNIPPET = [
    'if __name__ == "__main__":',
    "    test()",
]


NEW_PY_FILE_SNIPPET = [
    "from typing import (",
    "    Any,",
    "    Optional,",
    "    Union,",
    "    ClassVar,",

    "    Dict,",
    "    List,",
    "    Tuple,",
    ")",
    "",
    "",
    "enu = enumerate",
    "",
    "",
    "def test():",
    "    pass",
    "",
    "",
    'if __name__ == "__main__":',
    "    test()",
]


def inject_snippet(snippet: List[str]):
    cwindow = vim.current.window
    cursor_line = cwindow.cursor[0]
    cbuffer = vim.current.buffer
    cbuffer.append(snippet, cursor_line - 1)


def data_class_snippet(json_kwargs):
    return inject_snippet(DATACLASS_SNIPPET)


def if_name_main_snippet(json_kwargs):
    return inject_snippet(IF_NAME_MAIN_SNIPPET)


def new_py_file_snippet(json_kwargs):
    return inject_snippet(NEW_PY_FILE_SNIPPET)
