#!/usr/bin/env python3

import sys
import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

sys.path.append(os.path.join(os.getcwd(), 'touchy'))
try:
    from t_lib import preferences
    HAS_PREFS = True
except ImportError:
    HAS_PREFS = False
    print(">>> WARNING: Could not import preferences from ./touchy/t_lib/")

class HandlerClass:
    def __init__(self, halcomp, builder, useropts):
        self.builder = builder
        self.halcomp = halcomp
    
        self.gremlin = self.builder.get_object("hal_gremlin1")
        if not self.gremlin:
            print(">>> ERROR: 'hal_gremlin1' not found in UI file")

        self.sync_theme_with_touchy()

    def on_clear_clicked(self, widget):
        if hasattr(self.gremlin, "clear_live_plotter"):
            self.gremlin.clear_live_plotter()

    def apply_zoom(self, factor):
        if hasattr(self.gremlin, "get_zoom_distance"):
            dist = self.gremlin.get_zoom_distance()
            self.gremlin.set_zoom_distance(dist * factor)
            self.gremlin.queue_draw()

    def on_zoom_in_clicked(self, widget):
        self.apply_zoom(0.8)

    def on_zoom_out_clicked(self, widget):
        self.apply_zoom(1.25)

    def sync_theme_with_touchy(self):
        if not HAS_PREFS:
            return

        prefs = preferences.preferences()
        theme_name = prefs.getpref('gtk_theme', 'Follow System Theme', str)

        if theme_name == "Follow System Theme":
            return

        settings = Gtk.Settings.get_default()
        try:
            settings.set_property("gtk-theme-name", theme_name)
        except Exception as e:
            print(f">>> ERROR setting theme: {e}")


def get_handlers(halcomp, builder, useropts):
    return [HandlerClass(halcomp, builder, useropts)]