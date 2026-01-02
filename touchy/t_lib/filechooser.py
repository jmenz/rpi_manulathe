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

# Modified for USB support
# Modified for USB support (Local first, then USB)

import os
import getpass
from gi.repository import Gdk

class filechooser:
    def __init__(self, gtk, emc, labels, eventboxes, listing, colors):
        self.labels = labels
        self.eventboxes = eventboxes
        self.numlabels = len(labels)
        self.listing = listing
        self.gtk = gtk
        self.emc = emc
        self.emccommand = emc.command()
        self.fileoffset = 0
        
        self.local_dir = os.path.join(os.getenv('HOME'), 'linuxcnc', 'nc_files')
        
        self.colors = colors
        
        self.files = [] 
        self.reload(0)

    def populate(self):
        page_files = self.files[self.fileoffset:]
        
        for i in range(self.numlabels):
            l = self.labels[i]
            e = self.eventboxes[i]
            
            if i < len(page_files):
                l.set_text(page_files[i][0])
            else:
                l.set_text('')

            if self.selected == self.fileoffset + i:
                e.modify_bg(self.gtk.StateFlags.NORMAL, self.colors['selected_bg'])
                l.modify_fg(self.gtk.StateFlags.NORMAL, self.colors['selected_fg'])
            else:
                e.modify_bg(self.gtk.StateFlags.NORMAL, self.colors['normal_bg'])
                l.modify_fg(self.gtk.StateFlags.NORMAL, self.colors['normal_fg'])

    def select(self, eventbox, event):
        try:
            name = self.gtk.Buildable.get_name(eventbox)
            n = int(name[20:])
        except (ValueError, IndexError):
            return

        idx = self.fileoffset + n
        if idx >= len(self.files):
            return ""

        display_name, full_path = self.files[idx]
        
        if full_path is None:
            return ""
        
        self.selected = idx
        self.emccommand.mode(self.emc.MODE_MDI)
        self.emccommand.program_open(full_path)
        self.listing.readfile(full_path)
        self.populate()
        return full_path

    def select_and_show(self, fn):
        self.reload(0)
        
        found_idx = -1
        for i, (name, path) in enumerate(self.files):
            if path == fn:
                found_idx = i
                break
        
        if found_idx == -1:
            base = os.path.basename(fn)
            for i, (name, path) in enumerate(self.files):
                if path and os.path.basename(path) == base:
                    found_idx = i
                    break

        if found_idx == -1:
            return 

        self.selected = found_idx
        page = found_idx // self.numlabels
        self.fileoffset = page * self.numlabels
        
        self.listing.readfile(fn)
        self.populate()

    def up(self, b):
        self.fileoffset -= self.numlabels
        if self.fileoffset < 0:
            self.fileoffset = 0
        self.populate()

    def down(self, b):
        self.fileoffset += self.numlabels
        if self.fileoffset >= len(self.files):
             self.fileoffset = max(0, len(self.files) - self.numlabels)
             if self.fileoffset < 0: self.fileoffset = 0
        self.populate()

    def reload(self, b):
        local_files = []
        usb_files = []
        valid_exts = ('.ngc', '.nc', '.tap', '.gcode')

        if os.path.exists(self.local_dir):
            try:
                for f in os.listdir(self.local_dir):
                    if f.lower().endswith(valid_exts):
                        full_path = os.path.join(self.local_dir, f)
                        if os.path.isfile(full_path):
                            local_files.append((f, full_path))
            except OSError:
                pass
        
        local_files.sort(key=lambda x: x[0])

        user = getpass.getuser()
        media_root = os.path.join('/media', user)
        if os.path.exists(media_root):
            try:
                for mount in os.listdir(media_root):
                    mount_path = os.path.join(media_root, mount)
                    if os.path.isdir(mount_path):
                        for f in os.listdir(mount_path):
                            if f.lower().endswith(valid_exts):
                                full_path = os.path.join(mount_path, f)
                                if os.path.isfile(full_path):
                                    # No prefix, just the filename
                                    usb_files.append((f, full_path))
            except OSError:
                pass

        usb_files.sort(key=lambda x: x[0])

        self.files = local_files
        
        if usb_files:
            self.files.append(("--- USB ---", None)) 
            self.files.extend(usb_files)
        
        self.selected = -1
        self.populate()