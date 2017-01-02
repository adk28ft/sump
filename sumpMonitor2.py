#############################################################################
## Sump Monitor Application
#############################################################################
#  
# Comment                                    Date
# ========================================== ==================
# Initial version of the monitor application 02/27/2016
#
#############################################################################
## LED OUTPUTS
#  
#  High Sump Alarm                LED = 0
#  Sump Pump Water Outside Well   LED = 1
#  Water In Well                  LED = 2
#  Basement Water Sensor Alarm    LED = 3 
#
print 'Initialize Global Memory Start'


#
## ALARM NOTIFICATION GROUPS
#  HighSumpAlarmGrp
#  WaterInWellGrp
#  WaterDetectedGrp
#  BasementWaterDetectedGrp
#
## X10 Activation
#  
#   -- Short beep will every 4 hours indicates that sump area has water
#   -- Continous alarm will indicate an immediate flooding
#
import sys
import x10
import json
import pifacedigitalio
import time
import signal
import smtplib 

from datetime import datetime 

# Setup the email sender
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email import Encoders

########################################################################
# Configuration setup 
########################################################################

## DIGITAL INPUTS
#   
#  High Sump Alarm                
SUMP_PUMP_FLOODING = 0

#  Water In Well                  
WATER_IN_WELL = 1

#  Water Detected                 
WATER_DETECTED_OUTSIDE_WELL = 2

#  Basement Water Detected
WATER_DETECTED_IN_BASEMENT = 3

#  Program Running LED
PROGRAM_RUNNING_LED = 4

app_config = None

app_running = True

########################################################################
# memory structures to hold our changed events
########################################################################
# water in well event memory variables to track condition of the well 
# pump; bottom bobber in the sump well
waterInWellState = False    # boolean flag for this condition
cycleCounter = 0            # cycle counter; 24 hours
lastCycleOnTime = None      # last time we saw the Rising Edge 

# top bobber in the sump well
sumpPumpFloodingState = False
lastCycleOnSumpPumpFlooding = None

# water sensor outside cellar door
sumpPumpWaterOutsideWellState = False
lastCycleOnTimeOutsideWell = None

# one of 3 possible sensors could turn this on
#    - water sensor near well pump
#    - sensor in the sub floor; typically indicates a dual pump failure
#    - hot water or furnace area sensor
basementWaterSensorState = False
lastCycleOnTimeBasementWater = None

print 'Initialize memory end'

########################################################################
# send email message:
########################################################################
# Send email message to preset subject, text and target email addresses 
# 
def sendEMail(subject, text, rcpts):
    try:
       print "send email:  ", text
       print rcpts

       FROM = 'thesillimansny@gmail.com'

       TO = '';
  
       msg = MIMEText(text)
       msg['From'] =  'thesillimansny@gmail.com'
       msg['Subject'] =  subject

       mailServer = smtplib.SMTP('smtp.gmail.com', 587)
       mailServer.set_debuglevel(0)
       mailServer.ehlo_or_helo_if_needed()
       mailServer.starttls()
       mailServer.ehlo_or_helo_if_needed()
       mailServer.login(FROM, "James1:2")
       
       print 'about to send email'
       mailServer.sendmail(FROM, rcpts, msg.as_string())

       mailServer.quit()

    except:
       print "failed to send email"
       e = sys.exc_info()[0]
       print e


########################################################################
# water in well event:
########################################################################
# Event is raised when the bottom bobber has detected water is present
# in the sump well.  This event is either an indication of water 
# becoming present for the first time or the pump is actually running
# 
def water_in_well_event(event):
   global lastCycleOnTime
   global waterInWellState
   global cycleCounter
   
   waterInWellState = True
   if lastCycleOnTime is None:
   	  print 'water in well'
   	  lastCycleOnTime = datetime.now()
   	  sendAlert('WaterInWellRcpt', 'Warning; sump well has water', 'Water in well: first notification event');
   	  cycleCounter = 1
   	  return
   
   cycleCounter = cycleCounter + 1
   
   tmDur = datetime.now() - lastCycleOnTime
   totHours = tmDur.total_seconds()/3600.0
   
   # see when we last fired this event; if > 
   if totHours > 24:
     sendAlert('WaterInWellRcpt', 'Warning; sump well has water', 'Water in well: pump continues to cycle: ' + str(cycleCounter));
   
   # set last cycle time to now
   lastCycleOnTime = datetime.now()

   print 'cycle counter = ', cycleCounter


