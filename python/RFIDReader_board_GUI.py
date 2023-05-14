# ______________________________CONTENTS
# 1. LIBRARY IMPORTS
# 2. TKINTER GUI   	DEFINITIONS
# 3. GUI BUTTON		FUNCTIONS
# 4. HELPER			FUNCTIONS
# 5. TKINTER GUI   	BUTTONS
# 6. TKINTER GUI   	LAYOUT
# 7. READERMODE    	MENU CONFIGURATION
# 8. POLLING DELAY 	MENU CONFIGURATION
# 9. MAIN LOOP

# To turn on all console messages for debugging, find & replace all "# print" with "print".

#1._____________________________GPIO/WIRINGPI imports & setup
import wiringpi as wiringpi2
import time
import sys
import argparse
import numbers
from tkinter import *
from tkinter.ttk import *
from tkinter import messagebox
from tkinter import simpledialog
from turtle import width
from curses import window

CTS_PIN = 1 # setup for GPIO Pin to use based on the jumper connection

# SINGLE ANTENNA MODE -- configure for your Pi
# GPIO_PIN = 0 # Jumper 2, also known as (BCM) GPIO17
GPIO_PIN = 1 # Jumper 1, also known as (BCM) GPIO18
# GPIO_PIN = 2 # Jumper 3, also known as (BCM) GPIO21 (Rv 1) or (BCM) GPIO27 (Rv 2)
# GPIO_PIN = 3 # Jumper 4, also known as (BCM) GPIO22

# MULTI-ANTENNA MODE -- configure for your Pi
GPIO_PIN_A = 5 
GPIO_PIN_B = 5


#2._______________________________GUI DEFINITIONS

window = Tk()
window.configure(bg='black')
window.title("CognIot 125kHz RFID Reader")
window.resizable(width=0, height=0) # force-prevent resizing

# BUTTON STYLING
style  = Style()
style.configure('TButton', font = ('arial', 12), foreground = '#009900', width='30', wrap=WORD) # 'TButton' applies the style to _all_ buttons in the GUI


#3_______________________________GUI BUTTON FUNCTIONS

def ReadVersion(fd):	# Read the RFID BOARD version information
    WaitForCTS()
    # print ("ReadVersion: Sending Read Version Command")     #Added for Debug purposes
    wiringpi2.serialPuts(fd,"z")
    time.sleep(0.05)
    ans = ReadText(fd)
    textBox.delete('1.0', END)	# TKINTER SYNTAX: variableAlias.methodname("lineNum.columnNum", variable/command)
    textBox.insert('1.0', ans)


def AcknowledgeTagPresence(fd):
    messagebox.showinfo(title='ATTENTION', message='Place tag to receiver and then press OK')
    textBox.delete('1.0', END) # clears textBox
    timeout = 7
    start_time = time.time()
    
    notag = True     # read the RFID reader until a tag is present
    while notag:
        
        if (time.time() - start_time) > timeout:
            messagebox.showinfo(title='TIMEOUT', message='TIMEOUT: Unable to see tag.')
            return
        
        WaitForCTS()
        # print ("AcknowledgeTagPresence: Sending Tag Status Command")   #Added for Debug purposes
        wiringpi2.serialPuts(fd,"S")
        time.sleep(0.1)
        ans = ReadInt(fd)
        # print ("AcknowledgeTagPresence: Tag Status: %s" % hex(ans))    # Added for Debug purposes
        if ans == int("0xD6", 16):	 # D6 is a positive response meaning tag present and read
            notag = False
            textBox.insert('1.0', 'tag status: ' + hex(ans) + '\nTag present and read.')
    return


