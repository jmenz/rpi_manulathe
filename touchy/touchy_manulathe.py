#!/usr/bin/python3

# Touchy is Copyright (c) 2009  Chris Radek <chris@timeguy.com>
#
# Touchy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Touchy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

#modified by jmenz89

import sys, os
BASE = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), ".."))
libdir = os.path.join(BASE, "lib", "python")
datadir = os.path.join(BASE, "share", "linuxcnc")
sys.path.insert(0, libdir)
themedir = "/usr/share/themes"

custom_lib_path = './touchy/'
sys.path.append(os.path.dirname(custom_lib_path))

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Pango

import atexit
import tempfile
import signal
import locale
import time
import subprocess

empty_program = tempfile.NamedTemporaryFile()
empty_program.write(b"%\n%\n")
empty_program.flush()

import gettext
LOCALEDIR = os.path.join(BASE, "share", "locale")
locale.setlocale(locale.LC_ALL, '')
locale.bindtextdomain("linuxcnc", LOCALEDIR)
gettext.install("linuxcnc", localedir=LOCALEDIR)

def set_active(w, s):
    if not w: return
    os = w.get_active()
    if os != s: w.set_active(s)

def set_label(w, l):
    if not w: return
    ol = w.get_label()
    if ol != l: w.set_label(l)

def set_text(w, t):
    if not w: return
    ot = w.get_label()
    if ot != t: w.set_label(t)

def show_widget(w):
    if not w: return
    if not w.get_visible():
        w.show()

def hide_widget(w):
    if not w: return
    if w.get_visible():
        w.hide()

import linuxcnc
from t_lib import emc_interface
from t_lib import mdi
from t_lib import hal_interface
from t_lib import filechooser
from t_lib import listing
from t_lib import preferences
from QuitDialog import QuitDialog

pix_data = '''/* XPM */
static char * invisible_xpm[] = {
"1 1 1 1",
"        c None",
" "};'''


#color = Gdk.Color(0,0,0)
#pix = Gdk.pixmap_create_from_data(None, pix_data, 1, 1, 1, color, color)
#invisible = Gdk.Cursor(pix, pix, color, color, 0, 0)

