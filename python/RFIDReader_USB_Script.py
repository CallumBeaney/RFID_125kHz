import serial
import time
import binascii
import sys


def RFIDSetup():
    # You may need to configure the below .Serial() function based on your setup
    fd = serial.Serial('/dev/ttyUSB0', 9600, rtscts=True) 
    fd.reset_input_buffer()
    if fd.is_open:
        print("RFIDSetup: PI setup complete on channel %s" %fd)     # Added for debug purposes
    else:
        print("Unable to Setup communications.")
        sys.exit()
        
    return fd


def ReadText(fd):
    # read the data back from the serial line and return it as a string to the calling function
    response = ""
    while fd.inWaiting():
        # while there is data to be read, read it back
        # print("Reading data back %d" % qtydata)   #Added for Debug purposes
        response = response + chr(fd.read().decode())
    return response

def ReadInt(fd):
    qtydata = fd.in_waiting
    time.sleep(0.3)
    qtydata = fd.in_waiting
    
    response = 0
    if (qtydata > 0):
        response_bytes = fd.read()
        response = int.from_bytes(response_bytes, byteorder='big')
        # read a single character back from the serial line
        time.sleep(0.3) # Use interrupt to avoid erroneous read failures
    return response


def ReadPageWithTimeout(fd, page=None):
    
    if page is None:
        page = CaptureBlockPageNo('read')
    
    timeout = 2
    start_time = time.time()

    notag = True
    # print ("Reading Tag Data Page %d......." % page)
    # print ("Waiting for a tag ....")
    while notag:
        WaitForCTS(fd)
        # print ("Sending Tag Read Page Command")    #Added for Debug purposes
        fd.write(bytes([0x52]))
        fd.write(bytes([page]))
        time.sleep(0.05)
        ans = ReadInt(fd)
        # print ("Tag Status: %s" % hex(ans))    #Added for Debug purposes
        if (time.time() - start_time) > timeout:
            print("timeout\n")
            return "timeout"
        if ans != int("0xD6", 16):
            # print ("Tag Status: %s" % hex(ans))    #Added for Debug purposes
            fd.reset_input_buffer()
            continue    
        else:
            notag = False	# Tag present and read
            ans = ReadText(fd)
            print ("\nPage %d" % page)
            print ("-->%s<--" % ans)
            print("++>", end="")
            for f in ans:
                print(" %d" % ord(f), end="")
            print(" <++")
            return ans


def ReadTagStatus(fd):
    # read the RFID reader until a tag is present
    notag = True
    while notag:
        WaitForCTS(fd)
        # print ("Sending Tag Status Command")   #Added for Debug purposes
        fd.write(b'S')
        time.sleep(0.1)
        ans = ReadInt(fd)
        print ("Tag Status: %s (expected: D6)" % hex(ans))
        if ans == int("0xD6", 16):
            # D6 is a positive response meaning tag present and read
            notag = False
#     print ("Tag Status: %s (expected: D6)" % hex(ans))
    return


def ReadTagPageDefaultZero(fd, page=0):
    # read the tag page 00 command
    notag = True

    print ("\nReading Tag Data Page %d......." % page)
    print ("\nWaiting for a tag ....")

    notag = True
    while notag:
        WaitForCTS(fd)
        # print ("Sending Tag Read Page Command")    #Added for Debug purposes
        fd.write(bytes([0x52, page]))
        time.sleep(0.1)
        ans = ReadInt(fd)
        # print ("Tag Status: %s" % hex(ans))    #Added for Debug purposes
        if ans == int("0xD6", 16):
            # Tag present and read
            notag = False
            # print ("Tag Present") #Added for Debug purposes
            ans = ReadText(fd)
            print ("\nPage %d" % page)
            print ("-->%s<--" % ans)
            print("++>", end="")
            for f in ans:
                print(" %d" % ord(f), end="")
            print(" <++")
        elif ans == int("0xD2", 16):
            # Tag page doesn't exist
            # Return ans to break out of the ReadAllPages() calling loop.
            print("Page %s does not exist." % page)
            return ans
        else:
            # ans is likely a failed read = C0
            print("Failed to read data from the serial line.\nError Code: %s (expected: D6)\n" % hex(ans))
    return

