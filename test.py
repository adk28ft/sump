import pifacedigitalio 

def toggle_led0(event):
   event.chip.leds[0].toggle();
   print event;

pifacedigitalio.init()

pfd = pifacedigitalio.PiFaceDigital()

listener = pifacedigitalio.InputEventListener(chip=pfd)
listener.register(0, pifacedigitalio.IODIR_FALLING_EDGE, toggle_led0)
listener.activate()

raw_input();
print 'signal to exit'

listener.deactivate()
print 'application exit'
