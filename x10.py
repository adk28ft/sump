#####################################################################
# X10 Modules to send commands to the mochad
#####################################################################
#
# Module x10;  Simple module to send X10 command over the socket
#
#  Example commands:  pl a1 on
#                     pl a1 off
#
#                     rf a1 on
#                     rf a1 off
#
import socket
import sys

host = '127.0.0.1'
port = 1099

#####################################################################
# Function: send_cmd will push a command notification to the X10
#           controller
#####################################################################
def send_cmd(cmd):
   print 'connect host=',host,' port=',port
   try:
      s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      s.connect((host,port))
      s.send(cmd)
      s.send('\n')
      s.close()
   except:
      e = sys.exc_info()[0]
      print e
   
   
#####################################################################
# Main entry point for the test application
#####################################################################
def main():
   send_cmd('pl a5 on')
   print 'press enter to continue'
   raw_input()
   send_cmd('pl a5 off')
   print 'program complete'
   
if __name__ == '__main__':
   print 'Main Function Start'
   main()
   print 'Main Function End'
