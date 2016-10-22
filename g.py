# Simple example of using general timer objects. This is used to update
# the time placed in the title of the figure.
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import sys

def update_title(axes):
    axes.set_title(datetime.now())
    axes.figure.canvas.draw()

fig, ax = plt.subplots()

x = np.linspace(0, 10, 11)
print(x, x*x)
sys.exit()
ax.plot(x, x*x)

# Create a new timer object. Set the interval to 100 milliseconds
# (1000 is default) and tell the timer what function should be called.
timer = fig.canvas.new_timer(interval=100)
timer.add_callback(update_title, ax)
timer.start()

# Or could start the timer on first figure draw
#def start_timer(evt):
#    timer.start()
#    fig.canvas.mpl_disconnect(drawid)
#drawid = fig.canvas.mpl_connect('draw_event', start_timer)

def SinwaveformGenerator(arg):
  global values,T1,Konstant,T0
  #ohmegaCos=arccos(T1)/Ta
  #print "fcos=", ohmegaCos/(2*pi), "Hz"

  Tnext=((Konstant*T1)*2)-T0
  if len(values)%100>70:
          values.append(random()*2-1)
  else:
          values.append(Tnext)
  T0=T1
  T1=Tnext


timer = fig.canvas.new_timer(interval=20)
timer.add_callback(SinwaveformGenerator, ())
timer.start()

plt.show()