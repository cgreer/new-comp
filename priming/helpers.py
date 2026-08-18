
def batchify(iterable, batch_size=1):
    l = len(iterable) # noqa
    for ndx in range(0, l, batch_size):
        yield iterable[ndx:min(ndx + batch_size, l)]


def get_indent_level(line, indent_spaces):
    sub = len(line.lstrip())
    no_sub = len(line)
    level = (no_sub - sub) / indent_spaces
    return int(level)


def unindent(text, indent_spaces=None):
    if indent_spaces is None:
        indent_spaces = len(text) - len(text.lstrip())
    if indent_spaces == 0:
        return text

    lines = text.split("\n")
    ilevel = get_indent_level(lines[0], indent_spaces)

    lines = [x[ilevel * indent_spaces:] for x in lines]
    return "\n".join(lines)


def reindent(text, indent_spaces):
    no_indented = "\n".join(x.strip() for x in text.split("\n"))
    return indent(no_indented, indent_spaces)


def indent(text, indent_spaces):
    lines = text.split("\n")
    lines = [(" " * indent_spaces) + x for x in lines]
    return "\n".join(lines)
