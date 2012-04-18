#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Copyright (C) 2012 Rodrigo Pinheiro Marques de Araujo
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.


LICENSE = """ Copyright (C) 2012 Rodrigo Pinheiro Marques de Araujo

 This program is free software; you can redistribute it and/or modify it under
 the terms of the GNU General Public License as published by the Free Software
 Foundation; either version 2 of the License, or (at your option) any later
 version.

 This program is distributed in the hope that it will be useful, but WITHOUT
 ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
 details.

 You should have received a copy of the GNU General Public License along with
 this program; if not, write to the Free Software Foundation, Inc., 51
 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA."""


import os
import gtk
import thread
import pynotify


from Xlib import X, XK, display
from Xlib.protocol import rq



try:
    from Xlib.ext import record
except ImportError:
    print "RECORD extension not found"
    sys.exit(1)



class XOrgKeyObserver(object):

    CAPS_LOCK_MASK = 1
    NUM_LOCK_MASK = 2
    SCROLL_LOCK_MASK = 4


    def __init__(self, listener):
        self.local_dpy = display.Display()
        self.record_dpy = display.Display()
        self.listener = listener
        self.ctx = None
        if not self.record_dpy.has_extension("RECORD"):
            print "RECORD extension not found"
            sys.exit(1)

   
    def lookup_keysym(self, keysym):
        for name in dir(XK):
            if name[:3] == "XK_" and getattr(XK, name) == keysym:
                return name[3:]
        return "[%d]" % keysym

    @property
    def num_lock(self):
        control = self.local_dpy.get_keyboard_control()
        return bool( control.led_mask & self.NUM_LOCK_MASK )

    @property
    def caps_lock(self):
        control = self.local_dpy.get_keyboard_control()
        return bool( control.led_mask & self.CAPS_LOCK_MASK )

    @property
    def scroll_lock(self):
        control = self.local_dpy.get_keyboard_control()
        return bool( control.led_mask & self.SCROLL_LOCK_MASK )


    def _xorg_callback(self, reply):

        if reply.category != record.FromServer:
            return
        if reply.client_swapped:
            print "* received swapped protocol data, cowardly ignored"
            return
        if not len(reply.data) or ord(reply.data[0]) < 2:
            # not an event
            return

        if self.stop:
            self.stop = False
            self.local_dpy.record_disable_context(self.ctx)
            self.local_dpy.flush()
            return

        data = reply.data
        while len(data):
            event, data = rq.EventField(None).parse_binary_value(data, 
                                                    self.record_dpy.display, 
                                                    None, 
                                                    None)

            if event.type == X.KeyPress:
                pr = event.type == X.KeyPress and "Press"

                keysym = self.local_dpy.keycode_to_keysym(event.detail, 0)
                key = self.lookup_keysym(keysym)
                if key == "Num_Lock":
                    self.listener.num_lock_pressed()
                elif key == "Caps_Lock":
                    self.listener.caps_lock_pressed()
                elif key == "Scroll_Lock":
                    self.listener.scroll_lock_pressed()
                else:
                    pass #ignore

            

    def listen(self):
        self.stop = False
        self.ctx = self.record_dpy.record_create_context(
                0,
                [record.AllClients],
                [{
                        'core_requests': (0, 0),
                        'core_replies': (0, 0),
                        'ext_requests': (0, 0, 0, 0),
                        'ext_replies': (0, 0, 0, 0),
                        'delivered_events': (0, 0),
                        'device_events': (X.KeyPress, X.MotionNotify),
                        'errors': (0, 0),
                        'client_started': False,
                        'client_died': False,
                }])
        self.record_dpy.record_enable_context(self.ctx, self._xorg_callback)
        self.record_dpy.record_free_context(self.ctx)