def SetPollingDelay(fd, input):
    WaitForCTS()
    wiringpi2.serialPutchar(fd, 0x50)
    wiringpi2.serialPutchar(fd, 0x00)
    
    if input == "NO DELAY":
            wiringpi2.serialPutchar(fd, 0x00) # 0x00 is no delay
    elif input == "20ms":
        wiringpi2.serialPutchar(fd, 0x20) # 0x20 is approx 20ms
    elif input == "65ms":
        wiringpi2.serialPutchar(fd, 0x40) # 0x40 is approx 65ms
    elif input == "262ms":
        wiringpi2.serialPutchar(fd, 0x60) # 0x60 is approx 262ms
    elif input == "1s":
        wiringpi2.serialPutchar(fd, 0x80) # 0x80 is approx 1 Seconds
    elif input == "4s":
        wiringpi2.serialPutchar(fd, 0xA0) # 0xA0 is approx 4 Seconds

    time.sleep(0.1)
    textBox.delete('1.0', END)
    ans = ReadInt(fd)
    if ans == int("0xC0", 16): # C0 is a positive result
        textBox.insert('1.0', 'Polling delay changed.')
    else:
        errmsg = 'Unexpected response: %s \nPolling delay could not be changed.' % hex(ans)
        messagebox.showinfo(title="ERROR", message=errmsg)
        textBox.insert('1.0', errmsg)
        wiringpi2.serialFlush(fd) # flush any remaining characters from the buffer
    return


def SetReaderMode(fd, choice):
    if choice == "Hitag H2":
        WaitForCTS()
        wiringpi2.serialPutchar(fd, 0x76)
        wiringpi2.serialPutchar(fd, 0x01) # 0x01 = H2
    elif choice =="Hitag H1/S":
        WaitForCTS()
        wiringpi2.serialPutchar(fd, 0x76)
        wiringpi2.serialPutchar(fd, 0x02) # 0x02 = H1/S
    elif choice == "EM/MC2000":
        WaitForCTS()
        wiringpi2.serialPutchar(fd, 0x76)
        wiringpi2.serialPutchar(fd, 0x03) # 0x03 = EM/MC2000
    else:
        # print ("SetReaderMode: ERROR\nUnable to Set Reader Mode")
        choice = ""
        return

    time.sleep(0.1)
    textBox.delete('1.0', END)
    ans = ReadInt(fd)
    # print ("SetReaderMode: Tag Status: %s" % hex(ans)) #Added for Debug purposes
    if ans == int("0xC0", 16):
        textBox.insert('1.0', "Reader Operating Mode: %s ......" % choice)
        # print ("SetReaderMode: Reader Operating Mode %s ......" % choice)
    else:
        textBox.insert('1.0', "Unexpected response %s" % hex(ans))
        wiringpi2.serialFlush(fd)
    return


def ReadPage(fd, page=None):
    # This performs a one-page only read that catches serial line bugs and reports them back.
    # ReadPageWithTimeout() is provided to cycle through multiple pagereads in the event that stubborn errors pop up too often.

    if (antennaSetupCheck(antennaSetup, "single")) == "fail":
        return

    if page == None:	# If calling a single page and not ReadAllPages()
        textBox.delete('1.0', END)
        textBox.insert('1.0', 'To read Tag Data Page, place tag on receiver...\n')
        
        page = simpledialog.askstring(title="INPUT INFORMATION", prompt="Page Numbers start at 0.\nRead what page number?")
        if page.isnumeric() == False:
            messagebox.showinfo(title='ATTENTION', message='You must input a number. Cancelled.')
            return
        if int(page) < 0:
            messagebox.showinfo(title='ATTENTION', message='Number must be greater than 0. Cancelled.')
            return

    notag = True
    while notag:
        WaitForCTS()
        pageInt = int(page)
                
        # print ("ReadPage: Sending Tag Read Page Command")    #Added for Debug purposes
        WaitForCTS()
        wiringpi2.serialPutchar(fd, 0x52)
        wiringpi2.serialPutchar(fd, pageInt)
        time.sleep(0.05)
        
        ans = ReadInt(fd)
        time.sleep(0.05)
        # print ("ReadPage: Tag Status: %s" % hex(ans))    #Added for Debug purposes
        if ans == int("0xD6", 16):
            # print("ReadPage: Tag Present and Read") #Added for Debug purposes
            notag = False
            ans = ReadText(fd)
            printText(ans, page, "page")
            # interrupt the loop thread in multi-read functions to show results in real time
            window.update()		# Do not refactor into printText; brings up errors.
        elif ans == int("0xD2", 16):	# "0xD2" means the Tag Page doesn't exist
            errmsg = 'Error Code: 0xD2\nPage %s does not exist.' % page
            messagebox.showinfo(title='ATTENTION', message=errmsg)
            return ans
        else:	# 0xC0 is a failure code
            failmsg = 'Failed to read data from the serial line. Please try again.\nError Code: %s' % hex(ans)
            messagebox.showinfo(title='ERROR', message=failmsg)
            wiringpi2.serialFlush(fd)
            return
    return


