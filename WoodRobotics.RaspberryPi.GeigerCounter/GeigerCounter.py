from PiPocketGeiger import RadiationWatch
from datetime import datetime
import subprocess
import time
import RPi.GPIO as GPIO
import random
import thread
import SevenSegment

if __name__ == "__main__":

    # Hello, my name is
    print "WoodRobotics Pi Pocket Geiger and Logger"

    # setup the LED display
    display = SevenSegment.SevenSegment()
    display.begin()

    # Verify the display is working
    # by displaying a deceptive message
    display.clear()
    display.print_number_str('dead')
    display.write_display()

    # Initialize the Globals variables
    DetectedRadiation = False
    DisplayCPM = False
    LastSwitch = 0
    LastNoise = 0

    # uSv/h warning level
    RadiationWarningLevel = 10

    # setup the piezo buzzer GPIO pin
    GPIO.setmode(GPIO.BCM) # Broadcom pin-numbering scheme
    GPIO.setwarnings(False)
    GPIO.setup(25, GPIO.OUT)
    GPIO.output(25, GPIO.LOW)

    # This is out of habit
    # am I making you wait for quiescent or just because?
    time.sleep(5)

    # gets the current time in milliseconds
    def millis():
        return int(round(time.time() * 1000))

    # Call back on detected radiation from the Pocket Geiger
    # I found that if I added my sound and display coder here
    # It would affect the accuracy of the Pocket Geiger
    # I may just be crazy but this method works
    # Simply set a flag when we have detected radiation
    def onRadiation():
        
        global DetectedRadiation
        DetectedRadiation = True

    # Call back on detected noise from the Pocket Geiger
    # Noise/Vibration on the Pocket Geiger gives false Radiation readings
    # The device driver supplied by Radiation-Watch.com takes this into account
    # But it still raises the Radiation Detected event
    # I counter act this by monitoring the noise 
    # and stopping reactions to radiation detected
    def onNoise():

        global DetectedRadiation, DisplayCPM, LastNoise, LastSwitch

        # Clear our flag notifying we detected radiation
        DetectedRadiation = False

        # Calculate the time we last heard some noise
        TimeBetweenNoise = millis() - LastNoise
        TimeBetweenSwitch = millis() - LastSwitch

        # I wanted to keep the number of components down to a minimum
        # I also want to be able to switch between CPM and uSv/h
        # This little hack uses the noise from the device as a type of button
        # if you tap on the device twice in under a second 
        # with a 250 ms pause after the first tap,
        # and more than a second after the last switch,
        # it will switch the flag stating what unit is displayed
        if TimeBetweenNoise > 250 and TimeBetweenNoise < 1000 and TimeBetweenSwitch > 1000:

            # log our last switch time
            LastSwitch = millis()

            # switch back and forth between displayed units
            DisplayCPM = not DisplayCPM
        
        # Store the current time
        LastNoise = millis()

    # Simulate the infamous geiger click
    # Pulse the piezo buzzer for a short period
    def PlayClick():
        GPIO.output(25, GPIO.HIGH)
        time.sleep(.0017)
        GPIO.output(25, GPIO.LOW)

    # Pulse the piezo buzzer in an irritating fashion
    def PlayWarning():
        for i in range(2):
            GPIO.output(25, GPIO.HIGH)
            time.sleep(.5)
            GPIO.output(25, GPIO.LOW)
            time.sleep(.5)

    # I like seeing the time when messages come through
    # Appends your message to the current formatted date and time
    def Print(message):
        print datetime.now().strftime('%a, %d %b %Y %H:%M:%S.%f') + '     ' + message

    # Here we are, in the meat of it
    # Create and use our Pocket Geiger
    with RadiationWatch(24, 23) as radiationWatch:

        # Initialize our noise variables
        LastNoise = millis()
        LastSwitch = millis()
        LastLog = millis()

        # register our Noise and Radiation Detection call backs
        radiationWatch.registerRadiationCallback(onRadiation)
        radiationWatch.registerNoiseCallback(onNoise)

        # loop until something terrible happens
        while True:
            
            # get the current radiation values
            radiation = radiationWatch.status()

            # print the current radiation values
            Print('uSv/h: ' + str(radiation['uSvh']) + '  \tCPM: ' + str(radiation['cpm']) + '\tErr: ' + str(radiation['uSvhError']))

            # clear the display and turn the colon off
            display.clear()
            display.set_colon(False)
            
            # if the radiation levels are below our warning threshold
            # and radiation has been detected
            if radiation['uSvh'] < RadiationWarningLevel and DetectedRadiation == True:

                # reset the global radiation flag
                DetectedRadiation = False
                
                # Make sure there hasn't been nose in the last second
                # that would indicates false readings
                # and we don't want to notify/display them
                if millis() - LastNoise > 1000:
                    # Play our Geiger click and set the colon on
                    PlayClick()
                    display.set_colon(True)

            # The radiation levels are above or equal to our warning threshold
            # play our warning tone
            elif radiation['uSvh'] >= RadiationWarningLevel:
                PlayWarning()

            # Pick between which unit is selected
            # then select the appropriate decimal point placement
            # and print it to the LED display
            if DisplayCPM == True:
                if radiation['cpm'] >= 1000:
                    display.print_float(round(radiation['cpm'], 0), 0)
                elif radiation['cpm'] >= 100:
                    display.print_float(round(radiation['cpm'], 1), 1)
                else:
                    display.print_float(round(radiation['cpm'], 2), 2)
            else:
                if radiation['uSvh'] >= 1000:
                    display.print_float(round(radiation['uSvh'], 0), 0)
                elif radiation['uSvh'] >= 100:
                    display.print_float(round(radiation['uSvh'], 1), 1)
                elif radiation['uSvh'] >= 10:
                    display.print_float(round(radiation['uSvh'], 2), 2)
                else:
                    display.print_float(radiation['uSvh'], 3)
            
            # Write everything to the LED display
            display.write_display()

            #sleep for 1 second or until Radiation is detected
            waitTime = 0
            while DetectedRadiation == False and waitTime < 1000:
                waitTime += 1
                time.sleep(0.001)
            
            # turn off the colon and write it to the display
            # I do this to make it look cooler. Did it work?
            display.set_colon(False)
            display.write_display()

            # if its been a minute sense the last log time
            # append the current radiation values to our log
            if millis() - LastLog >= 60000:

                # Store the current log time
                LastLog = millis()

                # Open our log file for append and create it if it doesn't exist
                with open("/home/pi/share/geiger.log","a+") as f:
                    f.write(datetime.now().strftime('%a, %d %b %Y %H:%M:%S') + "," + str(radiation['uSvh']) + "," + str(radiation['cpm']) + "," + str(radiation['uSvhError']) + '\r\n')