class App(object):


    def __init__(self):
        self.setup_icon()
        self.load_menu()
        self.stop = False
        self.observer = XOrgKeyObserver(listener=self)
        self.num_lock_state = self.observer.num_lock
        self.caps_lock_state = self.observer.caps_lock
        self.scroll_lock_state = self.observer.scroll_lock
        pynotify.init("PyLedsStatus")
        self.notification = pynotify.Notification("LED Status", "")
        self.notification.set_timeout(5000)
        self.notification.set_icon_from_pixbuf(self.icon.get_pixbuf())



    def show_led_status(self):
        message = ""
        message += "Num Lock - %s\n" %\
                self._get_status_to_str(self.num_lock_state)
        message += "Caps Lock - %s\n" %\
                self._get_status_to_str(self.caps_lock_state)
        message += "Scroll Lock - %s\n" %\
                self._get_status_to_str(self.scroll_lock_state)

        self.notification.update("LED Status", message)
        self.notification.show()

    def setup_icon(self):
        self.icon = gtk.StatusIcon()
        self.icon.set_from_file("/usr/share/icons/gnome/24x24/apps/accessories-character-map.png")
        self.icon.set_visible(True)
        self.icon.connect('popup_menu', self.popup_menu)
        self.icon.connect('activate', self.icon_activate)


    def icon_activate(self, *args):
        self.show_led_status()


    def load_menu(self):
        self.menu = gtk.Menu()

        about = gtk.ImageMenuItem("About")
        img = gtk.Image()
        img.set_from_stock(gtk.STOCK_ABOUT, gtk.ICON_SIZE_MENU)
        about.set_image(img)
        about.connect('activate', self.menu_item_callback, "About")

        exit = gtk.ImageMenuItem("Exit")
        img = gtk.Image()
        img.set_from_stock(gtk.STOCK_QUIT, gtk.ICON_SIZE_MENU)
        exit.set_image(img)
        exit.connect('activate', self.menu_item_callback, "Exit")


        self.menu.append(about)
        self.menu.append(exit)

        self.menu.show_all()


    def menu_item_callback(self, widget, item):
        if item == "About":
            self.show_about()
        else:
            self.stop = True
            gtk.main_quit()


    def _get_status_to_str(self, status):
        if status:
            return "Enabled"
        return "Disabled"

    def num_lock_pressed(self):
        self.num_lock_state = not self.num_lock_state
        self.show_notify("Num Lock", 
                         self._get_status_to_str(self.num_lock_state))

    def caps_lock_pressed(self):
        self.caps_lock_state = not self.caps_lock_state
        self.show_notify("Caps Lock", 
                         self._get_status_to_str(self.caps_lock_state))

    def scroll_lock_pressed(self):
        self.scroll_lock_state = not self.scroll_lock_state
        self.show_notify("Scroll Lock", 
                         self._get_status_to_str(self.scroll_lock_state))


    def show_notify(self, led_name, led_status):
        message = "%s - %s" % (led_name, led_status)
        self.notification.update("LED Status", message)
        self.notification.show()


    def show_about(self):
        self.about = gtk.AboutDialog()
        self.about.set_name("PyLedsStatus")
        self.about.set_version("0.1")
        self.about.set_comments("Show keyboard leds status")
        self.about.set_copyright("Copyright (C) 2012 Rodrigo Pinheiro Marques de Araujo")
        self.about.set_authors(["Rodrigo Pinheiro Marques de Araujo <fenrrir@gmail.com>"])
        self.about.set_license(LICENSE)
        self.about.set_program_name("PyLedsStatus")
        self.about.set_website("http://github.com/fenrrir")
        self.about.run()
        self.about.destroy()

 

    def popup_menu(self, widget, button, ctime):
        self.menu.popup(None, None, 
                        gtk.status_icon_position_menu, 
                        button, ctime, widget)

    def run(self):
        self.show_led_status()
        #self.observer.listen()
        gtk.gdk.threads_init()
        thread.start_new_thread(self.observer.listen, ())
        gtk.gdk.threads_leave()
        gtk.main()



if __name__ == "__main__":
    App().run()
