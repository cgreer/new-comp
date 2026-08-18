from typing import ClassVar, List
from collections import defaultdict
from dataclasses import dataclass

TTableRow = List[str]
MLineCol = List[str]
MLineRow = List[MLineCol]

enu = enumerate


@dataclass
class TextTable:
    rows: List[TTableRow]

    # Formatted table
    MAX_COL_WIDTH: ClassVar[int] = 28
    HEADER_ROW_CHAR: ClassVar[str] = "━"
    BODY_ROW_CHAR: ClassVar[str] = "─"
    CONTINUE_CHAR: ClassVar[str] = "…"

    # Raw table
    RAW_COL_SEP_CHAR: ClassVar[str] = "|"

    @classmethod
    def _wrapped_lines(cls, text, max_width=None) -> List[str]:
        text = text.strip()
        max_width = max_width if max_width else cls.MAX_COL_WIDTH
        wtext = []
        start = 0
        while start < len(text):
            space_wrap = True
            end = start + max_width - 1
            if (end >= len(text)):
                pass
            elif (end + 1 >= len(text)) or (text[end + 1] == " "):
                pass
            else:
                end -= 1
                while text[end + 1] != " ":
                    end -= 1

                    # If we can't find a space to wrap on, then just
                    # split the word.
                    if end <= start:
                        end = start + max_width - 1
                        space_wrap = False
                        break
            wtext.append(text[start:end + 1])
            if space_wrap:
                start = end + 2 # 1 for next char, 1 for space
            else:
                start = end + 1
        return wtext

    @classmethod
    def _get_col_starts(cls, header_line):
        # Get indices of column starts from first line
        # - First line should always have text at the start of
        #   every column position since it's the header row.
        column_starts = []
        prev_ws = 2
        for i, char in enu(header_line):
            if char == " ":
                prev_ws += 1
            else:
                if prev_ws >= 2:
                    column_starts.append(i)
                prev_ws = 0
        return column_starts

    @classmethod
    def _parse_row(cls, row_lines, col_starts):
        # Extract columns
        row = [""] * len(col_starts)
        for line_idx, line in enu(row_lines):
            precedes_another_line = (line_idx < len(row_lines) - 1)
            for col_idx, col_start in enu(col_starts):
                next_col_idx = col_idx + 1
                col_content = ""
                if next_col_idx < len(col_starts):
                    next_start = col_starts[col_idx + 1]
                    col_content = line[col_start:next_start]
                else:
                    col_content = line[col_start:]
                row[col_idx] += (
                    col_content
                    .strip()
                    .replace(cls.CONTINUE_CHAR, "")
                )
                if precedes_another_line:
                    row[col_idx] += " "
        return [x.strip() for x in row]

    @classmethod
    def from_formatted_text(cls, text):
        lines = text.strip().split("\n")

        # Parse out rows
        row_seps = {cls.HEADER_ROW_CHAR, cls.BODY_ROW_CHAR}
        rows: List[TTableRow] = []
        row_lines = []
        col_starts = cls._get_col_starts(lines[0])
        for line in lines:
            if line[0] in row_seps:
                rows.append(cls._parse_row(row_lines, col_starts))
                row_lines = []
            else:
                row_lines.append(line)
        return cls(rows)

    @classmethod
    def from_raw_text(cls, text):
        lines = text.strip().split("\n")
        rows = []
        for line in lines:
            row = [x.strip() for x in line.split(cls.RAW_COL_SEP_CHAR)]
            rows.append(row)
        return cls(rows)

    def to_raw_table(self):
        # XXX: Print out justified just to make it easier to read?
        table_text = ""
        for row in self.rows:
            table_text += " | ".join(row) + "\n"
        return table_text

    def to_formatted_table(self):
        spacer = "    "

        # Convert to multiline rows
        # - Check that all rows have the same number of columns
        #   along the way.
        # - For conversion, first add as many sub rows as you need for
        #   column content that is too long. Then go back through the
        #   other columns as needed and add continuation characters and
        #   blank padding to ensure they all have same number of sub rows.
        num_header_cols = len(self.rows[0])
        ml_rows: List[MLineRow] = []
        for row in self.rows:
            assert len(row) == num_header_cols

            ml_row = []
            for col in row:
                ml_col = self._wrapped_lines(col)
                ml_row.append(ml_col)
            max_sub_rows = max(len(x) for x in ml_row)
            for col_idx, col in enu(ml_row):
                while len(col) < max_sub_rows:
                    cont_char = self.CONTINUE_CHAR
                    if col_idx > 0:
                        cont_char = ""
                    col.append(cont_char)
            ml_rows.append(ml_row)

        # Get longest column for justifying columns
        longest_per_col = defaultdict(int)
        for row in ml_rows:
            for col_idx, col in enu(row):
                col_width = max(len(x) for x in col)
                if col_width >= longest_per_col[col_idx]:
                    longest_per_col[col_idx] = col_width

        # Calculate table width
        # - w = ColumnWidths + SpacerWidths
        num_cols = len(ml_rows[0])
        table_width = sum(longest_per_col.values())
        table_width += (num_cols - 1) * len(spacer)

        # Construct final table
        table_lines = []
        for ml_row_idx, ml_row in enu(ml_rows):
            # Row contents
            num_sub_rows = len(ml_row[0])
            for sub_row_idx in range(num_sub_rows):
                table_line = []
                for col_idx in range(num_cols):
                    is_last_col = col_idx == (num_cols - 1)
                    col = ml_row[col_idx][sub_row_idx]
                    just_amnt = longest_per_col[col_idx]
                    if is_last_col:
                        just_amnt = 0 # Last column
                    just_text = col.ljust(just_amnt)
                    table_line.append(just_text)
                table_lines.append(spacer.join(table_line))

            # Seperator line
            # - Header line if first row, else standard sep line.
            is_header_row = ml_row_idx == 0
            sep_char = self.BODY_ROW_CHAR
            if is_header_row:
                sep_char = self.HEADER_ROW_CHAR
            table_lines.append(sep_char * table_width)
        return "\n".join(table_lines) + "\n"