def ReadPageWithTimeout(fd, page=None):
    timeout = 1
    start_time = time.time()
    
    if page == None:
        page = 0

    notag = True
    # print ("\nReadPageWithTimeout: Reading Tag Data Page %d......." % page)
    # print ("\nReadPageWithTimeout: Waiting for a tag ....")
    while notag:
        WaitForCTS()
        # print ("ReadPageWithTimeout: Sending Tag Read Page Command")    #Added for Debug purposes
        wiringpi2.serialPutchar(fd, 0x52)
        wiringpi2.serialPutchar(fd, page)
        time.sleep(0.05)
        ans = ReadInt(fd)
        # print ("ReadPageWithTimeout: Tag Status: %s" % hex(ans))    #Added for Debug purposes
        if (time.time() - start_time) > timeout:
            # print("ReadPageWithTimeout: timeout\n\n")
            return "timeout"
        if ans != int("0xD6", 16):
            # print ("ReadPageWithTimeout: Tag Status: %s" % hex(ans))    #Added for Debug purposes
            wiringpi2.serialFlush(fd)
            continue    
        else:
            notag = False	# Tag present and read
            ans = ReadText(fd)
            printText(ans, page, "page")
            window.update()
            return "0xD6"
        


def ReadBlock(fd, block=None):    # read the tag and all blocks from within it
  
    mode = readerModeVariable.get()
    if mode != "Hitag H1/S":
        messagebox.showinfo(title='ATTENTION', message='This functionality only supports Hitag H1/S tags.')
        return
    if (antennaSetupCheck(antennaSetup, "single")) == "fail":
        return
    
    if block == None:
        textBox.delete('1.0', END)
        textBox.insert('1.0', 'To read Tag Data Block, please place tag on receiver...\n')
        
        block = simpledialog.askstring(title="INPUT", prompt="Place the tag to the receiver and input a block to read", initialvalue='Enter number >0 and <255')
        if block.isnumeric() == False:
            messagebox.showinfo(title='ATTENTION', message='You must input a number. Cancelled.')
            return
        if int(block) > 255 or int(block) < 0:
            messagebox.showinfo(title='ATTENTION', message='Number must be between 0 and 255. Cancelled.')
            return
    
    notag = True
    while notag:
        WaitForCTS()
        # print ("ReadBlock: Sending Tag Read Blocks command")  #Added for Debug purposes
        wiringpi2.serialPutchar(fd, 0x72)
        wiringpi2.serialPutchar(fd, int(block))
        time.sleep(0.1)
        
        ans = ReadInt(fd)
        # print ("ReadBlock: Tag Status: %s" % hex(ans))    #Added for Debug purposes
        if ans == int("0xD6", 16):  # Tag present and read
            notag = False
            textBox.delete('1.0', END)
            ans = ReadText(fd)
            printText(ans, block, "block")
            window.update()
        elif ans == int("0xD2", 16):
            # Tag page doesn't exist -- return ans to break out of the ReadAllPages() calling loop.
            errmsg = 'Block %s does not exist.' % block
            messagebox.showinfo(title='ATTENTION', message=errmsg)
            return ans
        else:	# ans == int("0xC0", 16):
            messagebox.showinfo(title='ERROR', message='Failed to read data from the serial line. Please try again.')
            wiringpi2.serialFlush(fd)
            return            
    return