def TestMode(fd):
    """ Routine to check the RFID module works
    Runs the following checks
    - Press any key to continue
    - Verify board type
    - Select tag mode A
        - Check tag range
    - Repeat for modes B and C
    - Set to default mode C
        - any key to change """
    key = input("\nHit ENTER to Start test ...")
    #ReadVersion(fd)
    for modes in ("B","C"):
        print("Present tag of mode %s" % modes)
        SetReaderMode(fd,modes)
        TagPresent(fd)
    key = input("\nHit ENTER to set back to default mode,\n else press A,B or C & Enter to set specific mode")
    if key.upper() in ("A","B","C"):
        print("\nSetting Mode :%s\n" % key.upper())
        FactoryReset(fd)
        SetReaderMode(fd,key.upper())
    else:
        print("\nSetting Default (C) Mode\n")
        FactoryReset(fd)
        SetReaderMode(fd,"C")
    return


def ReadAllBlocks(fd):
    #read through all the blocks
    print("Reading all blocks")
    for f in range(0, 16):
        ReadTagAndBlocks(fd, f, False)
    return


def ReadAllPages(fd):
    # Cycle through and read all pages available

    print("Reading all Pages...")
    for f in range(0, 0x3f):
        ans = ReadPageWithTimeout(fd, f)
        # print("\nReadAllPages: Reading Page:" + str(f) + "\nResult: " + str(ans))
        if ans == "0xD2":
            print('Successfully read all Pages on this tag.')
            break
        if ans != "0xD6":
            print("Page " + str(f) + "\nTimeout -- Unable to read this page.")



def UserChangeReaderOpMode(fd):
    # provide an additional menu to choose the type of tag to be read and set the reader accordingly
    print("Setting Reader Operating Tag Mode.......\n")

    choice = ""
    print("*********************************************")
    print("a - Hitag H2")
    print("b - Hitag H1/S (factory default)")
    print("c - EM/MC2000\n\n")
    # prompt the user for a choice
    choice = input("Please select tag type .....:")
    # print("choice: %s" % choice)  # Added for Debug purposes

    SetReaderMode(fd, choice)
    return

def SetReaderMode(fd, choice):
    # Given the mode choice, set the mode
    desc = ""
    if choice =="a" or choice == "A":
        desc = "Hitag H2"
        WaitForCTS(fd)
        fd.write(bytes([0x76]))
        fd.write(bytes([0x01])) # 0x01 = H2
    elif choice =="b" or choice == "B":
        desc = "Hitag H1/S"
        WaitForCTS(fd)
        fd.write(bytes([0x76]))
        fd.write(bytes([0x02])) # 0x02 = H1/S
    elif choice =="c" or choice == "C":
        desc = "Em / MC2000"
        WaitForCTS(fd)
        fd.write(bytes([0x76]))
        fd.write(bytes([0x03])) # 0x03 = EM/MC2000
    else:
        print("Invalid option.\n")
        choice = ""
        return

    time.sleep(0.1)
    ans = ReadInt(fd)
    print("Tag Status: %s" % ans) #Added for Debug purposes
#     print(int("0xC0", 16))
    if ans == int("0xC0", 16):
        # Positive result
        print("Reader Operating Mode %s ......" % desc)
    else:
        print("Unexpected response: %s" % ans)
        # clear the buffer
        fd.reset_input_buffer()
    return

def WaitForCTS(fd):
    # Wait for Clear to Send (CTS) signal to go high
    while True:
        if fd.getCTS():
            break
        time.sleep(0.01)
        
def ReadVersion(fd):
    # read the version from the RFID board
    WaitForCTS(fd)
    # print("Sending Read Version Command")  # Added for Debug purposes
    fd.write(b'z')
    time.sleep(0.1)
    ans = ReadText(fd)
    print("Response: %s" % ans)
        

