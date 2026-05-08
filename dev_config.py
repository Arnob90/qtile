from libqtile.backend.wayland.animate import AnimationManagerBuilder, NoOpAnimationManager
from libqtile import layout, bar, widget
from libqtile.config import Key, Screen, Group, Drag, Click
from libqtile.lazy import lazy


mod = "mod4"  # Super key
terminal = "alacritty"  # Change to your preferred terminal
menu = "rofi -show drun"


def ease_out_quartic(progress: float) -> float:
    # Clamp progress to [0, 1]
    t = max(0.0, min(1.0, progress))

    # Quartic ease-out curve
    return 1.0 - (1.0 - t) ** 4


animation_manager = NoOpAnimationManager()
keys = [
    # --- Launching ---
    Key([mod], "Return", lazy.spawn(terminal)),
    Key([mod], "d", lazy.spawn(menu)),
    Key([mod], "semicolon", lazy.spawn("rofi -show emoji")),
    Key([mod], "Print", lazy.spawn("flameshot gui")),
    # --- Window Management ---
    Key([mod], "w", lazy.window.kill()),
    Key([mod], "g", lazy.window.toggle_floating()),
    Key([mod], "Tab", lazy.window.toggle_fullscreen()),
    Key([mod, "shift"], "Return", lazy.layout.toggle_split()),
    # --- Directional Focus (Hyprland HJKL) ---
    Key([mod], "h", lazy.layout.left()),
    Key([mod], "l", lazy.layout.right()),
    Key([mod], "j", lazy.layout.down()),
    Key([mod], "k", lazy.layout.up()),
    # --- Shuffle/Swap (Hyprland Shift + HJKL) ---
    Key([mod, "shift"], "h", lazy.layout.shuffle_left()),
    Key([mod, "shift"], "l", lazy.layout.shuffle_right()),
    Key([mod, "shift"], "j", lazy.layout.shuffle_down()),
    Key([mod, "shift"], "k", lazy.layout.shuffle_up()),
    # --- Resize (Hyprland Ctrl + HJKL) ---
    Key([mod, "control"], "h", lazy.layout.grow_left()),
    Key([mod, "control"], "l", lazy.layout.grow_right()),
    Key([mod, "control"], "j", lazy.layout.grow_down()),
    Key([mod, "control"], "k", lazy.layout.grow_up()),
    # --- System Control ---
    Key([mod, "control"], "r", lazy.reload_config()),
    Key([mod, "control"], "q", lazy.shutdown()),
]

# --- Groups (Workspaces) ---
# Mod + [1-9] = Switch to group
# Mod + Shift + [1-9] = Move window to group
groups = [Group(i) for i in "123456789"]

for i in groups:
    keys.extend(
        [
            Key([mod], i.name, lazy.group[i.name].toscreen(), desc=f"Switch to group {i.name}"),
            Key(
                [mod, "shift"],
                i.name,
                lazy.window.togroup(i.name),
                desc=f"Move focused window to group {i.name}",
            ),
        ]
    )

# --- Layouts ---
# 'Columns' is the most Hyprland-like for window placement logic
layouts = [
    layout.Columns(border_focus="#5294e2", border_normal="#2c313a", border_width=2, margin=8),
    layout.Max(),
]

# --- Screen & Bar ---
screens = [
    Screen(
        bottom=bar.Bar(
            [
                widget.GroupBox(highlight_method="line", urgent_border="#ff0000"),
                widget.WindowName(),
                widget.Clock(format="%Y-%m-%d %a %I:%M %p"),
                widget.StatusNotifier(),  # For system tray icons in Wayland
            ],
            28,
            background="#1e222a",
        ),
    ),
]

# --- Mouse Bindings ---
mouse = [
    Drag([mod], "Button1", lazy.window.set_position_floating(), start=lazy.window.get_position()),
    Drag([mod], "Button3", lazy.window.set_size_floating(), start=lazy.window.get_size()),
    Click([mod], "Button2", lazy.window.bring_to_front()),
]
# Standard Qtile defaults
dgroups_key_binder = None
dgroups_app_rules = []
follow_mouse_focus = True
bring_front_click = False
cursor_warp = False
auto_fullscreen = True
focus_on_window_activation = "smart"
reconfigure_screens = True
auto_minimize = True
wl_input_rules = None
wmname = "LG3D"