def WritePage(fd):		# write to the tag page, user selecting the page

    mode = readerModeVariable.get()
    if mode == "EM/MC2000":
        messagebox.showinfo(title='ATTENTION', message='This functionality does not support EM/MC2000 tags.')
        return
    if (antennaSetupCheck(antennaSetup, "single")) == "fail":
        return
    
    data = []
    pagesize = 4

    page = simpledialog.askstring(title="INPUT", prompt="Place the tag to the receiver and enter the number\n of the page to which you wish to write", initialvalue='Enter number >0 and <255')
    if page.isnumeric() == False:
        messagebox.showinfo(title='ATTENTION', message='You must input a number. Cancelled.')
        return
    if int(page) > 255 or int(page) < 0:
        messagebox.showinfo(title='ATTENTION', message='Number must be between 0 and 255. Cancelled.')
        return
    
    data = CaptureDataToWrite(pagesize)
    # print("WritePage: Data to write:%s" % block)         #Added for Debug purposes
    notag = True
    while notag:
        WaitForCTS()
        # print ("WritePage: Sending Tag Write Page Command")    #Added for Debug purposes
        wiringpi2.serialPutchar(fd, 0x57)
        wiringpi2.serialPutchar(fd, int(page))           # Write to page ____
        wiringpi2.serialPutchar(fd, data[0])
        wiringpi2.serialPutchar(fd, data[1])
        wiringpi2.serialPutchar(fd, data[2])
        wiringpi2.serialPutchar(fd, data[3])
        time.sleep(0.1)
        
        ans = ReadInt(fd)
        time.sleep(0.1)
        # print ("WritePage: Tag Status: %s" % hex(ans))    #Added for Debug purposes
        
        if ans == int("0xD6", 16):
            notag = False
            # print ("WritePage: Tag Present") #Added for Debug purposes
            textBox.delete('1.0', END)
            textBox.insert('1.0', "Successfully wrote to tag:")
            ReadPage(fd, page)
    return


def WriteBlock(fd):	 # write to the tag and all blocks from within it
        
    mode = readerModeVariable.get()
    if mode != "Hitag H1/S":
        messagebox.showinfo(title='ATTENTION', message='This functionality only supports Hitag H1/S tags.')
        return
    if (antennaSetupCheck(antennaSetup, "single")) == "fail":
        return
    
    data = []
    blockno = 0
    blocksize = 16

    blockno = simpledialog.askstring(title="INPUT", prompt="Place the tag to the receiver and enter the number\n of the Block to which you wish to write", initialvalue='Enter number >0 and <255')
    if blockno.isnumeric() == False:
        messagebox.showinfo(title='ATTENTION', message='You must input a number. Cancelled.')
        return
    if int(blockno) > 255 or int(blockno) < 0:
        messagebox.showinfo(title='ATTENTION', message='Number must be between 0 and 255. Cancelled.')
        return
    
    data = CaptureDataToWrite(blocksize)
    # print("\nWriteBlock: Writing Tag Data Block %d ......." % int(blockno))
    # print("\nWriteBlock: Data to write:%s" % block)         #Added for Debug purposes

    notag = True
    while notag:
        WaitForCTS()
        # print("WriteBlock: Sending Tag Write Blocks command and data")  #Added for Debug purposes
        wiringpi2.serialPutchar(fd, 0x72)
        wiringpi2.serialPutchar(fd, int(blockno)) # Write to block ____
        for f in data:
            wiringpi2.serialPutchar(fd, f)
            time.sleep(0.1)
        time.sleep(0.1)
        ans = ReadInt(fd)
        # print ("WriteBlock: Tag block Status: %s" % hex(ans))    #Added for Debug purposes
        if ans == int("0xD6", 16):	# Tag present and read
            notag = False
            #print ("WriteBlock: Tag Present and Read")  #Added for Debug purposes
            textBox.delete('1.0', END)
            textBox.insert('1.0', "Successfully wrote to tag:")
            ReadBlock(fd, blockno)
    return


def ReadAllPages(fd):    # Cycle through and read all pages available
    
    if (antennaSetupCheck(antennaSetup, "single")) == "fail":
        return

    messagebox.showinfo(title='ATTENTION', message='Reading all Pages.\nThis may take up to a minute.')
    textBox.delete('1.0', END)
    
    for f in range (0, 0x3f):
        ans = ReadPageWithTimeout(fd, f)
        # print("\nReadAllPages: Reading Page:" + str(f) + "\nResult: " + str(ans))
        if ans == "0xD2":
            messagebox.showinfo(title='SUCCESS', message='Successfully read all Pages on this tag.')
            break
        if ans != "0xD6":
            textBox.insert(END, "\nPage " + str(f) + "\nTimeout\nUnable to read this page.\n")
            window.update()
    
    return


def ReadAllBlocks(fd):
    messagebox.showinfo(title='ATTENTION', message='Reading all Blocks.\nThis may take several seconds.')
    textBox.delete('1.0', END)
    
    for f in range (0, 16):
        ans = ReadBlock(fd, f)
        time.sleep(0.01)
        if ans == int("0xD2", 16):
            messagebox.showinfo(title='ATTENTION', message='Successfully read all Blocks on this tag.')
            break
    return
        

