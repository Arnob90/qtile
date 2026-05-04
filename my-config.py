from libqtile import layout, hook, qtile
from libqtile import widget as no_deco_widget
from qtile_extras import widget
from qtile_extras.widget.decorations import PowerLineDecoration
from libqtile.config import Click, Drag, Group, Key, Match, Screen
from libqtile.lazy import lazy
from libqtile.utils import guess_terminal
from key.keybinds import KeyBindings
import essentials
from libqtile.command.client import InteractiveCommandClient
from bar import bar_defaults
import pathlib

root = InteractiveCommandClient()
config_path = "/home/arnob/.config/qtile/"


@hook.subscribe.startup
def startup():
    """Startup necessary programs."""
    if qtile.core.name == "x11":
        essentials.run_async_cmd_command_function("picom")
    if qtile.core.name == "wayland":
        essentials.run_async_cmd_command_function("swaync")
    essentials.run_async_cmd_command_function("fdm")
    essentials.run_cmd_command_function("setxkbmap -option terminate:ctrl_alt_bksp")
    # essentials.run_async_cmd_command_function(
    #     "python $HOME/.config/qtile/window-rules.py"
    # )


@hook.subscribe.startup_once
def first_start():
    essentials.run_async_cmd_command_function("lxqt-policykit-agent")
    essentials.run_async_cmd_command_function(
        "/usr/lib/notification-daemon-1.0/notification-daemon"
    )


@hook.subscribe.startup_complete
def after_startup_complete():
    essentials.run_async_cmd_command_function("ibus-daemon")
    essentials.run_async_cmd_command_function("nm-applet")
    # mouse_id: int = 10
    # essentials.run_async_cmd_command_function(
    #     f"xinput - -set-prop {mouse_id} 'libinput Accel Profile Enabled' 0, 1")
    # essentials.run_async_cmd_command_function(
    #     "xinput - -set-prop {mouse_id} 'libinput Accel Speed' 1")


@hook.subscribe.client_new
def setup_window_rules(window):
    """Rules for windows."""
    if window.name == "Albert":
        albert_window_config = (
            f"{config_path}/window-rules/send_albert_to_current_group.py"
        )
        essentials.run_async_cmd_command_function(f"python {albert_window_config}")


mod = "mod4"
terminal = guess_terminal()

keys = KeyBindings().keys.copy()
move_directional_keys = {
    "left": [lazy.layout.left(), lazy.layout.shuffle_left()],
    "right": [lazy.layout.right(), lazy.layout.shuffle_right()],
    "up": [lazy.layout.up(), lazy.layout.shuffle_up()],
    "down": [lazy.layout.down(), lazy.layout.shuffle_down()],
}
for key in move_directional_keys:
    keys.append(Key([mod], key, move_directional_keys[key][0]))
    keys.append(Key([mod, "shift"], key, move_directional_keys[key][1]))

groups = [Group(i) for i in "123456789"]

for i in groups:
    keys.extend(
        [
            # mod1 + letter of group = switch to group
            Key(
                [mod],
                i.name,
                lazy.group[i.name].toscreen(),
                desc="Switch to group {}".format(i.name),
            ),
            # mod1 + shift + letter of group = switch to & move focused window to group
            Key(
                [mod, "shift"],
                i.name,
                lazy.window.togroup(i.name, switch_group=True),
                desc="Switch to & move focused window to group {}".format(i.name),
            ),
            # Or, use below if you prefer not to switch to that group.
            # # mod1 + shift + letter of group = move focused window to group
            # Key([mod, "shift"], i.name, lazy.window.togroup(i.name),
            #     desc="move focused window to group {}".format(i.name)),
        ]
    )

layouts = [
    layout.Max(),
    layout.Columns(
        border_focus_stack=["#d75f5f", "#8f3d3d"],
        border_width=4,
        margin=5,
        border_focus="#0FE0CD",
    ),
    # Try more layouts by unleashing below layouts.
    # layout.Stack(num_stacks=2),
    # layout.Bsp(),
    # layout.Matrix(),
    # layout.MonadTall(),
    # layout.MonadWide(),
    # layout.RatioTile(),
    # layout.Tile(),
    # layout.TreeTab(),
    # layout.VerticalTile(),
    # layout.Zoomy(),
]
arrow_corners = {"decorations": [PowerLineDecoration(path="arrow_right")]}
widget_defaults = dict(font="nord", fontsize=12, padding=3)
extension_defaults = widget_defaults.copy()
widget_defaulter = bar_defaults.SideBarWidgetDefaults