class touchy:
    def __init__(self, inifile):
        # System default Glade file:
        self.gladefile = os.path.join(datadir, "touchy.glade")
        if inifile:
            self.ini = linuxcnc.ini(inifile)
            alternate_gladefile = self.ini.find("DISPLAY", "GLADEFILE")
            if alternate_gladefile:
                self.gladefile = alternate_gladefile
        else:
            self.ini = None

        self.wTree = Gtk.Builder()
        self.wTree.add_from_file(self.gladefile)

        for widget in self.wTree.get_objects():
            try:
                widget.set_can_focus(False)
            except:
                pass

        self.widgets = {} # local storgage of widgets
        self.get_widget('MainWindow').set_can_focus(True)
        self.get_widget('MainWindow').grab_focus()

        self.num_mdi_labels = 11
        self.num_filechooser_labels = 11
        self.num_listing_labels = 20

        self.wheelinc = 0
        self.wheel = "fo"
        self.radiobutton_mask = 0
        self.resized_wheelbuttons = 0

        self.tab = 0

        self.fo_val = 100
        self.so_val = 100
        self.g10l11 = 1

        self.prefs = preferences.preferences()
        self.mv_val = self.prefs.getpref('maxvel', 100, int)
        self.jog_vel_val = self.prefs.getpref('maxvel', 100, int)
        self.control_font_name = self.prefs.getpref('control_font', 'Sans 18', str)
        self.dro_font_name = self.prefs.getpref('dro_font', 'FreeMono 10 Pitch Bold 16', str)
        self.error_font_name = self.prefs.getpref('error_font', 'Sans Bold 10', str)
        self.listing_font_name = self.prefs.getpref('listing_font', 'Sans 10', str)
        self.theme_name = self.prefs.getpref('gtk_theme', 'Follow System Theme', str)
        self.abs_textcolor = self.prefs.getpref('abs_textcolor', 'default', str)
        self.rel_textcolor = self.prefs.getpref('rel_textcolor', 'default', str)
        self.dtg_textcolor = self.prefs.getpref('dtg_textcolor', 'default', str)
        self.err_textcolor = self.prefs.getpref('err_textcolor', 'default', str)
        self.window_geometry = self.prefs.getpref('window_geometry', 'default', str)
        self.window_max = self.prefs.getpref('window_force_max', 'false', bool)

        self.velocity_limit = float(self.ini.find("DISPLAY", "MAX_LINEAR_VELOCITY"))
        self.default_velocity = float(self.ini.find("DISPLAY", "DEFAULT_LINEAR_VELOCITY"))

        self.spindle_default_speed = float(self.ini.find("DISPLAY", "SPINDLE_DEFAULT_SPEED"))
        self.spindle_increment = float(self.ini.find("DISPLAY", "SPINDLE_INCREMENT"))
        self.spindle_max_speed = float(self.ini.find("DISPLAY", "SPINDLE_MAX_SPEED"))

        self.spindle_speed_val = self.prefs.getpref('spindle_speed', self.spindle_default_speed, float)

        # initial screen setup
        if os.path.exists(themedir):
            model = self.get_widget("theme_choice").get_model()
            model.clear()
            model.append((_("Follow System Theme"),))
            temp = 0
            names = os.listdir(themedir)
            names.sort()
            for search,dirs in enumerate(names):
                model.append((dirs,))
                if dirs  == self.theme_name:
                    temp = search+1
            self.get_widget("theme_choice").set_active(temp)

        if self.window_geometry == "default":
            self.get_widget("MainWindow").maximize()
        else:
            self.get_widget("MainWindow").parse_geometry(self.window_geometry)
            if self.window_max:
                self.get_widget("MainWindow").window.maximize()
        self.invisible_cursor = self.prefs.getpref('invisible_cursor', 0)
        if self.invisible_cursor:
            self.pointer_hide()
        else:
            self.pointer_show()
        self.get_widget("controlfontbutton").set_font(self.control_font_name)
        self.control_font = Pango.FontDescription(self.control_font_name)

        self.get_widget("drofontbutton").set_font(self.dro_font_name)
        self.dro_font = Pango.FontDescription(self.dro_font_name)

        self.get_widget("errorfontbutton").set_font(self.error_font_name)
        self.error_font = Pango.FontDescription(self.error_font_name)

        self.get_widget("listingfontbutton").set_font(self.listing_font_name)
        self.listing_font = Pango.FontDescription(self.listing_font_name)

        self.colors = {
            'selected_bg': Gdk.color_parse('#0F579B'),
            'selected_fg': Gdk.color_parse('#fcfcfc'),
            'normal_bg':   Gdk.color_parse('#ccc'),
            'normal_fg':   Gdk.color_parse('#232323')
        }

        settings = Gtk.Settings.get_default()
        self.system_theme = settings.get_property("gtk-theme-name")
        if not self.theme_name == "Follow System Theme":
            settings.set_string_property("gtk-theme-name", self.theme_name, "")

        # interactive mdi command builder and issuer
        mdi_labels = []
        mdi_eventboxes = []
        for i in range(self.num_mdi_labels):
            mdi_labels.append(self.get_widget("mdi%d" % i))
            mdi_eventboxes.append(self.get_widget("eventbox_mdi%d" % i))
        self.mdi_control = mdi.mdi_control(Gtk, linuxcnc, mdi_labels, mdi_eventboxes, self.colors)
        if self.ini:
            macros = self.ini.findall("TOUCHY", "MACRO")
            if len(macros) > 0:
                self.mdi_control.mdi.add_macros(macros)
            else:
                self.get_widget("macro").set_sensitive(0)

        listing_labels = []
        listing_eventboxes = []
        for i in range(self.num_listing_labels):
            listing_labels.append(self.get_widget("listing%d" % i))
            listing_eventboxes.append(self.get_widget("eventbox_listing%d" % i))
        self.listing = listing.listing(Gtk, linuxcnc, listing_labels, listing_eventboxes, self.colors)

        # emc interface
        self.linuxcnc = emc_interface.emc_control(linuxcnc, self.listing, self.get_widget("error"))
        self.linuxcnc.continuous_jog_velocity(self.jog_vel_val)
        self.hal = hal_interface.hal_interface(self, self.linuxcnc, self.mdi_control, linuxcnc)

        # silly file chooser
        filechooser_labels = []
        filechooser_eventboxes = []
        for i in range(self.num_filechooser_labels):
            filechooser_labels.append(self.get_widget("filechooser%d" % i))
            filechooser_eventboxes.append(self.get_widget("eventbox_filechooser%d" % i))
        self.filechooser = filechooser.filechooser(Gtk, linuxcnc, filechooser_labels, filechooser_eventboxes, self.listing, self.colors)

        relative = ['xr', 'yr', 'zr', 'ar', 'br', 'cr', 'ur', 'vr', 'wr']
        absolute = ['xa', 'ya', 'za', 'aa', 'ba', 'ca', 'ua', 'va', 'wa']
        distance = ['xd', 'yd', 'zd', 'ad', 'bd', 'cd', 'ud', 'vd', 'wd']
        relative = [self.get_widget(i) for i in relative]
        absolute = [self.get_widget(i) for i in absolute]
        distance = [self.get_widget(i) for i in distance]
                
        estops = ['estop_reset', 'estop']
        estops = dict((i, self.get_widget(i)) for i in estops)
        machines = ['on', 'off']
        machines = dict((i, self.get_widget("machine_" + i)) for i in machines)
        floods = ['on', 'off']
        floods = dict((i, self.get_widget("flood_" + i)) for i in floods)
        mists = ['on', 'off']
        mists = dict((i, self.get_widget("mist_" + i)) for i in mists)
        spindles = ['forward', 'off', 'reverse']
        spindles = dict((i, self.get_widget("spindle_" + i)) for i in spindles)
        stats = ['file', 'file_lines', 'line', 'id', 'dtg', 'velocity', 'delay', 'onlimit',
                 'spindledir', 'spindlespeed', 'loadedtool', 'preppedtool',
                 'xyrotation', 'tlo', 'activecodes', 'spindlespeed2',
                 'label_g5xoffset', 'g5xoffset', 'g92offset', 'tooltable']
        stats = dict((i, self.get_widget("status_" + i)) for i in stats)
        prefs = ['actual', 'commanded', 'inch', 'mm']
        prefs = dict((i, self.get_widget("dro_" + i)) for i in prefs)
        opstop = ['on', 'off']
        opstop = dict((i, self.get_widget("opstop_" + i)) for i in opstop)
        blockdel = ['on', 'off']
        blockdel = dict((i, self.get_widget("blockdel_" + i)) for i in blockdel)
        spindle_values = ['sp_commanded', 'sp_current', 'sp_angle']
        spindle_values = dict((i, self.get_widget(i)) for i in spindle_values)

        self.status = emc_interface.emc_status(Gtk, linuxcnc, self.listing, self.hal, relative, absolute, distance,
                                               self.get_widget("dro_table"),
                                               self.get_widget("error"),
                                               estops, machines,
                                               self.get_widget("override_limits"),
                                               stats,
                                               floods, mists, spindles, prefs,
                                               opstop, blockdel, spindle_values)

        self.current_file = self.status.emcstat.file
        # check the ini file if UNITS are set to mm"
        # first check the global settings
        units = self.ini.find("TRAJ", "LINEAR_UNITS")
        if units == None:
            units = self.ini.find("AXIS_X", "UNITS")

        if units == "mm" or units == "metric" or units == "1.0":
            self.machine_units_mm = 1
            conversion = [1.0/25.4]*3 + [1]*3 + [1.0/25.4]*3
        else:
            self.machine_units_mm = 0
            conversion = [25.4]*3 + [1]*3 + [25.4]*3

        self.status.set_machine_units(self.machine_units_mm, conversion)

        if self.prefs.getpref('toolsetting_fixture', 0):
            self.g10l11 = 1
        else:
            self.g10l11 = 0

        if self.prefs.getpref('dro_mm', 0):
            self.status.dro_mm(0)
        else:
            self.status.dro_inch(0)

        if self.prefs.getpref('dro_actual', 0):
            self.status.dro_actual(0)
        else:
            self.status.dro_commanded(0)

        if self.prefs.getpref('blockdel', 0):
            self.linuxcnc.blockdel_on(0)
        else:
            self.linuxcnc.blockdel_off(0)

        if self.prefs.getpref('opstop', 1):
            self.linuxcnc.opstop_on(0)
        else:
            self.linuxcnc.opstop_off(0)

        self.linuxcnc.emccommand.program_open(empty_program.name)

        self.linuxcnc.max_velocity(self.mv_val)
                                
        GLib.timeout_add(50, self.periodic_status)
        GLib.timeout_add(100, self.periodic_radiobuttons)

        self.fullscreen = self.prefs.getpref('fullscreen', 1)
        self.fullscreen_startup_processed = 0
        GLib.timeout_add(1500, self.fullscreen_startup)

        # event bindings
        callbacks = {#todo rename
            "quit" : self.quit,
            "on_pointer_show_clicked" : self.pointer_show,
            "on_pointer_hide_clicked" : self.pointer_hide,
            "on_fullscreen_on_clicked" : self.fullscreen_on,
            "on_fullscreen_off_clicked" : self.fullscreen_off,
            "on_opstop_on_clicked" : self.opstop_on,
            "on_opstop_off_clicked" : self.opstop_off,
            "on_blockdel_on_clicked" : self.blockdel_on,
            "on_blockdel_off_clicked" : self.blockdel_off,
            "on_reload_tooltable_clicked" : self.linuxcnc.reload_tooltable,
            "on_notebook1_switch_page" : self.tabselect,
            "on_controlfontbutton_font_set" : self.change_control_font,
            "on_drofontbutton_font_set" : self.change_dro_font,
            "on_dro_actual_clicked" : self.dro_actual,
            "on_dro_commanded_clicked" : self.dro_commanded,
            "on_dro_inch_clicked" : self.dro_inch,
            "on_dro_mm_clicked" : self.dro_mm,
            "on_errorfontbutton_font_set" : self.change_error_font,
            "on_listingfontbutton_font_set" : self.change_listing_font,
            "on_estop_clicked" : self.linuxcnc.estop,
            "on_estop_reset_clicked" : self.linuxcnc.estop_reset,
            "on_machine_off_clicked" : self.linuxcnc.machine_off,
            "on_machine_on_clicked" : self.linuxcnc.machine_on,
            "on_mdi_clear_clicked" : self.mdi_control.clear,
            "on_mdi_back_clicked" : self.mdi_control.back,
            "on_mdi_next_clicked" : self.mdi_control.next,
            "on_mdi_decimal_clicked" : self.mdi_control.decimal,
            "on_mdi_minus_clicked" : self.mdi_control.minus,
            "on_mdi_keypad_clicked" : self.mdi_control.keypad,
            "on_mdi_g_clicked" : self.mdi_control.g,
            "on_mdi_gp_clicked" : self.mdi_control.gp,
            "on_mdi_m_clicked" : self.mdi_control.m,
            "on_mdi_t_clicked" : self.mdi_control.t,
            "on_mdi_select" : self.mdi_control.select,
            "on_mdi_set_tool_clicked" : self.mdi_set_tool,
            "on_mdi_set_origin_clicked" : self.mdi_set_origin,
            "on_mdi_macro_clicked" : self.mdi_macro,
            "on_filechooser_select" : self.fileselect,
            "on_filechooser_up_clicked" : self.filechooser.up,
            "on_filechooser_down_clicked" : self.filechooser.down,
            "on_filechooser_reload_clicked" : self.filechooser.reload,
            "on_listing_up_clicked" : self.listing.up,
            "on_listing_down_clicked" : self.listing.down,
            "on_listing_previous_clicked" : self.listing.previous,
            "on_listing_next_clicked" : self.listing.next,
            "on_listing_select" : self.listing.on_select,
            "on_mist_on_clicked" : self.linuxcnc.mist_on,
            "on_mist_off_clicked" : self.linuxcnc.mist_off,
            "on_flood_on_clicked" : self.linuxcnc.flood_on,
            "on_flood_off_clicked" : self.linuxcnc.flood_off,
            "on_home_all_clicked" : self.linuxcnc.home_all,
            "on_unhome_all_clicked" : self.linuxcnc.unhome_all,
            "on_home_x_clicked" : self.home_x_axis,
            "on_unhome_x_clicked" : self.unhome_x_axis,
            "on_home_z_clicked" : self.home_z_axis,
            "on_unhome_z_clicked" : self.unhome_z_axis,
            "on_fo_clicked" : self.fo,
            "on_so_clicked" : self.so,
            "on_rpm_clicked" : self.rpm,
            "on_mv_clicked" : self.mv,
            "on_manual_clicked" : self.set_manual,
            "on_scrolling_clicked" : self.scrolling,
            "on_override_limits_clicked" : self.linuxcnc.override_limits,
            "on_reset_spinde_index_clicked" : self.reset_spindle_index,
            "on_spindle_forward_clicked" : self.spindle_forward,
            "on_spindle_off_clicked" : self.linuxcnc.spindle_off,
            "on_spindle_reverse_clicked" : self.spindle_reverse,
            "on_spindle_slower_clicked" : self.spindle_slower,
            "on_spindle_faster_clicked" : self.spindle_faster,
            "on_toolset_fixture_clicked" : self.toolset_fixture,
            "on_toolset_workpiece_clicked" : self.toolset_workpiece,
            "on_changetheme_clicked" : self.change_theme,
            "on_shut_down_clicked" : self.shut_down,
        }
        self.wTree.connect_signals(callbacks)

        for widget in self.wTree.get_objects():
            if isinstance(widget, Gtk.Button):
                widget.connect_after('released',self.hack_leave)

        self._dynamic_childs = {}
        atexit.register(self.kill_dynamic_childs)
        self.set_dynamic_tabs()

        atexit.register(self.save_maxvel_pref)
        atexit.register(self.save_spindle_speed)

        self.setfont()

    def quit(self, unused):
        Gtk.main_quit()

    def shut_down(self, unused):
        dialog = QuitDialog()
        dialog.show_all()
        dialog.run()
        dialogResult = dialog.get_value()
        dialog.destroy()
        if (dialogResult == 0 ):
            Gtk.main_quit()
        elif (dialogResult == 1):
            Gtk.main_quit()
            subprocess.Popen('sleep 5 && systemctl reboot &', shell=True)
            # ubprocess.Popen('(sleep 5; gpioset gpiochip0 23=0; systemctl poweroff) & ', shell=True) # for turn off pin
        elif (dialogResult == 2):
            Gtk.main_quit()
            subprocess.Popen('sleep 5 && systemctl poweroff &', shell=True)

    def get_widget(self, widget_name):
        if widget_name not in self.widgets:
            self.widgets[widget_name] = self.wTree.get_object(widget_name)
        return self.widgets[widget_name]

    def tabselect(self, notebook, b, tab):
        self.tab = tab

    def pointer_hide(self, b = None):
            if self.radiobutton_mask: return
            self.prefs.putpref('invisible_cursor', 1)
            self.invisible_cursor = 1
            win = self.get_widget("MainWindow").get_window()
            cursor = Gdk.Cursor(Gdk.CursorType.BLANK_CURSOR)
            win.set_cursor(cursor)

    def pointer_show(self, b = None):
        if self.radiobutton_mask: return
        self.prefs.putpref('invisible_cursor', 0)
        self.invisible_cursor = 0
        win = self.get_widget("MainWindow").get_window()
        cursor = Gdk.Cursor(Gdk.CursorType.ARROW)
        win.set_cursor(cursor)

    def fullscreen_on(self, b):
        if self.radiobutton_mask: return
        self.prefs.putpref('fullscreen', 1)
        self.fullscreen = 1
        self.get_widget('MainWindow').fullscreen()

    def fullscreen_off(self, b):
        if self.radiobutton_mask: return
        self.prefs.putpref('fullscreen', 0)
        self.fullscreen = 0
        self.get_widget('MainWindow').unfullscreen()

    def dro_commanded(self, b):
        if self.radiobutton_mask: return
        self.prefs.putpref('dro_actual', 0)
        self.status.dro_commanded(b)

    def dro_actual(self, b):
        if self.radiobutton_mask: return
        self.prefs.putpref('dro_actual', 1)
        self.status.dro_actual(b)

    def dro_inch(self, b):
        if self.radiobutton_mask: return
        self.prefs.putpref('dro_mm', 0)
        self.status.dro_inch(b)

    def dro_mm(self, b):
        if self.radiobutton_mask: return
        self.prefs.putpref('dro_mm', 1)
        self.status.dro_mm(b)

    def opstop_on(self, b):
        if self.radiobutton_mask: return
        self.prefs.putpref('opstop', 1)
        self.linuxcnc.opstop_on(b)

    def opstop_off(self, b):
        if self.radiobutton_mask: return
        self.prefs.putpref('opstop', 0)
        self.linuxcnc.opstop_off(b)

    def blockdel_on(self, b):
        if self.radiobutton_mask: return
        self.prefs.putpref('blockdel', 1)
        self.linuxcnc.blockdel_on(b)

    def blockdel_off(self, b):
        if self.radiobutton_mask: return
        self.prefs.putpref('blockdel', 0)
        self.linuxcnc.blockdel_off(b)

    def home_x_axis(self, b):
        self.linuxcnc.home_selected(0)

    def unhome_x_axis(self, b):
        self.linuxcnc.unhome_selected(0)

    def home_z_axis(self, b):
        self.linuxcnc.home_selected(2)

    def unhome_z_axis(self, b):
        self.linuxcnc.unhome_selected(2)

    def reset_spindle_index(self, b):
        self.hal.resetSpindel(1)

    def spindle_forward(self, b):
        self.linuxcnc.spindle_forward(self.spindle_speed_val)

    def spindle_reverse(self, b):
        self.linuxcnc.spindle_reverse(self.spindle_speed_val)

    def spindle_faster(self, b):
        if(self.spindle_speed_val < self.spindle_max_speed):
            self.spindle_speed_val += self.spindle_increment
            self.linuxcnc.spindle_set_speed(self.spindle_speed_val)

    def spindle_slower(self, b):
        if(self.spindle_speed_val > 0):
            self.spindle_speed_val -= self.spindle_increment
            self.linuxcnc.spindle_set_speed(self.spindle_speed_val)

    def fo(self, b):
        if self.radiobutton_mask: return
        self.wheel = "fo"

    def so(self, b):
        if self.radiobutton_mask: return
        self.wheel = "so"

    def rpm(self, b):
        if self.radiobutton_mask: return
        self.wheel = "rpm"

    def mv(self, b):
        if self.radiobutton_mask: return
        self.wheel = "mv"

    def scrolling(self, b):
        if self.radiobutton_mask: return
        self.get_widget('notebook1').set_current_page(3)
        self.wheel = "scrolling"

    def set_manual(self, b):
        if self.radiobutton_mask: return
        self.linuxcnc.set_manual_mode(b)

    def toolset_fixture(self, b):
        if self.radiobutton_mask: return
        self.prefs.putpref('toolsetting_fixture', 1)
        self.g10l11 = 1

    def toolset_workpiece(self, b):
        if self.radiobutton_mask: return
        self.prefs.putpref('toolsetting_fixture', 0)
        self.g10l11 = 0

    def change_control_font(self, fontbutton):
        self.control_font_name = fontbutton.get_font()
        self.prefs.putpref('control_font', self.control_font_name, str)
        self.control_font = Pango.FontDescription(self.control_font_name)
        self.setfont()

    def change_dro_font(self, fontbutton):
        self.dro_font_name = fontbutton.get_font()
        self.prefs.putpref('dro_font', self.dro_font_name, str)
        self.dro_font = Pango.FontDescription(self.dro_font_name)
        self.setfont()

    def change_error_font(self, fontbutton):
        self.error_font_name = fontbutton.get_font()
        self.prefs.putpref('error_font', self.error_font_name, str)
        self.error_font = Pango.FontDescription(self.error_font_name)
        self.setfont()

    def change_listing_font(self, fontbutton):
        self.listing_font_name = fontbutton.get_font()
        self.prefs.putpref('listing_font', self.listing_font_name, str)
        self.listing_font = Pango.FontDescription(self.listing_font_name)
        self.setfont()

    def change_theme(self, b):
        tree_iter = b.get_active_iter()
        if tree_iter is not None:
            model = b.get_model()
            theme = model[tree_iter][0]
            self.prefs.putpref('gtk_theme', theme, str)
            if theme == "Follow System Theme":
                theme = self.system_theme
            settings = Gtk.Settings.get_default()
            settings.set_string_property("gtk-theme-name", theme, "")

    def setfont(self):
        # buttons
        for i in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
                  "minus", "decimal", "flood_on", "flood_off", "mist_on", "mist_off",
                  "g", "gp", "m", "t", "set_tool", "set_origin", "macro", "estop",
                  "estop_reset", "machine_off", "machine_on", "home_all", "unhome_all",
                  "home_x", "unhome_x", "home_z", "unhome_z", "fo", "so", "rpm", "mv",
                  "manual_mode", "scrolling", "override_limits", "spindle_forward",
                  "spindle_off", "spindle_reverse", "spindle_faster", "spindle_slower",
                  "dro_commanded", "dro_actual", "dro_inch", "dro_mm",
                  "reload_tooltable", "opstop_on", "opstop_off", "blockdel_on", "blockdel_off",
                  "pointer_hide", "pointer_show", "fullscreen_on", "fullscreen_off",
                  "toolset_workpiece", "toolset_fixture", "change_theme", "reset_spinde_index", "shut_down"]:
            w = self.get_widget(i)
            if w:
                w.override_font(self.control_font)

        notebook = self.get_widget('notebook1')
        for i in range(notebook.get_n_pages()):
            w = notebook.get_nth_page(i)
            notebook.get_tab_label(w).override_font(self.control_font)

        # labels
        for i in range(self.num_mdi_labels):
            w = self.get_widget("mdi%d" % i)
            w.override_font(self.control_font)
        for i in range(self.num_filechooser_labels):
            w = self.get_widget("filechooser%d" % i)
            w.override_font(self.control_font)
        for i in range(self.num_listing_labels):
            w = self.get_widget("listing%d" % i)
            w.override_font(self.listing_font)
        for i in ["mdi", "startup", "manual", "auto", "preferences", "status",
                  "relative", "absolute", "dtg", "ss2label", "status_spindlespeed2",
                  "spindle_stat"]:
            w = self.get_widget(i)
            w.override_font(self.control_font)

        # dro
        for i in ['xr', 'yr', 'zr', 'ar', 'br', 'cr', 'ur', 'vr', 'wr',
                  'xa', 'ya', 'za', 'aa', 'ba', 'ca', 'ua', 'va', 'wa',
                  'xd', 'yd', 'zd', 'ad', 'bd', 'cd', 'ud', 'vd', 'wd']:
                w = self.get_widget(i)
                if w:
                    w.override_font(self.dro_font)
                    if "r" in i and not self.rel_textcolor == "default":
                        w.modify_fg(Gtk.StateFlags.NORMAL,Gdk.color_parse(self.rel_textcolor))
                    elif "a" in i and not self.abs_textcolor == "default":
                        w.modify_fg(Gtk.StateFlags.NORMAL,Gdk.color_parse(self.abs_textcolor))
                    elif "d" in i and not self.dtg_textcolor == "default":
                        w.modify_fg(Gtk.StateFlags.NORMAL,Gdk.color_parse(self.dtg_textcolor))

        # spindle info
        for i in ["sp_commanded", "sp_current", "sp_angle"]:
            w = self.get_widget(i)
            w.override_font(self.dro_font)
            if not self.err_textcolor == "default":
                w.modify_fg(Gtk.StateFlags.NORMAL,Gdk.color_parse(self.dtg_textcolor))

        # status bar
        for i in ["error"]:
            w = self.get_widget(i)
            w.override_font(self.error_font)
            if not self.err_textcolor == "default":
                w.modify_fg(Gtk.StateFlags.NORMAL,Gdk.color_parse(self.err_textcolor))

    def mdi_set_tool(self, b):
        self.mdi_control.set_tool(self.status.get_current_tool(), self.g10l11)

    def mdi_set_origin(self, b):
        self.mdi_control.set_origin(self.status.get_current_system())

    def mdi_macro(self, b):
        self.mdi_control.o(b)

    def fileselect(self, eb, e):
        self.wheel = "scrolling"
        self.current_file = self.filechooser.select(eb, e)
        self.listing.clear_startline()

    def periodic_status(self):
        self.linuxcnc.mask()
        self.radiobutton_mask = 1
        self.status.periodic()
        # check if current_file changed
        # perhaps by another gui or a gladevcp app
        if self.current_file != self.status.emcstat.file:
            self.current_file = self.status.emcstat.file
            self.filechooser.select_and_show(self.current_file)
        self.radiobutton_mask = 0
        self.linuxcnc.unmask()
        self.hal.periodic(self.tab == 1)  # MDI tab?
        return True

    def wheelFoUpdate(self, d):
        if self.hal.wheelreset:
            self.fo_val = 100
            self.linuxcnc.feed_override(self.fo_val)
        else:
            self.fo_val += d
            if self.fo_val < 0:
                self.fo_val = 0
            max_feed_override = float(self.ini.find("DISPLAY", "MAX_FEED_OVERRIDE")) * 100
            if self.fo_val > max_feed_override:
                self.fo_val = max_feed_override
            if d != 0:
                self.linuxcnc.feed_override(self.fo_val)

    def wheelSoUpdate(self, d):
        if self.hal.wheelreset:
            self.so_val = 100
            self.linuxcnc.spindle_override(self.so_val)
        else:
            self.so_val += d
            if self.so_val < 0:
                self.so_val = 0
            max_spindle_override = float(self.ini.find("DISPLAY", "MAX_SPINDLE_OVERRIDE")) * 100
            if self.so_val > max_spindle_override:
                self.so_val = max_spindle_override
            if d != 0:
                self.linuxcnc.spindle_override(self.so_val)

    def wheelRPMUpdate(self, d):
        current_speed = self.spindle_speed_val
        if self.hal.wheelreset:
            self.spindle_speed_val = self.spindle_default_speed
        else:
            self.spindle_speed_val += d * self.spindle_increment
            if self.spindle_speed_val <= 0:
                self.spindle_speed_val = 0
            if self.spindle_speed_val > self.spindle_max_speed:
                self.spindle_speed_val = self.spindle_max_speed
        if current_speed != self.spindle_speed_val:
            self.linuxcnc.spindle_set_speed(self.spindle_speed_val)

    def wheelMvUpdate(self, d):
        if self.hal.wheelreset:
            self.mv_val = self.default_velocity
            self.linuxcnc.max_velocity(self.mv_val)
        else:
            increment = float(d) / 20
            self.mv_val += increment
            if self.mv_val < 0:
                self.mv_val = 0
            if self.mv_val > self.velocity_limit:
                self.mv_val = self.velocity_limit
            if d != 0:
                self.linuxcnc.max_velocity(self.mv_val)

    def wheelJogUpdate(self, d):
        if self.hal.wheelreset:
            self.jog_vel_val = self.default_velocity
            self.linuxcnc.continuous_jog_velocity(self.jog_vel_val)
        else:
            increment = float(d) / 20
            self.jog_vel_val += increment
            if self.jog_vel_val < 0:
                self.jog_vel_val = 0
            if self.jog_vel_val > self.velocity_limit:
                self.jog_vel_val = self.velocity_limit
            if d != 0:
                self.linuxcnc.continuous_jog_velocity(self.jog_vel_val)

    def periodic_radiobuttons(self):
        self.radiobutton_mask = 1
        s = linuxcnc.stat()
        s.poll()
        # Show effect of external override inputs
        self.fo_val = s.feedrate * 100
        self.so_val = s.spindle[0]['override'] * 100
        self.mv_val = s.max_velocity

        self.hal.resetSpindel(0)

        if self.tab != 3 and self.wheel == "scrolling":
            self.wheel = "fo"

        if (self.status.is_manual_mode == 1):
            hide_widget(self.get_widget("fo"))
            hide_widget(self.get_widget("fo"))
            hide_widget(self.get_widget("so"))
            show_widget(self.get_widget("rpm"))
            if self.wheel == "fo" or self.wheel == "so":
                self.wheel = "mv"
        else:
            show_widget(self.get_widget("fo"))
            show_widget(self.get_widget("so"))
            hide_widget(self.get_widget("rpm"))
            if self.wheel == "rpm":
                self.wheel = "fo"

        set_active(self.get_widget("fo"), self.wheel == "fo")
        set_active(self.get_widget("so"), self.wheel == "so")
        set_active(self.get_widget("rpm"), self.wheel == "rpm")
        set_active(self.get_widget("mv"), self.wheel == "mv")
        set_active(self.get_widget("manual_mode"), self.status.is_manual_mode == 1)
        set_active(self.get_widget("scrolling"), self.wheel == "scrolling")
        set_active(self.get_widget("pointer_show"), not self.invisible_cursor)
        set_active(self.get_widget("pointer_hide"), self.invisible_cursor)
        set_active(self.get_widget("fullscreen_on"), self.fullscreen)
        set_active(self.get_widget("fullscreen_off"), not self.fullscreen)
        set_active(self.get_widget("toolset_workpiece"), not self.g10l11)
        set_active(self.get_widget("toolset_fixture"), self.g10l11)
        self.radiobutton_mask = 0

        d = self.hal.wheel()
        if self.wheel == "fo":
            self.wheelFoUpdate(d)
        if self.wheel == "so":
            self.wheelSoUpdate(d)
        if self.wheel == "rpm":
            self.wheelRPMUpdate(d)
        if self.wheel == "mv":
            if (self.status.is_manual_mode == 1):
                self.wheelJogUpdate(d)
            else:
                self.wheelMvUpdate(d)
        if self.wheel == "scrolling":
            d0 = d * 10 ** (2 - self.wheelinc)
            if d != 0:
                self.listing.next(None, d0)

        self.get_widget("fo").set_label("FO: %d%%" % self.fo_val)
        self.get_widget("so").set_label("SO: %d%%" % self.so_val)

        if (self.status.is_manual_mode == 1):
            self.get_widget("rpm").set_label("RPM: %d" % self.spindle_speed_val)
            self.get_widget("mv").set_label("MV: %.2f" % self.jog_vel_val)
        else:
            self.get_widget("mv").set_label("MV: %.2f" % self.mv_val)

        if (self.hal.spindle_forward == 1):
            self.spindle_forward(0)
        
        if (self.hal.spindle_reverse == 1):
            self.spindle_reverse(0)

        if (self.hal.spindle_stop == 1):
            self.linuxcnc.spindle_off(0)

        return True
        
    def fullscreen_startup(self):
        if(self.fullscreen_startup_processed == 1): return
        if (self.fullscreen):
            self.get_widget('MainWindow').fullscreen()                
        self.fullscreen_startup_processed = 1
                
    def hack_leave(self,w):
        if not self.invisible_cursor: return
        w = self.get_widget("MainWindow").get_window()
        d = w.get_display()
        s = w.get_screen()
        _, x, y = Gdk.Window.get_origin(w)
        d.warp_pointer(s, x, y)

    def _dynamic_tab(self, notebook, text):
        s = Gtk.Socket()
        notebook.append_page(s, Gtk.Label(" " + text + " "))
        return s.get_id()

    def set_dynamic_tabs(self):
        from subprocess import Popen
        if not self.ini:
            return
        tab_names = self.ini.findall("DISPLAY", "EMBED_TAB_NAME")
        tab_cmd   = self.ini.findall("DISPLAY", "EMBED_TAB_COMMAND")
        if len(tab_names) != len(tab_cmd):
            print("Invalid tab configuration")  # Complain somehow
        nb = self.get_widget('notebook1')
        for t, c in zip(tab_names, tab_cmd):
            xid = self._dynamic_tab(nb, t)
            if not xid: continue
            cmd = c.replace('{XID}', str(xid))
            child = Popen(cmd.split())
            self._dynamic_childs[xid] = child
            child.send_signal(signal.SIGCONT)
            print("XID = ", xid)
        nb.show_all()

    def kill_dynamic_childs(self):
        for c in list(self._dynamic_childs.values()):
            c.terminate()

    def save_maxvel_pref(self):
        self.prefs.putpref('maxvel', self.mv_val, int)

    def save_spindle_speed(self):
        self.prefs.putpref('spindle_speed', self.spindle_speed_val, float)

    def postgui(self):
        postgui_halfile = self.ini.findall("HAL", "POSTGUI_HALFILE") or None
        return postgui_halfile,sys.argv[2]
 
    def trivkins(self):
        kins = self.ini.find("KINS", "KINEMATICS")
        if kins:
            if "coordinates" in kins:
                return kins.replace(" ","").split("coordinates=")[1].upper()
        return "XYZABCUVW"

if __name__ == "__main__":
        if len(sys.argv) > 2 and sys.argv[1] == '-ini':
            print("INI", sys.argv[2])
            hwg = touchy(sys.argv[2])
        else:
            hwg = touchy()
        # load legacy postgui file if used
        if os.path.exists('touchy.hal'):
            res = os.spawnvp(os.P_WAIT, "halcmd", ["halcmd", "-f", "touchy.hal"])
            if res: raise SystemExit(res)
        #Attempt to support trivkins with non-default axis to joint assignments
        emc_interface.coordinates = touchy.trivkins(hwg)
        print("COORDINATES = %s" % emc_interface.coordinates)
        # load a postgui file if one is present in the INI file
        postgui_halfile,inifile = touchy.postgui(hwg)
        print("TOUCHY postgui filename:",postgui_halfile)
        if postgui_halfile is not None:
            time.sleep(1)
            for f in postgui_halfile:
                if f.lower().endswith('.tcl'):
                    res = os.spawnvp(os.P_WAIT, "haltcl", ["haltcl", "-i", inifile, f])
                else:
                    res = os.spawnvp(os.P_WAIT, "halcmd", ["halcmd", "-i", inifile, "-f", f])
                if res: raise SystemExit(res)
        Gtk.main()