def BeginMultiAntennaRead(comms):
    
    if (antennaSetupCheck(antennaSetup, "multi")) == "fail":
        return
    
    while True:
        # print("\n\nAntenna A on")
        textBox.insert(END, "Antenna A on\n")
        wiringpi2.digitalWrite(GPIO_PIN_A, 1)
        wiringpi2.digitalWrite(GPIO_PIN_B, 0)
        antA = ReadPageWithTimeout(comms)
        window.update()
        
        # print("\n\nAntenna B on")
        textBox.insert(END, "Antenna B on\n")
        wiringpi2.digitalWrite(GPIO_PIN_A, 0)
        wiringpi2.digitalWrite(GPIO_PIN_B, 1)
        antB = ReadPageWithTimeout(comms)
        time.sleep(0.01)
        window.update()

        wiringpi2.digitalWrite(GPIO_PIN_A, 0) # Both antennae must Not be simultaneously powered HI
        wiringpi2.digitalWrite(GPIO_PIN_B, 0)

#         if antA == "0xD6" and antB == "0xD6":
#             # print("BeginMultiAntennaRead: both tags successfully read simultaneously")
#             textBox.insert(END, "\nBoth tags successfully read simultaneously. Exiting.\n")
#             break


def FactoryReset(fd, settingUp = None):
    WaitForCTS()
    # print ("FactoryReset: Performing a factory reset ....") #Added for Debug purposes
    wiringpi2.serialPutchar(fd, 0x46)
    wiringpi2.serialPutchar(fd, 0x55)
    wiringpi2.serialPutchar(fd, 0xAA)
    time.sleep(0.1)
    # Reset Reading Mode & Polling Delay
    SetReaderMode(comms, "Hitag H1/S")
    readerModeVariable.set(MODEOPTIONS[1]) # default value
    pollDelayVar.set(POLLOPTIONS[3]) # default value
    SetPollingDelay(comms, "262ms")
    if settingUp == None:
        textBox.delete("1.0", END)
    return


#4._______________________________HELPER FUNCTIONS

def WaitForCTS():
    # continually monitor the selected GPIO pin and wait for the line to go low
    # CTS is implemented via the use of the GPIO as the UART on the Pi dosen't have any control lines.
    # print ("Waiting for CTS")     # Added for debug purposes
    while wiringpi2.digitalRead(CTS_PIN):
        time.sleep(0.001)
    return


def RFIDSetup(mode=None):
    response = wiringpi2.wiringPiSetup()
    
    if mode == "single":
        wiringpi2.pinMode(GPIO_PIN, 0)
    elif mode == "multi":
        wiringpi2.pinMode(GPIO_PIN_A, 1) # SET UP EXTENSION ANTENNAE by setting both 'hi'
        wiringpi2.pinMode(GPIO_PIN_B, 1)
        wiringpi2.digitalWrite(GPIO_PIN_A, 0) # Set both to 'lo'. From hereon setting one 'hi' enables tag reading
        wiringpi2.digitalWrite(GPIO_PIN_B, 0)
    
    # Open serial port & set speed:
    fd = wiringpi2.serialOpen('/dev/serial0', 9600) # fd = 'file descriptor' 
        # Check your serial configuration with:
        #    ls -al /dev/ | grep serial  
        #    ls -lA /dev/serial/by-id  
            
    wiringpi2.serialFlush(fd)   # clear the serial buffer of any left over data
    
    if response == 0 and fd >0:
        # print ("RFIDSetup: PI setup complete on channel %d" %fd)     # Added for debug purposes
        return fd
    else:
        errmsg = "Unable to Setup communications.\nWiringPi setup status is '" + str(response) + "' (expected: 0).\nSerial port is " + str(fd) + " (expected: >0).\nExiting program."
        messagebox.showinfo('ERROR', errmsg)
        sys.exit()


