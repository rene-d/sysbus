#! /usr/bin/env python3
"""
Emulate an oscilloscope.  Requires the animation API introduced in
matplotlib 1.0 SVN.
"""

import sysbus

sysbus.auth()





import matplotlib
matplotlib.use('TKAgg')

from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import matplotlib.animation as animation

class Scope(object):
    def __init__(self, ax, maxt=30, dt=5):
        self.ax = ax
        self.dt = dt
        self.maxt = maxt
        self.tdata = [0]
        self.ydata = [0]
        self.line = Line2D(self.tdata, self.ydata)
        self.ax.add_line(self.line)
        self.ax.set_ylim(0, 1000)
        self.ax.set_xlim(0, self.maxt)

        self.M = 10

    def update(self, y):

        m = max(self.ydata)
        M = self.M
        while m > M:
            m /= 10
            M *= 10
        if self.M != M:
            self.ax.set_ylim(0, M)
            self.M = M
            self.ax.figure.canvas.draw()
            print("update", M)
        
        lastt = self.tdata[-1]
        if lastt > self.tdata[0] + self.maxt:  # reset the arrays
            self.tdata = [self.tdata[-1]]
            self.ydata = [self.ydata[-1]]
            self.ax.set_xlim(self.tdata[0], self.tdata[0] + self.maxt)
            self.ax.figure.canvas.draw()

        t = self.tdata[-1] + self.dt
        self.tdata.append(t)
        self.ydata.append(y[0])
        self.line.set_data(self.tdata, self.ydata)
        return self.line,


def emitter():
    tx = 0
    rx = 0
    while True:
        r = sysbus.requete('sysbus.NMC.Wifi:getStats')
        r = r['data']
        v = int(r['RxBytes'])
        if rx == 0: rx = v
        vv = (v - rx) / 1024.
        rx = v
        print(vv)
        yield vv,


fig, ax = plt.subplots()
scope = Scope(ax)

# pass a generator in "emitter" to produce data for the update func
ani = animation.FuncAnimation(fig, scope.update, emitter, interval=1000, blit=True)


plt.show()
