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

import math
import os

from __main__ import set_active, set_text

class emc_control:
        def __init__(self, emc, listing, error, emcstat):
                self.emc = emc
                self.emcstat = emcstat
                self.emccommand = emc.command()
                self.masked = 0
                self.sb = 0
                self.jog_velocity = 10
                self.mdi = 0
                self.spindle_dir = self.emc.SPINDLE_OFF
                self.listing = listing
                self.error = error
                self.isjogging = [0,0,0,0,0,0,0,0,0]
                self.emccommand.teleop_enable(1)
                self.emccommand.wait_complete()
                self.emcstat.poll()
                if self.emcstat.kinematics_type != emc.KINEMATICS_IDENTITY:
                    raise SystemExit("\n*** emc_control: Only KINEMATICS_IDENTITY is supported\n")

        def mask(self):
                # updating toggle button active states dumbly causes spurious events
                self.masked = 1

        def mdi_active(self, m):
                self.mdi = m

        def unmask(self):
                self.masked = 0

        def is_mode_manual(self):
                self.emcstat.poll()
                return self.emcstat.task_state == self.emc.MODE_MANUAL

        def mist_on(self, b):
                if self.masked: return
                self.emccommand.mist(1)

        def mist_off(self, b):
                if self.masked: return
                self.emccommand.mist(0)

        def flood_on(self, b):
                if self.masked: return
                self.emccommand.flood(1)

        def flood_off(self, b):
                if self.masked: return
                self.emccommand.flood(0)

        def estop(self, b):
                if self.masked: return
                self.emccommand.state(self.emc.STATE_ESTOP)

        def estop_reset(self, b):
                if self.masked: return
                self.emccommand.state(self.emc.STATE_ESTOP_RESET)

        def machine_off(self, b):
                if self.masked: return
                self.emccommand.state(self.emc.STATE_OFF)

        def machine_on(self, b):
                if self.masked: return
                self.emccommand.state(self.emc.STATE_ON)

        def home_all(self, b):
                if self.masked: return
                self.emccommand.mode(self.emc.MODE_MANUAL)
                self.emccommand.teleop_enable(0)
                self.emccommand.wait_complete()
                self.emccommand.home(-1)

        def unhome_all(self, b):
                if self.masked: return
                self.emccommand.mode(self.emc.MODE_MANUAL)
                self.emccommand.teleop_enable(0)
                self.emccommand.wait_complete()
                self.emccommand.unhome(-1)

        def home_selected(self, axis):
                if self.masked: return
                self.emccommand.mode(self.emc.MODE_MANUAL)
                self.emccommand.teleop_enable(0)
                self.emccommand.wait_complete()
                joint = coordinates.index("XYZABCUVW"[axis])
                self.emccommand.home(joint)

        def unhome_selected(self, axis):
                if self.masked: return
                self.emccommand.mode(self.emc.MODE_MANUAL)
                self.emccommand.teleop_enable(0)
                self.emccommand.wait_complete()
                joint = coordinates.index("XYZABCUVW"[axis])
                self.emccommand.unhome(joint)

        def set_manual_mode(self, b):
                if self.masked: return
                self.emccommand.mode(self.emc.MODE_MANUAL)

        def set_auto_mode(self, b):
                if self.masked: return
                self.emccommand.mode(self.emc.MODE_AUTO)

        def override_limits(self, b):
                if self.masked: return
                self.emccommand.mode(self.emc.MODE_MANUAL)
                self.emccommand.override_limits()

        def spindle_forward(self, speed):
                if self.masked: return
                self.spindle_dir = self.emc.SPINDLE_FORWARD
                self.emccommand.mode(self.emc.MODE_MANUAL)
                self.emccommand.spindle(self.spindle_dir, speed, 0);

        def spindle_off(self, b):
                if self.masked: return
                self.spindle_dir = self.emc.SPINDLE_OFF
                self.emccommand.mode(self.emc.MODE_MANUAL)
                self.emccommand.spindle(self.spindle_dir);

        def spindle_reverse(self, speed):
                if self.masked: return
                self.spindle_dir = self.emc.SPINDLE_REVERSE
                self.emccommand.mode(self.emc.MODE_MANUAL)
                self.emccommand.spindle(self.spindle_dir, speed, 0);

        def spindle_set_speed(self, speed):
                if self.masked: return
                if self.spindle_dir == self.emc.SPINDLE_OFF : return

                self.emccommand.spindle(self.spindle_dir, speed, 0);

        def spindle_faster(self, b):
                if self.masked: return
                self.emccommand.mode(self.emc.MODE_MANUAL)
                self.emccommand.spindle(self.emc.SPINDLE_INCREASE)

        def spindle_slower(self, b):
                if self.masked: return
                self.emccommand.mode(self.emc.MODE_MANUAL)
                self.emccommand.spindle(self.emc.SPINDLE_DECREASE)

        def set_motion_mode(self):
            self.emcstat.poll()
            if self.emcstat.motion_mode != self.emc.TRAJ_MODE_TELEOP:
                self.emccommand.teleop_enable(1)
                self.emccommand.wait_complete()

        def continuous_jog_velocity(self, velocity):
                self.set_motion_mode()
                self.jog_velocity = velocity
                for i in range(9):
                        if self.isjogging[i]:
                                self.emccommand.jog(self.emc.JOG_CONTINUOUS
                                ,0 ,i ,self.isjogging[i] * self.jog_velocity)
        
        def continuous_jog(self, axis, direction):
                if self.masked: return
                if direction == 0:
                        self.isjogging[axis] = 0
                        self.emccommand.jog(self.emc.JOG_STOP, 0, axis)
                else:
                        self.emccommand.mode(self.emc.MODE_MANUAL)
                        self.set_motion_mode()
                        self.isjogging[axis] = direction
                        self.emccommand.jog(self.emc.JOG_CONTINUOUS, 0, axis, direction * self.jog_velocity)
        
        def quill_up(self):
                if self.masked: return
                self.emccommand.mode(self.emc.MODE_MANUAL)
                self.set_motion_mode()
                self.emccommand.wait_complete()
                self.emccommand.jog(self.emc.JOG_CONTINUOUS, 0, 2, 100)

        def feed_override(self, f):
                if self.masked: return
                self.emccommand.feedrate(f/100.0)

        def spindle_override(self, s):
                if self.masked: return
                self.emccommand.spindleoverride(s/100.0)

        def max_velocity(self, m):
                if self.masked: return
                self.emccommand.maxvel(m)

        def reload_tooltable(self, b):
                if self.masked: return
                self.emccommand.load_tool_table()                

        def opstop_on(self, b):
                if self.masked: return
                self.emccommand.set_optional_stop(1)

        def opstop_off(self, b):
                if self.masked: return
                self.emccommand.set_optional_stop(0)

        def blockdel_on(self, b):
                if self.masked: return
                self.emccommand.set_block_delete(1)

        def blockdel_off(self, b):
                if self.masked: return
                self.emccommand.set_block_delete(0)

        def abort(self):
                self.emccommand.abort()
                set_text(self.error, "")

        def single_block(self, s):
                self.sb = s
                self.emcstat.poll()
                if self.emcstat.queue > 0 or self.emcstat.paused:
                        # program or mdi is running
                        if s:
                                self.emccommand.auto(self.emc.AUTO_PAUSE)
                        else:
                                self.emccommand.auto(self.emc.AUTO_RESUME)

        def cycle_start(self):
                self.emcstat.poll()
                if self.emcstat.paused:
                        if self.sb:
                                self.emccommand.auto(self.emc.AUTO_STEP)
                        else:
                                self.emccommand.auto(self.emc.AUTO_RESUME)
                        return

                if self.emcstat.interp_state == self.emc.INTERP_IDLE:
                        self.emccommand.mode(self.emc.MODE_AUTO)
                        self.emccommand.wait_complete()
                        if self.sb:
                                self.emccommand.auto(self.emc.AUTO_STEP)
                        else:
                                self.emccommand.auto(self.emc.AUTO_RUN, self.listing.get_startline())
                                self.listing.clear_startline()