def ReadText(fd):
    # read the data back from the serial line and return it as a string to the calling function
    qtydata = wiringpi2.serialDataAvail(fd)
    # print ("ReadText: Amount of data: %d bytes" % qtydata)   # Added for debug purposes
    response = ""
    while qtydata > 0:	# while there is data to be read, read it back
        # print ("ReadText: Reading data back %d" % qtydata)   #Added for Debug purposes
        response = response + chr(wiringpi2.serialGetchar(fd))
        qtydata = qtydata - 1   
    return response


def ReadInt(fd):
    # read a single character back from the serial line
    WaitForCTS()
    qtydata = wiringpi2.serialDataAvail(fd)
    time.sleep(0.05) # interrupt to avoid erroneous read failures
    # print ("ReadInt: Amount of data: %s bytes" % qtydata)    # Added for debug purposes
    
    response = 0
    if qtydata > 0:
        # print ("ReadInt: Reading data back %d" % qtydata)   #Added for Debug purposes
        response = wiringpi2.serialGetchar(fd)
        time.sleep(0.01)
    return response


def CaptureDataToWrite(qty):	# provide an additional menu to capture the data to be written to the tag, return the bytes to be written
    to_write = []
    choice = ""
    counter = 0

    while (counter < qty):
        # Loop round getting, checking and saving the byte, prompting the user for a choice
        choice = simpledialog.askstring(title="INPUT", prompt="Please enter byte %d to write (0 - 255).....:" % counter)
        try:
            # print ("CaptureDataToWrite: Values read:%d" % int(choice))            # added for debug purposes
            if int(choice) > 0 and int(choice) < 255:
                to_write.append(int(choice))
                counter = counter + 1
                # print("CaptureDataToWrite: Value Captured")           # added for debug purposes
            else:
                messagebox.showinfo(title='ERROR', message='Please ensure the number is between 0 and 255')
        except:
            messagebox.showinfo(title='ERROR', message='Please ensure you enter a number between 0 and 255')
            
    # print ("CaptureDataToWrite: data caltured:%s" % to_write)  # Added for Debug purposes
    return to_write


def printText(ans, page, printType):        # Construct output string
    if printType == "page":
        result = "\nPage " + str(page)
    else:
        result = "\nBlock " + str(page)

    textBox.insert(END, result)
    
    result2 = "\n--> %s" % ans
    textBox.insert(END, result2) 
    textBox.insert(END, " <--\n")

    result3 = "++> "
    for f in ans:
        result3 += str(ord(f))
        result3 += " "
    result3 += "<++\n"
    textBox.insert(END, result3)
    return


def antennaSetupCheck(antennaSetup, allowedMode):
    if antennaSetup != allowedMode:
        message = "This functionality can only be used with a " + allowedMode + " antenna setup."
        messagebox.showinfo(title='ATTENTION', message=message)
        return "fail"
    else:
        return "pass"
        

#5._______________________________GUI FUNCTION BUTTON CONFIGURATION
# Without lambda functions program will perform functions at startup and crash.

firmwareButton = Button(window,text='Display firmware version information', command=lambda:ReadVersion(comms)) 
acknowledgeTagButton = Button(window, text='Acknowledge the presence of Tag', command=lambda:AcknowledgeTagPresence(comms))
# SET POLLING DELAY   -- SEE BELOW SECTION
# SELECT READER MODE  -- SEE BELOW SECTION
readPageButton = Button(window, text='Read PAGE of data from Tag', command=lambda:ReadPage(comms))
readBlockButton = Button(window, text='Read BLOCK of data from Tag', command=lambda:ReadBlock(comms))
writePageButton = Button(window, text='Write PAGE of data to Tag', command=lambda:WritePage(comms))
writeBlockButton = Button(window, text='Write BLOCK of data to Tag', command=lambda:WriteBlock(comms)) 
readAllPagesButton = Button(window, text='Read All Pages', command=lambda:ReadAllPages(comms))
readAllBlocksButton = Button(window, text='Read All Blocks', command=lambda:ReadAllBlocks(comms))
multiAntennaActivation = Button(window, text='Begin Multi Antenna Reading', command=lambda:BeginMultiAntennaRead(comms))
factoryResetButton = Button(window, text='Perform a Factory Reset', command=lambda:FactoryReset(comms))


#6._______________________________BUTTON GRAPHICAL CONFIGURATION (GRID)