screens = [
    Screen(
        bottom=bar_defaults.BarDefaults().create_bar(
            [
                widget_defaulter(widget.CurrentLayout).create_widget(),
                widget_defaulter(widget.GroupBox)
                .override(
                    highlight_method="line",
                    highlight_color=widget_defaulter.get_color("sapphire"),
                )
                .create_widget(),
                widget.Prompt(),
                widget.Chord(
                    chords_colors={
                        "launch": ("#ff0000", "#ffffff"),
                    },
                    name_transform=lambda name: name.upper(),
                ),
                widget_defaulter(widget.TaskList)
                .override(
                    highlight_method="block",
                    border=widget_defaulter.get_color("surface1"),
                    **arrow_corners,
                )
                .create_widget(),
                widget_defaulter(widget.Systray)
                .override(
                    background=widget_defaulter.get_color("blue"), **arrow_corners
                )
                .create_widget(),
                widget_defaulter(widget.Memory)
                .override(
                    fmt="Memory: {}",
                    background=widget_defaulter.get_color("green"),
                    foreground="#000000",
                    **arrow_corners,
                )
                .create_widget(),
                widget_defaulter(widget.TextBox)
                .override(
                    text="",
                    background=widget_defaulter.get_color("sky"),
                    foreground="#000000",
                    fontsize=25,
                    width=28,
                )
                .create_widget(),
                widget_defaulter(widget.Clock)
                .override(
                    format="%a %d-%m-%Y  %I:%M:%S %p",
                    background=widget_defaulter.get_color("sky"),
                    foreground="#000000",
                    **arrow_corners,
                )
                .create_widget(),
                # TODO: Enable it when battery is replugged
                # Remove battery stuff as it's removed for the time being
                # widget_defaulter(widget.BatteryIcon)
                # .override(
                #     background=widget_defaulter.get_color("teal"),
                #     foreground="#000000",
                # )
                # .create_widget(),
                # widget_defaulter(
                #     widget.Battery,
                # )
                # .override(
                #     charge_char="C",
                #     discharge_char="",
                #     format="{char} {percent:2.0%}",
                #     background=widget_defaulter.get_color("teal"),
                #     foreground="#000000",
                #     **arrow_corners,
                # )
                # .create_widget(),
                widget_defaulter(widget.QuickExit)
                .override(
                    background=widget_defaulter.get_color("red"),
                    foreground="#000000",
                )
                .create_widget(),
            ],
        ),
        wallpaper=pathlib.Path(
            "~/Pictures/Wallpaper/ItadoriYujiWallpaper.jpg"
        ).expanduser(),
        wallpaper_mode="stretch",
    )
]


# Drag floating layouts.
mouse = [
    Drag(
        [mod],
        "Button1",
        lazy.window.set_position_floating(),
        start=lazy.window.get_position(),
    ),
    Drag(
        [mod], "Button3", lazy.window.set_size_floating(), start=lazy.window.get_size()
    ),
    Click([mod], "Button2", lazy.window.bring_to_front()),
]

dgroups_key_binder = None
dgroups_app_rules = []  # type: list
follow_mouse_focus = True
bring_front_click = False
cursor_warp = False
floating_layout = layout.Floating(
    float_rules=[
        # Run the utility of `xprop` to see the wm class and name of an X client.
        *layout.Floating.default_float_rules,
        Match(wm_class="confirmreset"),  # gitk
        Match(wm_class="makebranch"),  # gitk
        Match(wm_class="dialog"),
        Match(wm_class="maketag"),  # gitk
        Match(wm_class="ssh-askpass"),  # ssh-askpass
        Match(title="branchdialog"),  # gitk
        Match(title="pinentry"),  # GPG key password entry
    ],
    border_width=0,
    border_focus="#000000",
    border_normal="#000000",
)
auto_fullscreen = True
focus_on_window_activation = "smart"
reconfigure_screens = True
# If things like steam games want to auto-minimize themselves when losing
# focus, should we respect this or not?
auto_minimize = True

# When using the Wayland backend, this can be used to configure input devices.
wl_input_rules = None

# XXX: Gasp! We're lying here. In fact, nobody really uses or cares about this
# string besides java UI toolkits; you can see several discussions on the
# mailing lists, GitHub issues, and other WM documentation that suggest setting
# this string if your java app doesn't work correctly. We may as well just lie
# and say that we're a working one by default.
#
# We choose LG3D to maximize irony: it is a 3D non-reparenting WM written in
# java that happens to be on java's whitelist.
wmname = "LG3D"
