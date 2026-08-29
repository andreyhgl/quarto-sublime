import sublime
import sublime_plugin

# Correct fold/unfold for Quarto fenced divs (::: blocks), pairing fences with
# a proper stack so sibling and nested divs always fold to their own closing
# fence. Bound to the standard fold/unfold keys when the caret is on a fence
# line (see Default.sublime-keymap).

BEGIN_SEL = "meta.fenced-div.definition.begin"
END_SEL = "meta.fenced-div.definition.end"


def _line_regions(view, selector):
    """Fence lines for a selector, split per line (adjacent regions can merge)."""
    out = []
    for region in view.find_by_selector(selector):
        out.extend(view.lines(region))
    return out


def _div_pairs(view):
    """(begin_line, end_line) pairs via stack pairing in document order."""
    events = [(r.begin(), 0, r) for r in _line_regions(view, BEGIN_SEL)]
    events += [(r.begin(), 1, r) for r in _line_regions(view, END_SEL)]
    events.sort(key=lambda e: (e[0], e[1]))
    stack, pairs = [], []
    for _, kind, region in events:
        if kind == 0:
            stack.append(region)
        elif stack:
            pairs.append((stack.pop(), region))
    return pairs


def _innermost_pair_at(view, point):
    best = None
    for begin, end in _div_pairs(view):
        if begin.begin() <= point <= end.end():
            if best is None or begin.begin() >= best[0].begin():
                best = (begin, end)
    return best


def _fold_region(begin, end):
    # end of the opening line's text -> end of the closing line's text:
    # the opening fence stays visible, everything through the closing fence
    # collapses to "...", and following content keeps its own line.
    return sublime.Region(begin.end(), end.end())


class QuartoFoldDivCommand(sublime_plugin.TextCommand):
    """Fold the innermost fenced div at the caret; run again to unfold."""

    def run(self, edit):
        view = self.view
        if not view.sel():
            return
        pair = _innermost_pair_at(view, view.sel()[0].begin())
        if not pair:
            return
        region = _fold_region(*pair)
        if not view.fold(region):
            view.unfold(region)

    def is_enabled(self):
        return self.view.match_selector(0, "text.html.markdown.quarto")


class QuartoUnfoldDivCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        if not view.sel():
            return
        pair = _innermost_pair_at(view, view.sel()[0].begin())
        if pair:
            view.unfold(_fold_region(*pair))

    def is_enabled(self):
        return self.view.match_selector(0, "text.html.markdown.quarto")