########################################################################
# sump pump flooding event:
########################################################################
# This generally means the sensor that sits outside of the basement
# door has detected water.  If this happens
#
def sump_pump_flooding_event(event):
   global lastCycleOnSumpPumpFlooding
   global sumpPumpFloodingState
   
   print 'sump pump is flooding - critical alarm send email'
   sumpPumpFloodingState = True
   
   if lastCycleOnSumpPumpFlooding is None:
   	 x10.send_cmd('pl a1 on')
   	 sendAlert('SumpPumpFlooding', 'Sump high and flooding', 'Sump or hose failure in well pump')
   	 lastCycleOnSumpPumpFlooding = datetime.now()
   	 return

   tmDur = datetime.now() - lastCycleOnSumpPumpFlooding
   totMinutes = tmDur.total_seconds()/60.0
   if totMinutes >= 5.0:
     x10.send_cmd('pl a1 on')
     lastCycleOnSumpPumpFlooding = datetime.now()
     sendAlert('SumpPumpFlooding', 'Sump high and flooding', 'Sump or hose failture continues in well pump')
     return


########################################################################
# sump pump water outside well event:
########################################################################
# This generally means the sensor outside of the basement door has 
# detected water present.  
def sump_pump_water_outside_well_event(event):
   global sumpPumpWaterOutsideWellState
   global lastCycleOnTimeOutsideWell
   
   print 'sump pump water outside well';
   sumpPumpWaterOutsideWellState = True
   if lastCycleOnTimeOutsideWell is None:
      lastCycleOnTimeOutsideWell = datetime.now()
      x10.send_cmd('pl a1 on')
      sendAlert('OutsideWell', 'Flooding outside of sump well', 'Water detected outside of sump well or near walkout door (1st alert)')
      return

   tmDur = datetime.now() - lastCycleOnTimeOutsideWell
   totMinutes = tmDur.total_seconds()/60.0
   if totMinutes >= 5.0:
     lastCycleOnTimeOutsideWell = datetime.now()
     x10.send_cmd('pl a1 on')
     sendAlert('OutsideWell', 'Flooding outside of sump well', 'Water detected outside of sump well or near walkout door (n)')
    
       
########################################################################
# basement water detected:
# A sensor near the furnace/hot water heater, well pump area or 
# under the cement slab in the basement (high water alert) may indicate
# a pipe, valve leak, failed sump detection 
########################################################################
# This generally means the sensor outside of the basement door has 
# detected water present.  
def basement_water_sensor_event(event):
   global basementWaterSensorState
   global lastCycleOnTimeBasementWater
   
   print 'basement water sensor state';
   basementWaterSensorState = True
   if lastCycleOnTimeBasementWater is None:
      lastCycleOnTimeBasementWater = datetime.now()
      sendAlert('BasementWaterSensor', 'Basement Flood Sensor', 'Basement water sensor (Furnace, Well or Floor Drain is detected) (1st alert)')
      x10.send_cmd('pl a1 on')
      return

   tmDur = datetime.now() - lastCycleOnTimeBasementWater
   totMinutes = tmDur.total_seconds()/60.0
   if totMinutes >= 5.0:
     lastCycleOnTimeBasementWater = datetime.now()
     sendAlert('BasementWaterSensor', 'Basement Flood Sensor', 'Basement water sensor (Furnace, Well or Floor Drain is detected) (n)')
     x10.send_cmd('pl a1 on')
   	  

########################################################################
# water in well event off:
########################################################################
#
def water_in_well_event_off(event):
   global waterInWellState
   print 'OFF water in well: waterInWellState = False'
   waterInWellState = False
   
   
########################################################################
# sump pump flooding event off:
########################################################################
#
def sump_pump_flooding_event_off(event):
   global sumpPumpFloodingState
   print 'OFF sump pump is flooding: sumpPumpFloodingState = False'
   sumpPumpFloodingState = False
   x10.send_cmd('pl a1 off')
   	  
   	  
########################################################################
# sump pump water outside well event off:
########################################################################
#
def sump_pump_water_outside_well_event_off(event):
   global sumpPumpWaterOutsideWellState
   print 'OFF sump pump water outside well: sumpPumpWaterOutsideWellState = False';
   sumpPumpWaterOutsideWellState = False
   x10.send_cmd('pl a1 off')


########################################################################
# sump pump water sensor event off:
########################################################################
#
def basement_water_sensor_event_off(event):
   global basementWaterSensorState
   print 'OFF basement water sensor event: basementWaterSensorState = False'
   basementWaterSensorState = False
   x10.send_cmd('pl a1 off')


########################################################################
# Send email notification to email address/phones:
########################################################################
#
def sendAlert(msgtype, subj, msg):
   global app_config

   # read configuration file in case there are any changes
   read_config()

   # check to see if there are any emails for this message type
   if msgtype not in app_config.keys():
      print msgtype, ' has no email configuration'
      return
   
   # setup the members 
   rcpts = app_config[msgtype]
   
   # convert the string list of emails to a string array
   rcptsArr = rcpts.replace(' ','').split(',')
   
   # send notification to the email   
   sendEMail( subj, msg, rcptsArr )
   