def SetPollingDelay(fd):
    
    print("Setting Reader Operating Tag Mode.......\n")
    print("*********************************************")
    print ("a - no delay")
    print ("b - 20ms")
    print ("c - 65ms")
    print ("d - 262ms")
    print ("e - 1 second") 
    print ("f - 4 seconds")
    
    choice = input ("Select delay: ")
    
    WaitForCTS(fd)
    fd.write(bytes([0x50, 0x00]))

    if choice == "a":
        fd.write(bytes([0x00])) # 0x00 is no delay
    elif choice == "b":
        fd.write(bytes([0x20])) # 0x20 is approx 20ms
    elif choice == "c":
        fd.write(bytes([0x40])) # 0x40 is approx 65ms
    elif choice == "d":
        fd.write(bytes([0x60])) # 0x60 is approx 262ms
    elif choice == "e":
        fd.write(bytes([0x80])) # 0x80 is approx 1 Seconds
    elif choice == "f":
        fd.write(bytes([0xA0])) # 0xA0 is approx 4 Seconds
    else:
        printf('Error: input argument invalid. Setting to 65ms...')
        fd.write(bytes([0x40])) # 0x40 is approx 65ms

    time.sleep(0.1)
    ans = ReadInt(fd)
    if ans == int("0xC0", 16): # C0 is a positive result
        print('Polling delay changed.')
    else:
        print('Unexpected response: %s \nPolling delay could not be changed.' % hex(ans))
        serial_port.reset_input_buffer() # flush any remaining characters from the buffer
    return


def ReadTagAndBlocks(fd, block=4, enter=False):
    # read the tag and all blocks from within it
    # Only works for H1/S as other tags don't support it
        
    notag = True

    if enter:
        # enter flag determines if user is prompted for an entry
        block = CaptureBlockPageNo('read')
    
    print ("\nReading Tag Data Block %x ......." % block)

    print ("\nWaiting for a tag ....")

    notag = True
    while notag:
        WaitForCTS(serial_port)
        # print ("Sending Tag Read Blocks command")  #Added for Debug purposes
        fd.write(bytes([0x72, block]))
        time.sleep(0.1)
        ans = ReadInt(fd)
        # print ("Tag Status: %s" % hex(ans))    #Added for Debug purposes
        if ans == int("0xD6", 16):
            # Tag present and read
            notag = False
            #print ("Tag Present")  #Added for Debug purposes
            ans = ReadText(fd)
            print ("\nBlocks %x" % block)
            print ("-->%s<--" % ans)
            print("++>", end="")
            for f in ans:
                print(" %d" % ord(f), end="")
            print(" <++")
        elif ans == int("0xD2", 16):
            # Tag page doesn't exist
            # Return ans to break out of the ReadAllPages() calling loop.
            print("Page %s does not exist." % block)
            return ans
        else:
            # ans is likely a failed read = C0
            print("Failed to read data from the serial line.\nError Code: %s (expected: D6)\n" % hex(ans))
    
    return


def CaptureBlockPageNo(mode):
    # provide an additional menu to capture the block or page number
    # returns the block / page to be written
    to_write = 0
    choice = ""
    success = False 
    print("*********************************************")
    while not success:
        # Loop round getting, checking and saving the byte
        # promt the user for a choice
        choice = input("Please enter block / page to " + mode + "....:")
        try:
            # value entered is a number, so process it
            # print ("Value read:%d" % int(choice))  # added for debug purposes
            if int(choice) >= 0 and int(choice) < 255:
                to_write = int(choice)
                success = True
                # print("Value Captured")  # added for debug purposes
            else:
                print("Please ensure the number is between 0 and 255")
        except:
            print("Please ensure you enter a number between 0 and 255")

    # print("data captured:%s" % to_write)  # Added for Debug purposes

    return to_write


def WriteTagPage(fd):
    # write to the tag page, user selecting the page
    notag = True
    block = []
    pagesize = 4

    page = CaptureBlockPageNo('write')
    block = CaptureDataToWrite(pagesize)

    print ("\nWriting Tag Data Page %s......." % page)
    
    #print("Data to write:%s" % block)         #Added for Debug purposes
    
    print ("\nWaiting for a tag ....")

    notag = True
    while notag:
        WaitForCTS(fd)
        #print ("Sending Tag Write Page Command")    #Added for Debug purposes
        fd.write(bytes([0x57]))
        fd.write(bytes([page]))           # Write to page four
        fd.write(bytes(block))
        time.sleep(0.1)
        ans = ReadInt(fd)
        #print ("Tag Status: %s" % hex(ans))    #Added for Debug purposes
        if ans == int("0xD6", 16):
            # Tag present and read
            notag = False
            #print ("Tag Present") #Added for Debug purposes
            ReadTagPage(fd,page)
    return