firmwareButton.grid(column=1, row=1, columnspan = 2)
acknowledgeTagButton.grid(column=1, row=2, columnspan = 2)
# SET POLLING DELAY   -- SEE BELOW SECTION
# SELECT READER MODE  -- SEE BELOW SECTION
readPageButton.grid(column=1, row=5, columnspan = 2)
readBlockButton.grid(column=1, row=6, pady=(0,10), columnspan = 2)
writePageButton.grid(column=1, row=7, columnspan = 2)
writeBlockButton.grid(column=1, row=8, pady=(0,10), columnspan = 2)
readAllPagesButton.grid(column=1, row=9, columnspan = 2)
readAllBlocksButton.grid(column=1, row=10, pady=(0,15), columnspan = 2)
multiAntennaActivation.grid(column=1, row=11, pady=(0,15), columnspan=2)
factoryResetButton.grid(column=1, row=12, columnspan = 2)


#7._____________________________________READERMODE LABEL & DROPDOWN MENU CONFIGURATION

MODEOPTIONS = ["Hitag H2", "Hitag H1/S", "EM/MC2000"]
readerModeVariable = StringVar(window)
readerModeVariable.set(MODEOPTIONS[1]) # default value

# Construct Label and Dropdown Menu for changing Tag Reader Mode
modevar = StringVar()
modevar.set("Set Reader Mode:")
readerModeLabel = Label(window, textvariable=modevar, width='15', font=('arial', 12), foreground = '#009900')
readerModeLabel.grid(column=1,row=4)

# EXAMPLE SYNTAX: menuObject = OptionMenu(PARENT WINDOW, VALUE TO BE CHANGED, "DEFAULT TEXT", * OPTIONS ARRAY/LIST)
selectReaderModeMenu = OptionMenu(window, readerModeVariable, MODEOPTIONS[1], *MODEOPTIONS, command=lambda _:SetReaderMode(comms, readerModeVariable.get() ) )
selectReaderModeMenu.grid(column=2,row=4)


#8. _______________________________POLLING DELAY MENU CONFIGURATION
POLLOPTIONS = ["NO DELAY", "20ms", "65ms", "262ms", "1s", "4s"]

pollDelayVar = StringVar(window)
pollDelayVar.set(POLLOPTIONS[3]) # default value = 262ms

# Construct Label and Dropdown Menu for changing Polling Delay
pollText = StringVar()
pollText.set("Set Polling Delay:")
pollDelayLabel = Label(window, textvariable=pollText, width='15', font=('arial', 12), foreground = '#009900')
pollDelayLabel.grid(column=1,row=3)

pollDelayMenu = OptionMenu(window, pollDelayVar, POLLOPTIONS[3], *POLLOPTIONS, command=lambda _:SetPollingDelay(comms, pollDelayVar.get() ) )
pollDelayMenu.grid(column=2,row=3)


#9._______________________________MAIN & GUI TEXT BOX
# Set up text box on right side of GUI
textBox = Text(width='40', wrap='word')
textBox.grid(column=3,row=1,rowspan=12,sticky="NSEW",padx=10,pady=10)

getMode = messagebox.askyesnocancel("MODE", "Are you using a single antenna?\n\nIMPORTANT: You must configure this program to match your GPIO configuration.")
if getMode == None:
    sys.exit()
elif getMode == True:
    antennaSetup = "single" # antennaSetup is a global variable
elif getMode == False:
    messagebox.showinfo(title='MULTI-ANTENNA MODE', message='To begin reading, press "Begin Multi Antenna Reading" button. This program will then read from tags on a loop.')
    antennaSetup = "multi"

comms = RFIDSetup(antennaSetup) 
FactoryReset(comms, "setup") # Reset to ensure Polling/Reader Mode changes are reset on startup 

# Propagate the GUI textbox with text on program startup
message = "RFID Tag Reader 125kHz\nCogniot Products\nPirFlx\n\nThis program and its code is experimental, and is not intended to be used in a production environment. It demonstrates the very basics of what is required to get the Raspberry Pi receiving RFID data and configuring the RFID Reader parameters.\n\nChange the GPIO PIN setup by adjusting settings in this GUI's Python code.\n\nThis program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation as version 2 of the License. For more information refer to www.cogniot.eu"
textBox.delete('1.0', END) 
textBox.insert('end', message)

window.mainloop() # Initiate GUI program