########################################################################
# Save current state to json file
########################################################################
#
def save_state():
   rec_data = dict( {
      'waterInWellState': waterInWellState,
      'sumpPumpFloodingState': sumpPumpFloodingState,
      'sumpPumpWaterOutsideWellState': sumpPumpWaterOutsideWellState,
      'basementWaterSensorState': basementWaterSensorState
   } )
   
   # save to currentState.json file
   out_file = open('currentState.json', 'w')

   # dump the data to the output file
   json.dump(rec_data, out_file, indent=4)

   # close the file
   out_file.close()


########################################################################
# Read configuration file
########################################################################
#
def read_config():
   global app_config
   
   try:
      # read the configuration file
      with open('config.json') as json_file:
         app_config = json.load(json_file)

   except:
     e = sys.exc_info()[0]
     print e  
   

########################################################################
# SIGINT handler 
########################################################################
#
def signal_handler(signal, frame):
    global app_running
    global app_config 
    
    app_running = False
    print app_config
        
        
########################################################################
# Main Loop and Entry for Application:
########################################################################
def main():
   global app_running

   # read configuration file
   read_config()

   app_running = True
   
   # create the PI face digital interface
   pfd = pifacedigitalio.PiFaceDigital()

   # setup the LED displays
   sumpPumpFloodingLED = pfd.leds[SUMP_PUMP_FLOODING]
   waterInWellLED = pfd.leds[WATER_IN_WELL]
   waterDetectedOutsideWellLED = pfd.leds[WATER_DETECTED_OUTSIDE_WELL]
   waterDetectedInBasementLED = pfd.leds[WATER_DETECTED_IN_BASEMENT]
   progRunLED = pfd.leds[PROGRAM_RUNNING_LED]

   print 'Display LED startup'

   sumpPumpFloodingLED.turn_on()
   time.sleep(1)
   waterInWellLED.turn_on()
   time.sleep(1)
   waterDetectedOutsideWellLED.turn_on()
   time.sleep(1)
   waterDetectedInBasementLED.turn_on()
   time.sleep(1)
   
   progRunLED.turn_on()
   sumpPumpFloodingLED.turn_off()
   waterInWellLED.turn_off()
   waterDetectedOutsideWellLED.turn_off()
   waterDetectedInBasementLED.turn_off()

   print 'Startup LED complete'
   
   # get the starting date
   tmStart = datetime.now()

   # initialize the state variables based on the current condition of the input card
   listener = pifacedigitalio.InputEventListener(pfd)
   listener.register(WATER_IN_WELL, pifacedigitalio.IODIR_FALLING_EDGE, water_in_well_event)
   listener.register(WATER_IN_WELL, pifacedigitalio.IODIR_RISING_EDGE, water_in_well_event_off)
   listener.register(SUMP_PUMP_FLOODING, pifacedigitalio.IODIR_FALLING_EDGE, sump_pump_flooding_event)
   listener.register(SUMP_PUMP_FLOODING, pifacedigitalio.IODIR_RISING_EDGE, sump_pump_flooding_event_off)
   listener.register(WATER_DETECTED_OUTSIDE_WELL, pifacedigitalio.IODIR_FALLING_EDGE, sump_pump_water_outside_well_event)
   listener.register(WATER_DETECTED_OUTSIDE_WELL, pifacedigitalio.IODIR_RISING_EDGE, sump_pump_water_outside_well_event_off)
   listener.register(WATER_DETECTED_IN_BASEMENT, pifacedigitalio.IODIR_FALLING_EDGE, basement_water_sensor_event)
   listener.register(WATER_DETECTED_IN_BASEMENT, pifacedigitalio.IODIR_RISING_EDGE, basement_water_sensor_event_off)

   # active the listener to look for rising and falling edges for our
   # four input sensors
   listener.activate()

   # read the existing state of the alarms
   # bottom bobber 
   waterInWellState = pfd.input_pins[WATER_IN_WELL]
   if waterInWellState == True:
      waterInWellLED = true;
      
   # top bobber
   sumpPumpFloodingState = pfd.input_pins[SUMP_PUMP_FLOODING]
   if sumpPumpFloodingState == True:
      sumpPumpFloodingLED.turn_on()
      
   # water alarm outside the door
   ioWaterDetected = pfd.input_pins[WATER_DETECTED_OUTSIDE_WELL]
   if ioWaterDetected == True:
      waterDetectedOutsideWellLED.turn_on()
      
   # general basement water alarm
   ioBasementWaterDetected = pfd.input_pins[WATER_DETECTED_IN_BASEMENT]
   if ioBasementWaterDetected == True:
      waterDetectedInBasementLED.turn_on()

   signal.signal(signal.SIGINT, signal_handler)
   print 'press ctrl-c to terminate'
   
   while app_running:
      save_state()   
      progRunLED.toggle()
      time.sleep(1)
      
   print('ctrl-c detected...set app-running to false')
   app_running = False

   print 'terminate listener'
   listener.deactivate()

   print 'app shutdown'


# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()
    