class emc_status:
        def __init__(self, gtk, emc, listing, hal, relative, absolute, distance,
                     dro_table,
                     error,
                     estops, machines, override_limit, status,
                     floods, mists, spindles, prefs, opstop, blockdel, spindle_values,
                     emcstat):
                self.gtk = gtk
                self.emc = emc
                self.listing = listing
                self.hal = hal
                self.relative = relative
                self.absolute = absolute
                self.distance = distance
                self.dro_table = dro_table
                self.error = error
                self.estops = estops
                self.machines = machines
                self.override_limit = override_limit
                self.status = status
                self.floods = floods
                self.mists = mists
                self.spindles = spindles
                self.prefs = prefs
                self.opstop = opstop
                self.blockdel = blockdel
                self.spindle_values = spindle_values

                self.resized_dro = 0
                
                self.mm = 0
                self.machine_units_mm=0
                self.unit_convert=[1]*9
                self.actual = 0
                self.emcstat = emcstat
                self.emcerror = emc.error_channel()
                
                self.is_manual_mode = 0
                self.is_program_executing = 0

        def dro_inch(self, b):
                self.mm = 0

        def dro_mm(self, b):
                self.mm = 1

        def set_machine_units(self,u,c):
                self.machine_units_mm = u
                self.unit_convert = c

        def convert_units(self,v,c):
                return list(map(lambda x,y: x*y, v, c))

        def dro_commanded(self, b):
                self.actual = 0

        def dro_actual(self, b):
                self.actual = 1

        def get_current_tool(self):
                self.emcstat.poll()
                return self.emcstat.tool_in_spindle

        def get_current_system(self):
                self.emcstat.poll()
                g = self.emcstat.gcodes
                for i in g:
                        if i >= 540 and i <= 590:
                                return i/10 - 53
                        elif i >= 590 and i <= 593:
                                return i - 584
                return 1

        def periodic(self, status_tab_visible=True):
                stat = self.emcstat
                stat.poll()
                # every stat attribute access marshals fresh python objects
                # from the C status buffer, so read each one only once
                am = stat.axis_mask
                lathe = not (am & 2)
                dtg = stat.dtg
                g5x_offset = stat.g5x_offset
                g92_offset = stat.g92_offset
                tool_offset = stat.tool_offset
                homed = stat.homed
                spindle0 = stat.spindle[0]
                rotation_xy = stat.rotation_xy
                task_state = stat.task_state
                self.is_manual_mode = stat.task_mode == self.emc.MODE_MANUAL
                self.is_program_executing = stat.state == self.emc.RCS_EXEC

                if not self.resized_dro:
                        height = 9
                        for i in range(9):
                                if i == 1 and lathe:
                                        continue
                                if not (am & (1<<i)):
                                        height -= 1
                                        self.dro_table.remove(self.relative[height])
                                        self.dro_table.remove(self.absolute[height])
                                        self.dro_table.remove(self.distance[height])
                                        
                        self.dro_table.resize(height, 3)
                        self.resized_dro = 1
                                        
                if self.actual:
                        p = stat.actual_position
                else:
                        p = stat.position

                x = p[0] - g5x_offset[0] - tool_offset[0]
                y = p[1] - g5x_offset[1] - tool_offset[1]
                z = p[2] - g5x_offset[2] - tool_offset[2]
                a = p[3] - g5x_offset[3] - tool_offset[3]
                b = p[4] - g5x_offset[4] - tool_offset[4]
                c = p[5] - g5x_offset[5] - tool_offset[5]
                u = p[6] - g5x_offset[6] - tool_offset[6]
                v = p[7] - g5x_offset[7] - tool_offset[7]
                w = p[8] - g5x_offset[8] - tool_offset[8]

                if rotation_xy != 0:
                        t = math.radians(-rotation_xy)
                        xr = x * math.cos(t) - y * math.sin(t)
                        yr = x * math.sin(t) + y * math.cos(t)
                        x = xr
                        y = yr

                x -= g92_offset[0]
                y -= g92_offset[1]
                z -= g92_offset[2]
                a -= g92_offset[3]
                b -= g92_offset[4]
                c -= g92_offset[5]
                u -= g92_offset[6]
                v -= g92_offset[7]
                w -= g92_offset[8]

                relp = [x, y, z, a, b, c, u, v, w]

                self.hal.x_summ_offset = 0 - g5x_offset[0] - tool_offset[0] - g92_offset[0]

                if self.mm != self.machine_units_mm:
                        p = self.convert_units(p,self.unit_convert)
                        relp = self.convert_units(relp,self.unit_convert)
                        dtg = self.convert_units(dtg,self.unit_convert)

                if self.mm:
                        fmt = "%c:% 10.3f"
                else:
                        fmt = "%c:% 9.4f"

                d = 0
                if (am & 1):
                        h = " "
                        if homed[0]: h = "*"
                        
                        if lathe:
                                set_text(self.relative[d], fmt % ('R', relp[0]))
                                set_text(self.absolute[d], h + fmt % ('R', p[0]))
                                set_text(self.distance[d], fmt % ('R', dtg[0]))
                                d += 1
                                set_text(self.relative[d], fmt % ('D', relp[0] * 2.0))
                                set_text(self.absolute[d], " " + fmt % ('D', p[0] * 2.0))
                                set_text(self.distance[d], fmt % ('D', dtg[0] * 2.0))
                        else:
                                set_text(self.relative[d], fmt % ('X', relp[0]))
                                set_text(self.absolute[d], h + fmt % ('X', p[0]))
                                set_text(self.distance[d], fmt % ('X', dtg[0]))

                        d += 1
                        
                for i in range(1, 9):
                        if am & (1<<i):
                                letter = 'XYZABCUVW'[i]
                                h = "*" if homed[coordinates.index(letter)] else " "
                                set_text(self.relative[d], fmt % (letter, relp[i]))
                                set_text(self.absolute[d], h + fmt % (letter, p[i]))
                                set_text(self.distance[d], fmt % (letter, dtg[i]))
                                d += 1

                estopped = task_state == self.emc.STATE_ESTOP
                set_active(self.estops['estop'], estopped)
                set_active(self.estops['estop_reset'], not estopped)

                on = task_state == self.emc.STATE_ON
                set_active(self.machines['on'], on)
                set_active(self.machines['off'], not on)

                ovl = stat.joint[0]['override_limits']
                set_active(self.override_limit, ovl)

                flood = stat.flood
                set_active(self.floods['on'], flood)
                set_active(self.floods['off'], not flood)

                mist = stat.mist
                set_active(self.mists['on'], mist)
                set_active(self.mists['off'], not mist)

                spin = spindle0['direction']
                set_active(self.spindles['forward'], spin == 1)
                set_active(self.spindles['off'], spin == 0)
                set_active(self.spindles['reverse'], spin == -1)

                # spindlespeed2 lives outside the status tab, so it is
                # updated unconditionally
                set_text(self.status['spindlespeed2'], "%d" % spindle0['speed'])

                if status_tab_visible:
                        set_text(self.status['file'], os.path.basename(stat.file))
                        set_text(self.status['file_lines'], "%d" % len(self.listing.program))
                        set_text(self.status['line'], "%d" % stat.current_line)
                        set_text(self.status['id'], "%d" % stat.motion_id)
                        set_text(self.status['dtg'], "%.4f" % stat.distance_to_go)
                        set_text(self.status['velocity'], "%.4f" % (stat.current_vel * 60.0))
                        set_text(self.status['delay'], "%.2f" % stat.delay_left)

                        limit = stat.limit
                        ol = ""
                        for i in range(len(limit)):
                                if limit[i]:
                                        ol += "%c " % "XYZABCUVW"[i]
                        set_text(self.status['onlimit'], ol)

                        sd = (_("CCW"), _("Stopped"), _("CW"))
                        set_text(self.status['spindledir'], sd[spin+1])

                        set_text(self.status['spindlespeed'], "%d" % spindle0['speed'])
                        set_text(self.status['loadedtool'], "%d" % stat.tool_in_spindle)
                        tool_table = stat.tool_table
                        pocket_prepped = stat.pocket_prepped
                        if pocket_prepped == -1:
                                set_text(self.status['preppedtool'], _("None"))
                        else:
                                set_text(self.status['preppedtool'], "%d" % tool_table[pocket_prepped].id)

                        tt = ""
                        for p, t in zip(list(range(len(tool_table))), tool_table):
                                if t.id != -1:
                                        tt += "<b>P%02d:</b>T%02d\t" % (p, t.id)
                                        if p == 0: tt += '\n'
                        set_text(self.status['tooltable'], tt)

                        set_text(self.status['xyrotation'], "%d" % rotation_xy)

                        cs = stat.g5x_index
                        if cs<7:
                                cslabel = "G5%d" % (cs+3)
                        else:
                                cslabel = "G59.%d" % (cs-6)

                        set_text(self.status['label_g5xoffset'], '<b>' + cslabel + '</b>' + ' Offset:')

                        g5x = ""
                        g92 = ""
                        for i in range(len(g5x_offset)):
                                letter = "XYZABCUVW"[i]
                                if g5x_offset[i] != 0: g5x += "%s%.3f " % (letter, g5x_offset[i])
                                if g92_offset[i] != 0: g92 += "%s%.3f " % (letter, g92_offset[i])

                        set_text(self.status['g5xoffset'], g5x)
                        set_text(self.status['g92offset'], g92)

                        tlo = ""
                        for i in range(len(tool_offset)):
                                letter = "XYZABCUVW"[i]
                                if tool_offset[i] != 0: tlo += "%s%.3f " % (letter, tool_offset[i])
                        set_text(self.status['tlo'], tlo)

                        active_codes = []
                        for i in stat.gcodes[1:]:
                                if i == -1: continue
                                if i % 10 == 0:
                                        active_codes.append("G%d" % (i/10))
                                else:
                                        active_codes.append("G%d.%d" % (i/10, i%10))

                        for i in stat.mcodes[1:]:
                                if i == -1: continue
                                active_codes.append("M%d" % i)

                        settings = stat.settings
                        feed_str = "F%.1f" % settings[1]
                        if feed_str.endswith(".0"): feed_str = feed_str[:-2]
                        active_codes.append(feed_str)
                        active_codes.append("S%.0f" % settings[2])

                        set_text(self.status['activecodes'], " ".join(active_codes))

                set_active(self.prefs['inch'], self.mm == 0)
                set_active(self.prefs['mm'], self.mm == 1)
                set_active(self.prefs['actual'], self.actual == 1)
                set_active(self.prefs['commanded'], self.actual == 0)

                optional_stop = stat.optional_stop
                set_active(self.opstop['on'], optional_stop)
                set_active(self.opstop['off'], not optional_stop)

                block_delete = stat.block_delete
                set_active(self.blockdel['on'], block_delete)
                set_active(self.blockdel['off'], not block_delete)

                set_text(self.spindle_values['sp_commanded'], "Set: %d" % spindle0['speed'])
                set_text(self.spindle_values['sp_current'], "Current: %d" % self.hal.spindle_velocity)
                set_text(self.spindle_values['sp_angle'], "Angle: %#06.2f" % self.hal.spindle_pos)

                motion_id = stat.motion_id
                if motion_id == 0 and (stat.interp_state == self.emc.INTERP_PAUSED or stat.exec_state == self.emc.EXEC_WAITING_FOR_DELAY):
                        self.listing.highlight_line(stat.current_line)
                elif motion_id == 0:
                        self.listing.highlight_line(stat.motion_line)
                else:
                        self.listing.highlight_line(motion_id or stat.motion_line)

                e = self.emcerror.poll()
                if e:
                        kind, text = e
                        set_text(self.error, text.replace("\n", " "))

                