def WriteTagAndBlocks(fd):
    # write the tag and all blocks from within it
    # Only works for H1/S as other tags don't support it
    notag = True
    block = []
    blockno = 0
    blocksize = 16

    blockno = CaptureBlockPageNo('write')
    block = CaptureDataToWrite(blocksize)

    print ("\nWriting Tag Data Block %d ......." % blockno)

    # print("Data to write:%s" % block)         #Added for Debug purposes

    print ("\nWaiting for a tag ....")

    notag = True
    while notag:
        WaitForCTS(fd)
        #print ("Sending Tag Write Blocks command and data")  #Added for Debug purposes
        fd.write(bytes([0x72]))
        fd.write(bytes([blockno]))
        for f in block:
            fd.write(bytes([f]))
        time.sleep(0.1)
        ans = ReadInt(fd)
        #print ("Tag Status: %s" % hex(ans))    #Added for Debug purposes
        if ans == int("0xD6", 16):
            # Tag present and read
            notag = False
            #print ("Tag Present")  #Added for Debug purposes
            ans = ReadText(fd)

            ReadTagAndBlocks(fd, blockno, False)
    return




def CaptureDataToWrite(qty):
    # provide an additional menu to capture the data to be written to the tag
    # returns the bytes to be written
    
    to_write = []
    choice = ""
    counter = 0
    print ("*********************************************")
    print ("Please enter %d bytes of data to be written" % qty)

    while (counter < qty):
        # Loop round getting, checking and saving the byte
        # promt the user for a choice
        choice = input("Please enter byte %d to write (0 - 255).....:" % counter)
        try:
            # value entered is a number, so process it
            # print ("Values read:%d" % int(choice))            # added for debug purposes
            if int(choice) > 0 and int(choice) < 255:
                to_write.append(int(choice))
                counter = counter + 1
                # print("Value Captured")           # added for debug purposes
            else:
                print("Please ensure the number is between 0 and 255")
        except:
            print("Please ensure you enter a number between 0 and 255")

    # print ("data caltured:%s" % to_write)  # Added for Debug purposes
    return to_write





def FactoryReset(fd):
    # send the factory reset command
    WaitForCTS(fd)
    # print("Performing a factory reset ....") #Added for Debug purposes
    fd.write(bytes([0x46, 0x55, 0xAA]))
    time.sleep(0.1)
    # print("FACTORY RESET COMPLETE ")
    print("Reader Mode reset to: Hitag H1/S\nPolling Delay reset to: 262ms\n")
    return




def HelpText():
    # show the help text
    print ("**************************************************************************\n")
    print ("Available commands: -") 
    print ("z - Display firmware version information")
    print ("S - Acknowledge presence of Tag")
    print ("F - Perform a Factory Reset")
    print ("P - Program EEPROM Polling delay")
    print ("v - Select reader operating mode") 
    print ("R - Read Tag and PAGE 00 data")
    print ("r - Read Tag and BLOCK 04 data")
    print ("W - Write Tag and PAGE of data")
    print ("w - Write Tag and BLOCK of data")
    print ("A - Read All Pages 0 - 3f")
    print ("a - Read All blocks 0 - 16")
    print ("T - Test Mode")
    print ("e - Exit program\n\n")


# main loop

comms = RFIDSetup()

HelpText()

while True:
    choice = input ("Select Menu Option:")

    if choice == "H" or choice == "h":
        HelpText()
    elif choice == "z":
        ReadVersion(comms)
    elif choice == "S":
        ReadTagStatus(comms)
    elif choice == "F":
        FactoryReset(comms)
    elif choice == "P":
        SetPollingDelay(comms)
    elif choice == "v":
        UserChangeReaderOpMode(comms)
    elif choice == "R":
        # ReadPageWithTimeout(comms)
        ReadTagPageDefaultZero(comms)
    elif choice == "r":
        ReadTagAndBlocks(comms)
    elif choice == "W":
        WriteTagPage(comms)
    elif choice == "w":
        WriteTagAndBlocks(comms)
    elif choice == "A":
        ReadAllPages(comms)
    elif choice == "a":
        ReadAllBlocks(comms)
    elif choice == "T":
        TestMode(comms)
    elif choice == "E" or choice == "e":
        sys.exit()
