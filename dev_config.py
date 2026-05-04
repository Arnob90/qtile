# dev_config.py
from libqtile import layout, bar, widget
from libqtile.config import Key, Screen, Group
from libqtile.lazy import lazy
from libqtile.backend.wayland import InputConfig

mod = "mod4"  # CapsLock mapped to Super

keys = [
    Key([mod], "Return", lazy.spawn("alacritty")),  # Use a terminal you have installed
    Key([mod, "control"], "r", lazy.reload_config()),
    Key([mod, "control"], "q", lazy.shutdown()),
]

groups = [Group(i) for i in "123"]

layouts = [layout.Tile(), layout.Max()]

# Minimal bar so you can see it's working
screens = [
    Screen(
        bottom=bar.Bar(
            [
                widget.GroupBox(),
                widget.WindowName(),
                widget.Clock(format="%Y-%m-%d %a %I:%M %p"),
            ],
            24,
        ),
    ),
]
